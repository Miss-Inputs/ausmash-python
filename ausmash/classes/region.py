from collections.abc import Collection, Mapping
from functools import cached_property
from typing import cast

from ausmash.api import call_api_json
from ausmash.resource import Resource
from ausmash.typedefs import ID, JSONDict


class Region(Resource):
	"""Region where tournaments happen or players reside. May be a state/territory of Australia, or a country outside it
	Note that players can be from anywhere, but tournament data on Ausmash is only for Australia and New Zealand"""
	base_url = 'regions'

	def __init__(self, d: JSONDict | str | ID) -> None:
		"""For convenience, allow using just a short name, which will look up any additional properties automatically"""
		if isinstance(d, str):
			super().__init__({'Short': d})
		else:
			super().__init__(d)

	@classmethod
	def all(cls) -> Collection['Region']:
		"""All regions known to Ausmash, i.e. all states of Australia, ACT, NT, New Zealand, and some other countries where other players who have competed in Australian tournaments live (where whoever added that player to Ausmash would decide what counts as a country and what part of the world counts as which country)"""
		return cls.wrap_many(call_api_json('regions'))
	
	@classmethod
	def all_oceania(cls) -> Collection['Region']:
		"""All states and terrorities of Australia, and the secret far southeast state (New Zealand)"""
		return {r for r in cls.all() if not r.is_international}
	
	@classmethod
	def all_australia(cls) -> Collection['Region']:
		"""All states and terrorities of Australia (that are known by Ausmash)
		Not compliant with section 6 of the constitution!"""
		return {r for r in cls.all() if not r.is_international and r.short_name != 'NZ'}
	
	@classmethod
	def all_international(cls) -> Collection['Region']:
		"""All other countries that are not Australia or New Zealand that are listed on Ausmash"""
		return {r for r in cls.all() if r.is_international}
	
	@classmethod
	def from_name(cls, name: str) -> 'Region':
		"""Returns a Game matching the name given, either full_name or name, or acronym
		:raises KeyError: if no game has that name"""
		all_regions = cls.all()
		for region in all_regions:
			if region.name == name:
				return region
		#Only try by acronym as a fallback, because I dunno
		for region in all_regions:
			if region.short_name == name:
				return region
		raise KeyError(name)

	@classmethod
	def as_dict(cls) -> Mapping[str, 'Region']:
		"""Returns all games as a mapping with the short name as the key"""
		return {region.short_name: region for region in cls.all()}

	@property
	def name(self) -> str:
		"""Full name of this region (in English, for overseas regions)"""
		return cast(str, self['Name'])

	def __str__(self) -> str:
		return self.name

	@cached_property
	def _complete(self) -> 'Region':
		#IMPORTANT! Or else str constructor will return a paperweight
		if 'ID' in self._data or 'APILink' in self._data:
			return super()._complete
		
		short = self.get('Short')
		if short:
			complete = next((region for region in Region.all() if region.short_name == short), None)
			if complete:
				return complete
		raise NotImplementedError('Uh oh Region needs ID/Short/APILink')

	@property
	def short_name(self) -> str:
		"""2-3 letter uppercase acronym for this region, as per common everyday usage
		If you insist on being more official: Australian states/territories match https://meteor.aihw.gov.au/content/430134, other countries match
		ISO 3166-1 alpha-3 except New Zealand which is NZ and not NZL"""
		return cast(str, self['Short'])

	@property
	def colour(self) -> tuple[int, int, int]:
		"""Returns tuple of (red, blue, green) for a colour apparently associated with the region"""
		return cast(tuple[int, int, int], tuple(bytes.fromhex(self.colour_string[1:7])))
		
	@property
	def colour_string(self) -> str:
		"""Hexadecimal colour code for a colour apparently associated with the region"""
		return cast(str, self['Colour'])

	@property
	def cities(self) -> Collection[str]:
		"""Cities that are known to exist and have a competitive Smash scene in this region"""
		return cast(Collection[str], self['Cities'])

	@property
	def is_international(self) -> bool:
		"""Checks whether this region is somewhere outside Australia/NZ
		This is not actually on the API, it does it by seeing if there are any cities (tournament series need cities to be added, if this is not a region that tournaments can be uploaded for, it has no reason to have cities)
		Could be hardcoded instead I guess"""
		return not bool(self.cities)
