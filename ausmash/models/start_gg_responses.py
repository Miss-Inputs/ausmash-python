"""Pydantic models for start.gg API responses. There was probably a way to automatically make these from GraphQL, but eh. Allows for better type hinting/IDE autocomplete and helps ensure I'm not a dumbarse
Since GraphQL is annoying, though, we don't actually hint all of it"""
from typing import Literal

from pydantic import BaseModel

from ausmash.typedefs import IntID


class PageInfo(BaseModel):
	model_config = {'extra': 'forbid'}
	page: int
	perPage: int
	totalPages: int


class PhaseGroup(BaseModel):
	model_config = {'extra': 'forbid'}
	displayIdentifier: str
	wave: dict[Literal['identifier'], str] | None
	"""We only bother getting the name of the wave here, otherwise this should be typed as another layer of BaseModel instead"""


class EventEntrantSeed(BaseModel):
	model_config = {'extra': 'forbid'}
	progressionSource: IntID | None
	"""Indicates where this entrant came from in later phases, or none if it is the start phases"""
	phaseGroup: PhaseGroup
	"""Which pool this entrant is in"""
	seedNum: int


class EventParticipant(BaseModel):
	model_config = {'extra': 'forbid'}
	gamerTag: str
	prefix: str | None
	player: dict[Literal['id'], IntID]
	"""We only bother getting the ID here, otherwise this should be typed as another layer of BaseModel instead"""


class EventEntrant(BaseModel):
	model_config = {'extra': 'forbid'}
	name: str
	"""Combined prefix + tag, or perhaps a team name"""
	seeds: list[EventEntrantSeed]
	skill: int | None
	participants: list[EventParticipant]


class EventEntrantsResponse(BaseModel):
	model_config = {'extra': 'forbid'}
	pageInfo: PageInfo
	nodes: list[EventEntrant]

class User(BaseModel):
	model_config = {'extra': 'forbid'}
	genderPronoun: str | None
	name: str | None

class PlayerPronounsResponse(BaseModel):
	model_config = {'extra': 'forbid'}
	user: User | None

class TournamentLocationResponse(BaseModel):
	model_config = {'extra': 'forbid'}
	lat: float | None
	lng: float | None
	venueAddress: str | None
	venueName: str | None
	mapsPlaceId: str | None
	city: str | None
	postalCode: str | None
	addrState: str | None
	timezone: str | None
	countryCode: str | None
