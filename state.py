import numpy as np
from scipy import signal as sg
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
             'after': ['sched_beep',
                       'sched_trial_timer_reset',
                       'sched_record_trial_start',
                       'first_press_reset'],
             'dest': 'enter_trial'},

            # wait for 500 ms until showing first image (to coincide w/ real audio onset)
            {'source': 'enter_trial',
             'trigger': 'step',
             'conditions': 'trial_timer_passed_first',  # i.e. 500 ms - ~16ms elapsed
             'after': 'show_first_target',  # after state change (after conditions are evaluated, run once)
             'dest': 'first_target'},

            # after 500 ms, show the first image
            {'source': 'first_target',
             'trigger': 'step',
             'conditions': 'trial_timer_passed_second',  # i.e. the proposed prep time in table elapsed
             'after': 'show_second_target',  # after state change (after conditions are evaluated, run once)
             'dest': 'second_target'},

            # after n extra ms, show second image & wait until beeps are over (plus a little)
            {'source': 'second_target',
             'trigger': 'step',
             'conditions': 'trial_timer_elapsed',  # Beeps have finished + 200ms of mush
             'after': ['record_data',  # save data from trial
                       'check_answer',
                       'draw_feedback',  # figure out what was pushed based on buffer
                       'sched_feedback_timer_reset'],  # set timer for feedback duration
             'dest': 'feedback'},

            # show feedback for n seconds
            {'source': 'feedback',
             'trigger': 'step',
             'conditions': 'feedback_timer_elapsed',  # Once n milliseconds have passed...
             'after': ['remove_feedback', # remove targets and make sure all colours are normal
                       'increment_trial_counter', # add one to the trial counter
                       'sched_post_timer_reset'],  # # set timer for inter-trial break
             'dest': 'post_trial'},

            # evaluate whether to exit experiment first...
            {'source': 'post_trial',
             'trigger': 'step',
             'conditions': ['post_timer_elapsed', # Once n milliseconds have passed...
                            'trial_counter_exceed_table'],  # And the number of trials exceeds trial table
             'after': ['close_n_such'],  # Clean up, we're done here
             'dest': 'cleanup'},

            # ... or move to the next trial
            {'source': 'post_trial',
             'trigger': 'step',
             'conditions': 'post_timer_elapsed',  # If the previous one evaluates to False, we should end up here
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
                                 fullscr=settings['fullscreen'],
                                 screen=1,
                                 units='height',
                                 allowGUI=False,
                                 colorSpace='rgb',
                                 color = (-1, -1, -1))
        self.win.recordFrameIntervals = True

        # targets
        poses = [(-0.25, 0), (0.25, 0)]  # vary just on x-axis
        self.targets = [visual.Circle(self.win, size = 0.3, fillColor=[0.7, 1, 1], pos=p) for p in poses]

        # push feedback
        self.push_feedback = visual.Circle(self.win, size = 0.1, fillColor=[-1, -1, -1], pos=(0, 0),
                                           autoDraw=True, autoLog=False)
        # fixation
        self.fixation = visual.Circle(self.win, size = 0.05, fillColor=[1, 1, 1], pos=(0, 0),
                                      autoDraw=True)

        # audio
        tmp = beep_sequence(click_freq=(523.251, 659.255, 783.991, 1046.5),
                            inter_click_interval=0.4,
                            num_clicks=4,
                            dur_clicks=0.04)
        self.last_beep_time = round(0.5 + (0.4 * 3), 2)

        self.beep = sound.Sound(np.transpose(np.vstack((tmp, tmp))),
                                blockSize=16,
                                hamming=False)
        self.coin = sound.Sound('coin.wav', stereo=True) #TODO: check bug in auto-config of sounddevice (stereo = -1)

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
        self.trial_start = 0
        self.trial_counter = 0 # start at zero b/c zero indexing
        self.trial_input_buffer = np.full((600, 10), np.nan)
        self.trial_input_time_buffer = np.full((600, 1), np.nan)
        self.first_press = np.nan
        self.first_press_time = np.nan
        self.left_val = self.trial_table[['first', 'second']].min(axis=0).min()
        self.right_val = self.trial_table[['first', 'second']].max(axis=0).max()
        self.device_on = False
        self.correct_answer = False

    # pretrial functions
    def sched_beep(self):
        self.beep.seek(self.beep.stream.latency)
        self.win.callOnFlip(self.beep.play)

    def sched_trial_timer_reset(self):
        # trial ends 200 ms after last beep
        self.win.callOnFlip(self.trial_timer.reset, self.last_beep_time + 0.2)

    def sched_record_trial_start(self):
        self.win.callOnFlip(self._get_trial_start)

    def _get_trial_start(self):
        self.trial_start = self.win.lastFrameT

    def first_press_reset(self):
        self.first_press = np.nan
        self.first_press_time = np.nan

    # enter_trial functions
    def trial_timer_passed_first(self):
        # determine if 500 ms has elapsed
        # The timer is started at last_beep_time + 0.2
        # TODO: Think about this one
        return (self.last_beep_time + 0.2 - self.trial_timer.getTime() + self.frame_period) >= 0.5

    def show_first_target(self):
        # This is tricky -- if the condition evaluates to false, draw the left target
        self.targets[int(self.trial_table['first'][self.trial_counter] == self.right_val)].setAutoDraw(True)

    # first_target functions
    def trial_timer_passed_second(self):
        # this timer is the other way around
        return (self.trial_timer.getTime() - 0.2 - self.frame_period) <= self.trial_table['switch_time'][self.trial_counter]

    def show_second_target(self):
        self.targets[int(self.trial_table['first'][self.trial_counter] == self.right_val)].setAutoDraw(False)
        self.targets[int(self.trial_table['second'][self.trial_counter] == self.right_val)].setAutoDraw(True)

    # second_target functions
    def trial_timer_elapsed(self):
        return self.trial_timer.getTime() <= 0

    def record_data(self):
        pass

    def check_answer(self):
        correct_answer = self.trial_table['second'][self.trial_counter] == self.first_press
        delta = self.first_press_time - self.last_beep_time
        print(delta)
        good_timing = False
        if delta > 0.075:
            print('too slow')
        elif delta < -0.075:
            print('too fast')
        elif np.isnan(self.first_press):
            print('too slow')
        else:
            print('good timing')
            good_timing = True
        self.correct_answer = correct_answer
        if correct_answer and good_timing:
            self.coin.play()

    def draw_feedback(self):
        # text for timing, correctness
        [t.setFillColor((-0.3, 0.7, -0.3) if self.correct_answer else (0.7, -0.3, -0.3)) for t in self.targets]

    def sched_feedback_timer_reset(self):
        self.win.callOnFlip(self.feedback_timer.reset, 0.3) # 300 ms feedback?

    # feedback functions
    def feedback_timer_elapsed(self):
        return self.feedback_timer.getTime() <= 0

    def remove_feedback(self):
        # remove targets, make sure everything is proper colour
        [t.setAutoDraw(False) for t in self.targets]
        [t.setFillColor([0.7, 1, 1]) for t in self.targets]

    def increment_trial_counter(self):
        self.trial_counter += 1

    def sched_post_timer_reset(self):
        self.win.callOnFlip(self.post_timer.reset, 0.1) # can be short (500 ms already built in via audio delay)

    # post_trial functions
    def post_timer_elapsed(self):
        return self.post_timer.getTime() <= 0

    def trial_counter_exceed_table(self):
        return self.trial_counter >= len(self.trial_table.index)

    # cleanup functions
    def close_n_such(self):
        pass

    def input(self):
        # collect input
        data, timestamp = self.device.read() # need to correct timestamp
        if data is not None:
            current_nans = np.isnan(self.trial_input_buffer)
            next_index = np.where(current_nans)[0][0]
            self.trial_input_buffer[next_index, :] = data
            self.trial_input_time_buffer[next_index, :] = timestamp
            if type(self.device).__name__ is 'Keyboard':
                self.device_on = data.any() # colour in if any buttons pressed
                if np.isnan(self.first_press) and self.device_on:
                    self.first_press = np.where(data)[0] + 1
                    self.first_press_time = timestamp - self.trial_start
                    print((self.first_press, self.first_press_time))


            elif type(self.device).__name__ is 'ForceTransducers':
                # see sg.medfilt(trial_input_buffer, kernel_size=(odd, 1))
                pass

    def draw_input(self):
        self.push_feedback.setFillColor([0, 0, 0] if self.device_on else [-1, -1, -1])
