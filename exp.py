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
            state_machine.step()
            state_machine.win.flip()


core.quit()

