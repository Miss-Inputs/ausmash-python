#from datetime import date, datetime
#Dumb shit alert: mypy barfs at Tournament.matches_date_filter if the type hint for start_date and end_date is simply date and not datetime.date, as it seems to think that means the Tournament.date property, for some reason; which causes too much screwiness to just slap a type: ignore on I think
#It makes no sense because it's fine with Tournament.date itself returning a date, and also Tournament.date is not in the global scope
import datetime
from collections.abc import Collection, Sequence
import logging
import operator
from typing import cast

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper
from ausmash.resource import Resource
from ausmash.typedefs import ID

from .event import Event
from .region import Region

logger = logging.getLogger(__name__)

class Tournament(Resource):
	"""A competitive tournament, which should have one or more Events (or none if it has not happened yet)"""
	base_url = 'tourneys'

	@classmethod
	def all(cls, region: Region | str | None=None) -> Sequence['Tournament']:
		"""All tournaments that have been uploaded, or all tournaments in a region, from newest to oldest"""
		if region:
			if isinstance(region, str):
				return cls.wrap_many(call_api(f'tourneys/byregion/{region}'))
			return tuple(cls(t).updated_copy({'Region': region._data}) for t in call_api(f'tourneys/byregion/{region.short_name}')) #pylint: disable=protected-access
		return cls.wrap_many(call_api('tourneys'))

	@classmethod
	def all_with_results(cls) -> Sequence['Tournament']:
		"""All tournaments that have Events, from newest to oldest"""
		return cls.wrap_many(call_api('tourneys/withresults'))

	@classmethod
	def search(cls, query: str) -> Sequence['Tournament']:
		"""All tournaments with a name containing the specified query, from newest to oldest"""
		return cls.wrap_many(call_api('tourneys/search', {'q': query}))

	@classmethod
	def from_name(cls, name: str) -> 'Tournament':
		"""Returns tournament with exact name
		:raises KeyError: if no tournament with that name could be found
		"""
		for tournament in cls.search(name):
			if tournament.name == name:
				return tournament
		raise KeyError(name)

	@classmethod
	def upcoming(cls) -> Sequence['Tournament']:
		"""All tournaments occurring in the future
		TODO: May be more to it - on Sun 19 Feb 2023, 7:46pm, showed Dancing Blade 29 (Sat 18 Feb 2023, 10am-8pm) as upcoming? Is this a timezone issue"""
		return cls.wrap_many(call_api('tourneys/upcoming'))

	@property
	def name(self) -> str:
		"""Name of ths tournament"""
		return cast(str, self['Name'])
	
	def __str__(self) -> str:
		return self.name

	@property
	def __split_abbrev_name(self) -> tuple[bool, str, str]:
		"""Returns: (Does tournament name start with series name, abbreviated name of series, name remainder)"""
		name = self.name.replace(' #', ' ')
		
		series_name = self.series.name.casefold()
		series_name_len = len(series_name)
		series_abbrev_name = self.series.abbrev_name
		if not name.casefold().startswith(series_name):
			if name.casefold().startswith(series_abbrev_name.casefold()):
				name = name.replace(series_abbrev_name, series_name)
			elif self.region.short_name == 'WA' and name.startswith('Smashfest'):
				#Some are just named Smashfest and the date, but that might not be a unique series name
				name = name.replace('Smashfest', self.series.name)
			else:
				return False, series_abbrev_name, name.rsplit(' - ', 1)[0]
		name = name.rsplit(' @ ', 1)[0]
		
		if name[series_name_len: series_name_len + 2] in {': ', ', ', '. '}:
			#Last two are a bit unusual, but some Super Barista Bros tournaments are named like that
			return True, series_abbrev_name, name[series_name_len + 2:].rsplit(' - ', 1)[0]
		if name[series_name_len: series_name_len + 3] == ' - ':
			return True, series_abbrev_name, name[series_name_len + 3:]
		#Assume otherwise there is one separator character (probs a space) between series name and the rest
		#And then some tournament series still have some weird things on the end I guess
		return True, series_abbrev_name, name[series_name_len + 1:].removesuffix(' Esports')

	@property
	def index(self) -> int | str | None:
		"""Number or subtitle etc of this tournament within the series, e.g. "Cool Weekly #3" -> 3"""
		split = self.__split_abbrev_name
		if not split[0]:
			return False
		name_remainder = split[2]
		if name_remainder == '💯':
			return 100
		try:
			return int(name_remainder)
		except ValueError:
			pass
		return name_remainder

	@property
	def abbrev_name(self) -> str:
		"""Tournament name abbreviated to require less space for display, etc"""
		split = self.__split_abbrev_name
		if split[0]:
			#Abbrev the series name if it is part of it
			if not split[2]:
				#Format one-offs properly
				return split[1]
			return ' '.join(split[1:])
		return split[2]

	@property
	def region(self) -> Region:
		"""Region that this tournament was in"""
		#Only RegionShort on partial tournaments, partial Region with ID is on tourneys/{id}
		region = self.get('Region')
		if region:
			return Region(region)
		return Region(self['RegionShort'])
		
	@property
	def date(self) -> datetime.date:
		"""The day this tournament was held, which is always a single day, so for majors etc it might be just the first day"""
		return datetime.datetime.fromisoformat(self['TourneyDate']).date()
	
	@property
	def is_major(self) -> bool:
		"""If this tournament is considered a major, which is just determined by if the "is major" checkbox was ticked"""
		return cast(bool, self['IsMajor'])
	
	@property
	def series(self) -> 'TournamentSeries':
		"""Series that this particular tournament is an instance of
		Everything has one now, so one-off tournaments probably need to be created with their own series"""
		return TournamentSeries(self['Series'])
	
	@property
	def city(self) -> str:
		"""City within the region where this tournament was held, or more technically where it was expected to have been held given the series"""
		return self.series.city

	@property
	def events(self) -> Sequence[Event]:
		"""All events uploaded for this tournament. Should be ordered from earliest to latest, as in the admin page, though sometimes it might not be, so actually I don't know the order"""
		return [Event(e) for e in self['Events']]

	def matches_date_filter(self, start_date: datetime.date | None = None, end_date: datetime.date | None = None) -> bool:
		"""Returns true if this tournament is between the start and end dates (both inclusive)"""
		return (start_date is None or self.date >= start_date) and (end_date is None or self.date <= end_date)
	
	@property
	def start_gg_slug(self) -> str | None:
		"""Gets the start.gg slug for this tournament by looking at the source_url of this tournament's events, or None if no event was imported from start.gg or had its source URL set."""
		for event in self.events:
			url = event.source_url
			if url and 'start.gg/tournament/' in url:
				return url.rsplit('/', 1)[-1]
		return None
	
	def __other_phase_for_event(self, e: Event, previous=False) -> Event | None:
		#Can't use functools.cache here… or we could, but it'd cause a memory leak
		
		if not hasattr(self, '__phase_event_cache'):
			self.__phase_event_cache = {}
		cached = self.__phase_event_cache.get((e.id, previous), ...)
		if cached is not ...:
			return cached
		
		#While we've documented the order of .events doesn't always work, we have to assume it does
		event_indices = {e: i for i, e in enumerate(self.events)}
		index = event_indices.get(e)
		if index is None:
			raise ValueError(f'{e.id} {e} does not belong to this tournament')
		from .result import Result #Avoid ye olde circular import
		#Just to be really sure, make sure players from the next phase are all in the previous one
		results = Result.results_for_event(e)
		if not results:
			self.__phase_event_cache[(e.id, previous)] = None
			return None
		result_players = {result.player_name for result in results}
		def all_event_players_are_in_this_event(event: Event) -> bool:
			return all(result.player_name in result_players for result in Result.results_for_event(event))
		def all_players_are_in_event(event: Event) -> bool:
			player_names = {result.player_name for result in Result.results_for_event(event)}
			return player_names and all(player in player_names for player in result_players)

		potential_events_and_indexes = [(event, i) for event, i in event_indices.items() if (i < index if previous else i > index) and e.game == event.game and e.type == event.type and e.is_side_bracket == event.is_side_bracket and e.is_redemption_bracket == event.is_redemption_bracket and (all_players_are_in_event(event) if previous else all_event_players_are_in_this_event(event))]
		
		if not potential_events_and_indexes:
			phase = None
		elif previous:
			phase = max(potential_events_and_indexes, key=operator.itemgetter(1))[0]
		else:
			phase = min(potential_events_and_indexes, key=operator.itemgetter(1))[0]
		self.__phase_event_cache[(e.id, previous)] = phase
		return phase

	def next_phase_for_event(self, e: Event) -> Event | None:
		"""If e has a next phase as an Event, e.g. e is a round robin pools that progresses into a pro bracket, return that next phase
		If e is not, or could not tell what the next is, return None
		:raises ValueError: if e is not part of this tournament"""
		return self.__other_phase_for_event(e, False)
	
	def previous_phase_for_event(self, e: Event) -> Event | None:
		"""If e has a previous phase as an Event, e.g. e is a pro bracket that is progressed from a round robin pools, return that previous phase
		If e is not, or could not tell what the next is, return None
		:raises ValueError: if e is not part of this tournament"""
		return self.__other_phase_for_event(e, True)	
	
	def start_phase_for_event(self, e: Event) -> Event:
		"""If e has any previous phases, returns the first one that players start in, or returns e
		e.g. if there is pools > top 48 > top 8, will return pools for all of pools, top 48, and top 8"""
		prev = self.previous_phase_for_event(e)
		if not prev:
			return e
		return self.start_phase_for_event(prev)
	
	def final_phase_for_event(self, e: Event) -> Event:
		"""If e has any previous phases, returns the last one that players will aim to end up in, or returns e
		e.g. if there is pools > top 48 > top 8, will return top 8 for all of pools, top 48, and top 8"""
		prev = self.next_phase_for_event(e)
		if not prev:
			return e
		return self.final_phase_for_event(prev)


