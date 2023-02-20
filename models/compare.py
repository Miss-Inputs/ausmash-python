
from collections.abc import Sequence
from datetime import date
from fractions import Fraction
from typing import cast

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper

from .game import Game
from .player import Player
from .video import Video
from .match import Match
from .ranking import Ranking

class Comparison(DictWrapper):
	"""Comparison of stats returned from /compare/*/stats"""

	def __str__(self) -> str:
		return f'{self.player_1} vs {self.player_2} in {self.game}'

	@classmethod
	def compare_players(cls, game: Game | str, player1: Player, player2: Player, start_date: date | None=None, end_date: date | None=None) -> 'Comparison':
		"""Returns a comparison between two players for a certain game
		:param game: May be a Game, or the short name of a game
		:param player1: First player to compare, the "left" player if you will
		:param player2: The other player
		:param start_date: Only consider matches after (or on?) this date
		:param end_date: Only consider matches before (or on?) this date"""
		if isinstance(game, str):
			game = Game(game) #game
		params = {}
		if start_date:
			params['startDate'] = start_date
		if end_date:
			params['endDate'] = end_date
		return Comparison(call_api(f'compare/{game.id}/{player1.id}/{player2.id}/stats', params))

	@classmethod
	def compare_players_by_name(cls, game_shortname: str, player1_region: str, player1_name: str, player2_region: str, player2_name: str, start_date: date | None=None, end_date: date | None=None) -> 'Comparison':
		"""Like compare_players, but only needs region and name for each player"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		return Comparison(call_api(f'compare/{game_shortname}/{player1_region}/{player1_name}/{player2_region}/{player2_name}/stats', params))

	@property
	def player_1(self) -> Player:
		return Player(self['Player1'])

	@property
	def player_1_win_count(self) -> int:
		"""Number of sets where player_1 has played against player_2 and won"""
		return cast(int, self['Player1WinCount'])

	@property
	def player_1_win_rate(self) -> Fraction:
		return Fraction(self.player_1_win_count, self.total_sets)

	#PlayerNWinPercent not really needed, just player_N_win_rate * 100 rounded to nearest integer

	@property
	def player_1_elo(self) -> int:
		"""Player 1's current Elo
		TODO: Maybe null if player 1 was just recently added this week? Not sure"""
		return cast(int, self['Player1Elo'])

	@property
	def player_2(self) -> Player:
		return Player(self['Player2'])

	@property
	def player_2_win_count(self) -> int:
		"""Number of sets where player_2 has played against player_1 and won"""
		return cast(int, self['Player2WinCount'])

	@property
	def player_2_win_rate(self) -> Fraction:
		return Fraction(self.player_2_win_count, self.total_sets)

	@property
	def player_2_elo(self) -> int:
		"""Player 2's current Elo"""
		return cast(int, self['Player2Elo'])

	@property
	def players(self) -> tuple[Player, Player]:
		"""Both players being compared in this comparison"""
		return self.player_1, self.player_2

	@property
	def total_sets(self) -> int:
		"""Number of sets where these two have played against each other"""
		return self.player_1_win_count + self.player_2_win_count
	
	@property
	def game(self) -> Game:
		return Game(self['Game'])

def head_to_head(game: Game | str, player: Player, other: Player, start_date: date | None=None, end_date: date | None=None) -> Sequence[Match]:
	"""Matches featuring one player vs another player, sorted newest to oldest"""
	if isinstance(game, str):
		game = Game(game)
	params = {}
	if start_date:
		params['startDate'] = start_date.isoformat()
	if end_date:
		params['endDate'] = end_date.isoformat()
	return Match.wrap_many(call_api(f'compare/{game.id}/{player.id}/{other.id}/matches', params)['Matches'])

def head_to_head_videos(game: Game | str, player: Player, other: Player, start_date: date | None=None, end_date: date | None=None) -> Sequence[Video]:
	"""Videos featuring one player vs another player, sorted newest to oldest"""
	if isinstance(game, str):
		game = Game(game)
	params = {}
	if start_date:
		params['startDate'] = start_date.isoformat()
	if end_date:
		params['endDate'] = end_date.isoformat()
	return Video.wrap_many(call_api(f'compare/{game.id}/{player.id}/{other.id}/videos', params)['Videos'])

def compare_common_rankings(player: Player, game: Game, other: Player, start_date: date | None=None, end_date: date | None=None) -> Sequence[tuple[Ranking, int, int]]:
	"""(Ranking, player 1 rank, player 2 rank) for rankings that both of these players appear on (excluding HMs)"""
	params = {}
	if start_date:
		params['startDate'] = start_date.isoformat()
	if end_date:
		params['endDate'] = end_date.isoformat()
	return tuple((Ranking(ranking['Ranking']), ranking['Player1Rank'], ranking['Player2Rank']) for ranking in call_api(f'compare/{game.id}/{player.id}/{other.id}/rankings', params)['Rankings'])

#TODO: /compare/{gameid}/{player1id}/{player2id}/characters (not sure what it would be useful for, but it is there)
