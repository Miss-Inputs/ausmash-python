import itertools
from collections.abc import Collection, Mapping
from datetime import date, datetime, time, timedelta
from enum import IntEnum
from typing import cast
from zoneinfo import ZoneInfo

from ausmash.api import call_api_json
from ausmash.dictwrapper import DictWrapper
from ausmash.typedefs import IntID

from .game import Game
from .player import Player
from .region import Region


class EloBadge(IntEnum):
	"""Possible tier badges for Elo, with value = minimum required for that tier"""

	Bronze = 1000
	Silver = 1200
	Gold = 1400
	Platinum = 1600
	Diamond = 1800
	Master = 2000
	Grandmaster = 2500
	Elite = 3000


class Elo(DictWrapper):
	"""Elo data for one player for one game
	Players outside Australia/NZ do not get Elo calculated
	Hmm… /elo just has the game ID and player count basically, might as well ignore it (I guess other than to know what games are actively played?)
	"""

	@classmethod
	def all(cls) -> Collection['Elo']:
		"""Returns all Elo records for all games if you really wanted to do that"""
		return tuple(
			itertools.chain.from_iterable(
				cls.wrap_many(call_api_json(e['APILink'])) for e in call_api_json('/elo')
			)
		)

	@classmethod
	def for_game(
		cls, game: Game | str, region: Region | str | None = None
	) -> Collection['Elo']:
		"""All Elo records for a game, optionally only players in a certain region"""
		params = (
			{'region': region.short_name if isinstance(region, Region) else region}
			if region
			else None
		)
		if isinstance(game, str):
			game = Game(game)
		return cls.wrap_many(call_api_json(f'elo/game/{game.id}', params))

	@classmethod
	def for_player(cls, player: Player) -> Mapping[Game, 'Elo']:
		"""Returns empty dict if this player has never had Elo calculated - either they were just added to the database this week, or have never lived in Australia or New Zealand
		If a player used to live in Australia or New Zealand and is now tagged as being from some other country, then they will have an Elo of 1000 for every game they have played, but the peak Elo and last active date are still the same"""
		elos = Elo.wrap_many(call_api_json(f'players/{player.id}/elo'))
		return {elo.game: elo for elo in elos}

	@staticmethod
	def last_updated(day: date | None = None) -> datetime:
		"""Time when the Elo was last recalculated, ie. last Thursday.
		Can't remember the exact time but it's not like midnight, I think it was like 5am?"""
		if day is None:
			day = date.today()
		return datetime.combine(
			day + timedelta(days=4 - day.isoweekday()),
			time(5, 0),
			ZoneInfo('Australia/Queensland'),
		)

	@property
	def id(self) -> IntID:
		"""Mysteriously there is an ID field on here that doesn't seem to represent anything else, and doesn't have any operations using it"""
		return IntID(self['ID'])

	def __eq__(self, __o: object) -> bool:
		if not isinstance(__o, Elo):
			return False
		return self.elo == __o.elo

	def __hash__(self) -> int:
		return self.elo

	def __lt__(self, other: object) -> bool:
		if not isinstance(other, Elo):
			return NotImplemented
		return self.elo < other.elo

	@property
	def game(self) -> Game:
		"""Game that this player's Elo is for"""
		return Game(self['Game'])

	@property
	def player(self) -> Player:
		"""Player whose Elo this is for"""
		return Player(self['Player'])

	def __str__(self) -> str:
		return f'{self.player} in {self.game}'

	@property
	def elo(self) -> int:
		"""Elo value this week"""
		return cast(int, self['Elo'])

	@property
	def last_week_elo(self) -> int | None:
		"""What Elo was last week
		Returns None if player was only added last week and did not have Elo calculated then"""
		return cast(int | None, self['EloPrevious'])

	@property
	def local_rank(self) -> int | None:
		"""Rank of this player's elo amongst the rest of their region
		Returns None if player is not active"""
		return cast(int, self['RankLocal'])

	@property
	def national_rank(self) -> int | None:
		"""Rank of this player's elo amongst the rest of Australia (and maybe NZ? (TODO check that))
		Returns None if player is not active"""
		return cast(int, self['RankNational'])

	# TODO: Local/national previous/movement/peak, also all nullable

	@property
	def movement(self) -> int | None:
		"""Elo gained or lost compared to last week
		None if this player was only added this week or the week before so does not have Elo calculated for last week yet
		Should be equivalent to self.elo - self.elo_previous? But the field is already there I suppose"""
		return cast(int, self['EloMovement'])

	@property
	def peak(self) -> int | None:
		"""Highest Elo this player has ever had
		None if this player's Elo has always been lower than the starting amount (oof!)"""
		if self['PeakDate'] is None:
			# Otherwise it is still filled in as 1000, but that's not useful
			return None
		return cast(int, self['PeakElo'])

	@property
	def badge(self) -> EloBadge | None:
		"""Badge tier that should be displayed for this user"""
		if not self.peak:
			# Presumably, since the peak Elo is technically 1000, though badges are only shown on the Elo breakdown page on the site anyway (I think)
			return EloBadge.Bronze
		for badge in EloBadge:
			if self.peak >= badge:
				return badge
		raise AssertionError(
			"This shouldn't happen unless I did something wrong, Elo.peak is not None but it is under 1000"
		)

	@property
	def peak_date(self) -> date | None:
		"""Date on which this player had achieved peak Elo
		None if this player's Elo has always been lower than the starting amount (oof!)"""
		peak_date = self['PeakDate']
		return datetime.fromisoformat(peak_date).date() if peak_date else None

	@property
	def days_since_peak(self) -> timedelta | None:
		"""Days from today since when the player was at their highest Elo, or None if this player's Elo has always been lower than the starting Elo"""
		if not self.peak_date:
			return None
		return date.today() - self.peak_date

	@property
	def last_active(self) -> date:
		"""Last known date that this player has participated in a tournament (that impacted Elo in some way)
		This is the date of the actual event and not necessarily the Thursday when Elo is updated, though this value is still
		only updated every Thursday (i.e. if this player has entered an event this week and it is not Thursday yet, this will
		not show that until Thursday)"""
		return datetime.fromisoformat(self['LastActive']).date()

	@property
	def days_since_activity(self) -> timedelta:
		"""How long since last_active"""
		return date.today() - self.last_active

	@property
	def is_active(self) -> bool:
		"""If this player is considered active in this game
		https://twitter.com/URNotShitashi/status/1621768528586997760: "Been to a tournament in the last 3 months\" """
		today = date.today()
		months = ((today.year - self.last_active.year) * 12) + (
			today.month - self.last_active.month
		)
		return months < 3


def probability_of_winning(player_elo: int, opponent_elo: int) -> float:
	"""Returns what is mathematically the chance that one player will win a match against another
	Also known as the "expected score", which is actually possibility of winning + half the possibility of drawing… hmm
	A draw in the Elo system is considered half a win and half a loss, but that does not happen at Smash tournaments"""
	return 1 / (1 + (10 ** ((opponent_elo - player_elo) / 400)))
