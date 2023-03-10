from collections.abc import Mapping, Sequence
from functools import cached_property
from typing import cast

from ausmash.api import call_api
from ausmash.resource import Resource
from ausmash.typedefs import ID, URL, JSONDict


class Game(Resource):
	"""A video game that people play competitively and data is recorded on Ausmash for it"""
	base_url = 'games'

	def __init__(self, d: JSONDict | str | ID) -> None:
		"""For convenience, allow using just a short name, which will look up any additional properties automatically"""
		if isinstance(d, str):
			super().__init__({'Short': d})
		else:
			super().__init__(d)

	@classmethod
	def all(cls) -> Sequence['Game']:
		"""Returns all known games, ordered from newest to oldest.
		Uses the pocket API, which has the ImageUrl field accessible already without another request to get by ID, though there is no APILink field (but that might not be needed)"""
		return cls.wrap_many(call_api('pocket/games'))

	@classmethod
	def as_dict(cls) -> Mapping[str, 'Game']:
		"""Returns all games as a mapping with the short name as the key"""
		return {game.short_name: game for game in cls.all()}

	@property
	def short_name(self) -> str:
		"""Abbreviated name of this game, often the acronym"""
		return cast(str, self['Short'])

	@property
	def full_name(self) -> str:
		"""Name, including "Super Smash Bros.\""""
		return cast(str, self['Name'])

	@property
	def name(self) -> str:
		"""Informal name, excluding the "Super Smash Bros." title"""
		full_name = self.full_name
		if full_name == 'Super Smash Bros.':
			return '64'
		if full_name == 'Super Smash Bros. for Wii U':
			return 'Smash 4'
		if full_name == 'Super Smash Bros. for Nintendo 3DS':
			return '3DS'
		return full_name.removeprefix('Super Smash Bros. ')

	def __str__(self) -> str:
		return self.name
		
	def __eq__(self, __o: object) -> bool:
		"""Needed for incomplete Game fragments (from str passed to constructor) to compare equally with game IDs"""
		if not isinstance(__o, Game):
			return False
		return self.short_name == __o.short_name

	def __hash__(self) -> int:
		return hash(self.short_name)

	@cached_property
	def _complete(self) -> 'Game':
		#Otherwise, str constructor with just Short will return an object that cannot do anything useful
		if 'ID' in self._data or 'APILink' in self._data:
			return super()._complete
			
		short = self._data.get('Short')
		if short:
			return Game.as_dict()[short]
		raise NotImplementedError('Uh oh Game needs ID/Short/APILink')

	@property
	def sort_order(self) -> int:
		"""Seems to be in order of release date, 0 being newest game and ascending by 1"""
		return cast(int, self['SortOrder'])

	def __lt__(self, other: object) -> bool:
		if not isinstance(other, Game):
			raise TypeError(type(other))
		return self.sort_order < other.sort_order	

	@property
	def logo_url(self) -> URL:
		return cast(URL, self['ImageUrl'])

	#TODO: /rankings/bygame and /rankings/bygameandregion, but those seem to all error at the moment
