from collections.abc import Collection, Sequence
from typing import cast
from datetime import date

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper
from ausmash.resource import Resource
from ausmash.typedefs import ID, URL

from .character import Character
from .game import Game
from .player import Player
from .region import Region


class Ranking(Resource):
	"""Individual instance of a power ranking, player showcase, etc
	See also RankingSequence, Rank
	Start date is not currently exposed via the API, and I never quite figured out if that's when
	the PR season that this ranking took data from started, or when this ranking started being the most current one…"""

	base_url = "rankings"

	@classmethod
	def all(cls) -> Sequence['Ranking']:
		return cls.wrap_many(call_api('rankings'))

	@classmethod
	def all_active(cls) -> Collection['Ranking']:
		"""All rankings that are currently the current one in their sequence"""
		return cls.wrap_many(call_api('rankings/active'))

	@classmethod
	def for_region(cls, region: Region | str) -> Sequence['Ranking']:
		if isinstance(region, Region):
			region = region.short_name
		return cls.wrap_many(call_api(f'rankings/byregion/{region}'))

	@classmethod
	def featuring_player(cls, player: Player, start_date: date | None=None, end_date: date | None=None) -> Sequence['Ranking']:
		"""Rankings that a certain player has ever been on, from newest to oldest, optionally within a certain timeframe
		TODO: Document if start_date or end_date are inclusive/exclusive (because I dunno/forgor)"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		return Ranking.wrap_many(call_api(f'players/{player.id}/rankings', params))

	@property
	def game(self) -> Game:
		return Game(self['GameShort'])

	@property
	def link(self) -> URL:
		"""An external link to where this ranking was posted, e.g. a Twitter post announcing it"""
		return cast(URL, self['Link'])

	@property
	def sequence(self) -> 'RankingSequence':
		"""The series that this ranking is an instance of, e.g. "Cool Region Power Rankings"
		"""
		return RankingSequence(self['Sequence'])

	@property
	def version(self) -> str:
		"""The version of this PR in the sequence, e.g. "Sep-Dec 2022"
		Does not necessarily have to be in any format"""
		return cast(str, self['Version'])
	
	@property
	def caption(self) -> str:
		"""HTML fragment, often just containing the image itself, but could contain text
		Maybe this is nullable?"""
		return cast(str, self['Body'])
	
	@property
	def name(self) -> str:
		return f'{self["SequenceName"]} {self.version}'

	def __str__(self) -> str:
		return self.name

	@property
	def ranks(self) -> Sequence['Rank']:
		try:
			return Rank.wrap_many(self['Players'])
		except KeyError:
			#TODO: This is just dodgy error handling with the potential for _complete to get a 500 error (as it seems to with nationwide rankings?), it's not nullable or anything
			return []

	@property
	def players(self) -> Sequence[Player]:
		return tuple(rank.player for rank in self.ranks)

	def find_player(self, player: Player) -> 'Rank | None':
		return next((rank for rank in self.ranks if rank.player == player), None)

	@property
	def region(self) -> Region | None:
		"""The region this ranking is for. It can be null in the case of national rankings, etc"""
		region_short: str | None = self['RegionShort']
		return Region(region_short) if region_short else None

	@property
	def is_probably_player_showcase(self) -> bool:
		return 'Power Ranking' not in self['SequenceName']

	@property
	def is_active(self) -> bool:
		#TODO: Please say there is a better way to do this
		return self in Ranking.all_active()

	@classmethod
	def get_player_ranks_during_time(cls, player: Player, game: Game | str, start_date: date | None=None, end_date: date | None=None) -> Sequence['Rank']:
		"""Return any ranks the player had during a timeframe"""
		if isinstance(game, str):
			game = Game(game)
		rankings = cls.featuring_player(player, start_date, end_date)
		return [rank for rank in (ranking.find_player(player) for ranking in rankings if ranking.game == game) if rank]

	@classmethod
	def was_player_pr_during_time(cls, player: Player, game: Game | str, start_date: date | None=None, end_date: date | None=None) -> bool:
		"""Returns true if a player was on a PR that was current for a certain timeframe, excluding player showcases"""
		if isinstance(game, str):
			game = Game(game)
		rankings = cls.featuring_player(player, start_date, end_date)
		return any(ranking for ranking in rankings if ranking.game == game and not ranking.is_probably_player_showcase)

class Rank(DictWrapper):
	"""Item of Players array in Ranking"""
	@property
	def rank(self) -> int:
		return cast(int, self['Rank'])

	@property
	def player(self) -> Player:
		return Player(self['Player'])

	@property
	def tier(self) -> str:
		"""Tier of this player within the ranking, or - if the ranking does not use tiers"""
		return cast(str, self['RankingScale']) 

	@property
	def characters(self) -> Collection[Character]:
		return Character.wrap_many(self['Characters'])

class RankingSequence(DictWrapper):
	"""An ongoing series of Rankings, where one would obsolete the previous after it is released"""

	@classmethod
	def all(cls) -> Collection['RankingSequence']:
		return cls.wrap_many(call_api('rankingsequences'))
	
	@property
	def id(self) -> ID:
		return ID(self['ID'])

	@property
	def name(self) -> str:
		return cast(str, self['Name'])

	@property
	def region(self) -> Region | None:
		"""Region that these rankings are for, or None if not applicable (e.g. national rankings)"""
		region_short = self.get('RegionShort')
		return Region(region_short) if region_short else None

	@property
	def game(self) -> Game:
		return Game(self['GameShort'])

	@property
	def rankings(self) -> Sequence[Ranking]:
		"""Presumably, the first element is the most recent?"""
		return Ranking.wrap_many(call_api(f'rankings/bysequence/{self.id}'))
	
	def get_ranks_for_player_during_time(self, player: Player, game: Game | str, start_date: date | None=None, end_date: date | None=None) -> Sequence['Rank']:
		"""Return any ranks in this sequence the player had during a timeframe"""
		if isinstance(game, str):
			game = Game(game)
		rankings = Ranking.featuring_player(player, start_date, end_date)
		return [rank for rank in (ranking.find_player(player) for ranking in rankings if ranking.sequence == self and ranking.game == game) if rank]
