import os
import io
import json
import queue
import threading
import time
import numpy as np
from dataclasses import dataclass
from typing import Optional, Callable, List

try:
    import sounddevice as sd
    _HAS_SD = True
except ImportError:
    _HAS_SD = False
    print(">>> sounddevice tidak terinstall: pip install sounddevice")

try:
    import soundfile as sf
    _HAS_SF = True
except ImportError:
    _HAS_SF = False


COMMAND_MAP = {
    "mulai":    "start",   "start":    "start",
    "main":     "start",   "ayo":      "start",   "halo":  "start",
    "skip":     "skip",    "lewat":    "skip",
    "lanjut":   "skip",    "next":     "skip",    "ganti": "skip",
    "ulangi":   "retry",   "ulang":    "retry",
    "lagi":     "retry",   "retry":    "retry",
    "selesai":  "stop",    "stop":     "stop",    "berhenti": "stop",
    "bantuan":  "help",    "help":     "help",
}

SAMPLERATE = 16_000
CHUNK_SEC  = 2 
CHUNK_SAMPLES = SAMPLERATE * CHUNK_SEC


@dataclass
class VoiceEvent:
    command:   str
    raw_text:  str
    timestamp: float


class VoiceStatus:
    IDLE = "idle"; LISTENING = "listening"; DETECTED = "detected"; ERROR = "error"

    def __init__(self):
        self.state        = self.IDLE
        self.last_raw     = ""
        self.last_command = ""
        self._lock        = threading.Lock()

    def update(self, state, raw="", command=""):
        with self._lock:
            self.state = state; self.last_raw = raw; self.last_command = command

    def get(self):
        with self._lock:
            return {"state": self.state, "last_raw": self.last_raw,
                    "last_command": self.last_command}



class VoiceGreeter:
    """
    Usage:
        greeter = VoiceGreeter()
        greeter.greet("Budi")
        greeter.say("Wah keren sekali!")
        greeter.say_level(3)
    """

    GREETINGS = [
        "Halo {name}! Selamat datang! Ayo main otak atik merah putih!",
        "Hai {name}! Siap bermain? Susun blok merah putihnya ya!",
        "Selamat datang {name}! Yuk kita mulai!",
    ]
    FEEDBACK = {
        "fast":   ["Wah keren sekali!", "Luar biasa cepat!", "Mantap!"],
        "ok":     ["Bagus!", "Hebat sekali!", "Kerja bagus!"],
        "slow":   ["Ayo semangat!", "Pelan-pelan tidak apa-apa!", "Terus coba!"],
        "finish": ["Selesai! Kamu hebat!", "Permainan selesai! Terima kasih!"],
    }

    def __init__(self, lang: str = "id"):
        self._lang     = lang
        self._available = False
        try:
            from gtts import gTTS
            self._gTTS = gTTS
            self._available = _HAS_SD and _HAS_SF
            if self._available:
                print(">>> VoiceGreeter (gTTS) ready.")
            else:
                print(">>> VoiceGreeter: install sounddevice + soundfile untuk audio output.")
        except ImportError:
            print(">>> gTTS tidak terinstall: pip install gtts")

    def _speak_async(self, text: str):
        if not self._available:
            print(f"[Greeter] {text}")
            return
        def _run():
            try:
                buf = io.BytesIO()
                self._gTTS(text=text, lang=self._lang, slow=False).write_to_fp(buf)
                buf.seek(0)
                data, sr = sf.read(buf, dtype="float32")
                sd.play(data, sr)
                sd.wait()
            except Exception as e:
                print(f"[Greeter] TTS error: {e}")
        threading.Thread(target=_run, daemon=True).start()

    def greet(self, name: str = "Adik"):
        import random
        tpl = random.choice(self.GREETINGS)
        self._speak_async(tpl.format(name=name))

    def say(self, text: str):
        self._speak_async(text)

    def say_feedback(self, elapsed: float):
        import random
        if elapsed < 12:
            msgs = self.FEEDBACK["fast"]
        elif elapsed < 25:
            msgs = self.FEEDBACK["ok"]
        else:
            msgs = self.FEEDBACK["slow"]
        self._speak_async(random.choice(msgs))

    def say_level(self, level: int):
        self._speak_async(f"Lanjut ke level {level}!")

    def say_finish(self):
        import random
        self._speak_async(random.choice(self.FEEDBACK["finish"]))

