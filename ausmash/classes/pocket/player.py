from collections.abc import Sequence
from typing import cast

from ausmash.api import call_api_json
from ausmash.typedefs import URL, IntID

from ..game import Game
from ..player import Player
from ..region import Region


class PocketPlayer(Player):
	"""Returned from /pocket/player/{player id}/{game id}, has various stats for a player in a certain game"""
	#ID field here is player ID, so it should Just Work as a player
	#TwitterUrl, TwitchUrl are also here
	
	@classmethod
	def get_for_game(cls, player: Player, game: Game | str) -> 'PocketPlayer':
		if isinstance(game, str):
			game = Game(game)
		return cls(call_api_json(f'pocket/player/{player.id}/{game.id}'))
	
	@property
	def game(self) -> Game:
		return Game(IntID(self['GameID']))

	@property
	def elo(self) -> int:
		#TODO: Presumably null if newly added?
		return cast(int, self['Elo'])

	@property
	def win_percentage(self) -> int:
		"""Rounded to nearest (floor? ceil?) integer out of 100"""
		return cast(int, self['WinPercentage'])

	@property
	def match_count(self) -> int:
		return cast(int, self['MatchCount'])

	@property
	def region(self) -> Region:
		return Region({'ID': self['PlayerRegionID'], 'Short': self['PlayerRegionShort']})

	@property
	def character_usage(self) -> Sequence[tuple[str, URL]]:
		"""(Name, stock icon URL) of most commonly used characters? or characters with most Elo gain?"""
		return tuple((c['Name'], c['ImageUrl']) for c in self['CharacterUsage'])

	@property
	def rankings(self) -> Sequence[tuple[str, str]]:
		"""Presumably current rankings? (Rank but with an ordinal, ranking name)"""
		return tuple((c['Place'], c['Ranking']) for c in self['Rankings'])
