
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
    _mp_solutions = getattr(mp, "solutions", None)
    if _mp_solutions is None:
        from mediapipe.python import solutions as _mp_solutions
except ImportError:
    _mp_solutions = None


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
        self.available = _mp_solutions is not None and _HAS_CV2
        self._draw_tess    = draw_tesselation
        self._draw_cont    = draw_contours
        self._draw_iris    = draw_iris

        if not self.available:
            print(">>> MediaPipe tidak tersedia. Face mesh disabled.")
            self._face_mesh = None
            return

        self._mp_face_mesh = _mp_solutions.face_mesh
        self._drawing      = _mp_solutions.drawing_utils
        self._drawing_styles = _mp_solutions.drawing_styles

        self._face_mesh = self._mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,   
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self._tess_style = self._drawing.DrawingSpec(
            color=(40, 40, 40), thickness=1, circle_radius=1,
        )
        self._contour_style = self._drawing.DrawingSpec(
            color=(0, 220, 80), thickness=1, circle_radius=1,
        )
        self._iris_style = self._drawing.DrawingSpec(
            color=(0, 180, 255), thickness=1, circle_radius=1,
        )

    def draw(self, frame, emotion_label: str = "") -> "frame":
        if not self.available or self._face_mesh is None:
            return frame

        results = self._face_mesh.process(frame)
        if not results.multi_face_landmarks:
            return frame

        for face_landmarks in results.multi_face_landmarks:
            if self._draw_tess:
                self._drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=self._mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self._tess_style,
                )

            if self._draw_cont:
                self._drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=self._mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self._contour_style,
                )

            if self._draw_iris and hasattr(self._mp_face_mesh, "FACEMESH_IRISES"):
                self._drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=self._mp_face_mesh.FACEMESH_IRISES,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self._iris_style,
                )

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
        if self._face_mesh is not None:
            self._face_mesh.close()

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