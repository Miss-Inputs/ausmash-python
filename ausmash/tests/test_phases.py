import pytest
from ausmash import Tournament

#TODO: This is probably the wrong way to unit test since it relies on online data, but I dunno what I'm doing yet
#Probably supposed to mock a response from /tournaments/{id} (and look up by ID and not name) and /event/{id}/results or something

@pytest.fixture
def tournament():
	return Tournament.from_name('The Big Cheese #4')

@pytest.fixture
def events(tournament: Tournament):
	return {e.name: e for e in tournament.events}

def test_previous_phases(tournament: Tournament, events):
	ult_pools = events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = events['Super Smash Bros. Ultimate Singles Top 8']
	
	assert tournament.previous_phase_for_event(ult_pools) is None, 'Ult pools should not have a previous phase'
	assert tournament.previous_phase_for_event(ult_top_48) == ult_pools, 'Previous phase of Ult top 48 should be pools'
	assert tournament.previous_phase_for_event(ult_top_8) == ult_top_48, 'Previous phase of Ult top 8 should be top 48'

	melee_pools = events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = events['Super Smash Bros. Melee Singles Top 24']
	assert tournament.previous_phase_for_event(e=melee_pools) is None, 'Melee pools should not have a previous phase'
	assert tournament.previous_phase_for_event(e=melee_top_24) == melee_pools, 'Previous phase for Melee top 24 should be pools'

	dubs = events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = events['Smash Ultimate Singles Redemption Bracket']
	assert tournament.previous_phase_for_event(dubs) is None, 'Ult doubles should not have a previous phase'
	assert tournament.previous_phase_for_event(redemmies) is None, 'Ult redemption should not have a previous phase'

def test_next_phases(tournament: Tournament, events):
	ult_pools = events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = events['Super Smash Bros. Ultimate Singles Top 8']
	
	assert tournament.next_phase_for_event(ult_pools) == ult_top_48, 'Next phase of Ult pools should be top 48'
	assert tournament.next_phase_for_event(ult_top_48) == ult_top_8, 'Next phase of Ult top 48 should be top 8'
	assert tournament.next_phase_for_event(ult_top_8) is None, 'Ult top 8 should not have a next phase'

	melee_pools = events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = events['Super Smash Bros. Melee Singles Top 24']
	assert tournament.next_phase_for_event(e=melee_pools) == melee_top_24, 'Next phase of Melee pools should be top 24'
	assert tournament.next_phase_for_event(e=melee_top_24) is None, 'Melee top 24 should not have a next phase'

	dubs = events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = events['Smash Ultimate Singles Redemption Bracket']
	assert tournament.next_phase_for_event(dubs) is None, 'Ult doubles should not have a next phase'
	assert tournament.next_phase_for_event(redemmies) is None, 'Ult redemption should not have a next phase'

def test_start_phase(tournament: Tournament, events):
	ult_pools = events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = events['Super Smash Bros. Ultimate Singles Top 8']

	for event in (ult_pools, ult_top_48, ult_top_8):
		assert tournament.start_phase_for_event(event) == ult_pools, f'{event.name} start phase should be pools'

	melee_pools = events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = events['Super Smash Bros. Melee Singles Top 24']
	for event in (melee_pools, melee_top_24):
		assert tournament.start_phase_for_event(event) == melee_pools, f'{event.name} start phase should be pools'

	dubs = events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = events['Smash Ultimate Singles Redemption Bracket']	
	for event in (dubs, redemmies):
		assert tournament.start_phase_for_event(event) == event, f'{event.name} start phase should be itself'

def test_final_phase(tournament: Tournament, events):
	ult_pools = events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = events['Super Smash Bros. Ultimate Singles Top 8']

	for event in (ult_pools, ult_top_48, ult_top_8):
		assert tournament.final_phase_for_event(event) == ult_top_8, f'{event.name} start phase should be top 8'

	melee_pools = events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = events['Super Smash Bros. Melee Singles Top 24']
	for event in (melee_pools, melee_top_24):
		assert tournament.final_phase_for_event(event) == melee_top_24, f'{event.name} start phase should be top 24'

	dubs = events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = events['Smash Ultimate Singles Redemption Bracket']	
	for event in (dubs, redemmies):
		assert tournament.final_phase_for_event(event) == event, f'{event.name} start phase should be itself'


