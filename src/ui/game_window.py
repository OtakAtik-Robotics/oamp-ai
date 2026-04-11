import os
import time
import random
import numpy as np
import cv2
import torch
import customtkinter
from PIL import Image, ImageTk
from typing import Optional

from src.api_client import ServerClient, SessionResult
from src.utils.audio import play_audio, play_feedback_audio
from src.utils.math_eval import estimate_cognitive_age
from src.ui.components import (
    TextFrame, ImageFrame,
    TimerDisplay, LevelBadge, StatusBar, DualCameraPanel,
)
from src.vision.blocks import YOLODetectionThread
from src.vision.hands import HandTracker
from src.vision.face import FaceEmotionThread, FaceMeshDrawer
from src.vision.evaluator import BlockEvaluator
from src.voice.recog import VoiceCommandThread, VoiceGreeter, VoiceStatus


RED     = "#D32F2F"
BG_DARK = "#0f0f0f"
BG_CARD = "#1a1a1a"
WHITE   = "#f1f5f9"
MUTED   = "#64748b"


class GameWindow(customtkinter.CTk):

    def __init__(
        self,
        user_data: dict,
        server_client: Optional[ServerClient] = None,
        hardware_conn=None,
    ):
        super().__init__()
        self.user_data     = user_data
        self.server_client = server_client
        self.serial_thread = hardware_conn
        self.session_id: Optional[str] = None

        self._setup_env()
        self._setup_window()
        self._setup_layout()
        self._setup_game_state()
        self._setup_ai()
        self._preload_images()

        # Sapa anak setelah UI siap
        self.after(800, self._greet_player)

    def _setup_env(self):
        self.display_half  = os.getenv("DISPLAY_HALF", "true").lower() == "true"
        self.hide_camera   = os.getenv("HIDE_CAMERA",  "false").lower() == "true"
        self.button_mode   = os.getenv("BUTTON_MODE",  "false").lower() == "true"
        self.debug_mode    = os.getenv("DEBUG_MODE",   "false").lower() == "true"
        self.max_level     = min(max(int(os.getenv("MAX_LEVEL", "8")), 1), 8)
        self.yolo_skip     = int(os.getenv("YOLO_SKIP_FRAMES",      "2"))
        self.mp_skip       = int(os.getenv("MEDIAPIPE_SKIP_FRAMES",  "2"))
        self.enable_face   = os.getenv("ENABLE_FACE_CAMERA", "true").lower() == "true"
        self.enable_voice  = os.getenv("ENABLE_VOICE",        "true").lower() == "true"
        self.voice_model   = os.getenv("VOICE_MODEL", "indonesian-nlp/wav2vec2-large-xlsr-indonesian")
        # Dual camera indices
        self.cam_game_idx  = int(os.getenv("CAMERA_GAME_INDEX",  os.getenv("CAMERA_INDEX", "0")))
        self.cam_face_idx  = int(os.getenv("CAMERA_FACE_INDEX",  "1"))
        self.base_dir      = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    def _setup_window(self):
        self.title("Otak Atik Merah Putih")
        w, h = (1200, 620) if self.display_half else (1400, 820)
        self.geometry(f"{w}x{h}")
        self.configure(fg_color=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

    def _setup_layout(self):
        self._main = customtkinter.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._main.grid(row=0, column=0, sticky="nsew")
        # Kiri: soal + level + timer | Kanan: 2 kamera
        self._main.grid_columnconfigure(0, weight=1)
        self._main.grid_columnconfigure(1, weight=3)
        self._main.grid_rowconfigure(0, weight=1)

        # ── Left panel ────────────────────────────────────────────
        self._left = customtkinter.CTkFrame(self._main, fg_color=BG_CARD, corner_radius=12)
        self._left.grid(row=0, column=0, sticky="nsew", padx=(12,6), pady=12)
        self._left.grid_columnconfigure(1, weight=1)
        self._left.grid_rowconfigure(1, weight=1)

        self._level_badge = LevelBadge(self._left, width=90)
        self._level_badge.grid(row=0, column=0, rowspan=2, padx=(12,8), pady=12, sticky="n")

        customtkinter.CTkLabel(
            self._left, text="BLOCK DESIGN",
            font=("Helvetica",10,"bold"), text_color=MUTED,
        ).grid(row=0, column=1, sticky="w", padx=(0,12), pady=(12,0))

        self._img_frame = customtkinter.CTkFrame(self._left, fg_color="#111", corner_radius=8)
        self._img_frame.grid(row=1, column=1, sticky="nsew", padx=(0,12), pady=(4,12))
        self._img_frame.grid_propagate(False)

        self.frame_w = 340 if self.display_half else 480
        self.frame_h = 340 if self.display_half else 480

        self._img_label = customtkinter.CTkLabel(self._img_frame, text="")
        self._img_label.pack(expand=True, fill="both")

        self._timer = TimerDisplay(self._left, width=90, font_size=22)
        self._timer.grid(row=2, column=0, padx=(12,8), pady=(0,8), sticky="ew")

        self._start_btn = customtkinter.CTkButton(
            self._left, text="▶  MULAI",
            font=("Helvetica",14,"bold"), height=44,
            corner_radius=8, fg_color=RED, hover_color="#B71C1C",
            text_color=WHITE, command=self._on_start,
        )
        self._start_btn.grid(row=2, column=1, padx=(0,12), pady=(0,8), sticky="ew")

        # ── Right panel: DualCameraPanel ─────────────────────────
        if not self.hide_camera:
            self._cam_panel = DualCameraPanel(self._main)
            self._cam_panel.grid(row=0, column=1, sticky="nsew", padx=(6,12), pady=12)
        else:
            self._cam_panel = None

        # ── Status bar ────────────────────────────────────────────
        self._status_bar = StatusBar(self)
        self._status_bar.grid(row=1, column=0, sticky="ew")

        self.bind("<Return>", lambda _: self._on_skip())

    def _setup_game_state(self):
        self._timer_running = False
        self._start_time    = 0.0
        self._start_task    = 0.0
        self._frame_count   = 0
        self._fps_counter   = 0
        self._fps_ts        = time.time()
        self._latest_boxes  = []
        self._cached_images = {}
        self._task_flags    = {i: True for i in range(1, self.max_level+1)}
        self._timer_all     = []
        self._cog_ages      = []
        self._current_q     = 1
        self._current_variant = ""
        self._image_visible   = False
        self._image_show_ts   = 0.0
        self._image_duration  = 5.0
        self._level_btn: Optional[customtkinter.CTkButton] = None
        self._evaluator     = BlockEvaluator()
        self._cur_emotion   = "neutral"

    def _setup_ai(self):
        # Game camera (tangan + blok)
        self._cap_game = cv2.VideoCapture(self.cam_game_idx)
        self._cap_game.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self._cap_game.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Face camera (hanya jika di-enable)
        if self.enable_face:
            self._cap_face = cv2.VideoCapture(self.cam_face_idx)
            self._cap_face.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            self._cap_face.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._face_cam_ok = self._cap_face.isOpened()
            if not self._face_cam_ok:
                print(f">>> Kamera wajah (index {self.cam_face_idx}) tidak tersedia.")
        else:
            self._cap_face = None
            self._face_cam_ok = False
            print(">>> Face camera disabled via ENABLE_FACE_CAMERA=false")

        # Hand tracker
        self._hand_tracker = HandTracker(draw_style="rich")

        # Face mesh drawer (hanya jika face camera aktif)
        if self._face_cam_ok:
            self._face_mesh = FaceMeshDrawer(
                draw_tesselation=True, draw_contours=True, draw_iris=True,
            )
        else:
            self._face_mesh = None

        # Face emotion thread (hanya jika face camera aktif)
        if self._face_cam_ok:
            self._face_thread = FaceEmotionThread(smooth_window=5)
            self._face_thread.start()
        else:
            self._face_thread = None

        # Voice (hanya jika di-enable)
        if self.enable_voice:
            model_voice = os.path.join(self.base_dir, "models", "vosk-model-small-id")
            self._voice = VoiceCommandThread(
                model_name=self.voice_model,
                vosk_model_path=model_voice,
                on_command=self._on_voice_command,
            )
            self._voice.start()
            self._status_bar.voice.set_listening(self._voice.is_available)
        else:
            self._voice = None
            print(">>> Voice disabled via ENABLE_VOICE=false")

        # Greeter
        self._greeter = VoiceGreeter() if self.enable_voice else None

        # YOLO
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        use_bantal = os.getenv("MODEL_BANTAL","false").lower() == "true"
        model_yolo = None

        if use_bantal:
            p = os.path.join(self.base_dir,"models","weights","bantal.pt")
            try:
                from ultralytics import YOLO
                model_yolo = YOLO(p); model_yolo.to(device)
            except Exception: use_bantal = False

        if not use_bantal:
            p = os.path.join(self.base_dir,"models","weights","best.pt")
            try:
                model_yolo = torch.hub.load(
                    os.path.join(self.base_dir,"models","yolov5"),
                    "custom", path=p, force_reload=True, source="local",
                ); model_yolo.to(device)
            except Exception as e:
                print(f"[YOLO] Gagal load: {e}")

        if model_yolo:
            self._yolo = YOLODetectionThread(model_yolo, use_bantal, confidence=0.7)
            self._yolo.start()
        else:
            self._yolo = None

    def _preload_images(self):
        base = os.path.join(self.base_dir,"assets","images","FILES","TEST_RANDOM_1500x1500")
        for lvl in range(1,9):
            for var in "abcd":
                key  = f"{lvl}{var}"
                path = os.path.join(base, f"Lvl {key}.png")
                if os.path.exists(path):
                    img = Image.open(path).resize(
                        (self.frame_w, self.frame_h), Image.Resampling.LANCZOS
                    )
                    self._cached_images[key] = img


    def _greet_player(self):
        name = self.user_data.get("name", "Adik")
        if self._greeter:
            self._greeter.greet(name)


    def _tick(self):
        if self._timer_running:
            self._timer.set_time(time.time() - self._start_time)
            self.after(50, self._tick)

    def _start_timer(self):
        if not self._timer_running:
            self._start_time = time.time()
            self._timer_running = True
            self._tick()

    def _stop_timer(self):
        self._timer_running = False

    def _reset_timer(self):
        self._timer_running = False
        self._timer.reset()

    def _on_start(self):
        self._start_btn.grid_remove()
        if self._face_thread:
            self._face_thread.reset_session()
        self._hand_tracker.reset_session()
        self._show_level_btn()
        play_audio(os.path.join(self.base_dir,"assets","audio","hitung_mundur.wav"))

        if self.server_client:
            self.session_id = self.server_client.start_session(
                child_id=self.user_data.get("server_id",""),
                level=self._current_q, variant="1a",
            )
        self._next_level()
        self._stream()

    def _show_level_btn(self):
        if self._level_btn:
            self._level_btn.grid_remove()
        self._level_btn = customtkinter.CTkButton(
            self._left, text=f"Level {self._current_q}",
            font=("Helvetica",12,"bold"), height=34,
            corner_radius=6, fg_color="#1e1e1e",
            hover_color="#2a2a2a", border_width=1,
            border_color="#333", text_color=MUTED, state="disabled",
        )
        self._level_btn.grid(row=3, column=0, columnspan=2, padx=12, pady=(0,6), sticky="ew")

    def _next_level(self):
        variant = f"{self._current_q}{random.choice('abcd')}"
        self._current_variant = variant
        self._evaluator.set_variant(variant)
        self._level_badge.set_level(self._current_q)
        if self._level_btn:
            self._level_btn.configure(text=f"Level {self._current_q}")
        self._load_image(variant)
        self._hand_tracker.reset_session()
        self._start_task = time.time()
        self._reset_timer()
        self._start_timer()
        self._status_bar.set_attempts(0)

    def _load_image(self, variant: str):
        img = self._cached_images.get(variant)
        if not img: return
        self._img = customtkinter.CTkImage(light_image=img, size=(self.frame_w, self.frame_h))
        self._img_label.configure(image=self._img)
        if self.button_mode:
            self._image_visible = True
            self._image_show_ts = time.time()

    def _handle_button_mode(self):
        if not self.button_mode: return
        if self._image_visible and time.time()-self._image_show_ts >= self._image_duration:
            blank = Image.new("RGB",(self.frame_w,self.frame_h),"#111")
            self._img = customtkinter.CTkImage(light_image=blank, size=(self.frame_w,self.frame_h))
            self._img_label.configure(image=self._img)
            self._image_visible = False
        if self.serial_thread:
            msg = self.serial_thread.get_message()
            if msg == "disable_image" and not self._image_visible:
                self._load_image(self._current_variant)

    def _complete_level(self, elapsed: float):
        if not self._task_flags.get(self._current_q, False): return
        self._task_flags[self._current_q] = False
        self._timer_all.append(round(elapsed,2))
        self._cog_ages.append(estimate_cognitive_age(elapsed))
        play_feedback_audio(elapsed)
        if self._greeter:
            self._greeter.say_feedback(elapsed)
        self._status_bar.set_attempts(self._evaluator.attempt_count)

        if self._current_q >= self.max_level:
            self._end_game(); return

        nxt = self._current_q + 1
        audio = os.path.join(self.base_dir,"assets","audio",f"lanjut_lvl{nxt}.wav")
        if os.path.exists(audio): play_audio(audio)
        if self._greeter:
            self._greeter.say_level(nxt)
        self._current_q = nxt
        self._task_flags[self._current_q] = True
        self._next_level()

    def _on_skip(self):
        if self._timer_running:
            self._complete_level(time.time() - self._start_task)

    def _end_game(self):
        self._stop_timer()
        if self._level_btn: self._level_btn.grid_remove()

        avg  = sum(self._timer_all)/len(self._timer_all) if self._timer_all else 0
        age  = self.user_data.get("age", 0)
        cog  = int(sum(self._cog_ages)/len(self._cog_ages)) if self._cog_ages else age
        fit  = 100 if cog <= age else max(0,100-(cog-age))
        emo  = self._face_thread.get_session_summary() if self._face_thread else None
        hand = self._hand_tracker.flush_buffer()

        print(f"=== HASIL === Avg: {avg:.2f}s | CogAge: {cog} | Fitness: {fit}%")
        if emo: print(f"Emosi dominan: {emo.get('dominant')}")

        play_audio(os.path.join(self.base_dir,"assets","audio","selesai.wav"))
        if self._greeter:
            self._greeter.say_finish()

        if self.server_client and self.session_id:
            self.server_client.end_session(SessionResult(
                session_id=self.session_id,
                child_id=self.user_data.get("server_id",""),
                robot_id=self.server_client.robot_id,
                waktu_solve=avg, skor=fit,
                jumlah_percobaan=self._evaluator.attempt_count,
                status="completed", hand_logs=hand,
            ))

        end_img = os.path.join(self.base_dir,"assets","images","FILES","TEST_1000x1000","09.jpg")
        if os.path.exists(end_img):
            img = Image.open(end_img).resize((self.frame_w,self.frame_h), Image.Resampling.LANCZOS)
            self._img = customtkinter.CTkImage(light_image=img, size=(self.frame_w,self.frame_h))
            self._img_label.configure(image=self._img)

        customtkinter.CTkButton(
            self._left, text="↺  MAIN LAGI",
            font=("Helvetica",13,"bold"), height=44,
            corner_radius=8, fg_color="#1a3a1a",
            hover_color="#22c55e", text_color="#22c55e",
            command=self.destroy,
        ).grid(row=3, column=0, columnspan=2, padx=12, pady=(0,12), sticky="ew")

    def _on_voice_command(self, event):
        self.after(0, lambda: self._dispatch_voice(event.command))

    def _dispatch_voice(self, cmd: str):
        self._status_bar.voice.show_command(cmd)
        if cmd == "start" and self._start_btn.winfo_ismapped():
            self._on_start()
        elif cmd == "skip":
            self._on_skip()
        elif cmd == "retry":
            self.destroy()

    def _stream(self):
        self._handle_button_mode()

        if self._cap_game.isOpened():
            ret, frame = self._cap_game.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                if self._frame_count % (self.mp_skip+1) == 0:
                    frame_rgb, _ = self._hand_tracker.process_and_draw(frame_rgb)

                if self._yolo:
                    if self._frame_count % (self.yolo_skip+1) == 0:
                        self._yolo.submit_frame(frame)
                    result = self._yolo.get_result()
                    if result:
                        self._latest_boxes = result.boxes

                    for box in self._latest_boxes:
                        x1,y1,x2,y2 = int(box[0]),int(box[1]),int(box[2]),int(box[3])
                        cv2.rectangle(frame_rgb,(x1,y1),(x2,y2),(255,80,80),2)

                    if len(self._latest_boxes) == 4:
                        boxes = self._latest_boxes
                        is_ok, _ = self._evaluator.check(
                            pos_x=[(b[0]+b[2])/2 for b in boxes],
                            pos_y=[(b[1]+b[3])/2 for b in boxes],
                            designs=[],
                        )
                        if is_ok:
                            self._complete_level(time.time()-self._start_task)

                if self._cam_panel:
                    self._cam_panel.update_game_frame(Image.fromarray(frame_rgb))

        if self._face_cam_ok and self._cap_face and self._cap_face.isOpened():
            ret_f, frame_f = self._cap_face.read()
            if ret_f:
                frame_f_rgb = cv2.cvtColor(frame_f, cv2.COLOR_BGR2RGB)

                if self._face_thread and self._frame_count % 15 == 0:
                    self._face_thread.submit_frame(frame_f_rgb.copy())

                if self._face_thread:
                    emo = self._face_thread.get_emotion()
                    if emo:
                        self._cur_emotion = emo
                        self._status_bar.emotion.set_emotion(emo)

                if self._face_mesh:
                    frame_f_rgb = self._face_mesh.draw(frame_f_rgb, self._cur_emotion)

                if self._cam_panel:
                    self._cam_panel.update_face_frame(Image.fromarray(frame_f_rgb))

        self._frame_count += 1
        self._fps_counter += 1
        if time.time() - self._fps_ts >= 1.0:
            self._status_bar.set_fps(self._fps_counter)
            self._fps_counter = 0
            self._fps_ts = time.time()
            if self.server_client:
                self._status_bar.set_server_online(self.server_client.is_online)

        self.after(10, self._stream)

    def cleanup(self):
        for cap in (self._cap_game, self._cap_face):
            if cap and cap.isOpened(): cap.release()
        if getattr(self, "_yolo", None):    self._yolo.stop()
        if getattr(self, "_face_thread", None): self._face_thread.stop()
        if getattr(self, "_voice", None):   self._voice.stop()
        if getattr(self, "_hand_tracker", None): self._hand_tracker.close()
        if getattr(self, "_face_mesh", None): self._face_mesh.close()
        if self.serial_thread: self.serial_thread.stop()
        if torch.cuda.is_available(): torch.cuda.empty_cache()

    def destroy(self):
        self.cleanup()
        super().destroy()