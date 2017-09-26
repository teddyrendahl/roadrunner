"""
Safety measure to watch both the EventSequencer and the signal emitted by the
roadrunner in an effort to protect the CSPAD. The concept is that if the
EventSequencer is running, but we are not receiving a signal from the
RoadRunner that it is in motion, we are most likely in an unsafe state.
"""
############
# Standard #
############
import time
import logging

###############
# Third Party #
###############
from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import Component as C
from ophyd import FormattedComponent as FC
from pcdsdevices.epics.attenuator import Filter

##########
# Module #
##########

class BlockWatch(Device):
    """
    Class to monitor Sequencer and Analog Input

    The BlockWatch has a constant monitor callback on both the sequencer and
    the analog input calling :meth:`.process_event` whenever one of these
    changes. The handling of these signals is as follows; if the analog input
    is below a certain threshold and the sequencer is off a soft trip will be
    reported. This is simply to alert the operator, but no preventative measure
    will be taken. If the sequencer is running, and the signal is below the
    :attr:`.threshold`, we report a hard trip, and close the filter to protect
    our detector.

    In order to give the operator some control and readback, the status of
    the watcher is reported into a few soft PVS. In addition to the soft and
    hard trips, there is a string pv so that the status can be displayed.
    Finally, there is a quick enable toggle. If this is set to False, the logic
    will process the same, but motion of the attenuator will be prevented

    Parameters
    ----------
    prefix : str
        Base of the PV Notepad PVs

    ai : str
        Analog input channel of RoadRunner monitor

    fltr : str
        Base name of attenuator filter

    sequencer : str
        Base name of sequencer

    threshold : float, optional
        Minimum threshold to allow RoadRunner signal before tripping the watch
    """
    #Soft PVs
    soft_trip = C(EpicsSignal,   ':SOFT_TRIP')
    hard_trip = C(EpicsSignal,   ':HARD_TRIP')
    enabled   = C(EpicsSignalRO, ':ENABLE', auto_monitor=True)
    #Real PVs
    seq_run = FC(EpicsSignalRO, '{self._sequencer}:PLSTAT', auto_monitor=True)
    seq_cnt = FC(EpicsSignalRO, '{self._sequencer}:CURSTP', auto_monitor=True)
    ai      = FC(EpicsSignal,   '{self._ai}', auto_monitor=True)
    #Blocker 
    blocker = FC(Filter, '{self._filter}')

    def __init__(self, prefix, ai, fltr, sequencer, threshold=1):
        self.threshold = threshold
        #Store EPICS prefixes
        self._filter    = fltr
        self._ai        = ai
        self._sequencer = sequencer
        #Initialize ophyd device
        super().__init__(prefix)

    @property
    def sequencer_running(self):
        """
        Return whether the sequencer is running

        The play status of the sequencer is modified as well as the current
        step. This is done to avoid race conditions with the start of the
        sequencer and the beginning of the roadrunnner scan
        """
        return self.seq_run.value == 2 and self.seq_cnt.value > 25

    @property
    def signal_present(self):
        """
        Assert whether we have a signal over :attr:`.threshold`
        """
        return self.ai.value > self.threshold

    def remove(self):
        """
        Remove the blocker if it is not removed from the beam
        """
        if self.enabled.value == 1:
            self.blocker.move_out()

    def block(self):
        """
        Block the beam if the filter is not already inserted
        """
        if self.enabled.value == 1:
            self.blocker.move_in()

    def process_event(self, *args, **kwargs):
        """
        Process a change in state if either the sequencer or ai changes state
        """
        #If we are not receiving signal
        if not self.signal_present:
            #If the sequencer is running, hard-fault
            if self.sequencer_running:
                self.hard_trip.put(1)
                self.block()
            #Otherwise, alert the soft trip
            else:
                self.soft_trip.put(1)
        #Otherwise if we are seeing a signal
        else:
            #Remove our blocker
            self.remove()
            #Reset our faults
            self.soft_trip.put(0)
            self.hard_trip.put(0)

    def run(self):
        """
        Repeatedly run :func:`.process_event`
        """
        while True:
            try:
                self.process_event()
            except KeyboardInterrupt:
                print("Watch has been manually interrupted!")
                break
