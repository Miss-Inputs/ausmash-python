from bisect import bisect_right
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
	def as_tuple(self: _Result) -> tuple[int, int]:
		"""Tuple of (placing, total entrants), not really sure what to name it"""
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

	@staticmethod
	def get_pools_drown_placing(pool_result: int, people_who_made_it_out: int, highest_drown_placing: int, number_of_pools: int, lowest_placing: int, number_of_people_in_this_pools_round: int) -> int:
		"""Gets an effective placing for a whole tournament if player drowned, that is more useful than just the individual placing in the pool, so if you were one placing away from making it out to top 8 you would get 9th or if 2 placings away you would get 13th, etc
		people_who_made_it_out and highest_drown_placing would usually be the same, but maybe they are not in the case of any swiss/waterfall/etc weirdness
		:param pool_result: Numeric placing for the pools event
		:param people_who_made_it_out: Number of players who made it out to the next phase e.g pro bracket
		:param highest_drown_placing: Highest possible placing for any player who did not make it out of pools, which for most simple cases of 1 pool phase into 1 pro bracket phase can just be equal to people_who_made_it_out
		:param number_of_pools: Number of different pools in this pools phase
		:param lowest_placing: Lowest possible placing for this tournament, which can just be the number of entrants for the purposes of this function
		:param number_of_people_in_this_pools_round: Number of entrants for this pools phase"""
		#Placing within this pool
		placing_to_not_drown = people_who_made_it_out // number_of_pools
		#Because not all pools will have an even number of entrants, this is how many people are in each pool at the very least, and some other pools might have one more but this works for these calculations
		min_people_in_every_pool = number_of_people_in_this_pools_round // number_of_pools

		#All the placings for those whomst drowned in pools should be lower (which is a bigger number) than those who placed in pro bracket, but not lower (not bigger number) than the whole tournament because that makes no sense
		drown_placings = [p for p in possible_placings if highest_drown_placing < p <= lowest_placing]
		
		index = int(((pool_result - (placing_to_not_drown + 1)) / (min_people_in_every_pool - placing_to_not_drown)) * len(drown_placings))
		index = max(index, 0)
		if index >= len(drown_placings):
			index = len(drown_placings) - 1
		return drown_placings[index]

	def __str__(self) -> str:
		return f'{self.event.name} - #{self.placing}'

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
	def number_of_entrants(self) -> int:
		"""Number of entrants that were in the event this result is for, including this one
		If this Result was not from Result.results_for_event, it will require an API call to look up all results for the event to count them
		More specifically this phase, if they are uploaded as separate events"""
		num_entrants: int | None = self.get('Entrants')
		if num_entrants:
			return num_entrants
		return len(self.results_for_event(self.event))
	
	@cached_property
	def total_entrants(self) -> int:
		"""Like number_of_entrants, but if this has multiple phases as events, counts the number of entrants at the start phase
		Pools should correctly have the number of all players and not just how many in each pool"""
		prev_phase = self.tournament.previous_phase_for_event(self.event)
		#First check that we have a previous phase, because if we don't, we can use number_of_entrants and potentially optimize the count we already had from .results_for_event
		if prev_phase:
			return len(self.results_for_event(self.tournament.start_phase_for_event(prev_phase)))
		return self.number_of_entrants

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
	
	@cached_property
	def number_of_pools(self) -> int:
		"""Number of unique pools at this event, or just 1 if it does not have pools"""
		return len({r.pool for r in self.results_for_event(self.event)})

	@property
	def characters(self) -> Collection[Character]:
		"""Characters entered for this result
		How this relates to character data at the match level I guess is up to the player entering their character data"""
		return Character.wrap_many(self['Characters'])
	
	@property
	def seed_performance_rating(self) -> int | None:
		"""How well this result outperformed the seed, see https://www.pgstats.com/articles/introducing-spr-and-uf
		Returns None if event is not from start.gg, entrant could not be linked back to start.gg by player ID, etc"""
		if not self.player:
			return None
		seeds = self.event.seeds
		if not seeds:
			return None
		if self.player not in seeds:
			return None
		if seeds[self.player] is None:
			return None
		return rounds_from_victory(seeds[self.player]) - rounds_from_victory(self.real_placing)
	
	@cached_property
	def real_placing(self) -> int:
		"""Returns a placing that makes sense for comparison purposes, even if this is an RR pools event and player drowned (rather than returning the result for just within that pool), e.g. if top 2 of each pool makes it out into top 8, this returns 9th instead of 3rd and 13th instead of 4th, etc, of course returning the pro bracket result if that was achieved
		Maybe this needs a better name? I dunno"""
		#TODO: I dunno what would happen if this is used on a swiss or waterfall bracket, probably not work how I think it works

		pro_bracket = self.tournament.next_phase_for_event(self.event)
		if pro_bracket:
			pro_bracket_results = Result.results_for_event(pro_bracket)
			pro_bracket_size = pro_bracket_results[0].number_of_entrants
			pro_bracket_result = next((r for r in pro_bracket_results if r.player == self.player), None)
			if pro_bracket_result:
				return pro_bracket_result.placing
			
			#glub glub glub
			return Result.get_pools_drown_placing(self.placing, pro_bracket_size, pro_bracket_size, self.number_of_pools, self.number_of_entrants, self.number_of_entrants)

		return self.placing


def rounds_from_victory(result: int) -> int:
	"""Normalizes a result (or seed) so that it is just 1 more than the next one
	Used for SPR and upset factor, see also https://www.pgstats.com/articles/spr-uf-extra-mathematical-details"""
	return bisect_right(possible_placings, result) - 1
