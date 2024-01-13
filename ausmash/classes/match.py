from collections.abc import Collection, Sequence
from datetime import (
	date,  # pylint: disable=unused-import #Pylint, are you on drugs? (I guess it's confused by a property being named date?)
)
from functools import cache, cached_property
from typing import TYPE_CHECKING, cast

from ausmash.api import call_api
from ausmash.classes.result import rounds_from_victory
from ausmash.dictwrapper import DictWrapper
from ausmash.typedefs import ID, JSONDict

from .character import Character
from .event import BracketStyle, Event, EventType
from .player import Player
from .tournament import Tournament

if TYPE_CHECKING:
	from .game import Game


@cache
def _number_of_rounds_in_event(event: Event, bracket_side: str | None) -> int:
	return len([m for m in Match.matches_at_event(event) if m.round_bracket_side == bracket_side])


class Match(DictWrapper):
	"""Represents a full competitive set/match (grand finals bracket reset in double elimination is two Matches)."""

	@classmethod
	def matches_at_event(cls, event: Event) -> Sequence['Match']:
		"""Ordered from last rounds to starting rounds"""
		match_data = call_api(f'events/{event.id}/matches')
		# Not much point copying event._data into here
		if (len(match_data) > 1) and (
			match_data[0]['MatchName'] == 'GF' and match_data[1]['MatchName'] == 'GF'
		):
			# Girlfriend bracket reset happened, make the round identifier unique
			match_data[0]['MatchName'] = 'GF2'
		# Hmm do I really want to do this? It means it might break comparisons for other places Matches are returned
		return Match.wrap_many(match_data)

	@classmethod
	def get_matches_from_time(
		cls, player: Player, start_date: date | None = None, end_date: date | None = None
	) -> Sequence['Match']:
		"""All singles matches that this player was in, optionally within a certain timeframe, from newest to oldest"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		return Match.wrap_many(call_api(f'players/{player.id}/matches', params))

	@classmethod
	def matches_of_character(cls, character: Character) -> Sequence['Match']:
		"""Matches that have character data recorded as this character being used, newest to oldest"""
		return Match.wrap_many(call_api(f'characters/{character.id}/matches'))

	@classmethod
	def wins_of_character(cls, character: Character) -> Sequence['Match']:
		"""Matches that have character data recorded as the winner using this character, newest to oldest"""
		return Match.wrap_many(call_api(f'characters/{character.id}/matcheswins'))

	@classmethod
	def losses_of_character(cls, character: Character) -> Sequence['Match']:
		"""Matches that have character data recorded as the loser using this character, newest to oldest"""
		return Match.wrap_many(call_api(f'characters/{character.id}/matcheslosses'))

	@property
	def id(self) -> ID:
		"""Unique ID"""
		return ID(self['ID'])

	def __hash__(self) -> int:
		return hash(self.id)

	@property
	def round_name(self) -> str:
		"""Short string identifying this round within the event, e.g. W1, L1, GF
		Does not return anything like WF or LF"""
		return cast(str, self['MatchName'])

	@property
	def round_number(self) -> int | None:
		"""Round number, or None if not applicable (does not really make sense for round robin)"""
		bracket_style = self.event.bracket_style
		if bracket_style == BracketStyle.RoundRobin:
			return None
		try:
			return int(self.round_name[1:])
		except ValueError:
			return None

	@property
	def round_bracket_side(self) -> str | None:
		"""A description of the side of bracket this match was in (Winners, Losers), etc, or None if not applicable
		Only applicable for double elimination"""
		if self.event.bracket_style != BracketStyle.DoubleElimination:
			return None
		return {'W': 'Winners', 'L': 'Losers', 'G': 'Grands'}.get(self.round_name[0])

	@cached_property
	def round_full_name(self) -> str:
		"""A readable name for this round, including describing WF as Winners Finals etc
		Might not be unique for round robins"""
		bracket_style = self.event.bracket_style
		if bracket_style == BracketStyle.RoundRobin:
			# Note: Very rarely this is "RR Pool 0" which looks silly but not much else you can return for this
			return f'RR Pool {self.pool}'
		round_number = self.round_number
		if bracket_style == BracketStyle.Swiss:
			return f'Swiss Pool {self.pool} Round {round_number}'

		round_name = self.round_name
		if round_name == 'GF':
			return 'Grand Finals'
		if round_name == 'GF2':
			return 'Grand Finals Bracket Reset'
		number_of_rounds = _number_of_rounds_in_event(self.event, self.round_bracket_side)
		side = self.round_bracket_side

		if round_number == number_of_rounds:
			name = 'Finals'
		elif round_number == number_of_rounds - 1:
			name = 'Semifinals'
		elif number_of_rounds > 4 and round_number == number_of_rounds - 2:
			name = 'Quarterfinals'
		else:
			name = f'Round {round_number}'
		if not side:
			return name
		return f'{side} {name}'

	def __str__(self) -> str:
		return f'{self.event.name} {self.round_name} - {self.winner_name} vs {self.loser_name}'

	@property
	def winner(self) -> Player | None:
		"""Returns None if the winner is not in the database, in which case you would need to use winner_name, or if match is not singles"""
		return Player(self['Winner']) if self['Winner'] else None

	@property
	def loser(self) -> Player | None:
		"""Returns None if the loser is not in the database, in which case you would need to use loser_name, or if match is not singles"""
		return Player(self['Loser']) if self['Loser'] else None

	@property
	def doubles_winner(self) -> tuple[Player | None, Player | None]:
		"""The team of two players who won this set, where either player is None if they are not in the database, or this is not a doubles set"""
		team_1: JSONDict | None = self['TeamWinner1']
		team_2: JSONDict | None = self['TeamWinner2']
		return Player(team_1) if team_1 else None, Player(team_2) if team_2 else None

	@property
	def doubles_loser(self) -> tuple[Player | None, Player | None]:
		"""The team of two players who lost this set, where either player is None if they are not in the database, or this is not a doubles set"""
		team_1: JSONDict | None = self['TeamLoser1']
		team_2: JSONDict | None = self['TeamLoser2']
		return Player(team_1) if team_1 else None, Player(team_2) if team_2 else None

	@property
	def players(self) -> set[Player]:
		"""All players that are involved in this match and tagged"""
		return cast(
			set[Player],
			({self.winner, self.loser}.union(self.doubles_winner).union(self.doubles_loser))
			- {None},
		)

	@property
	def tournament(self) -> Tournament:
		"""Tournament that this match happened at"""
		return Tournament(self['Tourney'])

	@property
	def event(self) -> Event:
		"""Tournament that this match happened in"""
		return Event(self['Event'])

	@property
	def game(self) -> 'Game':
		"""Which video game was being played (by looking up Event)"""
		return self.event.game

	@property
	def date(self) -> date:
		"""Returns the date that this match occurred, which is not necessarily accurate as it's the singular date listed for the tournament, so for multi-day tournaments this would be the first day"""
		return self.tournament.date

	@property
	def winner_name(self) -> str:
		"""This is still filled in even if winner is not tagged and hence .winner is None
		This is also present for doubles matches, which may be a team name, or two player names separated by / (but this is not necessarily in the same order as doubles_winner)"""
		return cast(str, self['WinnerName'])

	@property
	def loser_name(self) -> str:
		"""This is still filled in even if loser is not tagged and hence .loser is None
		This is also present for doubles matches, which may be a team name, or two player names separated by / (but this is not necessarily in the same order as doubles_loser)"""
		return cast(str, self['LoserName'])

	@property
	def winner_description(self) -> str:
		"""String representation of the winner, with an unknown region if not tagged"""
		winner = self.winner
		if winner:
			return str(winner)
		if self.event.type == EventType.Teams:
			doubles_winner_description = self.doubles_winner_description
			assert doubles_winner_description
			return ' + '.join(doubles_winner_description)
		return f'[???] {self.winner_name}'

	@property
	def loser_description(self) -> str:
		"""String representation of the loser, with an unknown region if not tagged"""
		loser = self.loser
		if loser:
			return str(loser)
		if self.event.type == EventType.Teams:
			doubles_loser_description = self.doubles_loser_description
			assert doubles_loser_description
			return ' + '.join(doubles_loser_description)
		return f'[???] {self.loser_name}'

	@cached_property
	def doubles_winner_description(self) -> tuple[str, str] | None:
		"""String representation of each winner, with unknown region if not tagged, or None if this is not a doubles match"""
		if self.event.type == EventType.Singles:
			return None
		winner_1, winner_2 = self.doubles_winner
		if winner_1 and winner_2:
			return str(winner_1), str(winner_2)
		if ' / ' not in self.winner_name:
			return f'{self.winner_name} 1', f'{self.winner_name} 2'
		# Well I guess we hope no untagged players have a slash in their names
		winner_name_a, winner_name_b = self.winner_name.split(' / ', 1)
		if winner_1:
			# Winner 1 is tagged but winner 2 is not, but winner_name can be out of order, so winner 2's name is whichever one winner 1 is not
			winner_name_2 = winner_name_a if winner_1.name == winner_name_b else winner_name_b
			return str(winner_1), f'[???] {winner_name_2}'
		if winner_2:
			# winner 1 is not tagged but winner 2 is, but winner_name can be out of order, so their name is whichever one winner 2 is not
			winner_name_1 = winner_name_a if winner_2.name == winner_name_b else winner_name_b
			return f'[???] {winner_name_1}', str(winner_2)
		return f'[???] {winner_name_a}', f'[???] {winner_name_b}'

	@cached_property
	def doubles_loser_description(self) -> tuple[str, str] | None:
		"""String representation of each loser, with unknown region if not tagged, or None if this is not a doubles match"""
		if self.event.type == EventType.Singles:
			return None
		loser_1, loser_2 = self.doubles_loser
		if loser_1 and loser_2:
			return str(loser_1), str(loser_2)
		if ' / ' not in self.loser_name:
			return f'{self.loser_name} 1', f'{self.loser_name} 2'
		loser_name_a, loser_name_b = self.loser_name.split(' / ', 1)
		if loser_1:
			loser_name_2 = loser_name_a if loser_1.name == loser_name_b else loser_name_b
			return str(loser_1), f'[???] {loser_name_2}'
		if loser_2:
			loser_name_1 = loser_name_a if loser_2.name == loser_name_b else loser_name_b
			return f'[???] {loser_name_1}', str(loser_2)
		return f'[???] {loser_name_a}', f'[???] {loser_name_b}'

	@property
	def pool(self) -> int | None:
		"""If the event was round robin pools, which pool this match happened in"""
		return cast(int | None, self['Pool'])

	@property
	def game_wins(self) -> int | None:
		"""Winner won this many individual games. This can sometimes be null if the game score was not recorded, but that shouldn't happen often"""
		return cast(int | None, self['ScoreWins'])

	@property
	def game_losses(self) -> int | None:
		"""Loser won this many individual games. This can sometimes be null if the game score was not recorded, but that shouldn't happen often"""
		return cast(int | None, self['ScoreLosses'])

	@property
	def game_count(self) -> int | None:
		"""Total games in this set, or None if this data is unavailable"""
		wins = self.game_wins
		if wins is not None:
			losses = self.game_losses
			if losses is not None:
				# Should always be if wins is also not None but anyway
				return wins + losses
		return None

	@property
	def winner_characters(self) -> Collection[Character]:
		"""Winner used these characters, or empty collection if character data has not been entered"""
		return Character.wrap_many(self['WinnerCharacters'])

	@property
	def loser_characters(self) -> Collection[Character]:
		"""Winner used these characters, or empty collection if character data has not been entered"""
		return Character.wrap_many(self['LoserCharacters'])

	@property
	def winner_old_elo(self) -> int | None:
		"""Returns the winner's Elo before this match, or None if winner did not have Elo calculated (not in the database, or has never lived in Australia/NZ) or if this is not a singles match"""
		return cast(int | None, self['EloWinnerOldScore'])

	@property
	def loser_old_elo(self) -> int | None:
		"""Returns the loser's Elo before this match, or None if loser did not have Elo calculated (not in the database, or has never lived in Australia/NZ) or if this is not a singles match"""
		return cast(int | None, self['EloLoserOldScore'])

	@property
	def winner_new_elo(self) -> int | None:
		"""Returns the winner's Elo after this match, or None if winner does not have Elo calculated (not in the database, or has never lived in Australia/NZ), or if this is not a singles match, ie: winner_old_elo + elo_movement"""
		return cast(int | None, self['EloWinnerNewScore'])

	@property
	def loser_new_elo(self) -> int | None:
		"""Returns the loser's Elo after this match, or None if loser does not have Elo calculated (not in the database, or has never lived in Australia/NZ), or if this is not a singles match, ie: loser_old_elo - elo_movement"""
		return cast(int | None, self['EloLoserNewScore'])

	@property
	def elo_movement(self) -> int | None:
		"""None if tournament is too recent (Elo for this week hasn't been processed yet), or if one of the players is outside Australia/NZ and has never lived there, or if this is not a singles match
		Should be equivalent to winner_new_elo - winner_old_elo I guess"""
		return cast(int | None, self['EloMovement'])

	@property
	def winner_old_trueskill(self) -> tuple[int | None, int | None]:
		"""Returns the winners' TrueSkill before this match, with either element being None if winner did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillWinner1OldScore']), cast(
			int | None, self['TrueSkillWinner2OldScore']
		)

	@property
	def loser_old_trueskill(self) -> tuple[int | None, int | None]:
		"""Returns the losers' TrueSkill before this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillLoser1OldScore']), cast(
			int | None, self['TrueSkillLoser2OldScore']
		)

	@property
	def winner_new_trueskill(self) -> tuple[int | None, int | None]:
		"""Returns the winners' TrueSkill after this match, with either element being None if winner did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillWinner1NewScore']), cast(
			int | None, self['TrueSkillWinner2NewScore']
		)

	@property
	def loser_new_trueskill(self) -> tuple[int | None, int | None]:
		"""Returns the loser's TrueSkill after this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillLoser1NewScore']), cast(
			int | None, self['TrueSkillLoser2NewScore']
		)

	@property
	def trueskill_winner_movement(self) -> tuple[int | None, int | None]:
		"""How much TrueSkill mean each winner gained from this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillWinner1Movement']), cast(
			int | None, self['TrueSkillWinner2Movement']
		)

	@property
	def trueskill_loser_movement(self) -> tuple[int | None, int | None]:
		"""How much TrueSkill mean each loser lost from this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillLoser1Movement']), cast(
			int | None, self['TrueSkillLoser2Movement']
		)

	@property
	def upset_factor(self) -> int | None:
		"""Requires start.gg API key; how much of an upset was this win, see https://www.pgstats.com/articles/introducing-spr-and-uf
		Can return a negative number if it wasn't an upset
		Returns None if this match's bracket was not on start.gg, either player could not be found on start.gg, etc"""
		seeds = self.event.seeds
		if seeds is None:
			return None
		winner_seed = seeds.get(self.winner or self.winner_name)
		loser_seed = seeds.get(self.loser or self.loser_name)
		if winner_seed is None or loser_seed is None:
			return None

		return rounds_from_victory(winner_seed) - rounds_from_victory(loser_seed)
