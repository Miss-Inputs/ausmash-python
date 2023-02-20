from collections.abc import Collection, Sequence
from datetime import \
    date  # pylint: disable=unused-import #Pylint, are you on drugs? (I guess it's confused by a property being named date?)
from typing import cast

from ausmash.api import call_api
from ausmash.dictwrapper import DictWrapper
from ausmash.typedefs import JSONDict

from .character import Character
from .event import Event
from .game import Game
from .player import Player
from .tournament import Tournament


class Match(DictWrapper):
	"""Represents a full competitive set/match (grand finals bracket reset in double elimination is two Matches)."""

	@classmethod
	def matches_at_event(cls, event: Event) -> Sequence['Match']:
		"""Ordered from last rounds to starting rounds"""
		match_data = call_api(f'events/{event.id}/matches')
		#Not much point copying event._data into here
		if len(match_data) > 1: #Yes, somehow you can have a bracket with only one match (see event ID 12325 for how this can happen, where grand finals is uploaded as a separate phase)
			if match_data[0]['MatchName'] == 'GF' and match_data[1]['MatchName'] == 'GF':
				#Girlfriend bracket reset happened, make the round identifier unique
				match_data[0]['MatchName'] = 'GF2'
			#Hmm do I really want to do this? It means it might break comparisons for other places Matches are returned
		return Match.wrap_many(match_data)

	@classmethod
	def get_matches_from_time(cls, player: Player, start_date: date | None=None, end_date: date | None=None) -> Sequence['Match']:
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
	def round(self) -> str:
		"""Short string identifying this round within the event, e.g. W1, L1, GF
		Does not return anything like WF or LF"""
		return cast(str, self['MatchName'])

	def __str__(self) -> str:
		return f'{self.event.name} {self.round} - {self.winner_name} vs {self.loser_name}'

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
	def tournament(self) -> Tournament:
		return Tournament(self['Tourney'])

	@property
	def event(self) -> Event:
		return Event(self['Event'])
	
	@property
	def game(self) -> Game:
		"""Which video game was being played (by looking up Event)"""
		return self.event.game

	@property
	def date(self) -> date:
		"""Returns the date that this match occurred, which is not necessarily accurate as it's the singular date listed for the tournament, so for multi-day tournaments this would be the first day"""
		return self.tournament.date

	@property
	def winner_name(self) -> str:
		"""This is still filled in even if winner is not tagged and hence .winner is None"""
		return cast(str, self['WinnerName'])
	
	@property
	def loser_name(self) -> str:
		"""This is still filled in even if loser is not tagged and hence .loser is None"""
		return cast(str, self['LoserName'])

	@property
	def pool(self) -> int | None:
		"""Not sure this is used anymore"""
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
		wins = self.game_wins
		if wins is not None:
			losses = self.game_losses
			if losses is not None:
				#Should always be if wins is also not None but anyway
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
		return cast(int | None, self['TrueSkillWinner1OldScore']), cast(int | None, self['TrueSkillWinner2OldScore'])

	@property
	def loser_old_trueskill(self) -> tuple[int | None, int | None]:
		"""Returns the losers' TrueSkill before this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillLoser1OldScore']), cast(int | None, self['TrueSkillLoser2OldScore'])

	@property
	def winner_new_trueskill(self) -> tuple[int | None, int | None]:
		"""Returns the winners' TrueSkill after this match, with either element being None if winner did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillWinner1NewScore']), cast(int | None, self['TrueSkillWinner2NewScore'])

	@property
	def loser_new_trueskill(self) -> tuple[int | None, int | None]:
		"""Returns the loser's TrueSkill after this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillLoser1NewScore']), cast(int | None, self['TrueSkillLoser2NewScore'])

	@property
	def trueskill_winner_movement(self) -> tuple[int | None, int | None]:
		"""How much TrueSkill mean each winner gained from this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillWinner1Movement']), cast(int | None, self['TrueSkillWinner2Movement'])

	@property
	def trueskill_loser_movement(self) -> tuple[int | None, int | None]:
		"""How much TrueSkill mean each loser lost from this match, with either element being None if loser did not have TrueSkill calculated (not in the database, or has never lived in Australia/NZ) or if this is not a teams match"""
		return cast(int | None, self['TrueSkillLoser1Movement']), cast(int | None, self['TrueSkillLoser2Movement'])
