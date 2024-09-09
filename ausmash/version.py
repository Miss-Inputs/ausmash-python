import subprocess
from pathlib import Path

__version__ = '0.0.0'


def get_git_version() -> str:
	"""Returns version string based on git repo. Raises subprocess.CalledProcessError if we aren't in one

	Returns:
		Something like an 8-letter hex string
	"""
	return subprocess.check_output(
		['git', 'describe', '--tags', '--always'],
		encoding='utf8',
		cwd=Path(__file__).parent,
		stderr=subprocess.DEVNULL,
	)
