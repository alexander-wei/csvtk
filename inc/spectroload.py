import numpy as np
from scipy import signal
from scipy.io.wavfile import read as _wavread

class sampledAudio:
    """
    sampledAudio( fs, pre_emph )
    """
    def __init__(self, file, fs=16000, pre_emph=True):
        self.data = ""
        self.file = file
        self._readSample(pre_emph, fs)

    def _readSample(self, pre_emph=True, fs=16000):
        aud = _wavread(self.file)
        T1 = np.random.rand() * aud[1].shape[0]; T2= T1 + 5 * fs
        T1,T2 = int(np.floor(T1)), int(np.floor(T2))

        if pre_emph:
            preem = aud[1].astype(np.float64)
            preem[1:] -= 0.97 * preem[:-1]
            self.data = preem.astype(np.int16)
        else:
            self.data = aud[1].astype(np.int16)

        def butter_highpass(cutoff, fs, order=5):
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)
            return b, a

        b, a = butter_highpass(30, 16000, order=5)

        self.data = signal.filtfilt(b, a, self.data)

    def getSTFT(self, nfft=2000, noverlap=750, nperseg=1000,fs=1):
        Spect = signal.stft(self.data,fs=fs,nfft=nfft,noverlap=noverlap,nperseg=nperseg)
        Spect=Spect[2].T
        Spect = np.array(Spect)
        Spect = Spect.reshape(-1,nperseg+1)
        return Spect
