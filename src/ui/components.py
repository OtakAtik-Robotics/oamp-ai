import time
import threading
import customtkinter
from typing import Optional
from PIL import Image, ImageTk

class TextFrame(customtkinter.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(
            self, text=title, fg_color="gray30", corner_radius=6,
            font=("Helvetica", 13),
        ).grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")


class ImageFrame(customtkinter.CTkFrame):
    def __init__(self, master, title=""):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        if title:
            customtkinter.CTkLabel(
                self, text=title, corner_radius=6, font=("Helvetica",12),
            ).grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")

class TimerDisplay(customtkinter.CTkFrame):
    COLOR_FAST   = "#22c55e"
    COLOR_OK     = "#eab308"
    COLOR_SLOW   = "#f97316"
    COLOR_DANGER = "#ef4444"

    def __init__(self, master, width=120, font_size=28):
        super().__init__(master, corner_radius=8, fg_color="#1a1a1a", width=width)
        self.pack_propagate(False)
        self._label = customtkinter.CTkLabel(
            self, text="00:00.00",
            font=("Helvetica", font_size, "bold"),
            text_color=self.COLOR_FAST,
        )
        self._label.pack(expand=True, fill="both")

    def set_time(self, elapsed: float):
        m  = int(elapsed // 60)
        s  = int(elapsed % 60)
        ms = int((elapsed % 1) * 100)
        c  = (self.COLOR_FAST if elapsed < 10
              else self.COLOR_OK if elapsed < 25
              else self.COLOR_SLOW if elapsed < 40
              else self.COLOR_DANGER)
        self._label.configure(text=f"{m:02d}:{s:02d}.{ms:02d}", text_color=c)

    def reset(self):
        self._label.configure(text="00:00.00", text_color=self.COLOR_FAST)

class LevelBadge(customtkinter.CTkFrame):
    COLORS = {1:"#ef4444",2:"#f97316",3:"#eab308",4:"#22c55e",
              5:"#06b6d4",6:"#3b82f6",7:"#8b5cf6",8:"#ec4899"}

    def __init__(self, master, **kw):
        super().__init__(master, corner_radius=10, fg_color="#141414", **kw)
        self.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(
            self, text="LEVEL", font=("Helvetica",10,"bold"), text_color="#555",
        ).grid(row=0, column=0, pady=(8,0))
        self._num = customtkinter.CTkLabel(
            self, text="—", font=("Helvetica",42,"bold"), text_color="#D32F2F",
        )
        self._num.grid(row=1, column=0, pady=(0,8))

    def set_level(self, level: int):
        self._num.configure(text=str(level), text_color=self.COLORS.get(level,"#D32F2F"))

class VoiceIndicator(customtkinter.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._dot = customtkinter.CTkLabel(
            self, text="●", font=("Helvetica",14), text_color="#555", width=20,
        )
        self._dot.grid(row=0, column=0, padx=(4,2))
        self._text = customtkinter.CTkLabel(
            self, text="Voice off", font=("Helvetica",11), text_color="#666",
        )
        self._text.grid(row=0, column=1, padx=(0,8))
        self._blinking = False

    def set_listening(self, active: bool):
        if active and not self._blinking:
            self._blinking = True
            self._blink()
            self._text.configure(text="Mendengarkan...", text_color="#22c55e")
        elif not active:
            self._blinking = False
            self._dot.configure(text_color="#555")
            self._text.configure(text="Voice off", text_color="#666")

    def show_command(self, cmd: str):
        labels = {"start":"▶ Mulai!","skip":"⏭ Lewat","retry":"↺ Ulangi","stop":"■ Stop","help":"? Help"}
        self._text.configure(text=labels.get(cmd, cmd), text_color="#f59e0b")
        self._dot.after(1500, lambda: self._text.configure(text="Mendengarkan...", text_color="#22c55e"))

    def _blink(self):
        if not self._blinking: return
        current = self._dot.cget("text_color")
        self._dot.configure(text_color="#22c55e" if current=="#0a4020" else "#0a4020")
        self._dot.after(600, self._blink)

EMOTION_EMOJI = {
    "happy":("😊","#22c55e"), "sad":("😢","#3b82f6"),
    "angry":("😠","#ef4444"), "fear":("😨","#8b5cf6"),
    "surprise":("😲","#f59e0b"), "disgust":("😒","#6b7280"),
    "neutral":("😐","#94a3b8"),
}

class EmotionDisplay(customtkinter.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._emoji = customtkinter.CTkLabel(self, text="😐", font=("Helvetica",18), width=26)
        self._emoji.grid(row=0, column=0, padx=(4,2))
        self._label = customtkinter.CTkLabel(self, text="Netral", font=("Helvetica",11), text_color="#94a3b8")
        self._label.grid(row=0, column=1, padx=(0,8))

    def set_emotion(self, emotion: str):
        emoji, color = EMOTION_EMOJI.get(emotion, ("😐","#94a3b8"))
        self._emoji.configure(text=emoji)
        self._label.configure(text=emotion.capitalize(), text_color=color)

class DualCameraPanel(customtkinter.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="#111111", corner_radius=12, **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Label game camera
        customtkinter.CTkLabel(
            self, text="KAMERA PERMAINAN",
            font=("Helvetica",9,"bold"), text_color="#555",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8,2))

        self._game_cam = customtkinter.CTkLabel(self, text="", anchor="center")
        self._game_cam.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,4))

        # Separator
        customtkinter.CTkFrame(
            self, fg_color="#222", height=1,
        ).grid(row=2, column=0, sticky="ew", padx=10)

        # Label face camera
        customtkinter.CTkLabel(
            self, text="KAMERA WAJAH",
            font=("Helvetica",9,"bold"), text_color="#555",
        ).grid(row=2, column=0, sticky="w", padx=10, pady=(2,2))

        self._face_cam = customtkinter.CTkLabel(self, text="", anchor="center")
        self._face_cam.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0,8))

    def update_game_frame(self, pil_image: Image.Image):
        w = self._game_cam.winfo_width()
        h = self._game_cam.winfo_height()
        if w > 10 and h > 10:
            fw, fh = pil_image.size
            scale = min(w/fw, h/fh)
            if scale != 1.0:
                pil_image = pil_image.resize(
                    (int(fw*scale), int(fh*scale)), Image.Resampling.LANCZOS
                )
        tk_img = ImageTk.PhotoImage(image=pil_image)
        self._game_cam.imgtk = tk_img
        self._game_cam.configure(image=tk_img)

    def update_face_frame(self, pil_image: Image.Image):
        """Update frame kamera wajah."""
        w = self._face_cam.winfo_width()
        h = self._face_cam.winfo_height()
        if w > 10 and h > 10:
            fw, fh = pil_image.size
            scale = min(w/fw, h/fh)
            if scale != 1.0:
                pil_image = pil_image.resize(
                    (int(fw*scale), int(fh*scale)), Image.Resampling.LANCZOS
                )
        tk_img = ImageTk.PhotoImage(image=pil_image)
        self._face_cam.imgtk = tk_img
        self._face_cam.configure(image=tk_img)

