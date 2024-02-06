import logging
from functools import cached_property
from typing import TYPE_CHECKING, Any

from ausmash.api import call_api_json
from ausmash.exceptions import NotFoundError

from .dictwrapper import DictWrapper
from .typedefs import IntID, URL, JSONDict

if TYPE_CHECKING:
	from typing_extensions import Self

logger = logging.getLogger(__name__)


class Resource(DictWrapper):
	"""Something accessible directly by REST methods, with a /{base_url}/{id} endpoint that returns all fields. Acts as a proxy object for its own type, requesting APILink or the ID if it needs to access a field that isn't defined because this was returned from a property of something else etc"""

	base_url: str | None = None

	def __init__(self, dict_or_id: JSONDict | int) -> None:
		self.api_link: URL | None
		if isinstance(dict_or_id, int):
			super().__init__({'ID': dict_or_id})
			self.api_link = None
		else:
			super().__init__(dict_or_id)
			self.api_link = dict_or_id.get('APILink')

	def __init_subclass__(cls) -> None:
		if not cls.base_url:
			raise NotImplementedError(f'Forgor to set the base_url for {cls.__qualname__}!')

		return super().__init_subclass__()

	@property
	def id(self) -> IntID:
		"""Opaque ID used to request the resource again for more fields, or compare stuff, etc
		Would normally always be present, though if potentially not (such as with Game or Region, due to accepting a str in constructor to use just short name), _complete should be overridden"""
		return IntID(self['ID'])

	def __repr__(self) -> str:
		return f'{self.__class__.__qualname__}({self.id!r})'

	def __eq__(self, __o: object) -> bool:
		if not isinstance(__o, type(self)):
			return False
		return self.id == __o.id

	def __hash__(self) -> int:
		return hash(self.id)

	@classmethod
	def get_by_id(cls: type['Self'], id_: IntID) -> 'Self':
		"""Gets a new instance of this resource from an ID representing it
		:raises NotFoundError: If the request for this ID did not find anything
		:raises HTTPError: If some other HTTP error happens"""
		try:
			return cls(call_api_json(f'{cls.base_url}/{id_}'))
		except NotFoundError as e:
			raise NotFoundError(f'{cls.__qualname__} with ID {id_} not found') from e

	@cached_property
	def _complete(self: 'Self') -> 'Self':
		if self._data.get('is_complete'):
			raise NotImplementedError('This was already a complete resource')
		complete: dict[str, Any] | None = None
		if self.api_link:
			complete = call_api_json(self.api_link)
		else:
			id_ = self._data.get('ID')
			if id_:
				complete = call_api_json(f'{self.base_url}/{id_}')

		if complete:
			# Avoid infinitely recursing accidentally
			complete['is_complete'] = True
			return type(self)(complete)
		raise NotImplementedError('You cannot call _complete without an API link or ID etc')

	def __getitem__(self, name: str) -> Any:
		"""Look up an item in _data as normal, but also if this only has some of the fields that this resource might have, get the whole thing via ID/APILink"""
		try:
			return super().__getitem__(name)
		except KeyError as e:
			try:
				logger.debug('Requesting complete %s to get %s', type(self).__qualname__, name)
				return self._complete[name]
			except (NotImplementedError, NotFoundError):
				raise e  # pylint: disable=raise-missing-from #That would be weird actually
