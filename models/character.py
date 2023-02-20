from collections.abc import Collection, Mapping
from typing import cast

from ausmash.api import call_api
from ausmash.resource import Resource
from ausmash.typedefs import URL

from .game import Game

class Character(Resource):
	"""A playable character as they appear in one particular game"""
	base_url = 'characters'

	@classmethod
	def all(cls) -> Collection['Character']:
		return {Character(c).updated_copy({'IconUrl': c['ImageUrl']}) for c in call_api('pocket/characters')}

	@classmethod
	def characters_in_game(cls, game: Game | str) -> Collection['Character']:
		if isinstance(game, str):
			game = Game(game)
		return {cls(c).updated_copy({'Game': game._data}) for c in call_api(f'characters/bygame/{game.id}')} #pylint: disable=protected-access

	@classmethod
	def game_characters_by_name(cls, game: Game | str) -> Mapping[str, 'Character']:
		return {c.name: c for c in cls.characters_in_game(game)}

	@property
	def name(self) -> str:
		return cast(str, self['Name'])

	def __str__(self) -> str:
		return f'{self.name} ({self.game})'
	
	@property
	def game(self) -> Game:
		#Game, GameShort and GameID are all here… on partial data just GameShort
		game_dict = self._data.get('Game')
		if game_dict:
			return Game(game_dict)

		partial = {}
		game_id = self._data.get('GameID')
		game_short = self._data.get('GameShort')
		if game_id:
			partial['ID'] = game_id
		if game_short:
			partial['Short'] = game_short
		return Game(partial)		

	@property
	def colour(self) -> tuple[int, int, int]:
		"""Returns tuple of (red, blue, green) for some colour representing the character"""
		return cast(tuple[int, int, int], tuple(bytes.fromhex(self.colour_string[1:7])))
		
	@property
	def colour_string(self) -> str:
		"""Hexadecimal colour code for a colour representing the character"""
		return cast(str, self['Colour'])

	@property
	def stock_icon_url(self) -> URL:
		"""Small icon for this character, which is the stock icon for this character from this game"""
		return cast(URL, self['IconUrl'])

	@property
	def character_select_screen_pic_url(self) -> URL:
		"""The character's small pic in the character select screen, not the larger portrait when they are selected"""
		return cast(URL, self['CssUrl'])

	@property
	def match_count(self) -> int:
		return cast(int, self['MatchCount'])

	@property
	def result_count(self) -> int:
		return cast(int, self['ResultCount'])

	@property
	def player_count(self) -> int:
		return cast(int, self['PlayerCount'])

def get_grouped_characters(game: Game) -> Mapping[Character, tuple[Collection[Character], bool]]:
	"""Returns characters in this game that belong in some group together, e.g. echo fighters and their original, with the key being a Character with a name for the group of characters (otherwise equivalent to the first of the group), and value being: (a group of those characters, if the characters are considered basically equivalent to each other for most intents and purposes, i.e. if most tier lists would just put the characters in the same slot)
	The Characters in the returned values may not have all fields behave entirely as expected, they are essentially just there for the name"""
	chars = Character.game_characters_by_name(game)
	if game.short_name == 'SSB64': #TODO Check if this is the short name that is actually used
		return {
			chars['Mario'].updated_copy({'Name': 'Mario Bros.'}): ((chars['Mario'], chars['Luigi']), False),
		}
	if game.short_name == 'SSBM':
		return {
			chars['Mario'].updated_copy({'Name': 'Marios'}): ((chars['Mario'], chars['Dr. Mario']), False),
			chars['Fox'].updated_copy({'Name': 'Spacies'}): ((chars['Fox'], chars['Falco']), False),
			chars['Mario'].updated_copy({'Name': 'Mario Bros.'}): ((chars['Mario'], chars['Luigi']), False),
			chars['Pikachu'].updated_copy({'Name': 'Pikachu/Pichu'}): ((chars['Pikachu'], chars['Pichu']), False),
			#Hmm could put Roy/Marth and Falcon/Ganondorf and Link/YL in here if useful to do so
		}
	#Whoops only semi-clones in Brawl, unless the community does group characters together like this and I just didn't know that
	if game.short_name in {'SSBWU', 'SSB3DS'}:
		return {
			chars['Pit'].updated_copy({'Name': 'Pits'}): ((chars['Pit'], chars['Dark Pit']), True),
			chars['Marth'].updated_copy({'Name': 'Marcina'}): ((chars['Marth'], chars['Lucina']), False),
		}
	if game.short_name == 'SSBU':
		return {
			chars['Peach'].updated_copy({'Name': 'Princesses'}): ((chars['Peach'], chars['Daisy']), True),
			chars['Pit'].updated_copy({'Name': 'Pits'}): ((chars['Pit'], chars['Dark Pit']), True),
			chars['Samus'].updated_copy({'Name': 'Samuses'}): ((chars['Samus'], chars['Dark Samus']), True),
			chars['Simon'].updated_copy({'Name': 'Belmonts'}): ((chars['Simon'], chars['Richter']), True),
			chars['Roy'].updated_copy({'Name': 'Chroy'}): ((chars['Roy'], chars['Chrom']), False),
			chars['Ryu'].updated_copy({'Name': 'Shotos'}): ((chars['Ryu'], chars['Ken']), False),
			chars['Marth'].updated_copy({'Name': 'Marcina'}): ((chars['Marth'], chars['Lucina']), False),
			chars['Pikachu'].updated_copy({'Name': 'Rats'}): ((chars['Pikachu'], chars['Pichu']), False),
		}
	return {}

def combine_echo_fighters(character: Character) -> Character:
	"""Returns character if it is not an echo / does not have an echo fighter, or the grouping if it does
	The returned character might not have fields that entirely make sense other than for Name"""
	for group, (characters, is_equivalent) in get_grouped_characters(character.game).items():
		if is_equivalent and character in characters:
			return group
	return character
