import json
import logging
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path
from time import sleep

import requests

from ausmash.exceptions import NotFoundError, RateLimitException

from .settings import AusmashAPISettings
from .typedefs import JSON, URL

_settings = AusmashAPISettings()

__second = timedelta(seconds=1)
__minute = timedelta(minutes=1)
__hour = timedelta(hours=1)

logger = logging.getLogger(__name__)

RATE_LIMIT_SECOND = 200
RATE_LIMIT_MINUTE = 5000
RATE_LIMIT_HOUR = 300000
RATE_LIMIT_DAY = 8000000 #Probably we won't have to think _this_ far ahead
RATE_LIMIT_WEEK = 40000000

class _SessionSingleton():
	"""Share a single session for all API requests (presumably that will work and also improve performance), also keep track of how many requests are sent within a certain timeframe so that we don't go over the limit"""
	__instance = None

	def __init__(self) -> None:
		self._inited: bool
		if self._inited:
			return
		self._inited = True
		self.sesh = requests.session()
		self.last_sent: datetime | None = None
		self.requests_per_second = 0
		self.requests_per_minute = 0
		self.requests_per_hour = 0
		
		if _settings.api_key:
			#Well, good luck without it… I suppose if you have cache it'd work
			self.sesh.headers['X-ApiKey'] = _settings.api_key

	def __new__(cls: type['_SessionSingleton']) -> '_SessionSingleton':
		if not cls.__instance:
			cls.__instance = super(_SessionSingleton, cls).__new__(cls)
			cls.__instance._inited = False
		return cls.__instance

#TODO: Should try and make this portable, but making this work on Windows etc is not a priority because you can just not do that
__cache_dir = Path('~/.cache/ausmash').expanduser()

@cache
def _call_api(url: URL, params: tuple[tuple[str, str]] | None) -> JSON:
	cache_filename = __cache_dir/url.removeprefix(AusmashAPISettings().endpoint).removeprefix('/')
	if params:
		cache_filename = cache_filename.joinpath('&'.join(f'{k}={v}' for k, v in params))
	cache_filename = cache_filename.with_suffix('.json')
	try:
		cache_time = datetime.utcfromtimestamp(cache_filename.stat().st_mtime)
		cache_age = datetime.utcnow() - cache_time
		if not _settings.cache_timeout or cache_age < _settings.cache_timeout:
			return json.loads(cache_filename.read_bytes())
			
		cache_filename.unlink(missing_ok=True)
		for parent in cache_filename.parents:
			if parent == __cache_dir:
				break
			try:
				parent.rmdir()
			except OSError:
				pass
	except FileNotFoundError:
		pass

	sesh = _SessionSingleton()

	last_sent = sesh.last_sent
	if last_sent is None or (datetime.now() - last_sent) >= __second:
		sesh.requests_per_second = 0
	sesh.requests_per_second += 1
	if sesh.requests_per_second == RATE_LIMIT_SECOND:
		if _settings.sleep_on_rate_limit:
			logger.warning('Sleeping for 1 second to avoid rate limit')
			sleep(__second.total_seconds())
		else:
			raise RateLimitException(RATE_LIMIT_SECOND, 'second')

	if last_sent is None or (datetime.now() - last_sent) >= __minute:
		sesh.requests_per_minute = 0
	sesh.requests_per_minute += 1
	if sesh.requests_per_minute == RATE_LIMIT_MINUTE:
		if _settings.sleep_on_rate_limit:
			logger.warning('Sleeping for 1 minute to avoid rate limit')
			sleep(__minute.total_seconds())
		else:
			raise RateLimitException(RATE_LIMIT_MINUTE, 'minute')

	if last_sent is None or (datetime.now() - last_sent) >= __hour:
		sesh.requests_per_hour = 0
	sesh.requests_per_hour += 1
	if sesh.requests_per_hour == RATE_LIMIT_HOUR:
		if _settings.sleep_on_rate_limit:
			logger.warning('Sleeping for 1 hour to avoid rate limit, ggs')
			sleep(__hour.total_seconds())
		else:
			raise RateLimitException(RATE_LIMIT_HOUR, 'hour')

	response = sesh.sesh.get(url, params=params)
	sesh.last_sent = datetime.now()
	if response.status_code == 404:
		raise NotFoundError(response.reason)
	response.raise_for_status()
	cache_filename.parent.mkdir(parents=True, exist_ok=True)
	cache_filename.write_bytes(response.content)
	return response.json()

def call_api(url: str, params: Mapping[str, str | date] | None = None) -> JSON:
	"""Calls an API request on the Ausmash endpoint, reusing the same session
	If provided a complete URL it will use that, otherwise it will append the URL fragment to the endpoint (the former is useful for APILink fields)"""
	endpoint = _settings.endpoint
	if not url.startswith(endpoint):
		url = endpoint + url if url[0] == '/' else f'{endpoint}/{url}'
	return _call_api(url, tuple((k, v.isoformat() if isinstance(v, date) else v) for k, v in params.items()) if params else None)
