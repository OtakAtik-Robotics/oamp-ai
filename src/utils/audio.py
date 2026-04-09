import os
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path

def play_audio(wav):
    if isinstance(wav, (str, Path)):
        path = str(wav)
        if not Path(path).exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        data, samplerate = sf.read(path, dtype='float32')
    else:
        data = np.asarray(wav)
        samplerate = 22050

    if data.ndim == 1:
        data = data.reshape(-1, 1)

    sd.play(data, samplerate)
    sd.wait()

def play_feedback_audio(time_elapsed):
    if time_elapsed < 10:
        play_audio("assets/audio/menakjubkan.wav")
    elif time_elapsed < 15:
        play_audio("assets/audio/hebat_sekali.wav")
    elif time_elapsed < 20:
        play_audio("assets/audio/mantap.wav")
    elif time_elapsed < 25:
        play_audio("assets/audio/kerja_bagus.wav")
    elif time_elapsed < 30:
        play_audio("assets/audio/ayo_semangat.wav")
    else:
        play_audio("assets/audio/jangan_menyerah.wav")