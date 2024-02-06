import itertools
from collections.abc import Collection, Iterator, Sequence
from copy import deepcopy
from datetime import date
from typing import TYPE_CHECKING, cast

from ausmash.api import call_api_json
from ausmash.resource import Resource
from ausmash.typedefs import IntID, URL, JSONDict

from .match import Match
from .player import Player

if TYPE_CHECKING:
	from .character import Character
	from .event import Event


class Video(Match):
	"""A recorded video of a match. Basically just a combination of Match and a URL, and is only YouTube for now"""

	def __init__(self, d: JSONDict) -> None:
		"""Instead of bothering with a .match property, just use Video as a Match"""
		new_dict = deepcopy(d)
		match = new_dict.pop('Match')
		match = deepcopy(match) if isinstance(match, dict) else dict(match)
		new_dict['match_id'] = match.pop('ID')
		new_dict.update(match)
		super().__init__(new_dict)

	@classmethod
	def all(cls) -> Collection['Video']:
		"""All videos tagged on the site. This will probably hit the API a lot"""
		return frozenset(
			itertools.chain.from_iterable(
				channel.videos for channel in Channel.all() if channel.video_count
			)
		)

	@classmethod
	def for_match(cls, match: Match) -> 'Video | None':
		"""First Video associated with a Match, or None if it does not have one"""
		for video in cls.videos_at_event(match.event):
			if video.match_id == match.id:
				return video
		return None

	@classmethod
	def iter_all_for_match(cls, match: Match) -> Iterator['Video']:
		"""Iterates all videos associated with a Match"""
		for video in cls.videos_at_event(match.event):
			if video.match_id == match.id:
				yield video

	@classmethod
	def videos_of_player(
		cls,
		player: Player,
		start_date: date | None = None,
		end_date: date | None = None,
		character: 'Character | None' = None,
	) -> Sequence['Video']:
		"""Videos featuring this player, newest to oldest"""
		params = {}
		if start_date:
			params['startDate'] = start_date.isoformat()
		if end_date:
			params['endDate'] = end_date.isoformat()
		if character:
			return cls.wrap_many(
				call_api_json(f'players/{player.id}/videos/{character.id}', params)
			)
		return cls.wrap_many(call_api_json(f'players/{player.id}/videos', params))

	@classmethod
	def videos_at_event(cls, event: 'Event') -> Sequence['Video']:
		"""All videos for matches at this event that have a video tagged
		TODO: What is this sorted by, if anything meaningful?"""
		return cls.wrap_many(call_api_json(f'events/{event.id}/videos'))

	@classmethod
	def videos_of_character(cls, character: 'Character') -> Sequence['Video']:
		"""Videos featuring this character being played, newest to oldest"""
		return cls.wrap_many(call_api_json(f'characters/{character.id}/videos'))

	@property
	def id(self) -> IntID:
		"""There is no /videos/{id} URL, so it is not a Resource, but it has an ID anyway"""
		return IntID(self['ID'])

	@property
	def match_id(self) -> IntID:
		"""ID in the Match property"""
		return IntID(self['match_id'])

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

	base_url = 'channels'

	@classmethod
	def all(cls) -> Collection['Channel']:
		"""All known channels on Ausmash"""
		return cls.wrap_many(call_api_json('channels'))

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
