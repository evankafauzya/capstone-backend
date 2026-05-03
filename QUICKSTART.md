# Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Validate Setup
```bash
python setup_validator.py
```

### Step 3: Run the Server
```bash
python app.py
```

You should see:
```
Starting server on 0.0.0.0:5000
```

### Step 4: Test with Demo (in another terminal)
```bash
python demo_session.py
```

---

## Configuration

### Environment Variables (.env)
```
CAPTURE_INTERVAL=5              # Capture every 5 seconds
REVERIFICATION_INTERVAL=30      # Reverify every 30 seconds
SESSION_TIMEOUT=3600            # 1 hour session max
MAX_FACES_ALLOWED=1             # Only 1 face allowed
FACE_DETECTION_CONFIDENCE=0.5   # Detection confidence threshold
DEBUG=True                       # Enable debug mode
```

---

## API Quick Reference

### Start a Session
```bash
curl -X POST http://localhost:5000/api/proctoring/session/start \
  -H "Content-Type: application/json" \
  -d '{"session_id":"exam_001","user_id":"student_001"}'
```

### Get Current Frame
```bash
curl http://localhost:5000/api/proctoring/video/frame > frame.jpg
```

### Get Session Status
```bash
curl http://localhost:5000/api/proctoring/session/status
```

### Get Warnings
```bash
curl http://localhost:5000/api/proctoring/warnings?limit=20
```

### Stop Session & Get Report
```bash
curl -X POST http://localhost:5000/api/proctoring/session/stop
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|------------|
| Python | 3.8 | 3.10+ |
| RAM | 4GB | 8GB |
| Storage | 2GB | 5GB |
| CPU Cores | 2 | 4+ |
| GPU | None | NVIDIA with CUDA |

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'cv2'"
**Solution:** Run `pip install -r requirements.txt`

### Issue: "Cannot open camera"
**Solution:** 
- Check USB connection
- Verify camera permissions
- Try different camera ID in `src/processors/webcam_capture.py`

### Issue: "Model files not found"
**Solution:**
- Place model files in `models_data/` directory
- System will use fallback models if not available

### Issue: Low accuracy
**Solution:**
- Improve lighting conditions
- Check camera focus
- Adjust confidence thresholds in `.env`
- Use better trained model files

---

## Key Modules

### ModelManager (`src/core/model_manager.py`)
- Loads PKL and PTH model files
- Performs face detection and recognition
- Handles model inference

### FaceDetector (`src/detectors/face_detector.py`)
- Detects faces in frames
- Warns if multiple faces or no face
- Maintains detection history

### EyeTracker (`src/detectors/eye_tracker.py`)
- Tracks eye movements
- Detects gaze direction
- Identifies blinks
- Warns on unusual eye movement

### WebcamCapture (`src/processors/webcam_capture.py`)
- Manages webcam input
- Provides frame streaming
- Handles threading

### ProctoringSession (`src/processors/session_manager.py`)
- Manages session lifecycle
- Handles verification
- Records events and warnings
- Generates reports

### ProctoringSystem (`src/core/orchestrator.py`)
- Main system orchestrator
- Coordinates all components
- Manages processing loop
- Handles session lifecycle

---

## Project Flow

```
┌─────────────────────────────────────────┐
│     User Starts Proctoring Session      │
└──────────────┬──────────────────────────┘
               │
               ▼
    ┌─────────────────────────┐
    │  Initial Verification   │
    │  - Capture face         │
    │  - Verify user ID       │
    │  - Accept or reject     │
    └──────────┬──────────────┘
               │ (Verified)
               ▼
    ┌─────────────────────────┐
    │  Session Active         │
    │  - Capture frames       │
    │  - Track eye movement   │
    │  - Monitor face         │
    └────────┬────────────────┘
             │
        (Every 30s)
             ▼
    ┌─────────────────────────┐
    │  Reverification         │
    │  - Verify user still OK │
    │  - Alert on mismatch    │
    └────────┬────────────────┘
             │
        (On End)
             ▼
    ┌─────────────────────────┐
    │  Generate Reports       │
    │  - JSON report          │
    │  - Text report          │
    │  - PDF report           │
    └─────────────────────────┘
```

---

## Next Steps

1. **Test the System**: Run `python demo_session.py`
2. **Integrate Models**: Add your trained model files
3. **Configure Settings**: Adjust `.env` for your needs
4. **Build Frontend**: Create web UI to interact with API
5. **Add Database**: Persist sessions and data
6. **Deploy**: Move to production server

---

## Support & Documentation

- See `README.md` for detailed documentation
- Check `config/settings.py` for all configuration options
- Review model files documentation for model specifications
- Check logs in `logs/` directory for debugging

---

**Ready to go! 🚀**

Run `python app.py` to start the server!
