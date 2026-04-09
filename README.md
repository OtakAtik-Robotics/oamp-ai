# OAMP AI Robot 🤖

> Core AI logic (Computer Vision & NLP) and User Interface for the autonomous BDT robot table.
> Maintained by the Software & AI Division of OtakAtik-Robotics.

This repository contains the intelligent systems that power the robot table. It evaluates a participant's cognitive abilities in real-time by analyzing their block arrangements, hand dexterity, and facial expressions during gameplay.

## 🧠 AI Capabilities
* **Block Detection:** YOLOv5 (Custom trained model)
* **Hand Dexterity Tracking:** Google MediaPipe Hands
* **Facial Expression Recognition:** DeepFace / FER
* **Speech-to-Text (Offline):** Vosk API

## 📂 Project Structure
* `assets/` - Media files (Audio prompts, Level images)
* `models/` - AI weights (`best.pt`, `bantal.pt`)
* `src/vision/` - Computer vision modules (Blocks, Hands, Face)
* `src/voice/` - Audio processing and Speech Recognition
* `src/ui/` - CustomTkinter graphical interfaces
* `src/hardware/` - Serial communication with Sensors/Actuators
* `src/api_client.py` - HTTP client to communicate with `oamp-backend`
* `main.py` - Central application loop

## 🚀 Getting Started

### Prerequisites
* Python 3.9+
* A webcam (for detection)
* Microphone (for voice commands)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/OtakAtik-Robotics/oamp-ai.git
   cd oamp-ai
    ```
2. Create and activate a virtual environment (Recommended):
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Linux/MacOS
    python3 -m venv venv
    source venv/bin/activate
    ```
3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Create a .env file in the root directory:
    ```bash
    BACKEND_API_URL=http://localhost:8080/api/v1
    MODEL_BANTAL=false
    HIDE_CAMERA=false
    DEBUG_MODE=true
    ```
5. Running the System:
    ```bash
    python main.py
    ```