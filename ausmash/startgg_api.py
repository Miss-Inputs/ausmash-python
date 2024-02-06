import importlib.resources
import logging
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from time import sleep
from typing import Any

import pydantic_core
from requests_cache import CachedSession

from ausmash.exceptions import RateLimitError, StartGGError
from ausmash.models.start_gg_responses import (
	EventEntrant,
	EventEntrantsResponse,
	PlayerPronounsResponse,
	TournamentLocationResponse,
)
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


def __call_api_json(query_name: str, variables: Mapping[str, Any] | None) -> bytes:
	"""Calls the API and returns a JSON byte string"""
	ss = _SessionSingleton()
	body: dict[str, Any] = {'query': __queries.joinpath(f'{query_name}.gql').read_text('utf-8')}
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
	return response.content


def __call_api(query_name: str, variables: Mapping[str, Any] | None) -> JSON:
	"""Calls the API and returns a parsed JSON object (probably a dict). This is why GraphQL is annoying"""
	response = __call_api_json(query_name, variables)
	j = pydantic_core.from_json(response)
	# j also has annoying extra fields like "extensions" and "actionRecords"
	if 'errors' in j:
		raise StartGGError(j['errors'])
	return j['data']


def get_event_entrants(tournament_slug: str, event_slug: str) -> Sequence[EventEntrant]:
	slug = f'tournament/{tournament_slug}/event/{event_slug}'

	entrants = []
	page_num = 1
	while True:
		response = __call_api('GetEventEntrants', {'slug': slug, 'page': page_num})
		page = EventEntrantsResponse.model_validate(response['event']['entrants'])
		entrants += page.nodes
		if page_num >= page.pageInfo.totalPages:
			break
		page_num += 1
	return entrants


def get_tournament_location(tournament_slug: str) -> TournamentLocationResponse | None:
	result = __call_api('GetTournamentLocation', {'slug': tournament_slug})
	if not result:
		# e.g. if tournament does not exist
		return None
	return TournamentLocationResponse.model_validate(result['tournament'])


def get_player_pronouns(player_id: int) -> str | None:
	response = __call_api('GetPlayerPronouns', {'id': player_id})['player']
	if not response:
		# Might happen if ID isn't found?
		return None
	player = PlayerPronounsResponse.model_validate(response)
	user = player.user
	if not user:
		return None
	return user.genderPronoun
