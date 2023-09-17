
from datetime import timedelta
from pydantic import Field

from pydantic_settings import BaseSettings

class AusmashAPISettings(BaseSettings):
	"""Set your API key in here before using anything else!"""
	api_key: str | None = None
	endpoint: str = 'https://api.ausmash.com.au'
	cache_timeout: timedelta | None = timedelta(days=2)
	#TODO: Different cache timeouts for different URL prefixes, /elo should be days=7 (probably) and /games and /regions should be a long time (though the latter may have new cities added)
	sleep_on_rate_limit: bool = True #Set to false if you just want to raise an error instead, I guess
	startgg_api_key: str | None = Field(default=None, alias='startgg_api_key')

	class Config:
		"""Pylint, quit bugging me to put a docstring in here, it's for Pydantic to use"""
		env_prefix = 'ausmash_'
		env_file = '.env'
		env_file_encoding = 'utf-8'
