# System Architecture Documentation

## Overview

The Proctoring System is a comprehensive Python-based solution for secure exam monitoring using AI-powered face recognition and detection. It provides real-time monitoring with multiple verification layers and detailed reporting.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flask Web API                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /session/start  /session/stop  /video/frame   /reports  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────┐
        │     ProctoringSystem                │
        │     (Main Orchestrator)            │
        └────────────┬───────────────────────┘
                     │
          ┌──────────┼──────────┬──────────┐
          │          │          │          │
          ▼          ▼          ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────┐
    │Webcam   │ │Session  │ │Model    │ │Report        │
    │Capture  │ │Manager  │ │Manager  │ │Generator     │
    └─────────┘ └────┬────┘ └────┬────┘ └──────────────┘
                     │           │
                ┌────┴─────────┬─┴─────────┐
                │              │           │
                ▼              ▼           ▼
          ┌──────────┐  ┌────────────┐  ┌──────────────┐
          │Face      │  │Eye         │  │Model Files   │
          │Detector  │  │Tracker     │  │(PKL, PTH)    │
          └──────────┘  └────────────┘  └──────────────┘
```

## Core Components

### 1. **Flask Application (app.py)**
Entry point for the entire system.

**Responsibilities:**
- Initialize Flask web server
- Configure CORS and error handling
- Register API blueprints
- Initialize all core systems

**Dependencies:**
- Flask, Flask-CORS
- Configuration module

---

### 2. **Proctoring System (src/core/orchestrator.py)**
Main orchestrator coordinating all components.

**Responsibilities:**
- Initialize and manage all subsystems
- Manage the processing loop
- Handle session lifecycle
- Coordinate verification and monitoring

**Key Methods:**
- `start_session()` - Begin new proctoring session
- `stop_session()` - End session and generate reports
- `_processing_loop()` - Main monitoring loop
- `get_session_status()` - Current session state

---

### 3. **Model Manager (src/core/model_manager.py)**
Handles model loading and inference.

**Features:**
- Loads both PKL and PTH model files
- Manages PyTorch models with GPU support
- Provides fallback models (Haar Cascade, face_recognition library)
- Performs face detection inference
- Handles face recognition encoding

**Model Formats Supported:**
- **PKL Files**: Python pickle serialized objects for face recognition
- **PTH Files**: PyTorch model weights with state dict

---

### 4. **Face Detector (src/detectors/face_detector.py)**
Detects and validates faces in frames.

**Features:**
- Real-time face detection
- Multiple face detection warnings
- Face missing detection alerts
- Maintains detection history
- Provides statistical analysis

**Warning Conditions:**
- Number of faces > MAX_FACES_ALLOWED
- Number of faces = 0

---

### 5. **Eye Tracker (src/detectors/eye_tracker.py)**
Tracks eye movement and gaze direction.

**Features:**
- Uses MediaPipe Face Mesh for landmark detection
- Detects gaze direction (LEFT, RIGHT, CENTER, UP, DOWN)
- Calculates eye aspect ratio (blink detection)
- Tracks unusual eye movements
- Maintains gaze history

**Gaze Directions:**
- CENTER
- LEFT, RIGHT
- UP, DOWN
- Combinations: LEFT_UP, RIGHT_DOWN, etc.

---

### 6. **Webcam Capture (src/processors/webcam_capture.py)**
Manages webcam input and frame streaming.

**Features:**
- Threaded frame capture
- Configurable resolution and FPS
- Frame queue for buffering
- Threading-safe frame access
- Camera property management

**Key Methods:**
- `start()` - Begin capturing
- `stop()` - Stop capturing
- `get_frame()` - Get current frame
- `get_frame_nowait()` - Non-blocking frame retrieval

---

### 7. **Session Manager (src/processors/session_manager.py)**
Manages session lifecycle and event recording.

**Key Responsibilities:**
- Session initialization and termination
- User verification and reverification
- Event recording and logging
- Warning generation
- Data collection for reporting

**Session States:**
```
INITIALIZED → VERIFYING → ACTIVE ↔ REVERIFYING → COMPLETED
                              ↓
                         TERMINATED
```

**Event Types:**
- SESSION_STARTED
- INITIAL_VERIFICATION_SUCCESS/FAILED
- REVERIFICATION_SUCCESS/FAILED
- FACE_DETECTION_ISSUE
- EYE_TRACKING_ALERT

---

### 8. **Report Generator (src/utils/report_generator.py)**
Generates comprehensive session reports.

**Output Formats:**
- **JSON**: Machine-readable format with all data
- **TEXT**: Human-readable text format
- **PDF**: Professional formatted PDF (optional with reportlab)

**Report Contents:**
- Session information and timeline
- Statistical analysis
- Events and warnings log
- Verification timeline
- Detection accuracy metrics

---

### 9. **API Routes (src/api/proctoring_routes.py)**
RESTful API endpoints for system control.

**Endpoints:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| POST | `/session/start` | Start session |
| POST | `/session/stop` | Stop session |
| GET | `/session/status` | Session status |
| GET | `/session/report` | Session report |
| GET | `/video/frame` | Current frame |
| GET | `/video/stream` | Video stream |
| GET | `/face-detection/stats` | Detection stats |
| GET | `/eye-tracking/stats` | Eye tracking stats |
| GET | `/warnings` | Session warnings |
| GET | `/configuration` | System config |
| PUT | `/configuration` | Update config |

---

## Data Flow

### Session Start Flow
```
API /session/start
       │
       ▼
ProctoringSystem.start_session()
       │
       ├─→ Create ProctoringSession
       ├─→ Start Webcam
       ├─→ Start processing thread
       └─→ Begin verification state
