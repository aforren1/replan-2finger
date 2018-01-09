from psychopy import core, gui
from psychopy.event import Mouse
from state import StateMachine

if __name__ == '__main__':
    settings = {'subject': '001',
                'fullscreen': False,
                'forceboard': False,
                'trial_table': 'test.csv'}

    dialog = gui.DlgFromDict(dictionary=settings, title='Two-finger Replan')

    if not dialog.OK:
        core.quit()

    # could have a second menu, depending on the experiment
    state_machine = StateMachine(settings=settings)

    mouse = Mouse(visible=False, win=state_machine.win)
    state_machine.coin.play()
    with state_machine.device:
        state_machine.win.flip()
        while state_machine.state is not 'cleanup':
            state_machine.input() # collect input
            state_machine.draw_input() # draw the input
            state_machine.step() # evaluate any transitions (incl. drawing, scheduling audio, etc.)
            if any(mouse.getPressed()):
                state_machine.to_cleanup()
            state_machine.win.flip() # flip frame buffer
    state_machine.win.close()
    core.quit()
