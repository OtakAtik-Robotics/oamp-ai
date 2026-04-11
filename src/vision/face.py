
import os
import time
import threading
from collections import Counter, deque
from queue import Queue, Empty
from typing import Optional, Tuple

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

try:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import (
        FaceLandmarker,
        FaceLandmarkerOptions,
        FaceLandmarksConnections,
        RunningMode,
        drawing_utils as _mp_drawing_utils,
        drawing_styles as _mp_drawing_styles,
    )
    _HAS_MP = True
except Exception as e:
    print(f">>> [DEBUG] Gagal load MediaPipe: {e}")
    _HAS_MP = False


# ── Model path ──────────────────────────────────────────────────────
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models", "weights")
_FACE_MODEL = os.path.normpath(os.path.join(_MODEL_DIR, "face_landmarker.task"))


EMOTION_DISPLAY = {
    "happy":    ("😊 Senang",   (0, 220, 80)),
    "sad":      ("😢 Sedih",    (200, 80, 0)),
    "angry":    ("😠 Marah",    (0, 60, 220)),
    "fear":     ("😨 Takut",    (180, 0, 220)),
    "surprise": ("😲 Kaget",    (0, 200, 220)),
    "disgust":  ("😒 Jijik",    (80, 120, 80)),
    "neutral":  ("😐 Netral",   (160, 160, 160)),
}

