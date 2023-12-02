import re
from collections import defaultdict
from collections.abc import Collection, Mapping, MutableMapping
from datetime import date
from functools import cache, lru_cache
from typing import cast

from ausmash.api import call_api
from ausmash.resource import Resource
from ausmash.typedefs import JSON, URL, JSONDict
from ausmash.utils import parse_data

from .game import Game


@lru_cache(maxsize=1)
def _load_character_info() -> JSON:
	return parse_data('character_info')


@lru_cache(maxsize=1)
def _load_character_game_info() -> JSON:
	return parse_data('character_game_info')


class Character(Resource):
	"""A playable character as they appear in one particular game"""

	base_url = 'characters'

	@classmethod
	def all(cls) -> Collection['Character']:
		"""All characters in all games (using the pocket API)"""
		return {
			Character(c).updated_copy({'IconUrl': c['ImageUrl']})
			for c in call_api('pocket/characters')
		}

	@classmethod
	def characters_in_game(cls, game: Game | str) -> Collection['Character']:
		"""All characters in a particular game
		Ensures that the Game field is filled in with all of Game, to avoid extra API calls"""
		if isinstance(game, str):
			game = Game(game)
		return {
			cls(c).updated_copy({'Game': game._data})  # pylint: disable=protected-access #It's my class, I'm allowed
			for c in call_api(f'characters/bygame/{game.id}')
		}  # pylint: disable=protected-access

	@classmethod
	def game_characters_by_name(cls, game: Game | str) -> Mapping[str, 'Character']:
		"""Returns a mapping of name > character for all characters in a game"""
		return {c.name: c for c in cls.characters_in_game(game)}

	@staticmethod
	def _normalize_name(name: str) -> str:
		name = re.sub(r'\s*(?:&|/)\s*', ' and ', name)
		name = name.replace('.', '')
		return name.casefold()

	@classmethod
	def parse(
		cls,
		game: Game | str,
		name: str,
		*,
		use_extra_info: bool = False,
		return_groups: bool = True,
		error_if_not_found: bool = False,
	) -> 'Character | None':
		"""Find a character in a certain game matching a certain name
		:param game: Game to find characters in
		:param name: Name of character
		:param use_extra_info: Use aliases and abbreviations and such
		:param return_groups: If use_extra_info (otherwise ignored), may return a CombinedCharacter for a grouping of characters
		:param error_if_not_found: Raise an error if could not find any characters that match, instead of returning None
		:raises KeyError: If error_if_not_found is True and no character in game matched"""
		chars = cls.characters_in_game(game)
		name = cls._normalize_name(name)
		if not use_extra_info:
			char = next((char for char in chars if cls._normalize_name(char.name) == name), None)
			if char is None and error_if_not_found:
				raise KeyError(name)
			return char

		groups: defaultdict[str, set[Character]] = defaultdict(set)
		for char in chars:
			if char._extra_info_matches(name):
				return char

			for group_name in char.character_groups:
				groups[group_name].add(char)
			if char.echo_fighter_group:
				groups[char.echo_fighter_group].add(char)

		if return_groups:
			for group_name, group in groups.items():
				if name == cls._normalize_name(group_name):
					return CombinedCharacter(group_name, group)

		if error_if_not_found:
			raise KeyError(name)
		return None

	def _extra_info_matches(self, name: str) -> bool:
		names = {
			self._normalize_name(n) for n in (self.name, self.abbrev_name, self.full_name) if n
		}
		if self.other_names:
			names.update(self._normalize_name(n) for n in self.other_names)

		if name in names:
			return True
		if name.startswith('#') and self.fighter_number and str(self.fighter_number) == name[1:]:
			return True
		return False

	@property
	def name(self) -> str:
		"""This character's full name, as defined by Ausmash."""
		return cast(str, self['Name'])

	def __str__(self) -> str:
		return f'{self.name} ({self.game})'

	@property
	def game(self) -> Game:
		"""Game that this character is from."""
		# Game, GameShort and GameID are all here… on partial data just GameShort
		game_dict = self.get('Game')
		if game_dict:
			return Game(game_dict)

		partial = {}
		game_id = self.get('GameID')
		game_short = self.get('GameShort')
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
		"""Number of matches this character has been recorded as having been used in."""
		return cast(int, self['MatchCount'])

	@property
	def result_count(self) -> int:
		"""Number of results this character has been recorded for."""
		return cast(int, self['ResultCount'])

	@property
	def player_count(self) -> int:
		"""Number of players that record using this character."""
		return cast(int, self['PlayerCount'])

	def __add_info(self):
		if 'has_info' in self._data:
			return
		data = _load_character_info()
		if self.name in data:
			extra_data = data[self.name]
			extra_data['has_info'] = True
			if isinstance(self._data, MutableMapping):
				self._data.update(extra_data)
			else:
				self._data = self._data | extra_data

	def __add_game_info(self):
		if 'has_game_info' in self._data:
			return
		data = _load_character_game_info()
		if self.game.short_name in data:
			game_info = data[self.game.short_name]
			if self.name in game_info:
				extra_data = game_info[self.name]
				extra_data['has_game_info'] = True
				if isinstance(self._data, MutableMapping):
					self._data.update(extra_data)
				else:
					self._data = self._data | extra_data

	@property
	def universe(self) -> str | None:
		"""Universe/series/etc this character is from"""
		self.__add_info()
		return self.get('universe')

	@property
	def gender(self) -> str | None:
		"""Gender of this character: "male", "female", "non-binary", "agender", "selectable", "multiple" if multiple characters, "unspecified" if nondescript species, etc"""
		self.__add_info()
		return self.get('gender')

	@property
	def fighter_number(self) -> int | None:
		"""Official fighter number for this character"""
		self.__add_info()
		return self.get('number')

	@property
	def owner(self) -> str:
		"""Company that owns this character"""
		self.__add_info()
		return self.get('owner', 'Nintendo')

	@property
	def is_third_party(self) -> bool:
		"""If character is not owned by Nintendo"""
		return self.owner != 'Nintendo'

	@property
	def type(self) -> str:
		"""How the character is obtained: starter, unlockable, transformation, creatable, dlc"""
		self.__add_game_info()
		return self.get('type', 'starter')

	@property
	def release_date(self) -> date | None:
		"""If this is a DLC character, when they were released"""
		self.__add_game_info()
		release_date = self.get('release_date')
		if release_date:
			return date.fromisoformat(release_date)
		return None

	@property
	def character_groups(self) -> Collection[str]:
		"""If this character is similar enough to another in their game that they might be grouped together, returns the names of those combined groups, if any"""
		self.__add_game_info()
		groups: list[str] | None = self.get('groups')
		if groups:
			return groups
		return []

	@property
	def echo_fighter_group(self) -> str | None:
		"""If this character is an echo fighter or has one, that is more often than not similar enough to be combined in tier lists etc or other statistics, return the combined name for those characters, else None"""
		self.__add_game_info()
		return self.get('echo_group')

	def effectively_equal(self, other: 'Character') -> bool:
		"""Returns true if these objects refer to the same character, or if one is the echo fighter of another"""
		if self.echo_fighter_group and other.echo_fighter_group:
			return self.echo_fighter_group == other.echo_fighter_group
		return self == other

	@property
	def first_appearance(self) -> tuple[str | None, date | None, str | None]:
		"""The game this character first appeared in, returned as (name, date, platform)
		Returns (None, None, None) if this data is not available"""
		self.__add_info()
		first: JSONDict | None = self.get('first_appearance')
		if not first:
			return None, None, None
		game = first.get('game')
		d = first.get('date')
		platform = first.get('platform')
		if d:
			d = date.fromisoformat(d)
		return game, d, platform

	@property
	def abbrev_name(self) -> str | None:
		"""Commonly used abbrevation for this character's name, if any"""
		self.__add_info()
		return self.get('abbrev')

	@property
	def other_names(self) -> Collection[str]:
		"""Aliases, alternate spellings, grammatical forms, etc that might be used to refer to this character"""
		self.__add_info()
		names: list[str] | None = self.get('other_names')
		if not names:
			return []
		return names

	@property
	def full_name(self) -> str | None:
		"""This character's canon full name (for whichever definition of canon is most funny), or None if not available"""
		self.__add_info()
		return self.get('full_name')


