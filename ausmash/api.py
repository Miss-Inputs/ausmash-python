import logging
import subprocess
from collections.abc import Iterable, Iterator, Mapping
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Any

from pydantic_core import Url, from_json
from requests_cache import EXPIRE_IMMEDIATELY, CachedSession, FileCache, FileDict

from .exceptions import NotFoundError, RateLimitError
from .settings import AusmashAPISettings
from .version import __version__, get_git_version

if TYPE_CHECKING:
	from requests_cache.models import AnyRequest
	from requests_cache.serializers import SerializerType

_settings = AusmashAPISettings()

__second = timedelta(seconds=1)
__minute = timedelta(minutes=1)
__hour = timedelta(hours=1)

logger = logging.getLogger(__name__)

RATE_LIMIT_SECOND = 200
RATE_LIMIT_MINUTE = 5000
RATE_LIMIT_HOUR = 300000
RATE_LIMIT_DAY = 8000000  # Probably we won't have to think _this_ far ahead
RATE_LIMIT_WEEK = 40000000


class _FileCacheWithDirectories(FileCache):
	"""Like requests_cache filesystem backend, but puts files in subdirectories"""

	def __init__(
		self,
		cache_name='http_cache',
		use_temp: bool = False,  # noqa: FBT001, FBT002 #It's how requests_cache works
		decode_content: bool = True,  # noqa: FBT001, FBT002
		serializer: 'SerializerType | None' = None,
		**kwargs,
	):
		super().__init__(cache_name, use_temp, decode_content, serializer, **kwargs)
		skwargs = {'serializer': serializer, **kwargs} if serializer else kwargs

		self.responses: _FileDictWithDirectories = _FileDictWithDirectories(  # pyright: ignore[reportIncompatibleVariableOverride]
			cache_name, use_temp=use_temp, decode_content=decode_content, **skwargs
		)

	def create_key(
		self, request: 'AnyRequest', match_headers: Iterable[str] | None = None, **_kwargs
	) -> str:
		if not request.url:
			return 'wat'
		url = Url(request.url)
		key = url.path.removeprefix('/') if url.path else (url.host or 'wat')
		if url.query:
			key += f'/{url.query}'
		return key


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


def get_user_agent() -> str:
	try:
		version = get_git_version()
	except subprocess.CalledProcessError:
		version = f'v{__version__}'
	return f'ausmash-python {version}'


# TODO: This should be better reorganized for testability, etc - _SessionSingleton should be something like Client and not a singleton, and there would then be a default_client which is used unless something else sets api.client to something else, and maybe there can be a using_client() context manager


class _SessionSingleton:
	"""Share a single session for all API requests (presumably that will work and also improve performance), also keep track of how many requests are sent within a certain timeframe so that we don't go over the limit"""

	__instance = None

	def __init__(self, cache_expiry: timedelta | int | None = None) -> None:
		self._inited: bool
		if self._inited:
			return
		self._inited = True

		if cache_expiry is None:
			cache_expiry = (
				EXPIRE_IMMEDIATELY if _settings.cache_timeout is None else _settings.cache_timeout
			)
		self.sesh = CachedSession(
			'ausmash',
			_FileCacheWithDirectories('ausmash', use_cache_dir=True),
			expire_after=cache_expiry,
			stale_if_error=True,
			headers={'User-Agent': get_user_agent()},
		)
		# self.sesh.cache.delete(expired=True)
		self.last_sent: datetime | None = None
		self.requests_per_second = 0
		self.requests_per_minute = 0
		self.requests_per_hour = 0

		if _settings.api_key:
			# Well, good luck without it… I suppose if you have cache it'd work
			self.sesh.headers['X-ApiKey'] = _settings.api_key.get_secret_value()

	def set_last_sent(self):
		last_sent = self.last_sent
		if last_sent is None or (datetime.now() - last_sent) >= __second:
			self.requests_per_second = 0
		if last_sent is None or (datetime.now() - last_sent) >= __minute:
			self.requests_per_minute = 0
		if last_sent is None or (datetime.now() - last_sent) >= __hour:
			self.requests_per_hour = 0
		self.last_sent = datetime.now()

	def __new__(cls) -> '_SessionSingleton':
		if not cls.__instance:
			cls.__instance = super().__new__(cls)
			cls.__instance._inited = False
		return cls.__instance


@cache
def _call_api(url: 'Url | str', params: tuple[tuple[str, str]] | None) -> bytes | None:
	ss = _SessionSingleton()

	response = ss.sesh.get(str(url), params=params)
	if not response.from_cache:
		ss.set_last_sent()

		ss.requests_per_second += 1
		if ss.requests_per_second == RATE_LIMIT_SECOND:
			if _settings.sleep_on_rate_limit:
				logger.warning('Sleeping for 1 second to avoid rate limit')
				sleep(__second.total_seconds())
			else:
				raise RateLimitError(RATE_LIMIT_SECOND, 'second')

		ss.requests_per_minute += 1
		if ss.requests_per_minute == RATE_LIMIT_MINUTE:
			if _settings.sleep_on_rate_limit:
				logger.warning('Sleeping for 1 minute to avoid rate limit')
				sleep(__minute.total_seconds())
			else:
				raise RateLimitError(RATE_LIMIT_MINUTE, 'minute')

		ss.requests_per_hour += 1
		if ss.requests_per_hour == RATE_LIMIT_HOUR:
			if _settings.sleep_on_rate_limit:
				logger.warning('Sleeping for 1 hour to avoid rate limit, ggs')
				sleep(__hour.total_seconds())
			else:
				raise RateLimitError(RATE_LIMIT_HOUR, 'hour')

	if response.status_code == 404:
		raise NotFoundError(response.reason)
	response.raise_for_status()
	return response.content


def call_api(url: 'str | Url', params: Mapping[str, str | date] | None = None) -> bytes | None:
	"""Calls an API request on the Ausmash endpoint, reusing the same session
	If provided a complete URL it will use that, otherwise it will append the URL fragment to the endpoint (the former is useful for APILink fields)
	Returns:
		API response as bytes"""
	if isinstance(url, str):
		if '://' in url:
			# Complete URL with host
			url = Url(url)
		else:
			endpoint = _settings.endpoint
			assert endpoint.host, 'Endpoint should have a host'
			if not url.startswith(endpoint.host):
				url = url.removeprefix('/')
				url = f'{endpoint!s}{url}'
	return _call_api(
		url,
		tuple((k, v.isoformat() if isinstance(v, date) else v) for k, v in params.items())
		if params
		else None,
	)


def call_api_json(url: 'str | Url', params: Mapping[str, str | date] | None = None) -> 'Any':
	# We should use JSON as the type hint here, but for now that just generates too much spam
	response = call_api(url, params)
	if response is None:
		return None
	return from_json(response)
