import importlib.resources
from collections.abc import Mapping, Sequence
from typing import Any

from requests_cache import CachedSession
from ausmash.exceptions import StartGGException
from ausmash.settings import AusmashAPISettings
from ausmash.typedefs import JSON

__queries = importlib.resources.files('ausmash.startgg_queries')
_settings = AusmashAPISettings()
endpoint = 'https://api.start.gg/gql/alpha'
_sesh = CachedSession('startgg', 'filesystem', use_cache_dir=True, decode_content=True, allowable_methods=['GET', 'POST'])

def __call_api(query_name: str, variables: Mapping[str, Any]|None) -> JSON:
	body = {
		'query': __queries.joinpath(f'{query_name}.gql').read_text('utf-8')
	}
	if variables:
		body['variables'] = variables
	response = _sesh.post(endpoint, json=body, headers={'Authorization': f'Bearer {_settings.startgg_api_key}'}, timeout=10)
	response.raise_for_status() #It returns 200 on errors, but just in case it ever doesn't
	j = response.json()
	if 'errors' in j:
		raise StartGGException(j['errors'])
	return j['data']

def get_event_entrants(tournament_slug: str, event_slug: str) -> Sequence[Mapping[str, JSON]]:
	slug = f'tournament/{tournament_slug}/event/{event_slug}'

	entrants = []
	page = 1
	while True:
		response = __call_api('GetEventEntrants', {'slug': slug, 'page': page})
		entrants += response['event']['entrants']['nodes']
		if page >= response['event']['entrants']['pageInfo']['totalPages']:
			break
		page += 1
	return entrants

def get_player_pronouns(player_id: int) -> str | None:
	user = __call_api('GetPlayerPronouns', {'id': player_id})['player']['user']
	if not user:
		return None
	return user['genderPronoun']
