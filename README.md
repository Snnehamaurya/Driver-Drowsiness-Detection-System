# AI Driver Drowsiness & Distraction Detection System (Web Edition)

A complete production-ready AI-based Driver Drowsiness Detection System built using Python. This application monitors the driver in real-time via a webcam and triggers voice warnings and alarms when signs of drowsiness (closing eyes, yawning) or distraction (looking away, using a cell phone) are detected.

## 🚀 Features

- **Real-Time Monitoring**: Low-latency video feed using OpenCV and CustomTkinter.
- **Eye Aspect Ratio (EAR) Calculation**: Detects sleepiness via facial landmarks.
- **Mouth Aspect Ratio (MAR) Calculation**: Detects yawning.
- **Head Pose Estimation**: Detects if the driver is looking away from the road using `solvePnP`.
- **Mobile Phone Detection**: Detects phone usage using a lightweight YOLOv8 AI model.
- **Modern Dashboard**: Built with CustomTkinter for a sleek dark/light mode UI.
- **Fatigue Score & Session Logging**: Tracks metrics dynamically and saves session logs to CSV.
- **Offline Text-to-Speech**: Voice warnings using `pyttsx3`.

## 🛠️ Technology Stack

- **Language**: Python 3.9+
- **Face/Pose Detection**: MediaPipe Face Mesh (CPU optimized)
- **Object/Phone Detection**: YOLOv8 nano via Ultralytics (CPU/GPU)
- **GUI Framework**: CustomTkinter
- **Audio/Voice**: Pygame (Alarms) & Pyttsx3 (Offline Voice)
- **Math/Processing**: NumPy, OpenCV

## 📁 Project Structure

```
PID Project/
├── main.py                     # Entry point
├── requirements.txt            # Dependencies
├── README.md                   # Project overview
├── detector/                   # Core ML models
│   ├── face_mesh.py            # EAR, MAR, Head Pose (MediaPipe)
│   └── object_detect.py        # Cell Phone detection (YOLOv8)
├── gui/                        # UI logic
│   └── app.py                  # CustomTkinter dashboard
├── utils/                      # Helper scripts
│   ├── audio_manager.py        # TTS and Siren logic
│   ├── logger.py               # CSV session logging
│   └── math_helpers.py         # 3D Math, EAR, MAR formulas
├── assets/                     # Sounds & media
├── logs/                       # Auto-generated CSVs
├── models/                     # YOLO weights (.pt files)
└── docs/                       # College & Portfolio Documentation
```

## ⚙️ Installation

1. Clone or download this repository.
2. Ensure you have Python 3.9 or higher installed.
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Generate the alarm sound (optional if you want to use your own `alarm.wav` in `assets/`):
   ```bash
   python utils/generate_alarm.py
   ```

## 🏃 Execution Steps

Run the main application file:
```bash
python main.py
```

1. The Dashboard will open. Click **"Start Detection"**.
2. Make sure your webcam is active.
3. To test drowsiness: **Close your eyes for 2-3 seconds**.
4. To test yawning: **Open your mouth wide**.
5. To test distraction: **Turn your head sideways** or **hold up a cell phone**.

## 📊 Session Logs
All detections are stored inside the `logs/` directory with a timestamped `.csv` file. You can export/view these for analytics.

## 🔮 Future Scope
- Deploy on edge devices like Raspberry Pi 4 / Jetson Nano.
- Send an SMS/Email to emergency contacts or fleet managers.
- Cloud Dashboard integration for real-time fleet monitoring.
