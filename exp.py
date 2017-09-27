from psychopy import core, gui
from state import StateMachine

settings = {'subject': '001',
            'fullscreen': False,
            'forceboard': False,
            'trial_table (relative)': 'C:/Users/aforrence/Documents/shared_docs/blam/replan-2finger/'}

dialog = gui.DlgFromDict(dictionary=settings, title='Two-finger Replan')

if not dialog.OK:
    core.quit()

state_machine = StateMachine(settings=settings)

with state_machine.device:
    state_machine.start()

    while state_machine.state is not 'cleanup':
            state_machine.input() # collect input
            state_machine.draw_input() # draw the input
            state_machine.step() # evaluate any transitions (incl. drawing, scheduling audio, etc.)
            state_machine.win.flip() # flip frame buffer


core.quit()

