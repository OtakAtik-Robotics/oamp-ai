# API Specification — OtakAtik-Robotics

Dokumentasi semua API, service eksternal, dan model yang dibutuhkan sistem.

---

## Daftar Isi

1. [Backend API (Go Server)](#1-backend-api-go-server)
2. [YOLO — Deteksi Blok](#2-yolo--deteksi-blok)
3. [MediaPipe — Hand & Face Tracking](#3-mediapipe--hand--face-tracking)
4. [DeepFace — Emosi Wajah](#4-deepface--emosi-wajah)
5. [Wav2Vec2 — Speech Recognition](#5-wav2vec2--speech-recognition)
6. [Vosk — Speech Recognition (Fallback)](#6-vosk--speech-recognition-fallback)
7. [Google TTS — Text-to-Speech](#7-google-tts--text-to-speech)
8. [ESP32 — Serial Communication](#8-esp32--serial-communication)
9. [Environment Variables](#9-environment-variables)

---

## 1. Backend API (Go Server)

HTTP REST API ke server backend Go untuk manajemen sesi dan data anak.

| Properti | Nilai |
|----------|-------|
| Base URL | `BACKEND_API_URL` (via `.env`) |
| Timeout | 3 detik |
| Format | JSON |
| Library | `requests` |
| Fallback | SQLite (`local_buffer.db`) saat offline |

### `GET /child/rfid/{rfid_tag}`

Mencari data anak berdasarkan RFID tag.

**Response:**
```json
{
  "success": true,
  "data": {
    "child_id": "uuid",
    "name": "Budi",
    "age": 10,
    "gender": "male"
  }
}
```

### `GET /child/qr/{qr_code}`

Mencari data anak berdasarkan QR code.

**Response:** Sama seperti RFID.

### `GET /child/nomor/{nomor}`

Mencari data anak berdasarkan nomor peserta.

**Response:** Sama seperti RFID.

### `POST /session/start`

Memulai sesi baru.

**Request:**
```json
{
  "child_id": "uuid",
  "robot_id": "uuid",
  "level": 1,
  "variant": "a"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "session_id": "uuid"
  }
}
```

**Fallback:** Jika offline, generate `session_id` lokal via `uuid.uuid4()`.

### `POST /session/end`

Mengakhiri sesi dan mengirim hasil.

**Request:**
```json
{
  "session_id": "uuid",
  "waktu_solve": 15.3,
  "skor": 100,
  "jumlah_percobaan": 2,
  "status": "completed"
}
```

`status` bisa: `"completed"` atau `"skipped"`.

**Response:**
```json
{
  "success": true
}
```

**Fallback:** Jika offline, buffer ke SQLite.

### `POST /session/hand-logs`

Mengirim log pergerakan tangan dalam satu sesi.

**Request:**
```json
{
  "session_id": "uuid",
  "logs": [
    {
      "timestamp_ms": 1500,
      "koordinat_x": 0.4523,
      "koordinat_y": 0.6712,
      "kecepatan": 0.0234
    }
  ]
}
```

### `POST /session/sync-buffer`

Sinkronisasi data sesi yang terbuffer offline.

**Request:** Array of session payloads.
```json
[
  {
    "session_id": "uuid",
    "waktu_solve": 15.3,
    "skor": 100,
    "jumlah_percobaan": 2,
    "status": "completed"
  }
]
```

**Response:**
```json
{
  "success": true,
  "data": {
    "synced": 2
  }
}
```

### `POST /robot/heartbeat`

Mengirim status heartbeat robot secara berkala.

**Request:**
```json
{
  "robot_id": "uuid",
  "status": "idle",
  "baterai_persen": 85
}
```

---

## 2. YOLO — Deteksi Blok

Deteksi blok merah putih di area permainan menggunakan YOLOv5.

| Properti | Nilai |
|----------|-------|
| Framework | Ultralytics YOLOv5 |
| Library | `ultralytics` |
| Model Primary | `models/weights/best.pt` |
| Model Alternatif | `models/weights/bantal.pt` |
| Switch | `MODEL_BANTAL=true` di `.env` |

### Input
- Frame BGR dari kamera game (`CAMERA_GAME_INDEX`)
- Proses setiap `YOLO_SKIP_FRAMES + 1` frame

### Output
- Array of bounding boxes: `[[x1, y1, x2, y2], ...]`
- Jumlah blok: 4 blok = level selesai (dicek oleh `BlockEvaluator`)

---

## 3. MediaPipe — Hand & Face Tracking

Tracking tangan dan wajah menggunakan MediaPipe Tasks API.

| Properti | Nilai |
|----------|-------|
| Library | `mediapipe` >= 0.10.33 |
| API | Tasks API (bukan Solutions API lama) |
| Running Mode | `IMAGE` (synchronous per frame) |

### Hand Tracking

| Properti | Nilai |
|----------|-------|
| Model | `models/weights/hand_landmarker.task` |
| Download | `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task` |
| Max Hands | 2 |
| Detection Confidence | 0.6 |
| Tracking Confidence | 0.5 |

**Input:** Frame RGB via `mp.Image(image_format=SRGB, data=rgb_frame)`

**Output:**
- `results.hand_landmarks` — List of hands, masing-masing berisi 21 landmark (NormalizedLandmark)
- `HandMovementSample` per tangan: `timestamp_ms`, `koordinat_x`, `koordinat_y`, `kecepatan`

### Face Mesh

| Properti | Nilai |
|----------|-------|
| Model | `models/weights/face_landmarker.task` |
| Download | `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task` |
| Max Faces | 1 |
| Detection Confidence | 0.5 |
| Tracking Confidence | 0.5 |

**Input:** Frame RGB via `mp.Image`

**Output:**
- `results.face_landmarks` — List of faces, masing-masing berisi 478 landmark
- Overlay: tesselation, kontur, iris digambar di frame

---

## 4. DeepFace — Emosi Wajah

Deteksi emosi wajah secara real-time.

| Properti | Nilai |
|----------|-------|
| Library | `deepface` |
| Backend | TensorFlow / PyTorch |
| Actions | `["emotion"]` |
| Enforcement | `False` (tidak harus ada wajah) |
| Smoothing | Sliding window 5 sample, majority vote |

### Emosi yang Dideteksi
`happy`, `sad`, `angry`, `fear`, `surprise`, `disgust`, `neutral`

### Output
- `current_emotion` — Emosi mentah terbaru
- `stable_emotion` — Emosi setelah smoothing
- Session summary: distribusi emosi dalam persen + emosi dominan

---

## 5. Wav2Vec2 — Speech Recognition

Pengenalan suara bahasa Indonesia menggunakan model Wav2Vec2 dari HuggingFace.

| Properti | Nilai |
|----------|-------|
| Library | `transformers`, `torch` |
| Model Primary | `indonesian-nlp/wav2vec2-indonesian-javanese-sundanese` |
| Model Alternatif | `indonesian-nlp/wav2vec2-large-xlsr-indonesian` |
| Sample Rate | 16000 Hz |
| Channels | 1 (mono) |
| Chunk Duration | 2 detik |
| Volume Threshold | 0.015 RMS |
| Device | CUDA jika tersedia, fallback CPU |

### Input
- Audio stream real-time via `sounddevice` (16kHz mono float32)

### Commands
| Kata Kunci (ID/EN) | Command |
|---------------------|---------|
| mulai, start, main, ayo, halo | `start` |
| skip, lewat, lanjut, next, ganti | `skip` |
| ulangi, ulang, lagi, retry | `retry` |
| selesai, stop, berhenti | `stop` |
| bantuan, help | `help` |

### Output
- `VoiceEvent(command, raw_text, timestamp)` ke `command_queue`

---

## 6. Vosk — Speech Recognition (Fallback)

Pengenalan suara offline jika Wav2Vec2 gagal dimuat.

| Properti | Nilai |
|----------|-------|
| Library | `vosk` |
| Model | `models/vosk-model-small-id/` |
| Sample Rate | 16000 Hz |
| Block Size | 8000 sample |
| Format | Int16 mono |

### Input
- Audio stream via `sounddevice.RawInputStream`

### Output
- Sama seperti Wav2Vec2 (`VoiceEvent`) melalui `COMMAND_MAP`

---

## 7. Google TTS — Text-to-Speech

Text-to-speech untuk sapaan dan feedback suara.

| Properti | Nilai |
|----------|-------|
| Library | `gtts` |
| Bahasa | Indonesian (`lang="id"`) |
| Playback | `sounddevice` + `soundfile` |
| Mode | Async (thread terpisah) |

### Method

| Method | Deskripsi |
|--------|-----------|
| `greet(name)` | Sapaan random dengan nama anak |
| `say(text)` | Bicara teks bebas |
| `say_feedback(elapsed)` | Feedback berdasar waktu (fast < 12s, ok < 25s, slow >= 25s) |
| `say_level(level)` | Umumkan level baru |
| `say_finish()` | Umumkan permainan selesai |

---

## 8. ESP32 — Serial Communication

Komunikasi serial dengan ESP32 untuk hardware input.

| Properti | Nilai |
|----------|-------|
| Library | `pyserial` |
| Baud Rate | 115200 |
| Protocol | UART text-based (UTF-8, newline terminated) |
| Timeout | 0.1 detik |

### Auto-detection Port

1. Linux Bluetooth: `/dev/rfcomm0`
2. USB Serial: scan port dengan identifier `USB`, `CH340`, `CP210`, `UART`, `Serial`, `Bluetooth`

### Pesan dari ESP32
| Pesan | Aksi |
|-------|------|
| `"disable_image"` | Non-aktifkan tampilan gambar |

### Pesan ke ESP32
- Saat ini hanya read-only dari sisi Python

---

## 9. Environment Variables

Konfigurasi via file `.env`.

| Variable | Tipe | Default | Deskripsi |
|----------|------|---------|-----------|
| `BACKEND_API_URL` | string | `http://localhost:8080/api/v1` | URL backend server |
| `DISPLAY_HALF` | bool | `true` | UI compact (1200x620 vs 1400x820) |
| `MAX_LEVEL` | int | `8` | Level maksimum (1-8) |
| `NORMAL_PATTERN` | bool | `true` | Gunakan pattern normal vs OtakAtik |
| `MODEL_BANTAL` | bool | `false` | Gunakan model YOLO alternatif |
| `BUTTON_MODE` | bool | `false` | Mode tombol hardware |
| `HIDE_CAMERA` | bool | `false` | Sembunyikan panel kamera |
| `YOLO_SKIP_FRAMES` | int | `2` | Skip frame YOLO (0 = setiap frame) |
| `MEDIAPIPE_SKIP_FRAMES` | int | `2` | Skip frame MediaPipe |
| `CAMERA_GAME_INDEX` | int | `0` | Index kamera game |
| `CAMERA_FACE_INDEX` | int | `1` | Index kamera wajah |
| `DEBUG_MODE` | bool | `false` | Mode debug |

---

## Ringkasan Dependency

```
requirements.txt
├── ultralytics          # YOLO deteksi blok
├── mediapipe >= 0.10.33 # Hand & face tracking (Tasks API)
├── deepface             # Emosi wajah
├── transformers         # Wav2Vec2 speech recognition
├── torch                # Backend ML (PyTorch)
├── vosk                 # Speech recognition offline (fallback)
├── gtts                 # Google Text-to-Speech
├── sounddevice          # Audio I/O
├── soundfile            # Audio file reading
├── opencv-python        # Computer vision
├── numpy                # Numerical computing
├── requests             # HTTP client ke backend
├── pyserial             # Serial ke ESP32
├── customtkinter        # UI framework
├── pillow               # Image processing
├── pandas               # Data manipulation
└── python-dotenv        # Environment variables
```

### File Model yang Dibutuhkan

| File | Ukuran | Download |
|------|--------|----------|
| `models/weights/best.pt` | ~14 MB | Custom trained YOLO |
| `models/weights/bantal.pt` | ~14 MB | Custom trained YOLO (alternatif) |
| `models/weights/hand_landmarker.task` | ~8 MB | [Link](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task) |
| `models/weights/face_landmarker.task` | ~4 MB | [Link](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task) |
| `models/vosk-model-small-id/` | ~40 MB | [Vosk Indonesian](https://alphacephei.com/vosk/models) |
| `indonesian-nlp/wav2vec2-*` | ~1.2 GB | Auto-download dari HuggingFace |