class TournamentSeries(DictWrapper):
	"""Series of tournaments, returned from /series or as part of of /tournament/{id}"""
	name_abbreviations = {
		#Does not have to be an acronym necessarily, just as long as it's still distintinguishable by the average person interested in those tournaments
		'Ultimate Pop-Off Village': 'UPOV',
		'Dancing Blade': 'DB',
		'Okay This Is Epping': 'Epping',
		'Friday Night Smash': 'FNS',
		'Guf n\' Watch @ GUF Bendigo': 'GUF', #Or should this be abbrev'd to GUF & Watch specifically
		'Super Barista Bros': 'SBB',
		'CouchWarriors RanBat': 'CW RanBat',
		'Murdoch Monthly': 'Murdoch',
	}

	@classmethod
	def all(cls) -> Collection['TournamentSeries']:
		"""All known tournament series on Ausmash"""
		return cls.wrap_many(call_api('series'))

	@property
	def id(self) -> ID:
		"""Opaque ID identifying this series, though there is no /series/{id} (all fields are here anyway)"""
		return ID(self['ID'])

	def __eq__(self, __o: object) -> bool:
		if not isinstance(__o, TournamentSeries):
			return False
		return self.id == __o.id

	def __hash__(self) -> int:
		return hash(self.id)
	
	@property
	def name(self) -> str:
		"""Full name of this series"""
		return cast(str, self['Name'])
	
	@property
	def abbrev_name(self) -> str:
		"""Returns a shorter form of this series' name if one is known (not pulled from the API, defined here), for easier display
		Returns full name (with no The prefix or Smash suffix) if no abbreviation known"""
		name = self.name
		return self.name_abbreviations.get(name, name.removeprefix('The ').removesuffix(' Smash').rsplit(' @ ', 1)[0])

	def __str__(self) -> str:
		return self.name
	
	@property
	def region(self) -> Region:
		"""Region that these tournaments are held in"""
		return Region(self['RegionShort'])
	
	@property
	def city(self) -> str:
		"""City that these tournaments are generally held in, from a defined list of cities"""
		return cast(str, self['City'])

	@property
	def tournaments(self) -> Collection[Tournament]:
		"""All tournaments that are part of this series"""
		return {Tournament(t).updated_copy({'Series': self._data}) for t in call_api(f'tourneys/byseries/{self.id}')}
