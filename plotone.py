import sys
import pandas as pd
import matplotlib.pyplot as plt

xx = pd.read_csv(sys.argv[1])

yy = xx[xx['first_target'] != xx['second_target']]

plt.plot(yy['prep_time'], yy['correct'], 'ro')

plt.show()
