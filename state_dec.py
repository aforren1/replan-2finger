from transitions import Machine


class StateMachine(Machine):
    def __init__(self):
        states = ['wait',
                  'pretrial',
                  'enter_trial',
                  'first_target',
                  'second_target',
                  'feedback',
                  'post_trial',
                  'cleanup']
        transitions = [
            {'source': 'wait',
             'trigger': 'step',
             'conditions': 'wait_for_press',
             'after': 'remove_text',
             'dest': 'pretrial'},

            {'source': 'pretrial',
             'trigger': 'step',
             'conditions': 'wait_for_release',
             'after': ['sched_beep',
                       'sched_trial_timer_reset',
                       'sched_record_trial_start',
                       'first_press_reset'],
             'dest': 'enter_trial'},

            # wait for 100 ms until showing first image (to coincide w/ real audio onset)
            {'source': 'enter_trial',
             'trigger': 'step',
             'conditions': 'trial_timer_passed_first',  # i.e. 100 ms - ~16ms elapsed
             # after state change (after conditions are evaluated, run once)
             'after': 'show_first_target',
             'dest': 'first_target'},

            # after 100 ms, show the first image
            {'source': 'first_target',
             'trigger': 'step',
             # i.e. the proposed prep time in table elapsed
             'conditions': 'trial_timer_passed_second',
             # after state change (after conditions are evaluated, run once)
             'after': 'show_second_target',
             'dest': 'second_target'},

            # after n extra ms, show second image & wait until beeps are over (plus a little)
            {'source': 'second_target',
             'trigger': 'step',
             'conditions': 'trial_timer_elapsed',  # Beeps have finished + 200ms of mush
             'after': ['check_answer',
                       'draw_feedback',  # figure out what was pushed based on buffer
                       'sched_feedback_timer_reset'],  # set timer for feedback duration
             'dest': 'feedback'},

            # show feedback for n seconds
            {'source': 'feedback',
             'trigger': 'step',
             # Once n milliseconds have passed...
             'conditions': 'feedback_timer_elapsed',
             'after': ['remove_feedback',  # remove targets and make sure all colours are normal
                       'record_data',  # save data from trial
                       'increment_trial_counter',  # add one to the trial counter
                       'sched_post_timer_reset'],  # # set timer for inter-trial break
             'dest': 'post_trial'},

            # evaluate whether to exit experiment first...
            {'source': 'post_trial',
             'trigger': 'step',
             'conditions': ['post_timer_elapsed',  # Once n milliseconds have passed...
                            'trial_counter_exceed_table'],  # And the number of trials exceeds trial table
             'after': ['close_n_such'],  # Clean up, we're done here
             'dest': 'cleanup'},

            # ... or move to the next trial
            {'source': 'post_trial',
             'trigger': 'step',
             'conditions': ['post_timer_elapsed',  # If the previous one evaluates to False, we should end up here
                            'wait_for_press'],
             'dest': 'pretrial'}
        ]
        Machine.__init__(self, states=states,
                         transitions=transitions, initial='wait')