```

### Frame Processing Flow
```
Webcam Frame
       │
       ▼
FaceDetector.detect_faces()
       │
       ├─→ Model inference
       ├─→ Generate warnings
       └─→ Record detection
            │
            ▼
EyeTracker.detect_eyes()
       │
       ├─→ MediaPipe landmarks
       ├─→ Calculate eye metrics
       ├─→ Detect gaze direction
       └─→ Check for unusual movement
            │
            ▼
SessionManager.record_face_detection()
SessionManager.record_eye_tracking()
       │
       ▼
Check for verification/reverification
```

### Session Stop & Reporting Flow
```
SessionManager.end_session()
       │
       ├─→ Compile statistics
       ├─→ Generate session report
       │
       ▼
ReportGenerator.generate_all_reports()
       │
       ├─→ JSON report
       ├─→ Text report
       └─→ PDF report (optional)
            │
            ▼
Return report paths to API
```

---

## Configuration Architecture

### Settings Hierarchy
```
1. Environment Variables (.env)
   └─→ Override defaults
2. config/settings.py
   └─→ Application defaults
3. Runtime Configuration
   └─→ API configuration endpoint
```

### Key Configuration Parameters
```python
# Timing
CAPTURE_INTERVAL = 5              # seconds
REVERIFICATION_INTERVAL = 30      # seconds
SESSION_TIMEOUT = 3600            # seconds

# Thresholds
FACE_DETECTION_CONFIDENCE = 0.5   # 0-1
EYE_MOVEMENT_THRESHOLD = 0.3      # 0-1
EYE_ASPECT_RATIO_THRESHOLD = 0.2  # 0-1

# Limits
MAX_FACES_ALLOWED = 1             # integer
```

---

## State Management

### Session State Machine
```
State: INITIALIZED
  └─→ start_session()
      └─→ State: VERIFYING
          ├─→ verify_user() [success]
          │   └─→ State: ACTIVE
          │       ├─→ Processing loop
          │       │   ├─→ check_reverification_needed()
          │       │   │   └─→ State: REVERIFYING
          │       │   │       └─→ reverify_user()
          │       │   │           └─→ State: ACTIVE
          │       │   └─→ check_session_timeout()
          │       │       └─→ State: TERMINATED
          │       └─→ stop_session()
          │           └─→ State: COMPLETED
          └─→ verify_user() [failed]
              └─→ State: TERMINATED
```

---

## Verification Process

### Initial Verification
1. User starts session
2. System enters VERIFYING state
3. Waits for clear face detection
4. Performs face recognition/encoding
5. Compares with registered user
6. If match: → ACTIVE state
7. If no match: → TERMINATED state

### Reverification
1. Triggered every REVERIFICATION_INTERVAL seconds
2. Captures current face
3. Performs face recognition
4. Compares with original user ID
5. If match: Continue ACTIVE state
6. If no match: Generate CRITICAL warning

---

## Error Handling

### Error Recovery Strategy
```
Component Error
  │
  ├─→ Log error
  ├─→ Generate warning event
  ├─→ Fallback mechanism (if available)
  └─→ Continue session or terminate
```

### Graceful Degradation
- Model loading fails → Use fallback models
- GPU unavailable → Use CPU
- Camera disconnects → Alert and pause
- API unreachable → Queue events locally

---

## Performance Considerations

### Threading Model
- **Main Thread**: Flask request handling
- **Capture Thread**: Webcam frame capture (non-blocking queue)
- **Processing Thread**: Main monitoring loop (singleton)

### Resource Management
```
Memory:
- Frame buffer: ~10-20MB
- Model inference: ~500MB-1GB
- Session data: ~1-10MB per hour

CPU:
- Face detection: 50-100ms per frame
- Eye tracking: 30-50ms per frame
- Processing overhead: 10-20%

GPU (if available):
- Acceleration factor: 3-5x
- Memory: 1-4GB
```

---

## Security Considerations

### Authentication & Authorization
- Currently: None (demo/development mode)
- Production: Implement JWT or OAuth2

### Data Privacy
- Models are not trained on sensitive data
- No biometric storage (optional in future)
- Session data can be encrypted

### API Security
- Input validation on all endpoints
- Rate limiting (recommended)
- HTTPS/TLS in production

---

## Deployment Architecture

### Development
```
Single Machine
├─→ Flask Server (port 5000)
├─→ Webcam connected
└─→ Local file storage
```

### Production
```
Cloud Infrastructure
├─→ Load Balancer (HTTPS)
├─→ Flask Servers (multiple instances)
├─→ Camera Stream Service
├─→ Database (PostgreSQL/MySQL)
├─→ Storage Service (S3/GCS)
└─→ Report Service
```

---

## Extension Points

### Adding Custom Detectors
```python
class CustomDetector:
    def __init__(self, model_manager):
        self.model_manager = model_manager
    
    def detect(self, frame):
        # Custom detection logic
        return results
```

### Adding Custom Report Formats
```python
class ReportGenerator:
    def generate_custom_report(self, session_data):
        # Custom report generation
        return report_path
```

### Adding Custom Verification Methods
```python
class ProctoringSession:
    def custom_verify_user(self, data):
        # Custom verification logic
        return verification_result
```

---

## Version & Compatibility

| Component | Version | Compatibility |
|-----------|---------|---|
| Python | 3.8+ | 3.8, 3.9, 3.10, 3.11 |
| Flask | 3.0.0 | 2.0+ |
| OpenCV | 4.8.1 | 4.x |
| PyTorch | 2.0.1 | 1.9+ |
| CUDA | 11.8+ | (Optional) |

---

**Last Updated:** May 3, 2024
