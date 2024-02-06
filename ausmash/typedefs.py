from typing import Any, NewType

ID = NewType('ID', int)
JSON = Any
"""Just used as a placeholder for return types etc to indicate they are parsed JSON of some kind"""
JSONDict = dict[str, JSON]
URL = str
