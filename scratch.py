import numpy as np
import matplotlib.pyplot as plt

xx = np.genfromtxt('lastFrameIntervals.log', delimiter=',')
plt.plot(xx)

plt.show()