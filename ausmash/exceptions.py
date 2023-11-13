
from typing import Any


class RateLimitError(Exception):
	"""Raised if user wants that instead of sleeping, if a request would go over the API limit
	(Otherwise, the server would return a "connection reset by peer" error)"""
	def __init__(self, max_requests: int, time_period: str) -> None:
		self.max_requests = max_requests
		self.time_period = time_period
		super().__init__(f'Exceeded {max_requests} in one {time_period}')

class NotFoundError(Exception):
	"""Raised if something returned a 404 error"""

class StartGGError(Exception):
	"""Raised because GraphQL is annoying and returns 200 if there was an error"""
	
	def _format_error(self, error: dict[str, Any]):
		#extensions should be dict like {'category': 'graphql'}, locations should be list of dict e.g. [{'line': 1, 'column': 40}] but I cbf doing anything with that
		message = f'{error["errorId"]}: {error["message"]}\nextensions: {error["extensions"]}'
		if 'locations' in error:
			message += f', locations: {error["locations"]}'
		return message
		
	def __init__(self, errors: list[dict[str, Any]]) -> None:
		self.errors = errors
		super().__init__('\n'.join(self._format_error(error) for error in errors))
