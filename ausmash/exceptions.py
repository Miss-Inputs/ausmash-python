
class RateLimitException(Exception):
	"""Raised if user wants that instead of sleeping, if a request would go over the API limit
	(Otherwise, the server would return a "connection reset by peer" error)"""
	def __init__(self, max_requests: int, time_period: str) -> None:
		self.max_requests = max_requests
		self.time_period = time_period
		super().__init__(f'Exceeded {max_requests} in one {time_period}')

class NotFoundError(Exception):
	"""Raised if something returned a 404 error"""
