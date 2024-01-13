from typing import Any, NewType

from pydantic import JsonValue

ID = NewType('ID', int)
JSON = (
	JsonValue | Any
)  # Just used as a placeholder for return types etc to indicate they are parsed JSON of some kind
JSONDict = dict[str, JSON]
URL = str
