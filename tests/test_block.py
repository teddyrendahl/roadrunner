############
# Standard #
############
import logging

###############
# Third Party #
###############
import pytest
from pcdsdevices.sim.pv import using_fake_epics_pv
from pcdsdevices.epics.attenuator import Filter

##########
# Module #
##########
from roadrunner import BlockWatch 


cmd = Filter.filter_sets

@using_fake_epics_pv
@pytest.fixture(scope='function')
def watchblock():
    bw =  BlockWatch("MFX", "AI", "FLTR", "SEQ", threshold=2.5)
    bw.ai._read_pv.put(5)
    return bw

@using_fake_epics_pv
def test_block_watch_soft_trip(watchblock):
    #Start enabled and sequencer off
    watchblock.enabled._read_pv.put(1)
    watchblock.seq_run._read_pv.put(0)
    assert not watchblock.sequencer_running

    #Cause a trip, but do not close the blocker
    watchblock.ai._read_pv.put(0)
    #Process event
    watchblock.process_event()
    assert watchblock.soft_trip.get() == 1
    assert watchblock.hard_trip.get() == 0
    #Filter did not close
    assert not watchblock.blocker.state_sig._write_pv.get() == cmd.IN.value

@using_fake_epics_pv
def test_block_watch_hard_trip(watchblock):
    #Start enabled and sequencer on
    watchblock.enabled._read_pv.put(1)
    watchblock.seq_run._read_pv.put(2)
    watchblock.seq_cnt._read_pv.put(50)
    assert watchblock.sequencer_running

    #Cause a trip, and close the blocker
    watchblock.ai._read_pv.put(0)
    #Process event
    watchblock.process_event()
    assert watchblock.soft_trip.get() == 0
    assert watchblock.hard_trip.get() == 1
    #Filter closed
    assert watchblock.blocker.state_sig._write_pv.get() == cmd.IN.value

    #Recover
    watchblock.ai._read_pv.put(5)
    #Process event
    watchblock.process_event()
    assert watchblock.soft_trip.get() == 0
    assert watchblock.hard_trip.get() == 0
    #Filter re-opened    
    assert watchblock.blocker.state_sig._write_pv.get() == cmd.OUT.value

@using_fake_epics_pv
def test_block_watch_disabled(watchblock):
    #Start disabled and sequencer off
    watchblock.enabled._read_pv.put(0)
    watchblock.seq_run._read_pv.put(2)
    watchblock.seq_cnt._read_pv.put(50)
    assert watchblock.sequencer_running

    #Cause a trip, but do not close the blocker
    watchblock.ai._read_pv.put(0)
    #Process event
    watchblock.process_event()
    assert watchblock.soft_trip.get() == 0
    assert watchblock.hard_trip.get() == 1
    #Filter did not close
    assert not watchblock.blocker.state_sig._write_pv.get() == cmd.IN.value


