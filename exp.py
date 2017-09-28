from psychopy import core, gui
from state import StateMachine

settings = {'subject': '001',
            'fullscreen': False,
            'forceboard': False,
            'trial_table': 'test.csv'}

dialog = gui.DlgFromDict(dictionary=settings, title='Two-finger Replan')

if not dialog.OK:
    core.quit()

# could have a second menu, depending on the experiment
state_machine = StateMachine(settings=settings)

with state_machine.device:

    while state_machine.state is not 'cleanup':
            state_machine.input() # collect input
            state_machine.draw_input() # draw the input
            state_machine.step() # evaluate any transitions (incl. drawing, scheduling audio, etc.)
            state_machine.win.flip() # flip frame buffer

core.quit()
