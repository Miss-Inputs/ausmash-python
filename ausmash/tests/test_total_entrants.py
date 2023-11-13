
import pytest

from ausmash import Result, Tournament


@pytest.fixture()
def tournament():
	return Tournament.from_name('The Big Cheese #4')

@pytest.fixture()
def events(tournament: Tournament):
	return {e.name: e for e in tournament.events}

def test_total_entrants(tournament, events):
	#TODO: Split into 3 test functions for len(results), result.number_of_entrants, result.total_entrants
	pools_results = Result.results_for_event(events['Super Smash Bros. Ultimate Singles Pools'])
	top_48_results = Result.results_for_event(events['Super Smash Bros. Ultimate Singles Top 48'])
	top_8_results = Result.results_for_event(events['Super Smash Bros. Ultimate Singles Top 8'])
	dubs_results = Result.results_for_event(events['Super Smash Bros. Ultimate Doubles Bracket'])
	redemmies_results = Result.results_for_event(events['Smash Ultimate Singles Redemption Bracket'])
	
	assert len(pools_results) == 90
	assert pools_results[0].number_of_entrants == 90
	assert pools_results[0].total_entrants == 90

	assert len(top_48_results) == 48
	assert top_48_results[0].number_of_entrants == 48
	assert top_48_results[0].total_entrants == 90

	assert len(top_8_results) == 8
	assert top_8_results[0].number_of_entrants == 8
	assert top_8_results[0].total_entrants == 90

	assert len(dubs_results) == 26
	assert dubs_results[0].number_of_entrants == 26
	assert dubs_results[0].total_entrants == 26
	
	assert len(redemmies_results) == 19
	assert redemmies_results[0].number_of_entrants == 19
	assert redemmies_results[0].total_entrants == 19
