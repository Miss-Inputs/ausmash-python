# ausmash-python
Python wrapper for Ausmash API

Wraps the API for [Ausmash](https://ausmash.com.au/), with type hints and automatic rate limit respecting and other nice things.  

You will need to provide your own API key, see AusmashAPISettings or [Pydantic docs](https://docs.pydantic.dev/usage/settings/) for configuring it: Set the ausmash_api_key environment variable, or you should be able to do:
```
from ausmash.settings import AusmashAPISettings
settings
```


More to come, I'm bad at readmes
