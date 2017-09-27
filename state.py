import numpy as np
from transitions import Machine
import pandas as pd
from toon.audio import beep_sequence
from toon.input import Keyboard
from psychopy import prefs
prefs.general['audioLib'] = ['sounddevice']
from psychopy import core, visual, sound

class StateMachine(Machine):
    """
    `sched_` denotes things that are scheduled to coincide w/ the frame buffer flip
    Remember to account for lag in drawing (plan on drawing ~ 1 frame (e.g. 15ms) before onset)

    """
    def __init__(self, settings=None):
        states = ['pretrial',
                  'enter_trial',
                  'first_target',
                  'second_target',
                  'feedback',
                  'post_trial',
                  'cleanup']
        transitions = [

            {'source': 'pretrial',
             'trigger': 'step',
             'prepare': '',
             'conditions': '', # nothing needs to block
             'after': ['sched_beep',
                       'sched_trial_timer_reset',
                       'sched_record_trial_start'],
             'dest': 'enter_trial'},

            # wait for 500 ms until showing first image (to coincide w/ real audio onset)
            {'source': 'enter_trial',
             'trigger': 'step',
             'prepare': '',  # called as soon as transition starts (every time)
             'conditions': 'trial_timer_passed_first',  # i.e. 500 ms - ~16ms elapsed
             'after': 'show_first_target',  # after state change (after conditions are evaluated, run once)
             'dest': 'first_target'},

            # after 500 ms, show the first image
            {'source': 'first_target',
             'trigger': 'step',
             'prepare': '',
             'conditions': 'trial_timer_passed_second',  # i.e. the proposed prep time in table elapsed
             'after': 'show_second_target',  # after state change (after conditions are evaluated, run once)
             'dest': 'second_target'},

            # after n extra ms, show second image & wait until beeps are over (plus a little)
            {'source': 'second_target',
             'trigger': 'step',
             'prepare': '',
             'conditions': 'trial_timer_elapsed',  # Beeps have finished + 200ms of mush
             'after': ['record_data',  # save data from trial
                       'draw_feedback',  # figure out what was pushed based on buffer
                       'sched_feedback_timer_reset'],  # set timer for feedback duration
             'dest': 'feedback'},

            # show feedback for n seconds
            {'source': 'feedback',
             'trigger': 'step',
             'prepare': '',
             'conditions': 'feedback_timer_elapsed',  # Once n milliseconds have passed...
             'after': ['remove_feedback', # remove targets and make sure all colours are normal
                       'increment_trial_counter', # add one to the trial counter
                       'sched_post_timer_reset'],  # # set timer for inter-trial break
             'dest': 'post_trial'},

            # evaluate whether to exit experiment first...
            {'source': 'post_trial',
             'trigger': 'step',
             'prepare': '',
             'conditions': ['post_timer_elapsed', # Once n milliseconds have passed...
                            'trial_counter_exceed_table'],  # And the number of trials exceeds trial table
             'after': ['close_n_such'],  # Clean up, we're done here
             'dest': 'cleanup'},

            # ... or move to the next trial
            {'source': 'post_trial',
             'trigger': 'step',
             'prepare': '',
             'conditions': 'post_timer_elapsed',  # If the previous one evaluates to False, we should end up here
             'after': '',
             'dest': 'pretrial'}
        ]
        Machine.__init__(self, states=states, transitions=transitions, initial='pretrial')

        # clocks and timers
        self.global_clock = core.monotonicClock  # gives us a time that we can relate to the input device
        self.trial_timer = core.CountdownTimer() # gives us the time until the end of the trial (counts down)
        self.feedback_timer = core.CountdownTimer() # gives time that feedback shows (counts down)
        self.post_timer = core.CountdownTimer() # gives time between trials (counts down)

        # trial table
        try:
            self.trial_table = pd.read_csv(settings['trial_table'])
        except FileNotFoundError:
            core.quit()

        # visually-related things
        # window
        self.win = visual.Window(size=(800, 800),
                                 pos=(0, 0),
                                 fullscr=False,#settings['fullscreen'],
                                 screen=1,
                                 units='height',
                                 allowGUI=False)
        self.win.recordFrameIntervals = True

        # targets
        poses = [(-0.25, 0), (0.25, 0)]  # vary just on x-axis
        self.targets = [visual.Circle(self.win, size = 0.3, fillColor='cyan', pos=p) for p in poses]

        # push feedback
        self.push_feedback = visual.Circle(self.win, size = 0.15, fillColor='white', pos=(0, 0),
                                           autoDraw=True)
        # fixation
        self.fixation = visual.Circle(self.win, size = 0.1, fillColor='white', pos=(0, 0),
                                      autoDraw=True)

        # audio
        tmp = beep_sequence(click_freq=(523.251, 659.255, 783.991, 1046.5),
                            inter_click_interval=0.4,
                            num_clicks=4,
                            dur_clicks=0.04)
        self._time_last_beep = round(0.5 + (0.4 * 3), 2)

        self.beep = sound.Sound(np.transpose(np.vstack((tmp, tmp))),
                                blockSize=16,
                                hamming=False)

        # Input device
        if settings['forceboard']:
            self.device = None
        else:
            keys = 'awefvbhuil'
            chars = []
            for key in keys:
                chars.append(key)
            self.device = Keyboard(keys=chars, clock_source=self.global_clock)

        # extras
        self.frame_period = 1/self.win.getActualFrameRate()
        self.trial_start = None

    # pretrial functions
    def sched_beep(self):
        self.beep.seek(self.beep.stream.latency)
        self.win.callOnFlip(self.beep.play)

    def sched_trial_timer_reset(self):
        # trial ends 200 ms after last beep
        self.win.callOnFlip(self.trial_timer.reset, self._time_last_beep + 0.2)

    def sched_record_trial_start(self):
        self.win.callOnFlip(self._get_trial_start)

    def _get_trial_start(self):
        self.trial_start = self.win.lastFrameT

    # enter_trial functions
    def trial_timer_passed_first(self):
        # determine if 500 ms has elapsed
        return self._time_last_beep


    # first_target functions


    # second_target functions


    # feedback functions


    # post_trial functions


    # cleanup functions

