"""
Script to verify all required packages are installed
and provide installation help if needed
"""
import sys
import subprocess


def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True, None
    except ImportError as e:
        return False, str(e)


def main():
    print("\n" + "=" * 70)
    print(" " * 15 + "PROCTORING SYSTEM - DEPENDENCY CHECK")
    print("=" * 70 + "\n")
    
    packages = {
        'flask': 'flask',
        'Flask-CORS': 'flask_cors',
        'opencv-python': 'cv2',
        'numpy': 'numpy',
        'torch': 'torch',
        'torchvision': 'torchvision',
        'mediapipe': 'mediapipe',
        'scipy': 'scipy',
        'scikit-learn': 'sklearn',
        'Pillow': 'PIL',
        'reportlab': 'reportlab',
        'python-dotenv': 'dotenv',
        'requests': 'requests',
    }
    
    print("Checking installed packages...\n")
    
    missing = []
    installed = []
    
    for package, import_name in packages.items():
        is_installed, error = check_package(package, import_name)
        
        if is_installed:
            installed.append(package)
            status = "✓ OK"
            print(f"  {package:.<40} {status}")
        else:
            missing.append(package)
            status = "✗ MISSING"
            print(f"  {package:.<40} {status}")
    
    print("\n" + "-" * 70)
    print(f"Installed: {len(installed)}/{len(packages)}")
    print("-" * 70 + "\n")
    
    if missing:
        print("❌ Missing packages:")
        for pkg in missing:
            print(f"   - {pkg}")
        
        print("\n💡 To install missing packages, run:")
        print("   pip install -r requirements.txt")
        print("\n   Or install individually:")
        for pkg in missing:
            print(f"   pip install {pkg}")
        
        return False
    else:
        print("✅ All required packages are installed!")
        print("\n🚀 You can now run:")
        print("   python app.py")
        return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