class FaceMeshDrawer:
    def __init__(
        self,
        draw_tesselation: bool = True,
        draw_contours: bool = True,
        draw_iris: bool = True,
    ):
        self._draw_tess    = draw_tesselation
        self._draw_cont    = draw_contours
        self._draw_iris    = draw_iris

        if not _HAS_MP or not _HAS_CV2 or not os.path.isfile(_FACE_MODEL):
            print(f">>> MediaPipe tidak tersedia atau model tidak ditemukan: {_FACE_MODEL}")
            self.available = False
            self._landmarker = None
            return

        try:
            options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=_FACE_MODEL),
                running_mode=RunningMode.IMAGE,
                min_face_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                num_faces=1,
                output_facial_transformation_matrixes=False,
                output_face_blendshapes=False,
            )
            self._landmarker = FaceLandmarker.create_from_options(options)
            self.available = True
        except Exception as e:
            print(f">>> [DEBUG] Gagal inisialisasi FaceLandmarker: {e}")
            self.available = False
            self._landmarker = None

    def draw(self, frame, emotion_label: str = "") -> "frame":
        if not self.available or self._landmarker is None:
            return frame

        if cv2 is None:
            return frame

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = self._landmarker.detect(mp_image)

        if not results.face_landmarks:
            return frame

        for face_landmarks in results.face_landmarks:
            h_img, w_img = frame.shape[:2]

            if self._draw_tess:
                tess_style = _mp_drawing_styles.get_default_face_mesh_tesselation_style()
                for conn in FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION:
                    start_lm = face_landmarks[conn.start]
                    end_lm   = face_landmarks[conn.end]
                    cv2.line(frame,
                             (int(start_lm.x * w_img), int(start_lm.y * h_img)),
                             (int(end_lm.x * w_img), int(end_lm.y * h_img)),
                             tess_style.color, tess_style.thickness, cv2.LINE_AA)

            if self._draw_cont:
                contour_styles = _mp_drawing_styles.get_default_face_mesh_contours_style()
                for conn in FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS:
                    start_lm = face_landmarks[conn.start]
                    end_lm   = face_landmarks[conn.end]
                    style = contour_styles.get((conn.start, conn.end),
                              contour_styles.get((conn.end, conn.start)))
                    if style:
                        cv2.line(frame,
                                 (int(start_lm.x * w_img), int(start_lm.y * h_img)),
                                 (int(end_lm.x * w_img), int(end_lm.y * h_img)),
                                 style.color, style.thickness, cv2.LINE_AA)

            if self._draw_iris:
                iris_styles = _mp_drawing_styles.get_default_face_mesh_iris_connections_style()
                iris_conns = (
                    FaceLandmarksConnections.FACE_LANDMARKS_LEFT_IRIS
                    + FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_IRIS
                )
                for conn in iris_conns:
                    start_lm = face_landmarks[conn.start]
                    end_lm   = face_landmarks[conn.end]
                    style = iris_styles.get((conn.start, conn.end),
                             iris_styles.get((conn.end, conn.start)))
                    if style:
                        cv2.line(frame,
                                 (int(start_lm.x * w_img), int(start_lm.y * h_img)),
                                 (int(end_lm.x * w_img), int(end_lm.y * h_img)),
                                 style.color, style.thickness, cv2.LINE_AA)

        if emotion_label:
            label_text, color_bgr = EMOTION_DISPLAY.get(
                emotion_label, (emotion_label, (200, 200, 200))
            )
            overlay = frame.copy()
            cv2.rectangle(overlay, (8, 8), (200, 44), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
            cv2.putText(
                frame, label_text.split()[1] if " " in label_text else label_text,
                (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                color_bgr, 2, cv2.LINE_AA,
            )

        return frame

    def close(self):
        if self._landmarker is not None:
            self._landmarker.close()

class FaceEmotionThread(threading.Thread):
    """
    Background thread deteksi emosi via DeepFace.
    Berjalan terpisah agar tidak block main loop.
    """

    def __init__(self, smooth_window: int = 5):
        super().__init__(daemon=True, name="FaceEmotion")
        self.frame_queue:  Queue = Queue(maxsize=1)
        self.result_queue: Queue = Queue(maxsize=1)
        self.running = True
        self._smooth_window  = smooth_window
        self._emotion_window = deque(maxlen=smooth_window)
        self._session_history: list = []
        self._session_start  = time.time()
        self.current_emotion = "neutral"
        self.stable_emotion  = "neutral"

        try:
            from deepface import DeepFace
            self._DeepFace = DeepFace
            self.is_available = True
            print(">>> DeepFace loaded.")
        except ImportError:
            self._DeepFace = None
            self.is_available = False
            print(">>> DeepFace tidak terinstall: pip install deepface")

    def _smooth(self, raw: str) -> str:
        self._emotion_window.append(raw)
        from collections import Counter
        return Counter(self._emotion_window).most_common(1)[0][0]

    def run(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
            except Empty:
                continue
            if not self.is_available:
                continue
            try:
                result = self._DeepFace.analyze(
                    frame, actions=["emotion"],
                    enforce_detection=False, silent=True,
                )
                if isinstance(result, list):
                    result = result[0]
                raw = result.get("dominant_emotion", "neutral")
                smoothed = self._smooth(raw)
                self.current_emotion = raw
                self.stable_emotion  = smoothed
                ts_ms = int((time.time() - self._session_start) * 1000)
                self._session_history.append((ts_ms, smoothed))
                if self.result_queue.full():
                    try: self.result_queue.get_nowait()
                    except Empty: pass
                self.result_queue.put(smoothed)
            except Exception:
                time.sleep(0.05)

    def submit_frame(self, frame) -> bool:
        if not self.is_available or self.frame_queue.full():
            return False
        try:
            self.frame_queue.put_nowait(frame)
            return True
        except Exception:
            return False

    def get_emotion(self) -> Optional[str]:
        try:
            return self.result_queue.get_nowait()
        except Empty:
            return None

    def get_display_label(self) -> str:
        label, _ = EMOTION_DISPLAY.get(self.stable_emotion, (self.stable_emotion, None))
        return label

    def reset_session(self, session_start: Optional[float] = None):
        self._session_start = session_start or time.time()
        self._session_history.clear()
        self._emotion_window.clear()
        self.current_emotion = "neutral"
        self.stable_emotion  = "neutral"

    def get_session_summary(self) -> dict:
        if not self._session_history:
            return {"dominant": "neutral", "distribution": {}}
        from collections import Counter
        emotions = [e for _, e in self._session_history]
        counter  = Counter(emotions)
        total    = len(emotions)
        return {
            "dominant": counter.most_common(1)[0][0],
            "distribution": {k: round(v/total*100,1) for k,v in counter.items()},
            "total_samples": total,
        }

    def stop(self):
        self.running = False