class StatusBar(customtkinter.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="#0a0a0a", corner_radius=0, height=34, **kw)
        self.grid_propagate(False)
        self.grid_columnconfigure(5, weight=1)

        self._sdot = customtkinter.CTkLabel(self, text="●", font=("Helvetica",12), text_color="#555", width=16)
        self._sdot.grid(row=0, column=0, padx=(10,2), pady=5)
        self._slbl = customtkinter.CTkLabel(self, text="Offline", font=("Helvetica",11), text_color="#666")
        self._slbl.grid(row=0, column=1, padx=(0,12), pady=5)

        customtkinter.CTkLabel(self, text="|", text_color="#222").grid(row=0, column=2, pady=5)
        self.emotion = EmotionDisplay(self)
        self.emotion.grid(row=0, column=3, padx=(8,12), pady=2)
        customtkinter.CTkLabel(self, text="|", text_color="#222").grid(row=0, column=4, pady=5)
        self.voice = VoiceIndicator(self)
        self.voice.grid(row=0, column=5, padx=(8,0), pady=2)

        self._fps = customtkinter.CTkLabel(self, text="FPS: —", font=("Helvetica",10), text_color="#444")
        self._fps.grid(row=0, column=6, padx=(0,12), pady=5, sticky="e")
        self._att = customtkinter.CTkLabel(self, text="Percobaan: —", font=("Helvetica",10), text_color="#555")
        self._att.grid(row=0, column=7, padx=(0,16), pady=5, sticky="e")

    def set_server_online(self, online: bool):
        if online:
            self._sdot.configure(text_color="#22c55e")
            self._slbl.configure(text="Server online", text_color="#22c55e")
        else:
            self._sdot.configure(text_color="#ef4444")
            self._slbl.configure(text="Offline (buffer)", text_color="#ef4444")

    def set_fps(self, fps: int):
        c = "#22c55e" if fps >= 20 else "#f97316" if fps >= 10 else "#ef4444"
        self._fps.configure(text=f"FPS: {fps}", text_color=c)

    def set_attempts(self, n: int):
        self._att.configure(text=f"Percobaan: {n}")