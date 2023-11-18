import importlib.resources
import logging
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from time import sleep
from typing import Any

from requests_cache import CachedSession

from ausmash.exceptions import RateLimitError, StartGGError
from ausmash.settings import AusmashAPISettings
from ausmash.typedefs import JSON

from .api import get_user_agent

logger = logging.getLogger(__name__)

__queries = importlib.resources.files('ausmash.startgg_queries')
_settings = AusmashAPISettings()
endpoint = 'https://api.start.gg/gql/alpha'
__minute = timedelta(minutes=1)
RATE_LIMIT_MINUTE = 80


class _SessionSingleton:
	"""Keep track of our cached session and also how many requests have been sent"""

	__instance = None

	def __init__(self) -> None:
		self._inited: bool
		if self._inited:
			return
		self._inited = True

		self.sesh = CachedSession(
			'startgg',
			'filesystem',
			use_cache_dir=True,
			decode_content=True,
			allowable_methods=['GET', 'POST'],
			headers={'User-Agent': get_user_agent()},
		)
		self.last_sent: datetime | None = None
		self.requests_per_minute = 0

		if _settings.startgg_api_key:
			# Well, good luck without it… I suppose if you have cache it'd work
			self.sesh.headers['Authorization'] = f'Bearer {_settings.startgg_api_key}'

	def __new__(cls: type['_SessionSingleton']) -> '_SessionSingleton':
		if not cls.__instance:
			cls.__instance = super().__new__(cls)
			cls.__instance._inited = False
		return cls.__instance


def has_startgg_api_key() -> bool:
	return _settings.startgg_api_key is not None


def __call_api(query_name: str, variables: Mapping[str, Any] | None) -> JSON:
	ss = _SessionSingleton()
	body: dict[str, Any] = {
		'query': __queries.joinpath(f'{query_name}.gql').read_text('utf-8')
	}
	if variables:
		body['variables'] = variables
	response = ss.sesh.post(endpoint, json=body, timeout=10)
	if not response.from_cache:
		if ss.last_sent is None or (datetime.now() - ss.last_sent) >= __minute:
			ss.requests_per_minute = 0

		ss.last_sent = datetime.now()
		ss.requests_per_minute += 1

		if ss.requests_per_minute + 1 > RATE_LIMIT_MINUTE:
			# To play it safe here, assume we're going to send another uncached request, which would hit the rate limit
			if _settings.sleep_on_rate_limit:
				logger.warning('Sleeping for 1 minute to avoid start.gg rate limit')
				sleep(__minute.total_seconds())
			else:
				raise RateLimitError(RATE_LIMIT_MINUTE, 'minute')

	response.raise_for_status()  # It returns 200 on errors, but just in case it ever doesn't
	j = response.json()
	if 'errors' in j:
		raise StartGGError(j['errors'])
	return j['data']


def get_event_entrants(
	tournament_slug: str, event_slug: str
) -> Sequence[Mapping[str, JSON]]:
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


def get_tournament_location(tournament_slug: str) -> Mapping[str, JSON] | None:
	result = __call_api('GetTournamentLocation', {'slug': tournament_slug})
	if not result:
		# e.g. if tournament does not exist
		return None
	return result['tournament']


def get_player_pronouns(player_id: int) -> str | None:
	player = __call_api('GetPlayerPronouns', {'id': player_id})['player']
	if not player:
		# Might happen if ID isn't found?
		return None
	user = player['user']
	if not user:
		return None
	pronouns: str | None = user['genderPronoun']
	return pronouns
