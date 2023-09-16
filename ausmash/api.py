import logging
from collections.abc import Iterable, Iterator, Mapping
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path
from time import sleep
from urllib.parse import unquote_plus

from requests import Response
from requests_cache import (EXPIRE_IMMEDIATELY, CachedSession, FileCache,
                            FileDict)
from requests_cache.backends.sqlite import AnyPath
from requests_cache.models import AnyRequest
from requests_cache.serializers import SerializerType

from .exceptions import NotFoundError, RateLimitException
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

def _hax_content_type(r: Response, **_):
	"""requests-cache hardcodes "application/json" without a startswith, so it won't decode the "application/json; charset=utf-8"""
	r.headers['Content-Type'] = 'application/json'
	return r

class _FileCacheWithDirectories(FileCache):
	"""Like requests_cache filesystem backend, but puts files in subdirectories"""
	def __init__(self, cache_name: AnyPath = 'http_cache', use_temp: bool = False, decode_content: bool = True, serializer: SerializerType | None = None, **kwargs):
		super().__init__(cache_name, use_temp, decode_content, serializer, **kwargs)
		skwargs = {'serializer': serializer, **kwargs} if serializer else kwargs
		self.responses: _FileDictWithDirectories = _FileDictWithDirectories(cache_name, use_temp=use_temp, decode_content=decode_content, **skwargs)

	def create_key(self, request: AnyRequest, match_headers: Iterable[str] | None = None, **kwargs) -> str:
		url = request.url.split('://', 1)[1]
		url = url.split('/', 1)[1] #Don't need hostname here
		url = url.replace('?', '/')
		return unquote_plus(url)

class _FileDictWithDirectories(FileDict):
	def _path(self, key) -> Path:
		return self.cache_dir.joinpath(key).with_suffix(self.extension)

	def __setitem__(self, key, value):
		with self._lock:
			self._path(key).parent.mkdir(parents=True, exist_ok=True)
		return super().__setitem__(key, value)
	
	def __delitem__(self, key):
		with self._try_io():
			path = self._path(key)
			path.unlink()
			if path.parent != self.cache_dir and len(list(path.parent.iterdir())) == 0:
				path.parent.rmdir()
		
	def paths(self) -> Iterator[Path]:
		with self._lock:
			return self.cache_dir.rglob(f'*{self.extension}')

class _SessionSingleton():
	"""Share a single session for all API requests (presumably that will work and also improve performance), also keep track of how many requests are sent within a certain timeframe so that we don't go over the limit"""
	__instance = None

	def __init__(self, cache_expiry: timedelta | None = None) -> None:
		self._inited: bool
		if self._inited:
			return
		self._inited = True

		if cache_expiry is None:
			cache_expiry = EXPIRE_IMMEDIATELY if _settings.cache_timeout is None else _settings.cache_timeout
		self.sesh = CachedSession('ausmash', _FileCacheWithDirectories('ausmash', use_cache_dir=True), expire_after=cache_expiry, stale_if_error=True)
		self.sesh.cache.delete(expired=True)
		self.sesh.hooks = {'response': _hax_content_type}
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

@cache
def _call_api(url: URL, params: tuple[tuple[str, str]] | None) -> JSON:
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
	return response.json()

def call_api(url: str, params: Mapping[str, str | date] | None = None) -> JSON:
	"""Calls an API request on the Ausmash endpoint, reusing the same session
	If provided a complete URL it will use that, otherwise it will append the URL fragment to the endpoint (the former is useful for APILink fields)"""
	endpoint = _settings.endpoint
	if not url.startswith(endpoint):
		url = endpoint + url if url[0] == '/' else f'{endpoint}/{url}'
	return _call_api(url, tuple((k, v.isoformat() if isinstance(v, date) else v) for k, v in params.items()) if params else None)
