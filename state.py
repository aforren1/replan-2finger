import numpy as np
import pandas as pd
from psychopy import prefs
prefs.general['audioLib'] = ['sounddevice']
from psychopy import core, visual, sound
from transitions.extensions import GraphMachine as Machine
from toon.audio import beep_sequence
from toon.input import Keyboard


class StateMachine(Machine):
    def __init__(self, settings=None):
        """Intialize everything """
        self.trial_start = None
        self._second_drawn = False

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
        # check `plt.plot(np.arange(0, len(tmp)/44100, 1/44100), tmp)`
        tmp = beep_sequence(click_freq=(523.251, 659.255, 783.991, 1046.5),
                            inter_click_interval=0.4,
                            num_clicks=4,
                            dur_clicks=0.04)
        self._time_last_beep = round(0.5 + (0.4 * 3), 2)

        self._beep = sound.Sound(np.transpose(np.vstack((tmp, tmp))),
                                 blockSize=16,
                                 hamming=False)

        # timers
        self.trial_timer = core.CountdownTimer

        # build state machine
        states = ['setup', 'intrial', 'feedback', 'posttrial', 'cleanup']
        transitions = [
            {'trigger': 'start',
             'source': 'setup',
             'dest': 'intrial',
             'after': ['schedule_beep',
                       'reset_trial_timer', 'record_trial_start',
                       'reset_second_timer']},
            {'trigger': 'step',
             'source': 'intrial',
             'dest': 'first',
             'after': ['show_first_target']},
            {'trigger': 'step',
             'source': 'second',
             'dest': 'feedback',
             'before': 'show_second_target',
             'conditions': '',
             'after': ['reset_timer']
             }

        ]
        Machine.__init__(self, states=states, transitions=transitions, initial='setup')
        self.win = visual.Window(size=(800, 800),
                                 pos=(0, 0),
                                 fullscr=settings['fullscreen'],
                                 screen=1,
                                 units='height')
        self.win.recordFrameIntervals = True

        poses = [(-0.25, 0), (0.25, 0)]
        self.targets = [visual.Circle(self.win, fillColor='cyan', pos=p) for p in poses]

    def schedule_beep(self):
        self._beep.seek(self._beep.stream.latency)  # seek into file for better timing
        self.win.callOnFlip(self._beep.play)
        # you can also grab the audio latency via self._beep.stream.latency (~10 ms on Windows)
        # you can also get the last frame occurrence via win.lastFrameT (if win.recordFrameIntervals=True)

    def show_first_target(self):
        self.targets[self.trial_table['first'][self.trial_count]].setAutoDraw(True)
        self._second_drawn = False

    def show_second_target(self):
        if not self._second_drawn and self.second_target_timer <= 0:
            self.targets[self.trial_table['first'][self.trial_count]].setAutoDraw(False)
            self.targets[self.trial_table['second'][self.trial_count]].setAutoDraw(True)
            self._second_drawn = True

    # TODO: timer for second target (accounting for time != frames)

    def reset_trial_timer(self):
        """Reset trial timer right before new trial"""
        self.win.callOnFlip(_reset_countdown, self.trial_timer, self._time_last_beep + 0.2)  # reset timer

    def record_trial_start(self):
        """Get the start of the trial (when the first frame appears)"""
        self.win.callOnFlip(self._get_trial_start)

    def _get_trial_start(self):
        self.trial_start = self.win.lastFrameT


def _reset_countdown(timer, to_what):
    """Set countdown timers to (positive) times"""
    timer.reset()
    timer.add(to_what)

