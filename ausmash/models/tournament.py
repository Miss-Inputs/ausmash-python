#from datetime import date, datetime
#Dumb shit alert: mypy barfs at Tournament.matches_date_filter if the type hint for start_date and end_date is simply date and not datetime.date, as it seems to think that means the Tournament.date property, for some reason; which causes too much screwiness to just slap a type: ignore on I think
#It makes no sense because it's fine with Tournament.date itself returning a date, and also Tournament.date is not in the global scope
import datetime
from collections.abc import Collection, Sequence
from typing import cast

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper
from ausmash.resource import Resource
from ausmash.typedefs import ID

from .event import Event
from .region import Region


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
	def upcoming(cls) -> Sequence['Tournament']:
		"""All tournaments occurring in the future
		TODO: May be more to it - shows DB29 right now (Sun 19 Feb 2023, 7:46pm)? Is this a timezone issue"""
		return cls.wrap_many(call_api('tourneys/upcoming'))

	@property
	def name(self) -> str:
		return cast(str, self['Name'])
	
	def __str__(self) -> str:
		return self.name

	@property
	def __split_abbrev_name(self) -> tuple[bool, str, str]:
		name = self.name.replace(' #', ' ')
		
		series_name = self.series.name.casefold()
		series_name_len = len(series_name)
		series_abbrev_name = self.series.abbrev_name
		if not name.casefold().startswith(series_name):
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
		#Only RegionShort on partial tournaments, partial Region with ID is on tourneys/{id}
		return Region(self['Region']) if 'Region' in self._data else Region(self['RegionShort'])

	@property
	def date(self) -> datetime.date:
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
		"""All events uploaded for this tournament. Should be ordered from earliest to latest, as in the admin page"""
		return Event.wrap_many(self['Events'])

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
	}

	@classmethod
	def all(cls) -> Collection['TournamentSeries']:
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
		return Region(self['RegionShort'])
	
	@property
	def city(self) -> str:
		return cast(str, self['City'])

	@property
	def tournaments(self) -> Collection[Tournament]:
		return {Tournament(t).updated_copy({'Series': self._data}) for t in call_api(f'tourneys/byseries/{self.id}')}
