import pandas as pd
import matplotlib.pyplot as plt

x1 = pd.read_csv('data/001/id_001_block1_105628.csv')
x2 = pd.read_csv('data/001/id_001_block2_112027.csv')

y1 = pd.read_csv('data/001/id_001_block1_adapt_104935.csv')
y2 = pd.read_csv('data/001/id_001_block2_adapt_111200.csv')

x = pd.concat([x1, x2])
y = pd.concat([y1, y2])
x = x[x['first_target'] != x['second_target']]
y = y[y['first_target'] != y['second_target']]
x = x.sort_values('prep_time')
y = y.sort_values('prep_time')
plt.plot(x['prep_time'], x['correct'], 'ro', alpha=0.6)
plt.plot(y['prep_time'], y['correct'] + 0.01, 'go', alpha=0.6)
plt.show()
