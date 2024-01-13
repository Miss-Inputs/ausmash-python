import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FirstAppearance(BaseModel):
	game: str
	date: datetime.date | None = None
	"""First date that game was released anywhere"""
	platform: str


class CharacterInfo(BaseModel):
	"""Extra info for characters outside the API that applies to all games they are in

	I've definitely gotten carried away here"""

	abbrev: str | None = None
	"""Commonly used abbreviation if any"""
	number: int | None = None
	"""Official fighter number"""
	universe: str | None = None
	"""Franchise, universe, whichever, I think universe is the official term"""
	owner: str = 'Nintendo'
	"""Copyright owner if not Nintendo (i.e. specify this if third party), of course in real life it is more complicated than that so this is just for casual entertainment purposes only"""
	gender: str | None = Field(
		None, examples=['male', 'female', 'selectable', 'unspecified', 'multiple']
	)
	"""male, female, etc, could theoretically include all sorts of things but Nintendo are cowards, otherwise selectable (via alts) or unspecified (if a species etc) or multiple (if character is two characters in one that are different)"""
	first_appearance: FirstAppearance | None = None
	"""Game this character first appeared in ever"""
	full_name: str | None = None
	"""Canonical full name because I don't know why"""
	other_names: set[str] = Field(default_factory=set)
	"""Other names for the character that might be used (why am I doing this?)"""
	costume_for: str | None = None
	"""If this character appears as a costume for another, which one"""


CharacterType = Literal['starter', 'unlockable', 'transformation', 'creatable', 'dlc', 'individual']


class CharacterGameInfo(BaseModel):
	"""Some character info specific to that character's appearance in each game, unrelated to the API, e.g. who is an echo fighter of who"""

	# Type == individual isn't represented on Ausmash, but I guess I got carried away, so whatever
	type: CharacterType = 'starter'
	"""How this character is able to be played"""
	groups: set[str] = Field(default_factory=set)
	"""If this character is sometimes grouped together with another for statistical purposes, the names of those groups"""
	echo_group: str | None = None
	"""Like groups, but where a character is almost the same as one another (an echo fighter, officially in Ultimate), the name of that combination, only one is allowed"""
	vs_matches_to_unlock: int | None = None
	"""How many VS mode matches required to unlock the character, if relevant to that game"""
	component_of: str | None = None
	"""If type == individual, which composite character this is an individual part of"""
	transformation_of: str | None = None
	"""If type == transformation, the character that this character transforms from, else leave out"""
	unlock_order: int | None = None
	"""For Ultimate, order in the Classic Mode unlock tree if type == unlockable"""
	unlock_tree: str | None = None
	"""For Ultimate, starter character of this character's Classic Mode unlock tree if type == unlockable"""
	release_date: datetime.date | None = None
	"""If type == dlc, date this character became available"""
	bundle: str | None = None
	"""If type == dlc, bundle this character is available in if any"""
	internal_name: str | None = None
	"""Internal name/filename/etc inside the game code"""
