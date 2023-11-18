import importlib.resources
import json
import re

from ausmash.typedefs import JSON

# Weird nonsense (also known as a regex) that ensures we can still have // inside a string literal
json_comment_reg = re.compile(r'(\".*?\")|(?://.*$)')


def parse_jsonc(text: str) -> JSON:
	lines = [json_comment_reg.sub(r'\1', line) for line in text.splitlines()]
	return json.loads('\n'.join(lines))


def parse_data(name: str) -> JSON:
	data = importlib.resources.files('ausmash.data')
	jsonc = data.joinpath(f'{name}.jsonc').read_text('utf-8')
	return parse_jsonc(jsonc)
