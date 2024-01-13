import random
from collections.abc import Mapping
from typing import cast

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper

from .game import Game
from .player import Player


class TrueSkill(DictWrapper):
	"""Rating system invented by Microsoft for teams matches, used here for doubles
	Represents a normal distribution of what the player's skill could be
	Starts with µ (mu) = 1000 and σ (sigma) = not sure but presumably 1000/3
	International players do get TrueSkill if they team with an AU/NZ player it seems
	Hmm is this name still trademarked by Microsoft? Hopefully this won't get me into trouble"""
	#Note: Could use scipy.stats.norm if one wanted to make scipy a dependency, or import it locally
	#There is also a Python module for this: https://trueskill.org/

	@classmethod
	def get_trueskill(cls, player: Player) -> Mapping[Game, 'TrueSkill']:
		trueskills = cls.wrap_many(call_api(f'players/{player.id}/trueskill'))
		return {trueskill.game: trueskill for trueskill in trueskills}

	@property
	def player(self) -> Player:
		return Player(self['Player'])

	@property
	def game(self) -> Game:
		return Game(self['Game'])

	@property
	def mean(self) -> int | None:
		"""Perceived skill, µ in the TrueSkill formulas"""
		return cast(int | None, self['Mean'])
	
	@property
	def stdev(self) -> int | None:
		return cast(int | None, self['StandardDeviation'])

	@property
	def conservative_rating(self) -> int | None:
		"""Player's skill is probably (random sample from this normal distribution can be sometimes under this) at least this much, which is what Microsoft uses for their TrueSkill rankings to display the player rank
		Confidence is 99% that the player's skill is higher than this
		TrueSkill algorithms calculate this as mean - (stdev * 3), but 1 is subtracted because I don't know why"""
		return cast(int | None, self['ConservativeRating'])

	def get_random_possible_skill_level(self) -> float:
		"""Return random.gauss for this distribution, I dunno lol (just because it's there)
		:raises ValueError: if mean/stdev are None"""
		if not self.mean or not self.stdev:
			raise ValueError('TrueSkill is not calculated for this player')
		return random.gauss(self.mean, self.stdev)

	#TODO: Local/national previous/movement/peak, also all nullable
