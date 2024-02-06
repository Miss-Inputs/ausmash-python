"""Other API methods that I didn't feel like making into a class method of something in models, or want to import into here, for circular dependency reasons or whatever"""
from collections.abc import Collection, MutableMapping, Sequence
from datetime import date
from typing import TYPE_CHECKING, Any, TypeVar

from .api import call_api_json
from .classes.character_player import CharacterPlayer
from .classes.elo import Elo
from .classes.event import EventType
from .classes.game import Game
from .classes.player import Player
from .classes.pocket.match import PocketMatchWithPOV, PocketVideo, _BasePocketMatch
from .classes.ranking import Ranking
from .classes.region import Region
from .classes.result import Result

if TYPE_CHECKING:
	from .classes.character import Character
	from .classes.match import Match
	from .typedefs import IntID

__all__ = [
	'get_active_players',
	'get_matches_of_player_in_game',
	'get_players_of_character',
	'get_videos_of_player_in_game',
	'is_current_pr',
]


def get_players_of_character(char: 'Character') -> Collection[CharacterPlayer]:
	"""Players who play this character"""
	return CharacterPlayer.wrap_many(call_api_json(f'characters/{char.id}/players'))


_PlayerPocketMatchType = TypeVar('_PlayerPocketMatchType', bound=_BasePocketMatch)


def __flatten_pocket_match_array(
	player: Player, d: MutableMapping[str, Any], cls: type[_PlayerPocketMatchType]
) -> Sequence[_PlayerPocketMatchType]:
	matches = []
	events: Sequence[MutableMapping[str, Any]] = d.pop('Events')
	for event in events:
		event_matches: Sequence[dict[str, Any]] = event.pop('Matches')
		for match in event_matches:
			# Both event and match have a PlayerCharacterIDs, but that might not be needed
			match.update(d)  # Contains Player* fields, and GameID
			match.update(event)
			if match['WinnerID'] == player.id:
				match['is_winner'] = True
				match['Opponent'] = {
					k.removeprefix('Loser'): v for k, v in match.items() if k.startswith('Loser')
				}
			else:
				match['is_winner'] = False
				match['Opponent'] = {
					k.removeprefix('Winner'): v for k, v in match.items() if k.startswith('Winner')
				}

			matches.append(cls(match))
	return matches


def is_current_pr(player: Player, game: Game | str) -> bool:
	"""Returns true if the player is on a currently active PR for a game, attempting to exclude player showcases"""
	if isinstance(game, str):
		game = Game(game)
	rankings = Ranking.featuring_player(player)
	# Ignore top 40 rankings etc
	return any(
		ranking
		for ranking in (ranking for ranking in rankings if not ranking.is_probably_player_showcase)
		if ranking.is_active and ranking.game == game
	)


def get_videos_of_player_in_game(player: Player, game: Game | str) -> Sequence[PocketVideo]:
	"""Uses the Pocket API to return videos featuring a specified player playing a specified game"""
	if isinstance(game, str):
		game = Game(game)
	return __flatten_pocket_match_array(
		player, call_api_json(f'pocket/player/videos/{player.id}/{game.id}'), PocketVideo
	)


def get_matches_of_player_in_game(player: Player, game: Game | str) -> Sequence[PocketMatchWithPOV]:
	"""Uses the Pocket API to return matches featuring a specified player playing a specified game"""
	if isinstance(game, str):
		game = Game(game)
	return __flatten_pocket_match_array(
		player, call_api_json(f'pocket/player/matches/{player.id}/{game.id}'), PocketMatchWithPOV
	)


def is_pr_win(self: '_BasePocketMatch | Match') -> bool:
	"""Returns true if a Match represents a win against a player that was PR at the time
	This might not work properly…"""
	if not self.loser:
		# Assume anyone not in the database (or untagged, perhaps deliberately due to being a side event) was not PR
		return False
	# TODO: Not entirely sure start_date and end_date are being used correctly here
	return Ranking.was_player_pr_during_time(
		self.loser, self.game, start_date=self.date, end_date=self.date
	)


def get_active_players(
	game: Game | str | None,
	region: Region | str | None,
	season_start: date | None = None,
	season_end: date | None = None,
	minimum_events_to_count: int = 1,
	series_to_exclude: Collection[str] | None = None,
	*,
	only_count_locals: bool = True,
	only_count_main_bracket: bool = True,
) -> Collection[Player]:
	"""Returns a list of players that are considered active according to certain optional parameters
	This would not return any player that is too new to have Elo calculated if game is specified, as it uses that to check tournament activity
	@param game: Only count players who entered events for a particular game, or None for all Smash players
	@param region: Region to get active players from, or None for anywhere
	@param season_start: Count tournaments starting from this date
	@param season_end: Count tournaments up until this date, so you can get active players for a PR season
	@param minimum_events_to_count: Require players to have attended this many tournaments to be considered active
	@param series_to_exclude: If specified, list of TournamentSeries names to not count, e.g. an arcadian series if that makes sense for whatever you are using this method for
	@param only_count_locals: Don't count tournaments outside of region
	@param only_count_main_bracket: Don't count a player as attending a tournament if they only entered redemption, a side bracket, or doubles
	"""

	players: dict[
		Player, tuple[set['IntID'], set['IntID']]
	] = {}  # Locals tournament IDs, interstate tournament IDs

	players_to_check = (
		(
			e.player
			for e in Elo.for_game(game, region)
			if not season_start or (e.last_active >= season_start)
		)
		if game
		else Player.all(region)
	)
	for player in players_to_check:
		for result in Result.results_for_player(player, season_start, season_end):
			tournament = result.tournament
			if region:
				is_local = tournament.region.short_name == (
					region.short_name if isinstance(region, Region) else region
				)

				if only_count_locals and not is_local:
					continue
			else:
				is_local = True

			if series_to_exclude and tournament.series.name in series_to_exclude:
				continue

			event = result.event
			if game and (
				event.game.short_name != (game.short_name if isinstance(game, Game) else game)
			):
				continue
			if only_count_main_bracket and (
				event.is_redemption_bracket
				or event.is_side_bracket
				or event.type != EventType.Singles
			):
				continue

			players.setdefault(player, (set(), set()))[0 if is_local else 1].add(tournament.id)

	return {
		p
		for p, (local_ids, interstate_ids) in players.items()
		if len(local_ids) + (0 if only_count_locals else len(interstate_ids))
		>= minimum_events_to_count
	}
