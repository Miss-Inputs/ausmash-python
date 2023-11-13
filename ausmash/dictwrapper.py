
from collections.abc import Iterable, Sequence
from typing import Any, TypeVar, overload

from typing_extensions import Self

from .typedefs import JSON, JSONDict

_T = TypeVar('_T', bound='DictWrapper')
_GetDefaultType = TypeVar('_GetDefaultType')
class DictWrapper:
	"""Wrapper around a dict/mapping, usually from JSON, providing attribute access as well as dict access"""
	def __init__(self, d: JSONDict) -> None:
		self._data = d

	@classmethod
	def wrap_many(cls, datas: Iterable[JSONDict]) -> Sequence[Self]:
		"""Wraps a sequence/iterable of JSON dicts into a sequence of this type"""
		return tuple(cls(data) for data in datas)

	def __eq__(self, __o: object) -> bool:
		"""If not overriden, checks that all fields in the wrapped dict are identical"""
		if not isinstance(__o, type(self)):
			return False
		return self._data == __o._data

	def __hash__(self) -> int:
		return hash(tuple(self._data.items()))
	
	def __getitem__(self, name: str) -> Any:
		return self._data[name]

	@overload
	def get(self, key: str) -> JSON | None: ...
	@overload
	def get(self, key: str, default: JSON | _T) -> JSON | _GetDefaultType: ...
	def get(self, key: str, default: _GetDefaultType | None=None) -> JSON | _GetDefaultType | None:
		"""Implements collections.abc.Mapping.get"""
		try:
			return self[key]
		except KeyError:
			return default

	def __getattr__(self, name: str) -> Any:
		"""In case there is something not yet exposed as a property on the subclass, get it from the dictionary"""
		if name.startswith('__'):
			#No shenanigans, thank you
			raise AttributeError(name)
		try:
			return self._data[name]
		except KeyError as e:
			raise AttributeError(name) from e

	def __repr__(self) -> str:
		return f'{self.__class__.__qualname__}({self._data!r})'

	def updated_copy(self: Self, new_data: JSONDict) -> Self:
		"""Returns a new instance with the same data as this, but with fields updated as specified by new_data"""
		data = self._data
		if not isinstance(data, dict):
			data = dict(data)
		return type(self)(data | new_data)
