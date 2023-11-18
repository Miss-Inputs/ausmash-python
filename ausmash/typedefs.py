from collections.abc import Mapping
from typing import Any, NewType

ID = NewType('ID', int)
JSON = Any  # Just used as a placeholder for return types etc to indicate they are parsed JSON of some kind
JSONDict = Mapping[
	str, JSON
]  # For now… recursive types are still experimental in mypy I think
URL = str