class CombinedCharacter(Character):
	"""May be returned from combine_echo_fighters.

	Considers the combination of name and game to be equal, so it can be used as dictionary keys, etc
	"""

	def __init__(self, name: str, chars: Collection[Character]) -> None:
		if not chars:
			raise ValueError('chars cannot be empty')
		self.group_name = name
		self.chars = chars
		self._first_char = next(iter(chars))
		super().__init__(self._first_char._data)

	@property
	def name(self) -> str:
		return self.group_name

	def __repr__(self) -> str:
		return f'{type(self).__qualname__}({self.group_name!r}, {self.chars!r})'

	@property
	# type: ignore[override] #shhhh
	def _complete(self) -> 'Character':
		"""Return the complete version of the first character.

		This ensures all inherited properties and methods will at least do something, although it might not always make sense. Most things should probably be overridden directly."""
		return self._first_char._complete  # pylint: disable=protected-access

	def __hash__(self) -> int:
		return hash((self.group_name, self.game))

	def __eq__(self, __o: object) -> bool:
		if not isinstance(__o, Character):
			return False
		# TODO: Should this compare true with Character objects that have this as an echo group? Or would that just be weird
		return self.group_name == __o.name and self.game == __o.game

	# TODO: add_info() should add instead any information that is common between .chars, e.g. Peach + Daisy should end up having gender = female still
	# TODO: colour and colour_string should maybe be averaged
	# TODO: match_count, player_count, result_count should be added together
	# TODO: effectively_equal should check that other CombinedCharacter has chars all effectively equal, or other Character is part of this? maybe


@cache
def _echo_groups_in_game(game: Game | str) -> Mapping[str, CombinedCharacter]:
	chars = Character.game_characters_by_name(game)
	if isinstance(game, Game):
		game = game.short_name
	groups: dict[str, list[Character]] = {}
	game_info: JSONDict = _load_character_game_info().get(game)
	for char_name, char in game_info.items():
		if 'echo_group' in char:
			groups.setdefault(char['echo_group'], []).append(chars[char_name])
	return {name: CombinedCharacter(name, group_chars) for name, group_chars in groups.items()}


@cache
def combine_echo_fighters(character: Character) -> Character:
	"""Returns character if it is not an echo / does not have an echo fighter, or the grouping if it does.

	The returned character might not have fields that entirely make sense other than for Name.
	"""
	if character.echo_fighter_group:
		return _echo_groups_in_game(character.game)[character.echo_fighter_group]
	return character
