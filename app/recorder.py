import sounddevice as sd
import numpy as np
import wavio
import threading
import time

class Recorder:
    def __init__(self, fs=44100):
        self.fs = fs
        self.recording = False
        self.frames = []

    def start(self):
        self.recording = True
        self.frames = []
        def callback(indata, frames, time, status):
            self.frames.append(indata.copy())
        self.stream = sd.InputStream(samplerate=self.fs, channels=1, callback=callback)
        self.stream.start()

    def stop(self, filename="recording.wav"):
        self.stream.stop()
        self.stream.close()
        self.recording = False
        audio = np.concatenate(self.frames, axis=0)
        wavio.write(filename, audio, self.fs, sampwidth=2)
        return filename
