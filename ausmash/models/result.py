from bisect import bisect_left
from collections.abc import Collection, Sequence
from datetime import date
from fractions import Fraction
from functools import cached_property
from typing import Any, Protocol, cast

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper
from ausmash.typedefs import ID, JSONDict

from .character import Character
from .event import Event, possible_placings
from .player import Player
from .tournament import Tournament

class _Result(Protocol):
	@property
	def total_entrants(self) -> int: ...
	
	@property
	def placing(self) -> int: ...

	@property
	def rounds_cleared(self) -> int: ...
	
class ResultMixin:
	"""Utility methods for Result and result-like classes"""

	@property
	def rounds_cleared(self: _Result) -> int:
		"""Player has placed X rounds away from the lowest possible placing
		This would only make sense for double elimination brackets, but it can be used for normalising results by having a number that
		goes up with higher placings, and goes up if there was more entrants"""
		return rounds_from_victory(self.total_entrants) - rounds_from_victory(self.placing)

	@property
	def better_than_other_entrants(self: _Result) -> Fraction:
		"""Player's result is higher than this amount of the entrants"""
		if self.placing == 1:
			return Fraction(self.total_entrants - 1, self.total_entrants)
		if self.placing == 2:
			return Fraction(self.total_entrants - 2, self.total_entrants)
			#0.0, 0.25, 0.5, 0.625, 0.75, 0.8125, 0.875,
		#FIXME: This isn't correct I think
		return Fraction(1, 2 ** self.rounds_cleared)

	@property
	def better_than_other_entrants_normalized(self: _Result) -> Fraction:
		#FIXME: I think this is also wrong
		"""Player's result is higher than this amount of the entrants, if the entrants was a perfect power of 2"""
		#possible_placings(Result.rounds_from_victory(self.total_entrants)) - possible_placings(Result.rounds_from_victory(self.placing))
		return Fraction(1, self.total_entrants) #FIXME Okay I think I forgor to implement this

	@property
	def result(self: _Result) -> tuple[int, int]:
		"""Tuple of (placing, total entrants), not sure what to name it"""
		return (self.placing, self.total_entrants)
	
	@property
	def as_fraction(self: _Result) -> Fraction:
		"""Also not sure what to name this one"""
		return Fraction(self.placing, self.total_entrants)

class Result(ResultMixin, DictWrapper):
	"""Player's result at an event, returned from event/{id}/results or players/{id}/results"""
	
	@classmethod
	def results_for_event(cls, event: Event | ID) -> Sequence['Result']:
		"""Results for an Event, or event ID
		Adds an Entrants field to avoid an extra API call for total_entrants
		Should be ordered from highest placing to lowest?"""
		if isinstance(event, Event):
			event = event.id
		response: Sequence[dict[str, Any]] = call_api(f'events/{event}/results')
		for r in response:
			r['Entrants'] = len(response)
		return cls.wrap_many(response)

	@classmethod
	def results_for_player(cls, player: Player, start_date: date | None=None, end_date: date | None=None) -> Sequence['Result']:
		"""Results for all events this player has entered, from newest to oldest, optionally within a certain timeframe
		TODO: Document if start_date or end_date are inclusive/exclusive"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		return cls.wrap_many(call_api(f'players/{player.id}/results', params))
	
	@classmethod
	def featuring_character(cls, character: Character) -> Sequence['Result']:
		"""Results with character data recorded as using this character, newest to oldest
		Not necessarily any result where a match was played using this character, as the match-level character data can be different and more specific if the player so desires"""
		return cls.wrap_many(call_api(f'characters/{character.id}/results'))

	def __str__(self) -> str:
		return f'{self.placing} - #{self.placing}'

	def __lt__(self, other: object) -> bool:
		if not isinstance(other, Result):
			raise TypeError(type(other))
		return self.placing > other.placing #Not a typo, future me! For some reason I keep forgetting when I look at this code again that 1st place is better than 2nd place

	def __hash__(self) -> int:
		return hash((self.player_name, self.event.name))

	@property
	def player(self) -> Player | None:
		"""Returns player who this result is for, or None if it is not someone in the database"""
		player: JSONDict | None = self.get('Player')
		if player:
			return Player(player)
		return None

	@property
	def tournament(self) -> Tournament:
		"""Tournament this result is from"""
		return Tournament(self['Tourney'])

	@property
	def event(self) -> Event:
		"""Event this result is from"""
		return Event(self['Event'])

	@cached_property
	def total_entrants(self) -> int:
		"""Number of entrants that were in the event this result is for, including this one
		If this Result was not from Result.results_for_event, it will require an API call to look up all results for the event to count them"""
		num_entrants: int | None = self.get('Entrants')
		if num_entrants:
			return num_entrants
		return len(self.results_for_event(self.event))

	@property
	def player_name(self) -> str:
		"""Name of the player this result is for, even if that player is not in the database"""
		return cast(str, self['PlayerName'])

	@property
	def placing(self) -> int:
		"""Numeric placing for this result"""
		return cast(int, self['Result'])

	def __int__(self) -> int:
		return self.placing

	@property
	def pool(self) -> int | None:
		"""Apparently this is an int? Sure why not
		Not often used, as brackets just don't often get uploaded that way"""
		return cast(int | None, self['Pool'])

	@property
	def characters(self) -> Collection[Character]:
		"""Characters entered for this result
		How this relates to character data at the match level I guess is up to the player entering their character data"""
		return Character.wrap_many(self['Characters'])

def rounds_from_victory(result: int) -> int:
	"""Normalizes a result (or seed) so that it is just 1 more than the next one
	Used for SPR and upset factor, see also https://www.pgstats.com/articles/introducing-spr-and-uf"""
	return bisect_left(possible_placings, result)
