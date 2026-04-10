"""
hands.py — MediaPipe hand tracking + rich skeleton visualization + data extraction

Changes:
- Skeleton dengan warna berbeda per jari (thumb=oranye, index=hijau, dst)
- Titik landmark lebih besar, ujung jari diberi label T/I/M/R/P
- draw_style: "rich" (default) atau "simple" (default MediaPipe)
- Data extraction untuk riset tetap ada
"""

import time
import math
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    import mediapipe as mp
    _mp_solutions = getattr(mp, "solutions", None)
    if _mp_solutions is None:
        from mediapipe.python import solutions as _mp_solutions
except ImportError:
    mp = None
    _mp_solutions = None


FINGER_COLORS = {
    "thumb":  (0,   165, 255),
    "index":  (0,   255, 0),
    "middle": (255, 255, 0),
    "ring":   (255, 0,   200),
    "pinky":  (80,  80,  255),
    "palm":   (180, 180, 180),
}

FINGER_LANDMARKS = {
    "thumb":  [1, 2, 3, 4],
    "index":  [5, 6, 7, 8],
    "middle": [9, 10, 11, 12],
    "ring":   [13, 14, 15, 16],
    "pinky":  [17, 18, 19, 20],
}

PALM_CONNECTIONS = [
    (0,1),(0,5),(0,9),(0,13),(0,17),
    (5,9),(9,13),(13,17),
]

TIP_LABELS = {4:"T", 8:"I", 12:"M", 16:"R", 20:"P"}


@dataclass
class HandMovementSample:
    timestamp_ms: int
    koordinat_x:  float
    koordinat_y:  float
    kecepatan:    float


class HandTracker:
    def __init__(
        self,
        max_num_hands: int = 2,
        draw_style: str = "rich",
        session_start: Optional[float] = None,
    ):
        self.available   = _mp_solutions is not None
        self.draw_style  = draw_style
        self._session_start = session_start or time.time()
        self._movement_buffer: List[HandMovementSample] = []
        self._last_pos: Optional[Tuple[float,float]] = None
        self._last_ts:  Optional[float] = None

        if not self.available:
            print(">>> MediaPipe tidak tersedia.")
            self._hands = None
            return

        self._mp_hands = _mp_solutions.hands
        self._drawing  = _mp_solutions.drawing_utils
        self._hands    = self._mp_hands.Hands(
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
            max_num_hands=max_num_hands,
        )
        self._lm_style   = self._drawing.DrawingSpec(color=(0,255,0), thickness=3, circle_radius=4)
        self._conn_style = self._drawing.DrawingSpec(color=(0,200,0), thickness=2)

    def _px(self, lmk, w, h):
        return int(lmk.x * w), int(lmk.y * h)

    def _draw_rich(self, frame, hand_landmarks):
        if cv2 is None:
            return
        h, w = frame.shape[:2]
        lm = hand_landmarks.landmark

        # Telapak
        for a, b in PALM_CONNECTIONS:
            cv2.line(frame, self._px(lm[a],w,h), self._px(lm[b],w,h),
                    FINGER_COLORS["palm"], 2, cv2.LINE_AA)

        # Jari
        for finger, indices in FINGER_LANDMARKS.items():
            color = FINGER_COLORS[finger]
            cv2.line(frame, self._px(lm[0],w,h), self._px(lm[indices[0]],w,h),
                    color, 2, cv2.LINE_AA)
            for i in range(len(indices)-1):
                cv2.line(frame,
                        self._px(lm[indices[i]],  w,h),
                        self._px(lm[indices[i+1]],w,h),
                        color, 2, cv2.LINE_AA)

        for i, lmk in enumerate(lm):
            px = self._px(lmk, w, h)
            r  = 7 if i in TIP_LABELS else 4
            cv2.circle(frame, px, r+2, (255,255,255), -1, cv2.LINE_AA)
            cv2.circle(frame, px, r,   (0, 180, 0),   -1, cv2.LINE_AA)

        for tip_idx, lbl in TIP_LABELS.items():
            px = self._px(lm[tip_idx], w, h)
            cv2.putText(frame, lbl, (px[0]+6, px[1]-6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (255,255,255), 1, cv2.LINE_AA)

    def process_and_draw(self, frame):
        if not self.available or self._hands is None:
            return frame, []

        results = self._hands.process(frame)
        samples: List[HandMovementSample] = []

        if not results.multi_hand_landmarks:
            self._last_pos = None
            self._last_ts  = None
            return frame, []

        now   = time.time()
        ts_ms = int((now - self._session_start) * 1000)

        for hand_landmarks in results.multi_hand_landmarks:
            if self.draw_style == "rich":
                self._draw_rich(frame, hand_landmarks)
            else:
                self._drawing.draw_landmarks(
                    frame, hand_landmarks,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._lm_style, self._conn_style,
                )

            wrist = hand_landmarks.landmark[0]
            cx, cy = wrist.x, wrist.y
            kecepatan = 0.0
            if self._last_pos is not None and self._last_ts is not None:
                dt_ms = (now - self._last_ts) * 1000
                if dt_ms > 0:
                    dx = (cx - self._last_pos[0]) * 1000
                    dy = (cy - self._last_pos[1]) * 1000
                    kecepatan = round(math.sqrt(dx*dx+dy*dy)/dt_ms, 4)

            self._last_pos = (cx, cy)
            self._last_ts  = now
            s = HandMovementSample(ts_ms, round(cx,4), round(cy,4), kecepatan)
            samples.append(s)
            self._movement_buffer.append(s)

        return frame, samples

    def reset_session(self, session_start: Optional[float] = None):
        self._session_start = session_start or time.time()
        self._movement_buffer.clear()
        self._last_pos = None
        self._last_ts  = None

    def flush_buffer(self):
        data = [asdict(s) for s in self._movement_buffer]
        self._movement_buffer.clear()
        return data

    def close(self):
        if self._hands is not None:
            self._hands.close()