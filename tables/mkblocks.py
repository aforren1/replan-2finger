import numpy as np
import pandas as pd
# header: first, second, switch_time
# first is the first side/stimulus, second is the swapped (or the same),
# switch_time is the time before the last beep that the switch occurs


def mk_block(name='testx.csv', pair=[0, 4], num_trials=120,
             prop_switch=0.35, min_max_time=(0.1, 0.45), frame_rate=60):
    num_switch_trials = int(num_trials * prop_switch)
    num_other_trials = int(num_trials - num_switch_trials)
    if num_switch_trials % 2 != 0:
        raise ValueError('Make sure both directions are sampled evenly.')

    min_frames = int(min_max_time[0] * frame_rate)  # assume 60 fps
    max_frames = int(min_max_time[1] * frame_rate)

    switch_times = np.random.randint(
        min_frames, max_frames + 1, num_switch_trials).astype('d')
    switch_times /= frame_rate  # recover time in seconds
    # otherwise, switch times are zero
    pair = [float(pair[0]), float(pair[1])]
    pair_1 = pair
    pair_2 = pair[::-1]
    pair_3 = [pair[0], pair[0]]
    pair_4 = [pair[1], pair[1]]

    # first switch pair
    pairs_1 = np.tile(pair_1, (num_switch_trials//2, 1))
    pairs_2 = np.tile(pair_2, (num_switch_trials//2, 1))
    pairs_3 = np.tile(pair_3, (num_other_trials//2, 1))
    pairs_4 = np.tile(pair_4, (num_other_trials // 2, 1))

    pairs_1 = np.concatenate(
        (pairs_1, switch_times[:num_switch_trials//2, None]), axis=1)
    pairs_2 = np.concatenate(
        (pairs_2, switch_times[-num_switch_trials//2:, None]), axis=1)
    pairs_3 = np.concatenate(
        (pairs_3, np.zeros((num_other_trials//2, 1))), axis=1)
    pairs_4 = np.concatenate(
        (pairs_4, np.zeros((num_other_trials//2, 1))), axis=1)

    pair_3.append(0)
    pair_4.append(0)
    practice = np.tile([pair_3, pair_4], (2, 1))  # 4 practice trials
    all_pairs = np.vstack((pairs_1, pairs_2, pairs_3, pairs_4))
    np.random.shuffle(all_pairs)
    all_pairs = np.vstack((practice, all_pairs))
    pair_frame = pd.DataFrame(
        all_pairs, columns=['first', 'second', 'switch_time'])
    pair_frame.to_csv(name, index=False, float_format='%.4f')


def mk_blocks(fingers=[0, 4, 5, 9], blocks_per_pair=2):
    pairs = [[a, b] for a in fingers for b in fingers if (a != b & b < a)]
    np.random.shuffle(pairs)
    pairs = np.repeat(pairs, blocks_per_pair, 0)
    mk_block('block0_demo.csv', pair=pairs[0], num_trials=50, prop_switch=0)
    for i, pair in enumerate(pairs):
        mk_block('block' + str(i + 1) + '.csv', pair=pair)


mk_blocks()
