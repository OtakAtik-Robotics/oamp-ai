# OAMP AI Robot

> Core AI logic (Computer Vision & NLP) and User Interface for the autonomous BDT robot table.
> Maintained by the Software & AI Division of OtakAtik-Robotics.

This repository contains the intelligent systems that power the robot table. It evaluates a participant's cognitive abilities in real-time by analyzing their block arrangements, hand dexterity, facial expressions, and voice commands during gameplay.

## AI Capabilities

| Capability | Technology | Description |
|-----------|-----------|-------------|
| Block Detection | YOLOv5 (Custom trained) | Detects and locates blocks in the game area |
| Hand Tracking | MediaPipe Tasks API | Tracks hand landmarks, measures movement speed |
| Face Mesh | MediaPipe Tasks API | Draws face overlay (tesselation, contours, iris) |
| Emotion Recognition | DeepFace | Detects 7 emotions: happy, sad, angry, fear, surprise, disgust, neutral |
| Speech-to-Text | Wav2Vec2 (HuggingFace) | Indonesian voice command recognition (primary) |
| Speech-to-Text | Vosk (Offline) | Fallback voice recognition when Wav2Vec2 unavailable |
| Text-to-Speech | gTTS | Indonesian voice feedback and greetings |

## Project Structure

```
├── main.py                  # Entry point
├── src/
│   ├── ui/game_window.py    # Main UI orchestrator (CustomTkinter)
│   ├── vision/
│   │   ├── blocks.py        # YOLO block detection thread
│   │   ├── hands.py         # Hand tracking (MediaPipe)
│   │   ├── face.py          # Face mesh + emotion detection
│   │   └── evaluator.py     # Level answer validation
│   ├── voice/recog.py       # Voice recognition (Wav2Vec2 + Vosk + gTTS)
│   ├── hardware/serial_io.py # ESP32 serial communication
│   └── api_client.py        # Backend HTTP client + offline buffer
├── models/
│   ├── weights/             # Model files (.pt, .task)
│   ├── vosk-model-small-id/ # Vosk offline model
│   └── yolov5/              # YOLOv5 framework
└── assets/
    ├── audio/               # Audio prompts and feedback
    └── images/FILES/        # Level design images
```

## Getting Started

### Prerequisites

- Python 3.9+
- Webcam (game area + face camera)
- Microphone (for voice commands)
- ESP32 connected via USB/Bluetooth (optional)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/OtakAtik-Robotics/oamp-ai.git
   cd oamp-ai
   ```

2. Create and activate a virtual environment:
   ```bash
   # Linux/MacOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Download MediaPipe model files (first run only):
   ```bash
   # Hand tracker model (~8 MB)
   curl -L -o models/weights/hand_landmarker.task \
     https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

   # Face landmarker model (~4 MB)
   curl -L -o models/weights/face_landmarker.task \
     https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
   ```

5. Create `.env` file in the root directory:
   ```bash
   cp .env.example .env
   ```

6. Run the system:
   ```bash
   python main.py
   ```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_API_URL` | `http://localhost:8080/api/v1` | Backend server URL |
| `CAMERA_GAME_INDEX` | `0` | Game camera device index |
| `CAMERA_FACE_INDEX` | `1` | Face camera device index |
| `DISPLAY_HALF` | `true` | Compact UI mode (1200x620 vs 1400x820) |
| `MAX_LEVEL` | `8` | Maximum level (1-8) |
| `MODEL_BANTAL` | `false` | Use alternative YOLO model |
| `HIDE_CAMERA` | `false` | Hide camera panel |
| `YOLO_SKIP_FRAMES` | `2` | YOLO frame skip (higher = faster UI, slower detection) |
| `MEDIAPIPE_SKIP_FRAMES` | `2` | MediaPipe frame skip |
| `BUTTON_MODE` | `false` | Hardware button-triggered image display |
| `DEBUG_MODE` | `false` | Debug mode |

## Hardware Integration

- **ESP32**: Serial communication at 115200 baud. Auto-detects USB and Bluetooth RFCOMM ports.
- **Dual Camera**: One camera for the game area (blocks + hands), one for face detection.

## Backend API

The system communicates with a Go backend server via REST API. When offline, session data is buffered to local SQLite and synced automatically every 15 seconds. Full API documentation is available in `api-spec.md`.

## Voice Commands

| Indonesian | English | Action |
|-----------|---------|--------|
| mulai, ayo, halo | start | Start the game |
| skip, lewat, lanjut | skip, next | Skip current level |
| ulangi, lagi | retry | Retry current level |
| selesai, berhenti | stop | Stop the game |
