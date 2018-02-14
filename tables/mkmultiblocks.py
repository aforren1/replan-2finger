import itertools

import numpy as np
import pandas as pd


def mk_multi_block(name='testy.csv', combo=[0, 4, 5, 9], num_trials=80,
                   prop_switch=0.3, min_max_time=(0.1, 0.45), frame_rate=60):
    num_switch_trials = int(num_trials * prop_switch)
    num_other_trials = int(num_trials - num_switch_trials)
    pairs = list(itertools.product(combo, combo))
    pairs = [list(x) for x in pairs]
    matching = sum([x[0] == x[1] for x in pairs])
    not_matching = sum([x[0] != x[1] for x in pairs])

    if num_switch_trials % not_matching != 0:
        raise ValueError('Make sure all selections are sampled evenly.')
    min_frames = int(min_max_time[0] * frame_rate)
    max_frames = int(min_max_time[1] * frame_rate)
    switch_times = np.random.randint(
        min_frames, max_frames + 1, num_switch_trials).astype('d')
    switch_times /= frame_rate
    tmp = list()
    count = 0
    for x in pairs:
        if x[0] == x[1]:
            rr = np.tile(x, (num_other_trials//matching, 1))
            rr = np.concatenate((rr, np.zeros((rr.shape[0], 1))), axis=1)
        else:
            rr = np.tile(x, (num_switch_trials//not_matching, 1))
            rr = np.concatenate(
                (rr, switch_times[count:count+rr.shape[0], None]), axis=1)
            count += rr.shape[0]
        tmp.append(rr)
    all_pairs = np.vstack(tmp)
    np.random.shuffle(all_pairs)
    practice = [[x, y] for x, y in zip(combo, combo)]
    for i in practice:
        i.append(0)
    all_pairs = np.vstack((practice, all_pairs))
    pair_frame = pd.DataFrame(
        all_pairs, columns=['first', 'second', 'switch_time'])
    pair_frame.to_csv(name, index=False, float_format='%.4f')


def mk_multi_blocks(fingers=[0, 4, 5, 9], blocks=8):
    mk_multi_block('multiblock0_demo.csv', combo=fingers,
                   num_trials=50, prop_switch=0)
    for i in range(blocks - 1):
        mk_multi_block('multiblock' + str(i + 1) + '.csv', combo=fingers)


mk_multi_blocks()
