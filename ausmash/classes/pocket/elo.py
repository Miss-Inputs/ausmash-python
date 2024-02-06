from collections.abc import Collection
from typing import cast

from ausmash.api import call_api_json
from ausmash.dictwrapper import DictWrapper
from ausmash.typedefs import IntID

from ..character import Character
from ..game import Game
from ..player import Player


class PocketElo(DictWrapper):
	"""Array item from /pocket/elo/, representing a subset of information about a player and their Elo for a certain game
	TODO: There is an ID field but I don't know what it identifies, as there is no /pocket/elo/{pocketeloid} or anything"""

	@classmethod
	def pocket_elo(cls, game: Game | str) -> Collection['PocketElo']:
		if isinstance(game, str):
			game = Game(game)
		return cls.wrap_many(call_api_json(f'pocket/elo/{game.id}'))

	@property
	def player(self) -> Player:
		data = {k.removeprefix('Player'): v for k, v in self._data.items() if k.startswith('Player')}
		data['SmashGGPlayerID'] = self['SmashGGPlayerID']
		return Player(data)

	@property
	def start_gg_player_id(self) -> IntID | None:
		"""start.gg player ID associated with this player, can be used in conjuction with start.gg's API and a query on player"""
		player_id: int | None = self['SmashGGPlayerID']
		return IntID(player_id) if player_id else None

	@property
	def elo(self) -> int:
		"""Elo score, without needing the /elo endpoint"""
		return cast(int, self['Elo'])

	@property
	def game(self) -> Game:
		"""Game that this Elo is for"""
		return Game({'ID': self['GameID']})

	@property
	def character(self) -> Character | None:
		"""TODO: Which one is this supposed to be? Most used? Most Elo gained? Most Elo change? Main from user profile?"""
		return Character({'ID': self['CharacterID'], 'IconUrl': self['CharacterImageUrl']}) if self['CharacterID'] else None
		
