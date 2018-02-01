from datetime import datetime as dt
import csv
import os.path as op
import numpy as np
from scipy import signal as sg
import pandas as pd
from psychopy import prefs
from state_imp import TwoChoice

# we need to set prefs *before* setting the other stuff
prefs.general['audioLib'] = ['sounddevice']
from psychopy import clock, core, visual, sound
from toon.audio import beep_sequence
from toon.input import Keyboard, ForceTransducers, MultiprocessInput

class MultiChoice(TwoChoice):
    def __init__(self, settings=None):
        super(FingerExp, self).__init__(settings=settings)

    def setup_visuals(self):
        right_hand = visual.ImageStim(self.win, image='hand.png', size=(0.4, 0.4), 
                                      pos=(0.3, 0), ori=-90)
        left_hand = visual.ImageStim(self.win, image='hand.png', size=(0.4, 0.4), 
                                     pos=(-0.3, 0), ori=90, flipHoriz=True)
        self.background = visual.BufferImageStim(self.win, stim=[left_hand, right_hand])
        # self.background.autoDraw = True
        # thumb, index, middle, ring, pinky
        pos_r = [[0.3075, -0.1525], [0.1775, -0.06125], [0.14375, 0.02375], [0.1775, 0.0925], [0.2475, 0.1525]]

        pos_l = [[-x[0], x[1]] for x in pos_r]
        pos_l.reverse()
        pos_l.extend(pos_r)

        self.targets = [visual.Circle(self.win, fillColor=(0.3, -0.2, -0.2), pos=x, 
                                      size=0.05, opacity=1.0) 
                        for x in pos_l]
        
        # push feedback
        self.push_feedback = visual.Circle(self.win, size=0.1, fillColor=[-1, -1, -1], pos=(0, 0),
                                           autoDraw=False, autoLog=False, name='push_feedback')
        # fixation
        self.fixation = visual.Circle(self.win, size=0.05, fillColor=[1, 1, 1], pos=(0, 0),
                                      autoDraw=False, name='fixation')

        # text
        self.wait_text = visual.TextStim(self.win, text='Press a key to start.', pos=(0, 0),
                                         units='norm', color=(1, 1, 1), height=0.2,
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
    
    def remove_text(self):
        self.wait_text.autoDraw = False
        self.background.autoDraw = True
        self.push_feedback.autoDraw = True
        self.fixation.autoDraw = True
    
    def show_first_target(self):
        self.targets[int(self.trial_table['first'][self.trial_counter])].autoDraw = True
    
    def show_second_target(self):
        self.targets[int(self.trial_table['first'][self.trial_counter])].autoDraw = False
        self.targets[int(self.trial_table['second'][self.trial_counter])].autoDraw = True
        self.win.callOnFlip(self.log_switch_time)
