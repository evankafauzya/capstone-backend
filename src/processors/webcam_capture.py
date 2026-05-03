"""
Webcam Capture Module
Handles webcam video capture and frame processing
"""
import logging
import cv2
import numpy as np
from typing import Optional, Dict
from threading import Thread, Lock
from queue import Queue
import time

logger = logging.getLogger(__name__)


class WebcamCapture:
    """Handles webcam capture and frame streaming"""
    
    def __init__(self, camera_id: int = 0, resolution: tuple = (1280, 720), fps: int = 30):
        """
        Initialize webcam capture
        
        Args:
            camera_id: Camera device ID (default: 0)
            resolution: Output resolution (width, height)
            fps: Frames per second
        """
        self.camera_id = camera_id
        self.resolution = resolution
        self.fps = fps
        self.frame_interval = 1.0 / fps
        
        self.cap = None
        self.is_running = False
        self.current_frame = None
        self.frame_lock = Lock()
        self.frame_queue = Queue(maxsize=10)
        self.capture_thread = None
        
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Initialize camera with desired settings"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Verify camera is opened
            if not self.cap.isOpened():
                raise RuntimeError("Failed to open camera")
            
            logger.info(f"Camera initialized (ID: {self.camera_id}, Resolution: {self.resolution})")
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            raise
    
    def start(self):
        """Start capturing frames"""
        if self.is_running:
            logger.warning("Capture already running")
            return
        
        self.is_running = True
        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info("Webcam capture started")
    
    def stop(self):
        """Stop capturing frames"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=5)
        
        if self.cap:
            self.cap.release()
        
        logger.info("Webcam capture stopped")
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        last_capture_time = time.time()
        
        while self.is_running:
            try:
                current_time = time.time()
                time_since_last = current_time - last_capture_time
                
                if time_since_last >= self.frame_interval:
                    ret, frame = self.cap.read()
                    
                    if ret and frame is not None:
                        with self.frame_lock:
                            self.current_frame = frame.copy()
                        
                        # Try to add to queue without blocking
                        try:
                            self.frame_queue.put_nowait(frame.copy())
                        except:
                            # Queue is full, discard oldest frame
                            try:
                                self.frame_queue.get_nowait()
                                self.frame_queue.put_nowait(frame.copy())
                            except:
                                pass
                        
                        last_capture_time = current_time
                    else:
                        logger.warning("Failed to capture frame")
                        time.sleep(0.01)
                else:
                    time.sleep(0.001)
            
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get current frame
        
        Returns:
            Frame or None if no frame available
        """
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def get_frame_nowait(self) -> Optional[np.ndarray]:
        """
        Get frame from queue without blocking
        
        Returns:
            Frame or None if no frame available
        """
        try:
            return self.frame_queue.get_nowait()
        except:
            return None
    
    def get_camera_info(self) -> Dict:
        """Get camera information"""
        if self.cap is None:
            return {"error": "Camera not initialized"}
        
        try:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            backend = int(self.cap.get(cv2.CAP_PROP_BACKEND))
            
            return {
                "camera_id": self.camera_id,
                "resolution": (width, height),
                "fps": fps,
                "backend": backend,
                "is_running": self.is_running
            }
        except Exception as e:
            logger.error(f"Error getting camera info: {e}")
            return {"error": str(e)}
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.is_running:
            self.stop()
