import numpy as np
import pandas as pd
from psychopy import core, visual, sound
from transitions.extensions import GraphMachine as Machine
from toon.audio import beep_sequence
from toon.input import Keyboard

class StateMachine(Machine):
    def __init__(self, settings=None):
        """Intialize everything """

        self.clock = core.monotonicClock

        # try loading trial table
        try:
            self.trial_table = pd.read_csv(settings['trial_table'])
        except FileNotFoundError:
            core.quit()

        # Input device
        if settings['forceboard']:
            self.device = None
        else:
            keys = 'awefvbhuil'
            chars = []
            for key in keys:
                chars.append(key)
            self.device = Keyboard(keys=chars, clock_source=self.clock)

        # beep train
        # remember, the *center* of the first beep is 0.5 s after the beginning of the file
        tmp = beep_sequence(click_freq=(523.251, 659.255, 783.991, 1046.5),
                            inter_click_interval=0.4,
                            num_clicks=4,
                            dur_clicks=0.04)

        self._beep = sound.Sound(np.transpose(np.vstack((tmp, tmp))),
                                 blockSize=32,
                                 hamming=False)

        # build state machine
        states = ['setup', 'intrial', 'feedback', 'posttrial', 'cleanup']
        transitions = [
            {'trigger': 'start',
             'source': 'setup',
             'dest': 'intrial'}

        ]
        Machine.__init__(self, states=states, transitions=transitions, initial='setup')
        self.win = visual.Window(size=(800, 800),
                                 pos=(0, 0),
                                 fullscr=settings['fullscreen'],
                                 screen=1,
                                 units='height')


    def _adjust_beep(self):
        self._beep.seek(self._beep.stream.latency) # seek into file for better timing

    def schedule_beep(self):
        self._adjust_beep()
        self.win.callOnFlip(self._beep.play)
        self.win.callOnFlip(self.timer.reset) # reset timer
        # you can also grab the audio latency via self._beep.stream.latency (~10 ms on Windows)
        # you can also get the last frame occurrence via win.lastFrameT (if win.recordFrameIntervals=True)

