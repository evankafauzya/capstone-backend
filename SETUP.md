# Complete Setup Instructions

## 📋 Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Running the System](#running-the-system)
5. [Testing & Validation](#testing--validation)
6. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum
- **Storage**: 2GB free space
- **Webcam**: USB or integrated camera
- **Internet**: For package installation

### Recommended Requirements
- **OS**: Windows 11 or Ubuntu 20.04+
- **Python**: 3.10 or 3.11
- **RAM**: 8GB
- **Storage**: 5GB SSD
- **GPU**: NVIDIA GPU with CUDA support for better performance
- **CPU**: Multi-core processor (4+ cores)

### Python Dependencies
The system uses the following key packages:
- **Flask** (3.0.0) - Web framework
- **OpenCV** (4.8.1) - Computer vision
- **PyTorch** (2.0.1) - Deep learning
- **MediaPipe** (0.10.1) - Face and hand tracking
- **NumPy** (1.24.3) - Numerical computing
- **scikit-learn** (1.3.2) - Machine learning utilities

---

## Installation Steps

### Step 1: Clone/Navigate to Project Directory

```bash
cd c:\capstone-backend
```

### Step 2: Create Python Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Verify Virtual Environment

```bash
# Check Python version
python --version

# Should show: Python 3.8.x or higher
```

### Step 4: Upgrade pip and setuptools

```bash
python -m pip install --upgrade pip setuptools wheel
```

### Step 5: Install Requirements

```bash
pip install -r requirements.txt
```

**Installation may take 5-15 minutes depending on internet speed and system performance.**

### Step 6: Verify Installation

```bash
python setup_validator.py
```

Expected output:
```
==================================================
Proctoring System - Setup Validator
==================================================
✓ Directory ensured: models_data
✓ Directory ensured: reports
✓ Directory ensured: logs
✓ Directory ensured: src
✓ Directory ensured: config

Model File Status:
--------------------------------------------------
Face Recognition..... ✗ Missing
Face Detection....... ✗ Missing

⚠ Some model files are missing!
  System will use fallback models.

Environment Validation:
--------------------------------------------------
Python Version: 3.x.x
✓ Python version OK

Required Packages:
  ✓ cv2
  ✓ flask
  ✓ numpy
  ✓ torch
  ✓ Webcam detected and accessible

✓ System is ready to run!
```

---

## Configuration

### Step 1: Create Environment File

```bash
# Copy example to .env
copy .env.example .env          # Windows
cp .env.example .env            # macOS/Linux
```

### Step 2: Edit .env File

Open `.env` and customize for your needs:

```env
# Flask Configuration
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
HOST=0.0.0.0
PORT=5000

# Proctoring Configuration
CAPTURE_INTERVAL=5              # Capture frame every 5 seconds
REVERIFICATION_INTERVAL=30      # Reverify user every 30 seconds
SESSION_TIMEOUT=3600            # 1 hour maximum session duration
EYE_MOVEMENT_THRESHOLD=0.3      # Sensitivity for eye movement detection
EYE_ASPECT_RATIO_THRESHOLD=0.2  # Threshold for blink detection
FACE_DETECTION_CONFIDENCE=0.5   # Minimum confidence for face detection
MAX_FACES_ALLOWED=1             # Maximum faces allowed (warning if exceeded)

# Database Configuration (for future use)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=proctoring_db
```

### Step 3: Add Model Files (Optional)

Place your trained models in `models_data/` directory:

```
models_data/
├── face_recognition_model.pkl    # Face recognition model
└── face_detection_model.pth      # Face detection model
```

**Note:** If models are not provided, the system will use fallback models.

### Step 4: Verify Configuration

```bash
python -c "from config.settings import ProctoringConfig; print(ProctoringConfig.CAPTURE_INTERVAL)"
```

---

## Running the System

### Start the Flask Server

```bash
python app.py
```

Expected output:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
 * Press CTRL+C to quit
```

**Server is now running and ready for requests!**

### In a New Terminal: Test with Demo

```bash
# Make sure virtual environment is activated
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

python demo_session.py
```

This will:
1. Start a test proctoring session
2. Run for ~15 seconds
3. Display statistics
4. Generate reports
5. Show results

---

## Testing & Validation

### Manual API Testing

#### 1. Health Check
```bash
curl http://localhost:5000/api/proctoring/health
```

#### 2. Start a Session
```bash
curl -X POST http://localhost:5000/api/proctoring/session/start \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test_001","user_id":"user_001"}'
```

#### 3. Get Current Status
```bash
curl http://localhost:5000/api/proctoring/session/status
```

#### 4. Capture Frame
```bash
curl http://localhost:5000/api/proctoring/video/frame -o frame.jpg
```

#### 5. Get Statistics
```bash
curl http://localhost:5000/api/proctoring/face-detection/stats
curl http://localhost:5000/api/proctoring/eye-tracking/stats
```

#### 6. Stop Session
```bash
curl -X POST http://localhost:5000/api/proctoring/session/stop
```

### Python Client Testing

Create `test_client.py`:

```python
import requests
import time
import json

BASE_URL = "http://localhost:5000/api/proctoring"

# Start session
response = requests.post(f"{BASE_URL}/session/start", json={
    "session_id": "test_session",
    "user_id": "test_user"
})
print("Session started:", response.status_code)

# Wait a bit
time.sleep(5)

# Get status
response = requests.get(f"{BASE_URL}/session/status")
print("Status:", json.dumps(response.json(), indent=2))

# Stop session
response = requests.post(f"{BASE_URL}/session/stop")
print("Session stopped:", response.status_code)
print("Report paths:", response.json().get("reports"))
```

Run with:
```bash
python test_client.py
```

---

## Troubleshooting

### Issue: ModuleNotFoundError

**Problem:**
```
ModuleNotFoundError: No module named 'cv2'
```

**Solution:**
```bash
# Make sure virtual environment is activated
pip install -r requirements.txt

# Or install specific package
pip install opencv-python opencv-contrib-python
```

---

### Issue: CUDA/GPU Not Found

**Problem:**
```
WARNING: No GPU available. Using CPU instead.
```

**Solution (Optional):**
```bash
# Install CUDA-enabled PyTorch (if you have NVIDIA GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

### Issue: Camera/Webcam Not Detected

**Problem:**
```
Failed to open camera
```

**Solutions:**
1. **Check USB connection**
   - Ensure camera is properly connected
   - Try different USB port

2. **Check permissions**
   - Windows: Check Device Manager
   - macOS: System Preferences → Security & Privacy → Camera
   - Linux: `sudo usermod -a -G video $USER`

3. **Try different camera ID**
   Edit `src/processors/webcam_capture.py`:
   ```python
   # Try camera ID 0, 1, 2, etc.
   self.cap = cv2.VideoCapture(0)  # Change to 1, 2, etc.
   ```

4. **Test with OpenCV**
   ```python
   import cv2
   cap = cv2.VideoCapture(0)
   if cap.isOpened():
       print("Camera OK")
   else:
       print("Camera not found")
   ```

---

### Issue: Low Model Accuracy

**Problem:**
```
Face not detected or recognition confidence low
```

**Solutions:**
1. **Improve lighting**
   - Ensure good lighting on face
   - Avoid backlighting
   - Use natural or bright artificial light

2. **Adjust confidence thresholds** (`.env`):
   ```env
   FACE_DETECTION_CONFIDENCE=0.3  # Lower = more detections
   ```

3. **Check camera focus**
   - Ensure camera is properly focused
   - Clean camera lens
   - Position face 30-60cm from camera

4. **Use better model files**
   - Train with larger dataset
   - Use better quality training images
   - Consider using pre-trained models (ResNet, MobileNet, etc.)

---

### Issue: Out of Memory

**Problem:**
```
MemoryError or CUDA out of memory
```

**Solutions:**
1. **Close other applications**
   - Free up system RAM
   - Close browser tabs and other programs

2. **Reduce queue size**
   Edit `src/processors/webcam_capture.py`:
   ```python
   self.frame_queue = Queue(maxsize=5)  # Reduce from 10 to 5
   ```

3. **Lower resolution**
   Edit `src/core/orchestrator.py`:
   ```python
   self.webcam = WebcamCapture(camera_id=0, resolution=(640, 480), fps=15)
   ```

4. **Use CPU instead of GPU**
   Edit model loading in `src/core/model_manager.py`

---

### Issue: API Errors (400, 500)

**Problem:**
```
Bad Request or Internal Server Error
```

**Solution:**
1. Check logs: `tail logs/proctoring.log`
2. Verify JSON format in requests
3. Ensure session exists for protected endpoints
4. Check `.env` configuration

---

### Issue: Port Already in Use

**Problem:**
```
Address already in use (port 5000)
```

**Solution:**
```bash
# Option 1: Use different port (edit .env)
PORT=5001

# Option 2: Kill existing process
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -ti:5000 | xargs kill -9
```

---

## Performance Optimization

### For Better Performance:

1. **Use GPU**
   - Install CUDA-enabled PyTorch
   - Place heavy models on GPU

2. **Optimize Capture Rate**
   ```env
   CAPTURE_INTERVAL=10  # Increase interval = less CPU load
   ```

3. **Reduce Resolution**
   Edit `orchestrator.py`:
   ```python
   WebcamCapture(resolution=(640, 480))  # Instead of 1280x720
   ```

4. **Use Faster Models**
   - MobileNet for detection
   - Lightweight face recognition models

---

## Next Steps

1. ✅ **Verify Setup**: Run `python setup_validator.py`
2. ✅ **Start Server**: Run `python app.py`
3. ✅ **Test System**: Run `python demo_session.py`
4. ✅ **Integrate Models**: Add trained model files
5. 🔄 **Build UI**: Create web frontend
6. 🔄 **Add Database**: Persist data
7. 🔄 **Deploy**: Move to production

---

## Support

For detailed information:
- See `README.md` for full documentation
- See `ARCHITECTURE.md` for system design
- See `QUICKSTART.md` for quick reference
- Check logs in `logs/proctoring.log`

---

**You're all set! 🎉**

Start the server with: `python app.py`
