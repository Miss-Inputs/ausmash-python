
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from typing import Any, TypeVar

from .typedefs import JSONDict

_T = TypeVar('_T', bound='DictWrapper')
class DictWrapper:
	"""Wrapper around a dict/mapping, usually from JSON, providing attribute access as well as dict access"""
	def __init__(self, d: JSONDict) -> None:
		self._data = d

	@classmethod
	def wrap_many(cls: type[_T], datas: Iterable[Mapping[str, Any]]) -> Sequence[_T]:
		"""Wraps a sequence/iterable of JSON dicts into a sequence of this type"""
		#TODO: When Python 3.11 comes around to Ubuntu or I otherwise don't feel bad about making it a requirement (maybe in the distant future when 3.10 is EOL), replace TypeVar stuff with Self type hint
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

	def __getattr__(self, name: str) -> Any:
		"""In case there is something not yet exposed as a property on the subclass, get it from the dictionary"""
		if name.startswith('__'):
			#No shenanigans, thank you
			raise AttributeError(name)
		try:
			# return self._data.get(name.title(), self._data[name])
			return self._data[name]
		except KeyError as e:
			raise AttributeError(name) from e

	def __repr__(self) -> str:
		return f'{self.__class__.__qualname__}({repr(self._data)})'

	def updated_copy(self: _T, new_data: JSONDict) -> _T:
		"""Returns a new instance with the same data as this, but with fields updated as specified by new_data"""
		data = self._data
		if not isinstance(data, dict):
			data = dict(data)
		return type(self)(data | new_data)
