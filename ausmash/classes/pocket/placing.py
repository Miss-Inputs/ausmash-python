from collections.abc import Collection, Sequence
from datetime import date, datetime
from typing import cast

from ausmash.classes.result import ResultMixin
from ausmash.dictwrapper import DictWrapper
from ausmash.typedefs import ID

from ..character import Character
from ..event import Event
from ..game import Game
from ..player import Player
from ..region import Region
from ..tournament import Tournament


class PocketPlacings(DictWrapper):
	"""Returned from /pocket/result/placings"""

	@property
	def game(self) -> Game:
		return Game(self['GameID'])

	@property
	def tournament(self) -> Tournament:
		return Tournament(
			{
				'ID': self['TourneyID'],
				'Name': self['ResultName'],
				'Region': self['ResultRegionShort'],
			}
		)

	@property
	def date(self) -> date:
		return datetime.fromisoformat(self['Date']).date()

	@property
	def region(self) -> Region:
		return Region(self['ResultRegionShort'])

	@property
	def events(self) -> Sequence['PocketPlacingsEvent']:
		return PocketPlacingsEvent.wrap_many(self['Events'])


class PocketPlacingsEvent(DictWrapper):
	"""Item of Events field in PocketPlacings"""

	@property
	def number_of_entrants(self) -> int:
		return cast(int, self['Entrants'])

	@property
	def event(self) -> Event:
		return Event({'ID': self['EventID'], 'Name': self['EventName']})

	@property
	def placings(self) -> Sequence['PocketPlacing']:
		"""Should already be ordered by ResultNumber"""
		return PocketPlacing.wrap_many(placing | self._data for placing in self['Placings'])


class PocketPlacing(ResultMixin, DictWrapper):
	"""Placings field of PocketPlacingsEvent"""

	@property
	def id(self) -> ID:
		"""ID of some kind
		TODO: What does this refer to? (e.g. 261969, 262198)"""
		return ID(self['ResultID'])

	@property
	def player(self) -> Player:
		return Player(
			{
				'ID': self['PlayerID'],
				'Name': self['PlayerName'],
				'RegionShort': self['PlayerRegionShort'],
			}
		)

	@property
	def placing(self) -> int:
		return cast(int, self['ResultNumber'])

	@property
	def placing_ordinal(self) -> str:
		return cast(str, self['Result'])

	@property
	def characters(self) -> Collection[Character]:
		"""I don't think this is in any particular order"""
		return {Character(c).updated_copy({'IconUrl': c['ImageUrl']}) for c in self['Characters']}

	# These two are on PocketPlacingEvent, but we put them in here so we can use ResultMixin
	@property
	def total_entrants(self) -> int:
		return cast(int, self['Entrants'])

	@property
	def event(self) -> Event:
		return Event({'ID': self['EventID'], 'Name': self['EventName']})