class Wav2Vec2RecogThread(threading.Thread):
    def __init__(
        self,
        model_name: str = "indonesian-nlp/wav2vec2-indonesian-javanese-sundanese",
        vosk_model_path: Optional[str] = None,
        on_command: Optional[Callable[[VoiceEvent], None]] = None,
    ):
        super().__init__(daemon=True, name="Wav2Vec2Recog")
        self.on_command    = on_command
        self.command_queue: queue.Queue[VoiceEvent] = queue.Queue()
        self.audio_buffer  = np.array([], dtype=np.float32)
        self._audio_lock   = threading.Lock()
        self.status        = VoiceStatus()
        self.running       = True
        self.is_available  = False
        self._mode         = None 

        self._load_wav2vec2(model_name)

        if not self.is_available and vosk_model_path:
            self._load_vosk(vosk_model_path)

    def _load_wav2vec2(self, model_name: str):
        try:
            import torch
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            print(f">>> Loading Wav2Vec2 model: {model_name} ...")
            self._processor = Wav2Vec2Processor.from_pretrained(model_name)
            self._model     = Wav2Vec2ForCTC.from_pretrained(model_name)
            self._device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model.to(self._device)
            self._model.eval()
            self._torch     = torch
            self._mode      = "wav2vec2"
            self.is_available = True
            print(f">>> Wav2Vec2 ready on {self._device}.")
        except Exception as e:
            print(f">>> Wav2Vec2 gagal load: {e}")
            print("    Fallback ke Vosk atau install: pip install transformers torch")

    def _load_vosk(self, path: str):
        try:
            from vosk import Model, KaldiRecognizer
            if not os.path.exists(path):
                print(f">>> Vosk model tidak ditemukan: {path}")
                return
            self._vosk_recognizer = KaldiRecognizer(Model(path), SAMPLERATE)
            self._vosk_q = queue.Queue(maxsize=20)
            self._mode   = "vosk"
            self.is_available = True
            print(">>> Vosk fallback ready.")
        except Exception as e:
            print(f">>> Vosk fallback gagal: {e}")

    def _transcribe_wav2vec2(self, audio: np.ndarray) -> str:
        try:
            inputs = self._processor(
                audio, sampling_rate=SAMPLERATE,
                return_tensors="pt", padding=True,
            )
            input_values = inputs.input_values.to(self._device)
            attention    = inputs.get("attention_mask")
            if attention is not None:
                attention = attention.to(self._device)

            with self._torch.no_grad():
                logits = self._model(
                    input_values,
                    attention_mask=attention,
                ).logits

            pred_ids = self._torch.argmax(logits, dim=-1)
            text = self._processor.batch_decode(pred_ids)[0]
            return text.lower().strip()
        except Exception as e:
            print(f"[Wav2Vec2] Inference error: {e}")
            return ""


    def _audio_cb(self, indata, frames, time_info, status):
        chunk = indata[:, 0].astype(np.float32)
        with self._audio_lock:
            self.audio_buffer = np.concatenate([self.audio_buffer, chunk])


    def _parse(self, text: str) -> Optional[str]:
        text = text.lower().strip()
        for word in text.split():
            cmd = COMMAND_MAP.get(word)
            if cmd:
                return cmd
        return None

    def _emit(self, text: str, cmd: str):
        event = VoiceEvent(command=cmd, raw_text=text, timestamp=time.time())
        self.command_queue.put(event)
        self.status.update(VoiceStatus.DETECTED, raw=text, command=cmd)
        print(f"[Voice] '{text}' → {cmd}")
        if self.on_command:
            try: self.on_command(event)
            except Exception as e: print(f"[Voice] callback error: {e}")


    def run(self):
        if not self.is_available:
            return

        if self._mode == "vosk":
            self._run_vosk()
            return

        import sounddevice as sd

        VOLUME_THRESHOLD = 0.04

        while self.running:
            try:
                audio_data = sd.rec(
                    int(SAMPLERATE * CHUNK_SEC),
                    samplerate=SAMPLERATE, channels=1, dtype="float32",
                )
                sd.wait()

                rms = np.sqrt(np.mean(audio_data ** 2))

                if rms < VOLUME_THRESHOLD:
                    continue

                self.status.update(VoiceStatus.LISTENING)

                text = self._transcribe_wav2vec2(audio_data.squeeze())

                if not text:
                    self.status.update(VoiceStatus.IDLE)
                    continue

                print(f"[Mic] (Vol: {rms:.3f}) Mendengar: {text}")
                cmd = self._parse(text)
                if cmd:
                    self._emit(text, cmd)
                else:
                    self.status.update(VoiceStatus.IDLE)

            except Exception as e:
                print(f"[Voice] Error: {e}")
                time.sleep(0.5)

    def _run_vosk(self):
        def _cb(indata, frames, t, status):
            try: self._vosk_q.put_nowait(bytes(indata))
            except queue.Full: pass

        try:
            with sd.RawInputStream(
                samplerate=SAMPLERATE, blocksize=8000,
                dtype="int16", channels=1, callback=_cb,
            ):
                print(">>> Mic aktif (Vosk fallback mode)...")
                while self.running:
                    data = self._vosk_q.get(timeout=1)
                    if self._vosk_recognizer.AcceptWaveform(data):
                        result = json.loads(self._vosk_recognizer.Result())
                        text   = result.get("text", "").strip()
                        if text:
                            cmd = self._parse(text)
                            if cmd:
                                self._emit(text, cmd)
        except Exception as e:
            print(f">>> Vosk thread error: {e}")


    def get_command(self) -> Optional[VoiceEvent]:
        try: return self.command_queue.get_nowait()
        except queue.Empty: return None

    def stop(self):
        self.running = False
        self.status.update(VoiceStatus.IDLE)


VoiceCommandThread = Wav2Vec2RecogThread