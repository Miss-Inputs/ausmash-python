from collections.abc import Sequence
from copy import deepcopy
from typing import cast

from ausmash.api import call_api
from ausmash.typedefs import JSONDict

from .character import Character
from .player import Player
from .video import Video


class CharacterPlayer(Player):
	"""An item in players_of_character, has Player but also containing a few other fields"""

	def __init__(self, d: JSONDict) -> None:
		"""Rather than having a .player property, just make the fields in Player part of this directly, so it acts as a Player"""
		new_dict = deepcopy(d) if isinstance(d, dict) else dict(d)
		new_dict.update(new_dict.pop('Player'))
		super().__init__(new_dict)

	def __str__(self) -> str:
		return f"{super().__str__()}'s {self.character}"

	@property
	def elo_gained(self) -> int:
		"""How much Elo in total this player has gained using this character"""
		return cast(int, self['EloGained'])

	@property
	def elo_lost(self) -> int:
		"""How much Elo in total this player has lost using this character"""
		return cast(int, self['EloLost'])

	@property
	def elo_change(self) -> int:
		"""Net Elo change for this player with this character"""
		return self.elo_gained - self.elo_lost

	@property
	def character(self) -> Character:
		"""The character being played"""
		return Character(self['Character'])
	
	@property
	def videos(self) -> Sequence[Video]:
		"""Videos featuring this player playing this character"""
		#Interestingly this is just an API link to /players/{player ID}/videos/{character ID}
		return Video.wrap_many(call_api(self['APIVideosLink']))
