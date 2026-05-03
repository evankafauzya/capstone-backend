# Proctoring System - Face Recognition & Detection

A comprehensive Python-based proctoring system using AI models for face recognition and detection, designed for secure exam monitoring with real-time warnings and detailed reporting.

## Features

✅ **Initial & Continuous Verification**
- User identity verification at session start
- Periodic reverification at admin-configurable intervals
- Face encoding comparison for identity matching

✅ **Face Detection & Monitoring**
- Real-time face detection using PyTorch models
- Multiple face detection warnings
- Missing face detection alerts
- Configurable confidence thresholds

✅ **Eye Tracking & Gaze Detection**
- Eye landmark detection using MediaPipe
- Gaze direction tracking (LEFT, RIGHT, CENTER, UP, DOWN)
- Blink detection with aspect ratio calculation
- Unusual eye movement detection

✅ **Warning System**
- Multi-level warnings (INFO, WARNING, ALERT, CRITICAL)
- Multiple face detected (>1 user)
- Face not detected
- Unusual eye movement patterns
- Reverification failures

✅ **Session Management**
- Configurable capture intervals
- Configurable reverification intervals
- Session timeout settings
- Detailed event logging

✅ **Comprehensive Reporting**
- JSON format reports
- Text format reports
- PDF format reports (optional)
- Session statistics and analytics
- Timeline of events and warnings

## Project Structure

```
capstone-backend/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
│
├── config/
│   ├── __init__.py
│   └── settings.py                 # Configuration settings
│
├── models_data/                    # Directory for PKL and PTH model files
│   ├── face_recognition_model.pkl  # Face recognition model
│   └── face_detection_model.pth    # Face detection model
│
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── model_manager.py        # Model loading and inference
│   │   └── orchestrator.py         # Main system orchestrator
│   │
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── face_detector.py        # Face detection module
│   │   └── eye_tracker.py          # Eye tracking module
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── webcam_capture.py       # Webcam capture and streaming
│   │   └── session_manager.py      # Session lifecycle management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── proctoring_routes.py    # Flask API endpoints
│   │
│   └── utils/
│       ├── __init__.py
│       └── report_generator.py     # Report generation
│
├── reports/                        # Generated reports directory
├── logs/                           # Application logs directory
└── README.md                       # This file
```

## Installation

### 1. Prerequisites
- Python 3.8 or higher
- Webcam/Camera device
- GPU support (CUDA) recommended for better performance

### 2. Clone and Setup

```bash
cd c:\capstone-backend
```

### 3. Create Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy example configuration
copy .env.example .env

# Edit .env with your settings
# Key settings:
# - CAPTURE_INTERVAL: Frame capture interval (seconds)
# - REVERIFICATION_INTERVAL: How often to reverify user (seconds)
# - SESSION_TIMEOUT: Maximum session duration (seconds)
# - MAX_FACES_ALLOWED: Maximum faces allowed in frame (default: 1)
```

### 6. Add Model Files

Place your model files in the `models_data/` directory:
- `face_recognition_model.pkl` - Face recognition model (pickle format)
- `face_detection_model.pth` - Face detection model (PyTorch format)

**Note:** If model files are not found, the system will use fallback models:
- Fallback face detection: OpenCV Haar Cascade Classifier
- Fallback face recognition: Library estimation

## Running the System

### Start the Server

```bash
python app.py
```

Server will start at `http://localhost:5000`

### API Endpoints

#### Session Management

**Start Session**
```bash
POST /api/proctoring/session/start
Content-Type: application/json

{
    "session_id": "exam_001",
    "user_id": "student_123"
}
```

**Stop Session**
```bash
POST /api/proctoring/session/stop
```

**Get Session Status**
```bash
GET /api/proctoring/session/status
```

**Get Session Report**
```bash
GET /api/proctoring/session/report
```

#### Video Streaming

**Get Current Frame**
```bash
GET /api/proctoring/video/frame
```

**Stream Video (Motion JPEG)**
```bash
GET /api/proctoring/video/stream
```

#### Analytics

**Face Detection Statistics**
```bash
GET /api/proctoring/face-detection/stats
```

**Eye Tracking Statistics**
```bash
GET /api/proctoring/eye-tracking/stats
```

**Session Warnings**
```bash
GET /api/proctoring/warnings?limit=50
```

#### Configuration

**Get Configuration**
```bash
GET /api/proctoring/configuration
```

**Update Configuration**
```bash
PUT /api/proctoring/configuration
Content-Type: application/json

{
    "capture_interval": 5,
    "reverification_interval": 30,
    "max_faces_allowed": 1
}
```

#### System Information

**Health Check**
```bash
GET /api/proctoring/health
```

**System Info**
```bash
GET /api/proctoring/system-info
```

## Configuration Parameters

Edit `.env` or `config/settings.py`:

```python
# Capture interval in seconds (how often to capture frames)
CAPTURE_INTERVAL = 5

# Reverification interval in seconds (how often to re-verify identity)
REVERIFICATION_INTERVAL = 30

# Session timeout in seconds (max session duration)
SESSION_TIMEOUT = 3600  # 1 hour

# Eye tracking parameters
EYE_MOVEMENT_THRESHOLD = 0.3
EYE_ASPECT_RATIO_THRESHOLD = 0.2

# Face detection parameters
FACE_DETECTION_CONFIDENCE = 0.5
MAX_FACES_ALLOWED = 1  # Warning if >1 face detected

# Debug mode
DEBUG = True
```

