from collections.abc import Collection, MutableMapping, Sequence
from datetime import date, datetime
from functools import cached_property
from typing import Protocol, cast

from ausmash.api import call_api_json
from ausmash.dictwrapper import DictWrapper
from ausmash.typedefs import JSON, URL, IntID

from ..character import Character
from ..event import Event
from ..game import Game
from ..player import Player
from ..region import Region
from ..result import rounds_from_victory
from ..tournament import Tournament


class _BasePocketMatch(DictWrapper):
	"""Base class for match objects returned from pocket API"""

	@property
	def id(self) -> IntID:
		"""There is nothing to directly get a match with just an ID, so it is not a Resource, but it has an ID anyway"""
		return IntID(self['MatchID'])

	def __eq__(self, __o: object) -> bool:
		if not isinstance(__o, type(self)):
			return False
		return self.id == __o.id

	def __hash__(self) -> int:
		return hash(self.id)

	@property
	def event(self) -> Event:
		"""The Event that this match is a part of
		This may not have all expected properties of Event"""
		return Event({'ID': self['EventID'], 'Name': self['EventName'], 'Game': {'ID': self['GameID']}})

	@property
	def game(self) -> Game:
		return Game(IntID(self['GameID']))
 
	@property
	def tournament_name(self) -> str:
		"""Name of the tournament this match was at, PocketVideo does not have an ID to link back to Tournament so you would need to look it up by name, so if you
		only need the name this would save an API request"""
		return cast(str, self['TourneyName'])

	@property
	def tournament(self) -> Tournament:
		"""Tournament this match was at, PocketVideo does not have an ID to link back to Tournament so you would need to look it up by name"""
		return Tournament({'ID': self['TourneyID'], 'Name': self.tournament_name, 'RegionShort': self.region})
	
	@property
	def date(self) -> date:
		"""Date this match happened, presumably just the same time as when the tournament is listed as starting (so it might be day 1 of multi-day tournaments)"""
		return datetime.fromisoformat(self['Date']).date()
		
	@property
	def region(self) -> Region:
		"""Region this match was in, i.e. the region of the tournament"""
		return Region(self['RegionShort'])

	@property
	def winner(self) -> Player:
		return Player({k.removeprefix('Winner'): v for k, v in self._data.items() if k.startswith('Winner')})

	@property
	def loser(self) -> Player:
		return Player({k.removeprefix('Loser'): v for k, v in self._data.items() if k.startswith('Loser')})

	@property
	def winner_characters(self) -> Collection[Character]:
		return {Character(c).updated_copy({'IconUrl': c['ImageUrl']}) for c in self['WinnerCharacters']}

	@property
	def loser_characters(self) -> Collection[Character]:
		return {Character(c).updated_copy({'IconUrl': c['ImageUrl']}) for c in self['LoserCharacters']}

	@property
	def upset_factor(self) -> int | None:
		"""Requires start.gg API key; how much of an upset was this win, see https://www.pgstats.com/articles/introducing-spr-and-uf
		Can return a negative number if it wasn't an upset
		Returns None if this match's bracket was not on start.gg, either player could not be found on start.gg, etc"""
		seeds = self.event.seeds
		if seeds is None:
			return None
		winner_seed = seeds.get(self.winner)
		loser_seed = seeds.get(self.loser)
		if winner_seed is None or loser_seed is None:
			return None
		
		return rounds_from_victory(winner_seed) - rounds_from_victory(loser_seed)


class _HasWinnerAndLoser(Protocol):
	@property
	def winner_characters(self) -> Collection[Character]: ...

	@property
	def loser_characters(self) -> Collection[Character]: ...

	#Don't need to define player and opponent here, as MatchPOVMixin gets values from dict instead

	def __getitem__(self, key: str) -> JSON: ...

	@property
	def is_winner(self) -> bool: ...
	#We do need this though, whoops

class MatchWithPOVMixin:
	"""Mixin for matches (or PocketVideo) returned from methods on Player, so has properties from that player's point of view (e.g. is_winner)"""
	
	@property
	def player_characters(self: _HasWinnerAndLoser) -> Collection[Character]:
		"""Characters used, or empty if character data not filled in"""
		return self.winner_characters if self.is_winner else self.loser_characters

	@property
	def opponent_characters(self: _HasWinnerAndLoser) -> Collection[Character]:
		"""Characters used by opponent, or empty if character data not filled in"""
		return self.loser_characters if self.is_winner else self.winner_characters

	@property
	def player(self: _HasWinnerAndLoser) -> Player:
		"""Player that we originally queried for matches"""
		#There is probably no use for PlayerCharacterIDs to be honest, since we already have WinnerCharacters here
		return Player({'ID': self['PlayerID'], 'Name': self['PlayerName'], 'RegionShort': self['RegionShort']})

	@property
	def opponent(self: _HasWinnerAndLoser) -> Player:
		"""Player that is playing against the player we originally queried for matches
		This is not from the API, it is from the other one of winner/loser in Player"""
		return Player(self['Opponent'])

	@property
	def is_winner(self: _HasWinnerAndLoser) -> bool:
		"""Whether the player that we originally queried was the winner or not
		Added by methods on Player that return this, not from API"""
		return cast(bool, self['is_winner'])

class PocketMatch(_BasePocketMatch):
	"""Returned from /pocket/result/matches, etc """

	@classmethod
	def get_pocket_matches(cls, tournament: Tournament, game: Game) -> Sequence['PocketMatch']:
		"""Returns matches from this tournament where a certain game was played
		TODO: Sorted by presumably round? Event order?"""
		matches = []
		d: MutableMapping[str, JSON] = call_api_json(f'/pocket/result/matches/{tournament.id}/{game.id}')
		tournament_name: str = d.pop('ResultName') #Just easier that way to rename it for compatibility with _BasePocketMatch
		region_short: str = d.pop('ResultRegionShort')
		events: Sequence[MutableMapping[str, JSON]] = d.pop('Events')
		for event in events:
			event_matches: Sequence[MutableMapping[str, JSON]] = event.pop('Matches')
			for match in event_matches:
				#Both event and match have a PlayerCharacterIDs, but that might not be needed
				match.update(d)
				match['TourneyName'] = tournament_name
				match['RegionShort'] = region_short
				match.update(event)
				matches.append(PocketMatch(match))
		return matches
		
	@property
	def elo_movement(self) -> int | None:
		"""Elo that the winner gained from this match, or None if that has not been calculated yet"""
		return cast(int | None, self['EloMovement'])

class PocketMatchWithPOV(MatchWithPOVMixin, PocketMatch):
	"""Returned from /pocket/players/matches, similarly to PocketVideo we will flatten the return value a bit
	Actually this seems to be identical to PocketVideo except with EloMovement instead of VideoURL, and with a TourneyID on the Event"""

	@property
	def elo_movement(self) -> int | None:
		"""Elo that the winner gained from this match, or None if that has not been calculated yet"""
		return cast(int | None, self['EloMovement'])
	
class PocketVideo(MatchWithPOVMixin, _BasePocketMatch):
	"""Item of Events array returned from /pocket/player/videos
	Contains events that contain matches featuring a specific player that have videos
	We will flatten the return value in get_videos_of_player_in_game to return one of these for each match with the other info"""

	@cached_property
	def tournament(self) -> Tournament:
		return next(t for t in Tournament.search(self.tournament_name) if t.name == self.tournament_name)

	@property
	def url(self) -> URL:
		"""External URL to watch this video"""
		return cast(URL, self['YouTubeUrl'])
