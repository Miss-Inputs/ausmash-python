
import itertools
import re
from collections.abc import Mapping, Sequence
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, cast

from ausmash.dictwrapper import DictWrapper
from ausmash.startgg_api import get_event_entrants
from ausmash.typedefs import ID, URL

from .game import Game

if TYPE_CHECKING:
	from .player import Player

#Whoa mathematics goin on here
#Top 8 is all unique placings, and then every placing after that follows this pattern, and I don't know what I'm actually doing but this oughta do the trick
#Not included: Expressing this in a concise way
#2 ** 16 is just an arbitrary maximum and I doubt there would be more entrants in a tournament ever than that
	#(item for sublist in list_of_lists for item in sublist)
normalized_elimination_bracket_sizes: Sequence[int] = tuple(2 ** n for n in range(1, 16)) #2 ** 16 is just arbitrarily the highest bracket size we will even think about
possible_placings: Sequence[int] = (1, 2, *tuple(itertools.chain.from_iterable((n + 1, int(n * 1.5) + 1) for n in normalized_elimination_bracket_sizes)))

class EventType(str, Enum):
	"""Values for Event.type"""
	Singles = 'Singles'
	Teams = 'Teams'

class BracketStyle(str, Enum):
	"""Values for Event.bracket_style"""
	RoundRobin = 'Round robin'
	Swiss = 'Swiss'
	SingleElimination = 'Single elimination'
	DoubleElimination = 'Double elimination'

class Event(DictWrapper):
	"""An individual event at a tournament, may be one particular phase if there is more than one, or
	a side bracket or redemption bracket etc
	Also not a resource (only obtainable as a result of full Tournament from /tournament/{id}) but has an APILink, which
	can't really be used to do anything?"""

	__redemption_bracket_name = re.compile(r'\b(?:amateur|amateurs|ammies|redemption|redemmies|ammys|no cigar)\b', re.IGNORECASE) #I thiiink Pissmas 2: No Cigar is some kind of redemption for 49th place?
	__side_bracket_name = re.compile(r'\b(?:mega smash|squad strike)\b', re.IGNORECASE)
	__startgg_url = re.compile(r'https?://.*start.gg/tournament/(?P<tournament>[^/]+)/event/(?P<event>[^/]+)')

	@property
	def id(self) -> ID:
		"""Used to look up results/matches/videos"""
		return ID(self['ID'])

	def __eq__(self, __o: object) -> bool:
		if not isinstance(__o, Event):
			return False
		return self.id == __o.id

	def __hash__(self) -> int:
		return hash(self.id)

	@property
	def name(self) -> str:
		"""Name of this event"""
		return cast(str, self['Name'])

	def __str__(self) -> str:
		return self.name

	@property
	def bracket_style(self) -> BracketStyle:
		"""Double elimination, Round robin, etc"""
		return BracketStyle(self['BracketStyle'])

	@property
	def type(self) -> EventType:
		"""Singles, Teams, etc"""
		return EventType(self['EventType'])

	@property
	def game(self) -> Game:
		"""The game being played in this event"""
		return Game(self['Game'])

	@property
	def is_redemption_bracket(self) -> bool:
		"""Detects if this is a redemption/amateur/rehab/whatever you like to call it in your neck of the woods bracket. Based on the name because there's nothing else that would indicate it."""
		return self.__redemption_bracket_name.search(self.name) is not None

	@property
	def is_side_bracket(self) -> bool:
		"""If this is presumably not the main bracket of the tournament"""
		return self.__side_bracket_name.search(self.name) is not None

	@property
	def source_url(self) -> URL | None:
		"""Returns the link to start.gg or Challonge that this was imported from, or null if it was imported before this field was added to the API (or presumably if tournaments are ever uploaded from TioPro); for usage with those site's APIs to get seeds and things"""
		return cast(URL | None, self['SourceUrl'])

	@property
	def startgg_slug(self) -> str | None:
		"""The event part of the slug (after /event/ in the URL) for this event, or None if this is not from start.gg"""
		if not self.source_url:
			return None
		match = self.__startgg_url.match(self.source_url)
		if not match:
			return None
		return match['event']

	@property
	def tournament_startgg_slug(self) -> str | None:
		"""The tournament part of the slug (after /tournament/ in the URL) for this event, or None if this is not from start.gg"""
		if not self.source_url:
			return None
		match = self.__startgg_url.match(self.source_url)
		if not match:
			return None
		return match['tournament']
	
	@cached_property
	def seeds(self) -> Mapping['Player | str', int | None] | None:
		"""Requires start.gg API key, gets player > seed number for this event, attempting to match start.gg player ID to Player
		Will only return anything for singles events for now
		Otherwise returns None"""
		if not self.startgg_slug or not self.tournament_startgg_slug:
			return None
		entrants = get_event_entrants(self.tournament_startgg_slug, self.startgg_slug)
		
		seeds_by_id: dict[int, int | None] = {}
		seeds_by_tag: dict[str, int | None] = {}
		for entrant in entrants:
			if len(entrant['participants']) != 1:
				continue #TODO: Doubles team seeds, this would need to return Player | str | tuple[Player | str, Player | str] instead
			seed = next((seed['seedNum'] for seed in entrant['seeds'] if seed['progressionSource'] is None), None)
			seeds_by_id[entrant['participants'][0]['player']['id']] = seed
			seeds_by_tag[entrant['participants'][0]['gamerTag'].lower()] = seed
			seeds_by_tag[entrant['name'].lower()] = seed

		from .result import (
			Result,  # Bugger it, naughty import outside of the top to avoid circular nonsense
		)
		return {result.player or result.player_name: seeds_by_id.get(result.player.start_gg_player_id if result.player else None, seeds_by_tag.get(result.player_name.lower())) for result in Result.results_for_event(self)}

__doc__ = Event.__doc__ or __name__
