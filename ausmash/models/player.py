from collections.abc import Collection, Mapping, Sequence
from datetime import date
from fractions import Fraction
from typing import cast

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper
from ausmash.exceptions import NotFoundError
from ausmash.resource import Resource
from ausmash.typedefs import ID, URL

from .event import Event
from .game import Game
from .region import Region

class Player(Resource):	
	"""Individual player who plays or has ever played a Super Smash Bros. game at a competitive event.
	Not all players at an event need to be added to the database, but doing so makes Elo more accurate, etc"""
	base_url = 'players'

	@classmethod
	def all(cls, region: Region | str | None=None) -> Collection['Player']:
		"""Gets all players, or all players currently in a region"""
		if region:
			if isinstance(region, str):
				return cls.wrap_many(call_api(f'players/byregion/{region}'))
			return {cls(p).updated_copy({'Region': region._data}) for p in call_api(f'players/byregion/{region.short_name}')} #pylint: disable=protected-access
		return cls.wrap_many(call_api('players'))

	@classmethod
	def get_player(cls, region: 'Region | str', name: str) -> 'Player':
		"""Gets the player from this region with this name
		:raises NotFoundException: If the region does not have a player with that name"""
		region_short = region.short_name if isinstance(region, Region) else region
		return cls(call_api(f'players/find/{name}/{region_short}'))
		
	@classmethod
	def search(cls, query: str) -> Collection['Player']:
		return cls.wrap_many(call_api('players/search', {'q': query}))
		
	@classmethod
	def reverse_lookup_start_gg_player_id(cls, player_id: str, player_name_hint: str | None=None, player_region_hint: Region | str | None=None, skip_searching_all: bool=False) -> 'Player | None':
		"""Given a player ID from start.gg's API, returns an Ausmash Player that is associated with that Start.gg player, or None if could not be found
		Will search for a player name first or get all players in a region first if hint for either is given, but these are not restrictive filters, it will fall back to checking all players if it cannot find a match
		:raises HTTPError: If some other HTTP error occurs other than not being found"""
		if isinstance(player_region_hint, str):
			player_region_hint = Region(player_region_hint)
		if player_name_hint:
			if player_region_hint:
				try:
					player = cls.get_player(player_region_hint, player_name_hint)
					if str(player.start_gg_player_id) == player_id:
						return player
				except NotFoundError:
					pass

			name_result = next((p for p in cls.search(player_name_hint) if str(p.start_gg_player_id) == player_id), None)
			if name_result:
				return name_result
		if player_region_hint:
			region_result = next((p for p in cls.all(player_region_hint) if str(p.start_gg_player_id) == player_id), None)
			if region_result:
				return region_result
		if skip_searching_all:
			return None
		return next((p for p in cls.all() if str(p.start_gg_player_id) == player_id), None)

	@property
	def name(self) -> str:
		return cast(str, self['Name'])

	@property
	def region(self) -> Region:
		region_dict = self.get('Region')
		if region_dict:
			return Region(region_dict)
		
		#We may have region ID or region short name, ideally use both for our partial proxy
		partial = {}
		region_id = self.get('RegionID')
		region_short = self.get('RegionShort')
		if region_id:
			partial['ID'] = region_id
		if region_short:
			partial['Short'] = region_short
		if not partial:
			raise AttributeError('No attributes on this player that indicate a region, somehow')
		return Region(partial)

	def __str__(self) -> str:
		return f'[{self.region.short_name}] {self.name}'

	@property
	def personal_url(self) -> URL | None:
		"""Link to this user's personal website, if they added this to their player page"""
		return cast(URL | None, self['PersonalUrl'])

	@property
	def twitch_url(self) -> URL | None:
		"""Link to this user's Twitch channel, if they added this to their player page"""
		return cast(URL | None, self['TwitchUrl'])

	@property
	def youtube_url(self) -> URL | None:
		"""Link to this user's YouTube channel, if they added this to their player page"""
		return cast(URL | None, self['YouTubeUrl'])

	@property
	def twitter_url(self) -> URL | None:
		"""Link to this user's Twitter profile, if they added this to their player page"""
		return cast(URL | None, self['TwitterUrl'])

	@property
	def facebook_url(self) -> URL | None:
		"""Link to this user's Facebook profile, if they added this to their player page"""
		return cast(URL | None, self['FacebookUrl'])

	@property
	def ssbworld_url(self) -> URL | None:
		"""Link to this user's SSBWorld profile, if they added this to their player page
		Note that SSBWorld is no longer an active site and has stoppd accepting new contributions"""
		return cast(URL | None, self['SSBWorldUrl'])

	@property
	def biography(self) -> str | None:
		"""User's biography, if they have written one
		May contain BBCode markup, including custom [char]character name[/char] tag to display a stock icon"""
		return cast(str | None, self['Bio'])

	@property
	def tournament_count(self) -> int:
		return cast(int, self['TournamentCount'])

	@property
	def match_count(self) -> int:
		return cast(int, self['MatchCount'])

	@property
	def result_count(self) -> int:
		"""Number of results for singles events this player has"""
		return cast(int, self['ResultCount'])
	
	@property
	def video_count(self) -> int:
		"""The number of videos on Ausmash featuring this player across their career and all Smash games, though only including singles matches"""
		return cast(int, self['VideoCount'])

	@property
	def start_gg_player_id(self) -> ID | None:
		"""start.gg player ID associated with this player, can be used in conjuction with start.gg's API and a query on player"""
		player_id: int | None = self['SmashGGPlayerID']
		return ID(player_id) if player_id else None

	def compare_common_winrates(self, game: Game, other: 'Player', start_date: date | None=None, end_date: date | None=None) -> tuple[Sequence['WinRate'], Sequence['WinRate']]:
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		response = call_api(f'compare/{game.id}/{self.id}/{other.id}/winrates', params)
		return WinRate.wrap_many(response['Player1WinRates']), WinRate.wrap_many(response['Player2WinRates'])

	def compare_common_results(self, game: Game, other: 'Player', start_date: date | None=None, end_date: date | None=None) -> Sequence[tuple[Event, int, int]]:
		"""(Event, player 1 result, player 2 result) for events that both of these players competed in"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		return tuple((Event(result['Event']), result['Player1Result'], result['Player1Result']) for result in call_api(f'compare/{game.id}/{self.id}/{other.id}/results', params)['Results'])
	
	def get_win_rates(self, game: Game | str, start_date: date | None=None, end_date: date | None=None) -> Sequence['WinRate']:
		"""Win rates against every opponent this player has ever played a singles match against for a certain game, from highest Elo to lowest"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		if isinstance(game, str):
			game = Game(game)
		#I guess /pocket/player/winrates/{player ID}/{game ID} ['Items'] does the same thing but without date params?
		return WinRate.wrap_many(call_api(f'players/{self.id}/winrates/{game.id}', params))

	def get_win_rate_dict(self, game: Game | str, start_date: date | None=None, end_date: date | None=None) -> Mapping['Player', 'WinRate']:
		"""get_win_rates as a mapping of {opponent: win rate}"""
		return {win_rate.opponent: win_rate for win_rate in self.get_win_rates(game, start_date, end_date)}

class WinRate(DictWrapper):
	"""Wins against a certain opponent, this is specific to a Player and Game"""
	@property
	def opponent(self) -> Player:
		"""Opponent that this win rate pertains to"""
		return Player(self['Opponent'])

	@property
	def opponent_elo(self) -> int:
		"""Opponent's Elo in this game"""
		return cast(int, self['Elo'])

	@property
	def wins(self) -> int:
		"""Number of matches where this player wins againt opponent"""
		return cast(int, self['Wins'])
	
	@property
	def losses(self) -> int:
		"""Number of matches where this player loses againt opponent"""
		return cast(int, self['Losses'])
	
	@property
	def total(self) -> int:
		"""Equivalent to wins + losses, though the field is already there so we might as well use it and save uhhh adding two other dict items"""
		return cast(int, self['Total'])

	@property
	def rate(self) -> Fraction:
		"""This win rate as wins/total"""
		return Fraction(self.wins, self.total)

	#Percent is rounded to integer from 0-100, not really needed
	