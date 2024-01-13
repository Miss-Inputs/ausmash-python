from datetime import timedelta

from pydantic import AnyUrl, Field, SecretStr
from pydantic_settings import BaseSettings


class AusmashAPISettings(BaseSettings):
	"""Set your API key in here before using anything else!"""

	api_key: SecretStr | None = None
	"""Ausmash API key, if left blank you won't accomplish much"""
	endpoint: AnyUrl = AnyUrl('https://api.ausmash.com.au')
	"""Endpoint for Ausmash API, probably not much reason to change this"""
	cache_timeout: timedelta | None = timedelta(days=2)
	"""Cached data from the Ausmash and start.gg APIs will be cached for this amount of time, or expire immediately if None"""
	# TODO: Different cache timeouts for different URL prefixes, /elo should be days=7 (probably) and /games and /regions should be a long time (though the latter may have new cities added)
	sleep_on_rate_limit: bool = True
	"""Set to false if you just want to raise an error instead, I guess"""
	startgg_api_key: str | None = Field(default=None, alias='startgg_api_key')
	"""API key for start.gg, to enable usage of that"""

	model_config = {'env_prefix': 'ausmash_', 'env_file': '.env', 'env_file_encoding': 'utf-8'}