## Usage Example

### Python Client Example

```python
import requests
import time
import json

BASE_URL = "http://localhost:5000/api/proctoring"

# Start session
session_data = {
    "session_id": "exam_001",
    "user_id": "student_123"
}
response = requests.post(f"{BASE_URL}/session/start", json=session_data)
print("Session started:", response.json())

# Wait for user verification
time.sleep(5)

# Get session status
response = requests.get(f"{BASE_URL}/session/status")
print("Session status:", response.json())

# Get warnings
response = requests.get(f"{BASE_URL}/warnings?limit=10")
print("Recent warnings:", response.json())

# Get statistics
response = requests.get(f"{BASE_URL}/face-detection/stats")
print("Face detection stats:", response.json())

response = requests.get(f"{BASE_URL}/eye-tracking/stats")
print("Eye tracking stats:", response.json())

# Stop session and generate report
time.sleep(10)
response = requests.post(f"{BASE_URL}/session/stop")
result = response.json()
print("Session stopped")
print("Reports generated:", result.get("reports"))

# Get detailed report
response = requests.get(f"{BASE_URL}/session/report")
report = response.json()
print(json.dumps(report, indent=2))
```

## Warning Types

### 1. Multiple Faces Detected
Triggered when more than `MAX_FACES_ALLOWED` faces are detected in a single frame.
```
Level: WARNING/ALERT
Description: "Multiple faces detected (N) in frame! Expected maximum M."
```

### 2. Face Not Detected
Triggered when no face is detected in a frame.
```
Level: WARNING
Description: "Face not detected in frame!"
```

### 3. Unusual Eye Movement
Triggered when sudden, unusual eye movements are detected.
```
Level: WARNING
Description: "Unusual eye movement detected!"
```

### 4. Reverification Failed
Triggered when user fails reverification.
```
Level: CRITICAL
Description: "User reverification failed. Possible identity change or spoofing attempt."
```

## Report Structure

Generated reports include:

### Session Information
- Session ID and User ID
- Start/End times and duration
- Verification status

### Statistics
- Total events recorded
- Warning counts (by level)
- Face detection accuracy
- Verification success rate
- Eye tracking data counts

### Events Timeline
- Chronological list of events
- Event type and severity
- Event details

### Warnings Log
- All warnings with timestamps
- Warning level and description
- Contextual details

## Logging

Logs are stored in the `logs/` directory:
- `proctoring.log` - Detailed application logs

### Log Levels
- DEBUG: Detailed debugging information
- INFO: General informational messages
- WARNING: Warning messages
- ERROR: Error messages

## Troubleshooting

### No Webcam Detected
- Check USB connection
- Verify camera permissions
- Try different camera ID (0, 1, 2, etc.)

### Models Not Loading
- Verify model files exist in `models_data/` directory
- Check file formats (`.pkl` for recognition, `.pth` for detection)
- System will use fallback models if not available

### Low Detection Accuracy
- Adjust `FACE_DETECTION_CONFIDENCE` threshold
- Ensure proper lighting
- Check camera resolution and focus
- Update model files with better trained models

### Performance Issues
- Reduce `CAPTURE_INTERVAL` (capture less frequently)
- Lower video resolution in `webcam_capture.py`
- Enable GPU acceleration (if CUDA available)
- Reduce queue size in webcam capture

## Model Management

### Using PKL Models (Face Recognition)
- Pickle format Python objects
- Place in `models_data/face_recognition_model.pkl`
- Expected to have a `predict()` method

### Using PTH Models (Face Detection)
- PyTorch model weights
- Place in `models_data/face_detection_model.pth`
- Currently expects ResNet50-based architecture
- Can be modified for other architectures

### Fallback Models
- OpenCV Haar Cascade (face detection)
- face_recognition library (face encoding)

## Performance Metrics

Typical performance on modern hardware:

| Metric | Value |
|--------|-------|
| Frame Processing | 30 FPS |
| Face Detection Latency | 50-100ms |
| Eye Tracking Latency | 30-50ms |
| Memory Usage | 500MB-1GB |
| CPU Usage | 20-40% (single core) |
| GPU Usage (with CUDA) | 30-50% |

## Security Considerations

1. **Model Security**: Keep model files secure and access-controlled
2. **Session Management**: Use unique session IDs
3. **Data Privacy**: Implement encryption for sensitive data
4. **API Authentication**: Add authentication layer for production
5. **HTTPS**: Use HTTPS for API in production
6. **Verification Confidence**: Adjust confidence thresholds appropriately

## Future Enhancements

- [ ] Multi-face identification and tracking
- [ ] Behavioral analysis and anomaly detection
- [ ] Audio monitoring and analysis
- [ ] Screen sharing detection
- [ ] Mobile device detection
- [ ] Database integration for persistent storage
- [ ] Dashboard UI for administrators
- [ ] Email report delivery
- [ ] Real-time alerts integration
- [ ] Advanced anti-spoofing techniques

## License

Proprietary - Capstone Project

## Support

For issues or questions, please refer to the documentation or contact the development team.

## Version History

- **v1.0.0** (2024) - Initial release
  - Face detection and recognition
  - Eye tracking
  - Session management
  - Report generation
  - REST API

---

**Last Updated:** May 3, 2024
