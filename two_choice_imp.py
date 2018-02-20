import csv
import os
import os.path as op
import shutil
from datetime import datetime as dt

import numpy as np
import pandas as pd
from psychopy import prefs
# we need to set prefs *before* setting the other stuff
prefs.general['audioLib'] = ['sounddevice']
from psychopy import clock, core, sound, visual, logging
from scipy import signal as sg

from state_dec import StateMachine
from toon.audio import beep_sequence
from toon.input import MultiprocessInput
from toon.input.force_transducers import ForceTransducers
from toon.input.keyboard import Keyboard
from toon.input.clock import mono_clock

logging.setDefaultClock(mono_clock)


class TwoChoice(StateMachine):
    """
    `sched_` denotes things that are scheduled to coincide w/ the frame buffer flip
    Remember to account for lag in drawing (plan on drawing ~ 1 frame (e.g. 15ms) before onset)

    """

    def __init__(self, settings=None):

        super(TwoChoice, self).__init__()
        # clocks and timers
        self.global_clock = mono_clock
        # gives us the time until the end of the trial (counts down)
        self.trial_timer = core.CountdownTimer()
        # gives time that feedback shows (counts down)
        self.feedback_timer = core.CountdownTimer()
        # gives time between trials (counts down)
        self.post_timer = core.CountdownTimer()

        # trial table
        try:
            self.trial_table = pd.read_csv(settings['trial_table'])
        except FileNotFoundError:
            core.quit()

        self.win = visual.Window(size=(800, 800),
                                 pos=(0, 0),
                                 fullscr=settings['fullscreen'],
                                 screen=1,
                                 units='height',
                                 allowGUI=False,
                                 colorSpace='rgb',
                                 color=(-1, -1, -1))
        self.win.recordFrameIntervals = True

        self.setup_visuals()  # decouple for the sake of the other exp
        # audio
        tmp = beep_sequence(click_freq=(523.251, 659.255, 783.991, 1046.5),
                            inter_click_interval=0.4,
                            num_clicks=4,
                            dur_clicks=0.04)
        self.last_beep_time = round(0.1 + (0.4 * 3), 2)

        self.beep = sound.Sound(tmp, blockSize=16, hamming=False)
        # TODO: check bug in auto-config of sounddevice (stereo = -1)
        self.coin = sound.Sound('media/coin.wav', stereo=True)
        # Input device
        if settings['forceboard']:
            self.device = MultiprocessInput(
                ForceTransducers, clock=self.global_clock.getTime)
        else:
            keys = 'awefvbhuil'
            self.device = MultiprocessInput(Keyboard, keys=list(
                keys), clock=self.global_clock.getTime)
            self.keyboard_state = [False] * 10
        # by-trial data
        data_path = 'data/' + settings['subject'] + '/'
        if not op.exists(data_path):
            os.makedirs(data_path)
        # copy the trial table to the data folder
        adaptstring = '_adapt' if settings['adaptive'] else ''
        shutil.copyfile(settings['trial_table'], data_path +
                        op.basename(settings['trial_table']))
        self.summary_file_name = data_path + 'id_' + settings['subject'] + '_' + \
            op.splitext(op.basename(settings['trial_table']))[0] + \
            adaptstring + dt.now().strftime('_%H%M%S') + '.csv'
        self.csv_header = ['index', 'subject', 'first_target', 'second_target',
                           'real_switch_time', 'first_press', 'first_press_time', 'correct', 'prep_time']
        with open(self.summary_file_name, 'w') as f:
            writer = csv.DictWriter(
                f, fieldnames=self.csv_header, lineterminator='\n')
            writer.writeheader()

        self.trial_data = {'index': np.nan, 'subject': settings['subject'], 'first_target': np.nan,
                           'second_target': np.nan, 'real_switch_time': np.nan,
                           'first_press': np.nan, 'first_press_time': np.nan,
                           'correct': np.nan, 'prep_time': np.nan}

        # extras
        self.frame_period = self.win.monitorFramePeriod
        self.trial_start = 0
        self.trial_counter = 0  # start at zero b/c zero indexing
        self.trial_input_buffer = np.full((600, 10), np.nan)
        self.trial_input_time_buffer = np.full((600, 1), np.nan)
        self.first_press = np.nan
        self.first_press_time = np.nan
        self.left_val = self.trial_table[['first', 'second']].min(axis=0).min()
        self.right_val = self.trial_table[['first', 'second']].max(axis=0).max()
        self.device_on = False
        self.correct_answer = False
        
        # things related to the adaptive version
        self.adaptive = settings['adaptive']
        self.sign_switch_count = 0 # number of times the correctness switched
        self.curr_sign = False
        self.prev_sign = False
        self.curr_prep_time = 0.5 # start at 500ms


    def setup_visuals(self):
        # visually-related things
        # targets
        poses = [(-0.6, 0), (0.6, 0)]  # vary just on x-axis
        names = ['left_target', 'right_target']
        self.targets = [visual.Rect(self.win, width=0.5, height=0.5, fillColor=[0, 0, 0], pos=p, lineWidth=0, name=n)
                        for p, n in zip(poses, names)]

        fingers = ['pinky', 'ring', 'middle', 'index', 'thumb']
        left_hand = ['left ' + f for f in fingers]
        fingers.reverse()
        right_hand = ['right ' + f for f in fingers]
        both_hands = left_hand + right_hand
        uniques = pd.unique(self.trial_table['first']).astype(int)
        unique_finger_names = [both_hands[i] for i in uniques]
        unique_str = ", ".join(unique_finger_names)  # gives something like "left pinky, left thumb"


        # push feedback
        self.push_feedback = visual.Circle(self.win, size=0.1, fillColor=[-1, -1, -1], pos=(0, 0),
                                           autoDraw=False, autoLog=False, name='push_feedback')
        # fixation
        self.fixation = visual.Circle(self.win, size=0.05, fillColor=[1, 1, 1], pos=(0, 0),
                                      autoDraw=False, name='fixation')

        # text
        self.wait_text = visual.TextStim(self.win, text='Press a key to start.\nKeys are:\n' + unique_str, pos=(0, 0),
                                         units='norm', color=(1, 1, 1), height=0.1,
                                         alignHoriz='center', alignVert='center', name='wait_text',
                                         autoLog=False, wrapWidth=2)
        self.wait_text.autoDraw = True
        self.good = visual.TextStim(self.win, text=u'Good timing!', pos=(0, 0.4),
                                    units='norm', color=(-1, 1, 0.2), height=0.1,
                                    alignHoriz='center', alignVert='center', autoLog=True, name='good_text')
        self.too_slow = visual.TextStim(self.win, text=u'Too slow.', pos=(0, 0.4),
                                        units='norm', color=(1, -1, -1), height=0.1,
                                        alignHoriz='center', alignVert='center', autoLog=True, name='slow_text')
        self.too_fast = visual.TextStim(self.win, text=u'Too fast.', pos=(0, 0.4),
                                        units='norm', color=(1, -1, -1), height=0.1,
                                        alignHoriz='center', alignVert='center', autoLog=True, name='fast_text')

    # wait functions
    def remove_text(self):
        self.wait_text.autoDraw = False
        self.push_feedback.autoDraw = True
        self.fixation.autoDraw = True

    # pretrial functions
    def wait_for_release(self):
        # Wait until all keys released
        return not self.device_on

    def sched_beep(self):
        self.beep.seek(self.beep.stream.latency)  # 100ms of silence is built into the click train, so we can seek in without affecting the actual stimulus
        self.win.callOnFlip(self.beep.play)

    def sched_trial_timer_reset(self):
        # trial ends 200 ms after last beep
        self.win.callOnFlip(self.trial_timer.reset, self.last_beep_time + 0.2 - self.frame_period)

    def sched_record_trial_start(self):
        self.win.callOnFlip(self._get_trial_start)

    def _get_trial_start(self):
        self.trial_start = self.win.lastFrameT

    def first_press_reset(self):
        self.first_press = np.nan
        self.first_press_time = np.nan

    # enter_trial functions
    def trial_timer_passed_first(self):
        # determine if 100 ms has elapsed
        # The timer is started at last_beep_time + 0.2
        # TODO: Think about this one
        return (self.last_beep_time + 0.2 - self.trial_timer.getTime() + self.frame_period) >= 0.1

    def show_first_target(self):
        # This is tricky -- if the condition evaluates to false, draw the left target
        self.targets[int(self.trial_table['first'][self.trial_counter] == self.right_val)].setAutoDraw(True)

    # first_target functions
    def trial_timer_passed_second(self):
        # this timer is the other way around
        return ((self.trial_timer.getTime() - 0.2 - self.frame_period) <= self.trial_table['switch_time'][self.trial_counter])

    def show_second_target(self):
        self.targets[int(self.trial_table['first'][self.trial_counter] == self.right_val)].setAutoDraw(False)
        self.targets[int(self.trial_table['second'][self.trial_counter] == self.right_val)].setAutoDraw(True)
        self.win.callOnFlip(self.log_switch_time)

    def log_switch_time(self):
        self.trial_data['real_switch_time'] = self.win.lastFrameT - self.trial_start
        # print(self.trial_table['switch_time'][self.trial_counter])
        # print(self.last_beep_time - self.trial_data['real_switch_time'])

    # second_target functions
    def trial_timer_elapsed(self):
        return self.trial_timer.getTime() <= 0

    def record_data(self):
        self.trial_data['index'] = self.trial_counter
        self.trial_data['first_target'] = int(self.trial_table['first'][self.trial_counter])
        self.trial_data['second_target'] = int(self.trial_table['second'][self.trial_counter])
        # real_switch_time logged in log_switch_time
        self.trial_data['first_press'] = self.first_press
        self.trial_data['first_press_time'] = self.first_press_time
        self.trial_data['correct'] = int(self.correct_answer)
        self.trial_data['prep_time'] = self.first_press_time - self.trial_data['real_switch_time']
        # now write data
        with open(self.summary_file_name, 'a') as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_header, lineterminator='\n')
            writer.writerow(self.trial_data)

        self.trial_data.update({'index': np.nan, 'first_target': np.nan, 'second_target': np.nan,
                                'real_switch_time': np.nan, 'first_press': np.nan,
                                'first_press_time': np.nan, 'correct': np.nan, 'prep_time': np.nan})

    def check_answer(self):
        correct_answer = self.trial_table['second'][self.trial_counter] == self.first_press
        delta = self.first_press_time - self.last_beep_time
        good_timing = False
        if delta > 0.075:
            self.too_slow.autoDraw = True
        elif delta < -0.075:
            self.too_fast.autoDraw = True
        elif np.isnan(self.first_press):
            self.too_slow.autoDraw = True
        else:
            good_timing = True
            self.good.autoDraw = True

        self.correct_answer = correct_answer
        if correct_answer and good_timing:
            self.coin.play()

    def draw_feedback(self):
        # text for timing, correctness
        [t.setFillColor((-0.3, 0.7, -0.3) if self.correct_answer else (0.7, -0.3, -0.3))
         for t in self.targets]

    def sched_feedback_timer_reset(self):
        self.win.callOnFlip(self.feedback_timer.reset, 0.3 -
                            self.frame_period)  # 300 ms feedback?

    # feedback functions
    def feedback_timer_elapsed(self):
        return self.feedback_timer.getTime() <= 0

    def remove_feedback(self):
        # remove targets, make sure everything is proper colour
        [t.setAutoDraw(False) for t in self.targets]
        [t.setFillColor([0, 0, 0]) for t in self.targets]
        self.good.autoDraw = False
        self.too_fast.autoDraw = False
        self.too_slow.autoDraw = False

    def increment_trial_counter(self):
        self.trial_counter += 1

    def sched_post_timer_reset(self):
        self.win.callOnFlip(self.post_timer.reset, 0.1 - self.frame_period)

    # post_trial functions
    def post_timer_elapsed(self):
        return self.post_timer.getTime() <= 0

    def trial_counter_exceed_table(self):
        return self.trial_counter >= len(self.trial_table.index)

    def wait_for_press(self):
        return not np.isnan(self.first_press)

    def calc_adapt(self):
        if self.adaptive and self.trial_table['first'][self.trial_counter] != self.trial_table['second'][self.trial_counter]:
            #self.prev_sign = self.correct_answer
            if self.trial_counter == 0:
                pass # initial point, 500 ms
            elif self.trial_counter == 1:
                self.curr_sign = -1.0 if self.correct_answer else 1.0  # shrink if right, grow if wrong
                self.curr_prep_time += (16/60) * self.curr_sign
                self.prev_sign = self.curr_sign
            elif self.trial_counter == 2:
                self.curr_sign = -1.0 if self.correct_answer else 1.0  # shrink if right, grow if wrong
                self.sign_switch_count += 1 if self.curr_sign != self.prev_sign else 0
                self.curr_prep_time += (8/60) * self.curr_sign
                self.prev_sign = self.curr_sign
            else:
                self.curr_sign = -1.0 if self.correct_answer else 1.0
                self.sign_switch_count += 1 if self.curr_sign != self.prev_sign else 0
                self.curr_prep_time += max(1/60, (2 ** (3 - self.sign_switch_count)/60)) * self.curr_sign
            # apply bounds
            self.curr_prep_time = min(0.6, self.curr_prep_time)
            self.curr_prep_time = max(0.05, self.curr_prep_time)
            self.trial_table.loc[self.trial_counter, 'switch_time'] = self.curr_prep_time
            print('Trial: ' + str(self.trial_counter) + ', prep: ' + str(self.curr_prep_time))

    # cleanup functions
    def close_n_such(self):
        pass

    def input(self):
        # collect input
        timestamp, data = self.device.read()  # need to correct timestamp
        if timestamp is not None:
            if self.device.device.__name__ is 'Keyboard':
                for i, j in zip(data[0], data[1]):
                    self.keyboard_state[j[0]] = i[0]
                # colour in if any buttons pressed
                self.device_on = any(self.keyboard_state)
                if np.isnan(self.first_press) and self.device_on:
                    self.first_press = data[1][0][0]
                    self.first_press_time = (timestamp - self.trial_start)[0]

            elif self.device.device.__name__ is 'ForceTransducers':
                # see sg.medfilt(trial_input_buffer, kernel_size=(odd, 1))
                pass
                current_nans = np.isnan(self.trial_input_buffer)
                if current_nans.any():
                    next_index = np.where(current_nans)[0][0]
                    self.trial_input_buffer[next_index, :] = data
                    self.trial_input_time_buffer[next_index, :] = timestamp

    def draw_input(self):
        self.push_feedback.setFillColor([0, 0, 0] if self.device_on else [-1, -1, -1])
