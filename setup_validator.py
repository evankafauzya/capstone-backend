"""
Utility functions for the proctoring system
"""
import os
from pathlib import Path


def ensure_directories():
    """Ensure all required directories exist"""
    dirs = [
        'models_data',
        'reports',
        'logs',
        'src',
        'config'
    ]
    
    for dir_name in dirs:
        Path(dir_name).mkdir(parents=True, exist_ok=True)
        print(f"✓ Directory ensured: {dir_name}")


def check_model_files():
    """Check if model files exist"""
    models_dir = 'models_data'
    
    models = {
        'face_recognition_model.pkl': 'Face Recognition',
        'face_detection_model.pth': 'Face Detection'
    }
    
    print("\nModel File Status:")
    print("-" * 50)
    
    all_exist = True
    for filename, description in models.items():
        path = os.path.join(models_dir, filename)
        exists = os.path.exists(path)
        status = "✓ Found" if exists else "✗ Missing"
        print(f"{description:.<30} {status}")
        
        if not exists:
            all_exist = False
    
    if not all_exist:
        print("\n⚠ Some model files are missing!")
        print("  System will use fallback models.")
        print("  For better performance, add the missing model files.")
    
    return all_exist


def validate_environment():
    """Validate system environment"""
    print("\nEnvironment Validation:")
    print("-" * 50)
    
    # Check Python version
    import sys
    py_version = sys.version_info
    print(f"Python Version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        print("✗ Python 3.8 or higher required!")
        return False
    else:
        print("✓ Python version OK")
    
    # Check required packages
    print("\nRequired Packages:")
    required_packages = [
        'cv2',
        'flask',
        'numpy',
        'torch',
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            return False
    
    # Check webcam
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("\n✓ Webcam detected and accessible")
            cap.release()
        else:
            print("\n⚠ Webcam not detected or not accessible")
    except Exception as e:
        print(f"\n⚠ Error checking webcam: {e}")
    
    return True


if __name__ == '__main__':
    print("=" * 50)
    print("Proctoring System - Setup Validator")
    print("=" * 50)
    
    ensure_directories()
    check_model_files()
    is_valid = validate_environment()
    
    print("\n" + "=" * 50)
    if is_valid:
        print("✓ System is ready to run!")
        print("\nStart the server with: python app.py")
    else:
        print("✗ Please fix the issues above before running.")
    print("=" * 50)
