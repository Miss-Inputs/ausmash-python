import pytest
from ausmash import Character, Game
from ausmash.models.character import CombinedCharacter


@pytest.fixture()
def ssbu() -> Game:
	return Game('SSBU')


def test_parse_character(ssbu: Game):
	jiggs = Character.parse(ssbu, 'Jigglypuff')
	assert jiggs, 'Did not find Jigglypuff'
	assert jiggs.name == 'Jigglypuff', 'Found some other character instead'
	assert jiggs.game == ssbu, 'Got the wrong game'


def test_parse_character_extra(ssbu: Game):
	falco = Character.parse(ssbu, 'Falco Lombardi', use_extra_info=True)
	assert falco, 'Did not find Falco'
	assert falco.name == 'Falco', "That ain't Falco"
	assert falco.game == ssbu, 'Got the wrong game'
	assert not Character.parse(
		ssbu, 'Falco Lombardi'
	), 'Should not use the full name for search if use_extra_info is False, as is default'
	assert Character.parse(ssbu, 'Jigglypuff') == Character.parse(
		ssbu, 'Jigglypuff', use_extra_info=True
	), "Should still work with the character's usual name"


def test_parse_group(ssbu: Game):
	rats = Character.parse(ssbu, 'Rats', use_extra_info=True)
	assert rats, 'Did not find Rats'
	assert isinstance(rats, CombinedCharacter), 'Rats are not combined'
	assert rats.name == 'Rats', 'Found some other group instead'
	assert rats.game == ssbu, 'Got the wrong game'
	assert len(rats.chars) == 2, 'Rats should be 2 characters'
	assert {ch.name for ch in rats.chars} == {
		'Pichu',
		'Pikachu',
	}, 'Rats should be Pikachu and Pichu'
	assert not Character.parse(
		ssbu, 'Rats', use_extra_info=False
	), 'Should not find groups if use_extra_info is False'
	assert not Character.parse(
		ssbu, 'Rats', use_extra_info=True, return_groups=False
	), 'Should not find groups if use_extra_info is True but return_groups is False'

	pits = Character.parse(ssbu, 'Pits', use_extra_info=True)
	assert pits, 'Did not find Pits'
	assert isinstance(pits, CombinedCharacter), 'Pits are not combined'
	assert {ch.name for ch in pits.chars} == {'Pit', 'Dark Pit'}, 'Pits should be Pit and Dark Pit'


def test_parse_normalized(ssbu: Game):
	mr_game_and_watch = Character.parse(ssbu, 'mr. game and watch')
	assert mr_game_and_watch, 'Did not find Mr. Game & Watch in lowercase'
	assert mr_game_and_watch.name == 'Mr. Game and Watch', 'Got some other character'
	mr_game_and_watch = Character.parse(ssbu, 'Mr. Game & Watch')
	assert mr_game_and_watch, 'Did not find Mr. Game & Watch with ampersand'
	assert mr_game_and_watch.name == 'Mr. Game and Watch', 'Got some other character'
	mr_game_and_watch = Character.parse(ssbu, 'Game and Watch', use_extra_info=True)
	assert mr_game_and_watch, 'Did not find Mr. Game & Watch with abbrev name'
	assert mr_game_and_watch.name == 'Mr. Game and Watch', 'Got some other character'
	mr_game_and_watch = Character.parse(ssbu, 'Mr Game and Watch')
	assert mr_game_and_watch, 'Did not find Mr. Game & Watch without dot'
	assert mr_game_and_watch.name == 'Mr. Game and Watch', 'Got some other character'


def test_raise_error(ssbu: Game):
	assert Character.parse(ssbu, 'ffsgdgdfgd') is None, 'Somehow returned a character?'
	with pytest.raises(KeyError) as ex:
		Character.parse(ssbu, 'Qwertyuiop', error_if_not_found=True)
	assert 'Qwertyuiop' in ex.value.args  # type: ignore[comparison-overlap] #huh don't be silly Mypy


def test_custom_group(ssbu: Game) -> None:
	mario_and_samus = Character.parse(ssbu, 'Mario + Samus', use_extra_info=True)
	assert mario_and_samus, 'Did not return a character for Mario + Samus combined'
	assert isinstance(
		mario_and_samus, CombinedCharacter
	), 'Mario + Samus was not a combined character'
	assert mario_and_samus.name == 'Mario + Samus', 'Returned some other name'
	assert len(mario_and_samus.chars) == 2, 'Should have just two characters'
	assert {ch.name for ch in mario_and_samus.chars} == {
		'Mario',
		'Samus',
	}, 'Characters were not Mario and Samus'


def test_custom_group_is_less_priority(ssbu: Game) -> None:
	pyra_mythra = Character.parse(ssbu, 'Pyra / Mythra', use_extra_info=True, return_groups=True)
	assert pyra_mythra, 'Did not even find Pyra & Mythra'
	assert not isinstance(
		pyra_mythra, CombinedCharacter
	), 'Pyra & Mythra should be returned as one character, even if return_groups is True'
	assert pyra_mythra.name == 'Pyra / Mythra'
