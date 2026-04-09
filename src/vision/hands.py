import cv2

try:
    import mediapipe as mp
    mp_solutions = getattr(mp, "solutions", None)
    if mp_solutions is None:
        from mediapipe.python import solutions as mp_solutions
except ImportError:
    mp = None
    mp_solutions = None

class HandTracker:
    def __init__(self, max_num_hands=2):
        if mp_solutions is None:
            self.hands = None
            return
            
        self.mp_hands = mp_solutions.hands
        self.mp_drawing = mp_solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            max_num_hands=max_num_hands
        )
        self.landmark_style = self.mp_drawing.DrawingSpec(color=(0,0,255), thickness=3, circle_radius=3)
        self.connection_style = self.mp_drawing.DrawingSpec(color=(0,0,255), thickness=4)

    def process_and_draw(self, frame):
        if self.hands is None:
            return frame, []
            
        results = self.hands.process(frame)
        landmarks_data = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS, 
                    self.landmark_style, 
                    self.connection_style
                )
                landmarks_data.append(hand_landmarks)
                
        return frame, landmarks_data

    def close(self):
        if self.hands is not None:
            self.hands.close()