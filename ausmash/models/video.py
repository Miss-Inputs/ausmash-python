from copy import deepcopy
import itertools
from collections.abc import Collection, Sequence
from datetime import date
from typing import cast

from ausmash.api import call_api
from ausmash.resource import Resource
from ausmash.typedefs import ID, URL, JSONDict

from .character import Character
from .event import Event
from .match import Match
from .player import Player


class Video(Match):
	"""A recorded video of a match. Basically just a combination of Match and a URL, and is only YouTube for now"""

	def __init__(self, d: JSONDict) -> None:
		"""Instead of bothering with a .match property, just use Video as a Match"""
		new_dict = deepcopy(d) if isinstance(d, dict) else dict(d)
		new_dict.update(new_dict.pop('Match'))
		super().__init__(new_dict)

	@classmethod
	def all(cls) -> Collection['Video']:
		"""All videos tagged on the site. This will probably hit the API a lot"""
		return set(itertools.chain.from_iterable(channel.videos for channel in Channel.all()))

	@classmethod
	def videos_of_player(cls, player: Player, start_date: date | None=None, end_date: date | None=None, character: Character | None=None) -> Sequence['Video']:
		"""Videos featuring this player, newest to oldest"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		if character:
			return cls.wrap_many(call_api(f'players/{player.id}/videos/{character.id}', params))
		return cls.wrap_many(call_api(f'players/{player.id}/videos', params))

	@classmethod
	def videos_at_event(cls, event: Event) -> Sequence['Video']:
		"""All videos for matches at this event that have a video tagged
		TODO: What is this sorted by, if anything meaningful?"""
		return cls.wrap_many(call_api(f'events/{event.id}/videos'))

	@classmethod
	def videos_of_character(cls, character: Character) -> Sequence['Video']:
		"""Videos featuring this character being played, newest to oldest"""
		return cls.wrap_many(call_api(f'characters/{character.id}/videos'))

	@property
	def id(self) -> ID:
		"""There is no /videos/{id} URL, so it is not a Resource, but it has an ID anyway"""
		return ID(self['ID'])

	def __eq__(self, __o: object) -> bool:
		if not isinstance(__o, Video):
			return False
		return self.id == __o.id

	def __hash__(self) -> int:
		return hash(self.id)
	
	@property
	def url(self) -> URL:
		"""URL to watch this video (for now, YouTube watch link)"""
		return cast(URL, self['Url'])

class Channel(Resource):
	"""A YouTube channel that has had videos of matches uploaded to it"""
	base_url = "channels"

	@classmethod
	def all(cls) -> Collection['Channel']:
		"""All known channels on Ausmash"""
		return cls.wrap_many(call_api('channels'))

	@property
	def name(self) -> str:
		"""Display name of this channel, gets it from YouTube by default but can be edited"""
		return cast(str, self['Name'])

	def __str__(self) -> str:
		return self.name

	@property
	def url(self) -> URL:
		"""YouTube URL to the channel page"""
		return cast(URL, self['Url'])

	@property
	def owner(self) -> Player | None:
		"""Owner of this channel, or None if it is not registered as belonging to a certain player
		The /channels API only returns a player ID, so accessing any properties will likely require an API call"""
		player_id: int | None = self['PlayerID']
		if not player_id:
			return None
		return Player(player_id)

	def __len__(self) -> int:
		return self.video_count

	@property
	def video_count(self) -> int:
		"""Number of videos on this channel, but does not require the /channels/{id} endpoint"""
		video_count: int = self['VideoCount']
		return video_count

	@property
	def videos(self) -> Collection[Video]:
		"""Videos of matches on this channel
		Does not seem to be in any particular order
		Not present on the /channels endpoint so will need an API call to get by ID"""
		return Video.wrap_many(self['Videos'])
