from collections.abc import Collection, MutableMapping, Sequence
from datetime import date
from typing import Any, TypeVar

from ausmash.typedefs import ID

from .api import call_api
from .models.character import Character
from .models.character_player import CharacterPlayer
from .models.event import EventType
from .models.game import Game
from .models.player import Player
from .models.pocket.match import (PocketMatchWithPOV, PocketVideo,
                                  _BasePocketMatch)
from .models.match import Match
from .models.ranking import Ranking
from .models.region import Region
from .models.result import Result
from .models.elo import Elo

__doc__ = """Other API methods that I didn't feel like making into a class method of something in models, or want to import into here, for circular dependency reasons or whatever"""
__all__ = [
	'get_active_players',
	'get_matches_of_player_in_game',
	'get_players_of_character',
	'get_videos_of_player_in_game',
	'is_current_pr',
	'was_player_pr_during_time',
]

def get_players_of_character(char: Character) -> Collection[CharacterPlayer]:
	"""Players who play this character"""
	return CharacterPlayer.wrap_many(call_api(f'characters/{char.id}/players'))

_PlayerPocketMatchType = TypeVar('_PlayerPocketMatchType', bound=_BasePocketMatch)
def __flatten_pocket_match_array(player: Player, d: MutableMapping[str, Any], cls: type[_PlayerPocketMatchType]) -> Sequence[_PlayerPocketMatchType]:
	matches = []
	events: Sequence[MutableMapping[str, Any]] = d.pop('Events')
	for event in events:
		event_matches: Sequence[MutableMapping[str, Any]] = event.pop('Matches')
		for match in event_matches:
			#Both event and match have a PlayerCharacterIDs, but that might not be needed
			match.update(d) #Contains Player* fields, and GameID
			match.update(event)
			if match['WinnerID'] == player.id:
				match['is_winner'] = True
				match['Opponent'] = {k.removeprefix('Loser'): v for k, v in match.items() if k.startswith('Loser')}
			else:
				match['is_winner'] = False
				match['Opponent'] = {k.removeprefix('Winner'): v for k, v in match.items() if k.startswith('Winner')}
				
			matches.append(cls(match))
	return matches

def is_current_pr(player: Player, game: Game | str) -> bool:
	if isinstance(game, str):
		game = Game(game)
	rankings = Ranking.featuring_player(player)
	#Ignore top 40 rankings etc
	return any(ranking for ranking in (ranking for ranking in rankings if not ranking.is_probably_player_showcase) if ranking.is_active and ranking.game == game)

def get_videos_of_player_in_game(player: Player, game: Game | str) -> Sequence[PocketVideo]:
	"""Uses the Pocket API to return videos featuring a specified player playing a specified game"""
	if isinstance(game, str):
		game = Game(game)
	return __flatten_pocket_match_array(player, call_api(f'pocket/player/videos/{player.id}/{game.id}'), PocketVideo)

def get_matches_of_player_in_game(player: Player, game: Game | str) -> Sequence[PocketMatchWithPOV]:
	"""Uses the Pocket API to return matches featuring a specified player playing a specified game"""
	if isinstance(game, str):
		game = Game(game)
	return __flatten_pocket_match_array(player, call_api(f'pocket/player/matches/{player.id}/{game.id}'), PocketMatchWithPOV)

def was_player_pr_during_time(player: Player, game: Game | str, start_date: date | None=None, end_date: date | None=None) -> bool:
	if isinstance(game, str):
		game = Game(game)
	rankings = Ranking.featuring_player(player, start_date, end_date)
	#Ignore top 40 rankings etc
	return any(ranking for ranking in rankings if ranking.game == game and not ranking.is_probably_player_showcase)

def is_pr_win(self: _BasePocketMatch | Match) -> bool:
	if not self.loser:
		#Assume anyone not in the database (or untagged, perhaps deliberately due to being a side event) was not PR
		return False
	#TODO: Not entirely sure start_date and end_date are being used correctly here
	return was_player_pr_during_time(self.loser, self.game, start_date=self.date, end_date=self.date)

def get_active_players(game: Game | str, region: Region | str, season_start: date | None=None, season_end: date | None=None, minimum_events_to_count: int=1, series_to_exclude: Collection[str] | None=None, only_count_locals: bool=True) -> Collection[Player]:
	players: dict[Player, tuple[set[ID], set[ID]]] = {} #Locals tournament IDs, interstate tournament IDs
	for elo in Elo.for_game(game, region):
		#Basically just to filter by last active to make things easier, instead of just getting all players in region
		if season_start and elo.last_active < season_start:
			continue
		for result in Result.results_for_player(elo.player, season_start, season_end):
			tournament = result.tournament
			is_local = tournament.region.short_name == (region.short_name if isinstance(region, Region) else region)

			if only_count_locals and not is_local:
				continue

			if series_to_exclude and tournament.series.name in series_to_exclude:
				continue
			
			event = result.event
			if event.game.short_name != (game.short_name if isinstance(game, Game) else game):
				continue
			if event.is_redemption_bracket or event.is_side_bracket or event.type != EventType.Singles:
				continue #Well… we don't really need to? Should a player count as active if they only ever enter redemption or side brackets or doubles

			players.setdefault(elo.player, (set(), set()))[0 if is_local else 1].add(tournament.id)

	return {p for p, (locals, interstates) in players.items() if len(locals) + (0 if only_count_locals else len(interstates)) >= minimum_events_to_count}	
