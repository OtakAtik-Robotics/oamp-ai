import time
import threading
from queue import Queue, Empty
import numpy as np

class DetectionResult:
    __slots__ = ("boxes", "timestamp")

    def __init__(self, boxes, timestamp):
        self.boxes = boxes
        self.timestamp = timestamp

    def __len__(self):
        return len(self.boxes)

class YOLODetectionThread(threading.Thread):
    def __init__(self, model, use_bantal_model, confidence=0.7, skip_frames=2, on_error=None):
        super().__init__(daemon=True, name="YOLODetection")
        self.model = model
        self.use_bantal_model = use_bantal_model
        self.confidence = confidence
        self.skip_frames = skip_frames
        self.on_error = on_error

        self.frame_queue = Queue(maxsize=1)
        self.result_queue = Queue(maxsize=1)
        self.running = True

        self.inference_count = 0
        self.last_inference_ms = 0.0
        self._inference_times = []
        self._max_history = 30

    def _infer(self, frame):
        if self.use_bantal_model:
            results = self.model(frame, verbose=False)
            if not results or not hasattr(results[0], "boxes"):
                return []
            detections = []
            for box in results[0].boxes:
                conf = float(box.conf[0].cpu().numpy())
                if conf < self.confidence:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cls_id = int(box.cls[0].cpu().numpy())
                detections.append([x1, y1, x2, y2, conf, cls_id, ""])
            return detections
        else:
            results = self.model(frame)
            df = results.pandas().xyxy[0]
            return [
                row.tolist()
                for _, row in df.iterrows()
                if row["confidence"] >= self.confidence
            ]

    def _update_metrics(self, elapsed_ms):
        self.last_inference_ms = elapsed_ms
        self._inference_times.append(elapsed_ms)
        if len(self._inference_times) > self._max_history:
            self._inference_times.pop(0)
        self.inference_count += 1

    @property
    def avg_inference_ms(self):
        if not self._inference_times:
            return 0.0
        return sum(self._inference_times) / len(self._inference_times)

    def submit_frame(self, frame):
        if self.frame_queue.full():
            return False
        try:
            self.frame_queue.put_nowait(np.array(frame, copy=True))
            return True
        except Exception:
            return False

    def get_result(self):
        try:
            return self.result_queue.get_nowait()
        except Empty:
            return None

    def run(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=0.05)
            except Empty:
                continue

            try:
                t0 = time.perf_counter()
                boxes = self._infer(frame)
                elapsed = (time.perf_counter() - t0) * 1000
                self._update_metrics(elapsed)

                result = DetectionResult(boxes=boxes, timestamp=time.time())

                if self.result_queue.full():
                    try:
                        self.result_queue.get_nowait()
                    except Empty:
                        pass
                self.result_queue.put(result)

            except Exception as e:
                if self.on_error:
                    self.on_error(e)
                time.sleep(0.01)

    def stop(self):
        self.running = False