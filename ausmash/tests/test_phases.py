import pytest
from ausmash import Tournament

#TODO: This is probably the wrong way to unit test since it relies on online data, but I dunno what I'm doing yet
#Probably supposed to mock a response from /tournaments/{id} (and look up by ID and not name) and /event/{id}/results or something

@pytest.fixture
def big_cheese_4():
	return Tournament.from_name('The Big Cheese #4')

@pytest.fixture
def big_cheese_4_events(big_cheese_4: Tournament):
	return {e.name: e for e in big_cheese_4.events}

@pytest.fixture
def the_action():
	return Tournament(16537)

@pytest.fixture
def the_action_events(the_action: Tournament):
	return {e.name: e for e in the_action.events}

def test_previous_phases_with_multiple_phases(big_cheese_4: Tournament, big_cheese_4_events):
	ult_pools = big_cheese_4_events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 8']
	
	assert big_cheese_4.previous_phase_for_event(ult_pools) is None, 'Ult pools should not have a previous phase'
	assert big_cheese_4.previous_phase_for_event(ult_top_48) == ult_pools, 'Previous phase of Ult top 48 should be pools'
	assert big_cheese_4.previous_phase_for_event(ult_top_8) == ult_top_48, 'Previous phase of Ult top 8 should be top 48'

	melee_pools = big_cheese_4_events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = big_cheese_4_events['Super Smash Bros. Melee Singles Top 24']
	assert big_cheese_4.previous_phase_for_event(e=melee_pools) is None, 'Melee pools should not have a previous phase'
	assert big_cheese_4.previous_phase_for_event(e=melee_top_24) == melee_pools, 'Previous phase for Melee top 24 should be pools'

	dubs = big_cheese_4_events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = big_cheese_4_events['Smash Ultimate Singles Redemption Bracket']
	assert big_cheese_4.previous_phase_for_event(dubs) is None, 'Ult doubles should not have a previous phase'
	assert big_cheese_4.previous_phase_for_event(redemmies) is None, 'Ult redemption should not have a previous phase'

def test_next_phases(big_cheese_4: Tournament, big_cheese_4_events):
	ult_pools = big_cheese_4_events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 8']
	
	assert big_cheese_4.next_phase_for_event(ult_pools) == ult_top_48, 'Next phase of Ult pools should be top 48'
	assert big_cheese_4.next_phase_for_event(ult_top_48) == ult_top_8, 'Next phase of Ult top 48 should be top 8'
	assert big_cheese_4.next_phase_for_event(ult_top_8) is None, 'Ult top 8 should not have a next phase'

	melee_pools = big_cheese_4_events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = big_cheese_4_events['Super Smash Bros. Melee Singles Top 24']
	assert big_cheese_4.next_phase_for_event(e=melee_pools) == melee_top_24, 'Next phase of Melee pools should be top 24'
	assert big_cheese_4.next_phase_for_event(e=melee_top_24) is None, 'Melee top 24 should not have a next phase'

	dubs = big_cheese_4_events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = big_cheese_4_events['Smash Ultimate Singles Redemption Bracket']
	assert big_cheese_4.next_phase_for_event(dubs) is None, 'Ult doubles should not have a next phase'
	assert big_cheese_4.next_phase_for_event(redemmies) is None, 'Ult redemption should not have a next phase'

def test_start_phase(big_cheese_4: Tournament, big_cheese_4_events):
	ult_pools = big_cheese_4_events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 8']

	for event in (ult_pools, ult_top_48, ult_top_8):
		assert big_cheese_4.start_phase_for_event(event) == ult_pools, f'{event.name} start phase should be pools'

	melee_pools = big_cheese_4_events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = big_cheese_4_events['Super Smash Bros. Melee Singles Top 24']
	for event in (melee_pools, melee_top_24):
		assert big_cheese_4.start_phase_for_event(event) == melee_pools, f'{event.name} start phase should be pools'

	dubs = big_cheese_4_events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = big_cheese_4_events['Smash Ultimate Singles Redemption Bracket']	
	for event in (dubs, redemmies):
		assert big_cheese_4.start_phase_for_event(event) == event, f'{event.name} start phase should be itself'

def test_final_phase(big_cheese_4: Tournament, big_cheese_4_events):
	ult_pools = big_cheese_4_events['Super Smash Bros. Ultimate Singles Pools']
	ult_top_48 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 48']
	ult_top_8 = big_cheese_4_events['Super Smash Bros. Ultimate Singles Top 8']

	for event in (ult_pools, ult_top_48, ult_top_8):
		assert big_cheese_4.final_phase_for_event(event) == ult_top_8, f'{event.name} start phase should be top 8'

	melee_pools = big_cheese_4_events['Super Smash Bros. Melee Singles Pools']
	melee_top_24 = big_cheese_4_events['Super Smash Bros. Melee Singles Top 24']
	for event in (melee_pools, melee_top_24):
		assert big_cheese_4.final_phase_for_event(event) == melee_top_24, f'{event.name} start phase should be top 24'

	dubs = big_cheese_4_events['Super Smash Bros. Ultimate Doubles Bracket']
	redemmies = big_cheese_4_events['Smash Ultimate Singles Redemption Bracket']	
	for event in (dubs, redemmies):
		assert big_cheese_4.final_phase_for_event(event) == event, f'{event.name} start phase should be itself'

def test_bronze_ammies_does_not_progress_to_silver(the_action: Tournament, the_action_events):
	bronze = the_action_events['The Action Bronze Ammies']
	silver = the_action_events['The Action Silver Ammies']
	assert the_action.next_phase_for_event(bronze) is None
	assert the_action.previous_phase_for_event(bronze) is None
	assert the_action.next_phase_for_event(silver) is None
	assert the_action.previous_phase_for_event(silver) is None
