from two_choice_imp import TwoChoice
from multi_choice_imp import MultiChoice
from psychopy import core, gui
from psychopy.event import Mouse

if __name__ == '__main__':
    settings = {'subject': '001',
                'fullscreen': False,
                'forceboard': False,
                'twochoice': True,
                'trial_table': 'tables/test.csv'}

    dialog = gui.DlgFromDict(dictionary=settings, title='Replanning')

    if not dialog.OK:
        core.quit()

    # could have a second menu, depending on the experiment
    if settings['twochoice']:
        experiment = TwoChoice(settings=settings)
    else:
        experiment = MultiChoice(settings=settings)

    mouse = Mouse(visible=False, win=experiment.win)
    experiment.coin.play()
    with experiment.device:
        experiment.win.flip()
        while experiment.state is not 'cleanup':
            experiment.input()  # collect input
            experiment.draw_input()  # draw the input
            experiment.step()  # evaluate any transitions
            if any(mouse.getPressed()):
                experiment.to_cleanup()
            experiment.win.flip()  # flip frame buffer
    experiment.win.close()
    # experiment.win.saveFrameIntervals() # for debugging
    core.quit()
