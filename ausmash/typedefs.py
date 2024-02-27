from typing import Any

IntID = int
JSON = Any
"""Just used as a placeholder for return types etc to indicate they are parsed JSON of some kind"""
JSONDict = dict[str, JSON]
URL = str
'Strings that are URLs, if pydantic_core.Url is undesirable'