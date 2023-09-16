from collections.abc import Collection, Sequence
from datetime import date, datetime
from typing import cast
from ausmash.api import call_api

from ausmash.dictwrapper import DictWrapper

from ..character import Character
from ..event import Event
from ..region import Region
from ..result import ResultMixin
from ..tournament import Tournament
from ..game import Game
from ..player import Player

class PocketResult(ResultMixin, DictWrapper):
	"""Item from /pocket/player/results
	Useful for a quick display of information, but perhaps less useful than Result from player.results overall
	Seems to only return singles double elimination results"""

	@classmethod
	def get_results(cls, player: Player, game: Game) -> Sequence['PocketResult']:
		return PocketResult.wrap_many(call_api(f'pocket/player/results/{player.id}/{game.id}')['Items'])

	@property
	def tournament(self) -> Tournament:
		"""Tournament that this result happened at. Will require an API request for anything except ID or name"""
		return Tournament({'ID': self['TourneyID'], 'Name': self['TourneyName']})

	@property
	def event_name(self) -> str:
		"""Name of the event that this result is for, avoiding looking up the tournament's events to query each one to get the Event that way"""
		return cast(str, self['EventName'])

	@property
	def event(self) -> Event:
		"""Because Event is not a Resource, we would need to look it up from the tournament to access any properties"""
		return next(e for e in self.tournament.events if e.id == self['EventID'])
	
	@property
	def name(self) -> str:
		"""The full name of the event for this result, concatenated from TourneyName + EventName"""
		return cast(str, self['FullName'])

	@property
	def placing(self) -> int:
		return int(self.placing_with_ordinal[:-2]) #That should work consistently I hope

	@property
	def placing_with_ordinal(self) -> str:
		return cast(str, self['Place'])

	@property
	def total_entrants(self) -> int:
		"""Number of entrants that were in this event, including this one"""
		return cast(int, self['Entrants'])

	@property
	def region(self) -> Region:
		"""Region that this tournament occurred in"""
		return Region(self['RegionShort'])

	@property
	def date(self) -> date:
		"""Date that this tournament occurred on"""
		return datetime.fromisoformat(self['Date']).date()

	@property
	def characters(self) -> Collection[Character]:
		"""I don't think this is in any particular order"""
		return {Character(c).updated_copy({'IconUrl': c['ImageUrl']}) for c in self['Characters']}

#TODO: /pocket/results/{game.id} but what can you do with it, as it just has ID (not sure what it refers to?)/game ID/tournament name/region short/date
