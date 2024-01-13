from collections.abc import Mapping
from typing import Any, NewType

from pydantic import JsonValue

ID = NewType('ID', int)
JSON = JsonValue  # Just used as a placeholder for return types etc to indicate they are parsed JSON of some kind
JSONDict = Mapping[str, JSON]  # For now… recursive types are still experimental in mypy I think
URL = str
