import numpy as np
from time import sleep
from pyfilterbank import melbank
import threading as thr

from .spectroload import sampledAudio

# CONSTANTS
# mel projection matrix
A = melbank.compute_melmat(80,90,7600,1001)
As = (A[0].T / A[0].sum(axis=1)).T
A = (As, A[0]) # normalized, unnormalized

# OBJECTS
class Update_Queue_Reader(thr.Thread):
    def __init__(self,
                 app_handle,
                 user_interact_queue,
                 refresh_rate=1.):
        super().__init__()

        global USER_INTERACT_QUEUE
        USER_INTERACT_QUEUE = user_interact_queue
        self.daemon = True
        self.app = app_handle
        self.fps = float(refresh_rate)

    def run(self):
        while True:
            last = len(USER_INTERACT_QUEUE)
            sleep(1 / self.fps)
            if last == len(USER_INTERACT_QUEUE): continue
            self.app.refresh_interactive()

class Update_Queue_Clearer(thr.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True

    def run(self):
        while True:
            sleep(20.)
            for i in range(len(USER_INTERACT_QUEUE) - 2):
                USER_INTERACT_QUEUE.pop()

# METHODS
def compute_spectrogram(fi, params):
    minlevel = 1e-5
    uu, v, s, t = params

    X = sampledAudio(fi, pre_emph=False).getSTFT()
    X = np.maximum(np.abs(X), minlevel)
    Y = sampledAudio(fi, pre_emph=False).getSTFT().T
    Y = np.abs(Y.T)@ A[1].T
    X = X @ A[1].T
    X = np.log10(X)
    Y = np.log10(np.maximum(Y, minlevel))
    D_db = (20 * Y) -16
    Q = (np.maximum(D_db - uu * 100, minlevel) + v)/v
    Y = np.clip(Q, 0, t) + s
    Y = np.maximum(Y, 0)
    return X, Y
