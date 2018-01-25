import numpy as np
import scipy

def moving_avg_std(idxs, data, window):
    avg_idxs, means, stds = [], [], []
    for i in range(window, len(data)):
        avg_idxs.append(np.mean(idxs[i - window:i]))
        means.append(np.mean(data[i - window:i]))
        stds.append(np.std(data[i - window:i]))
    return avg_idxs, np.asarray(means), np.asarray(stds)

class DataAverageInterpolation(object):
    def __init__(self):
        self.xs = []
        self.ys = []
        self.fs = []

    def add_data(self, x, y):
        self.xs.append(x)
        self.ys.append(y)
        self.fs.append(scipy.interpolate.interp1d(x, y))

    def eval(self, x):
        ys = [f(x) for f in self.fs]
        return np.array(np.mean(ys, axis=0)), np.array(np.std(ys, axis=0))