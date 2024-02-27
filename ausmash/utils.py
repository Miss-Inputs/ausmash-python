import importlib.resources
import re
from typing import TYPE_CHECKING, TypeVar, cast

import pydantic
from pydantic_core import from_json

if TYPE_CHECKING:
	from pydantic import BaseModel, JsonValue

# Weird nonsense (also known as a regex) that ensures we can still have // inside a string literal
json_comment_reg = re.compile(r'(\".*?\")|(?://.*$)')


def parse_jsonc(text: str) -> 'JsonValue':
	lines = [json_comment_reg.sub(r'\1', line) for line in text.splitlines()]
	return cast('JsonValue', from_json('\n'.join(lines)))


def parse_data(name: str) -> 'JsonValue':
	data = importlib.resources.files('ausmash.data')
	jsonc = data.joinpath(f'{name}.jsonc').read_text('utf-8')
	return parse_jsonc(jsonc)
