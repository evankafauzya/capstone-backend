"""
Demo script to test the proctoring system
Simulates a complete proctoring session flow
"""
import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:5000/api/proctoring"


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_complete_session():
    """Run a complete proctoring session demo"""
    
    print_section("PROCTORING SYSTEM - DEMO")
    
    try:
        # 1. Health Check
        print_section("1. Health Check")
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        # 2. System Info
        print_section("2. System Information")
        response = requests.get(f"{BASE_URL}/system-info")
        print(json.dumps(response.json(), indent=2))
        
        # 3. Get Configuration
        print_section("3. Current Configuration")
        response = requests.get(f"{BASE_URL}/configuration")
        config = response.json()
        print(json.dumps(config, indent=2))
        
        # 4. Start Session
        print_section("4. Starting Proctoring Session")
        session_data = {
            "session_id": f"demo_session_{int(time.time())}",
            "user_id": "demo_user_001"
        }
        response = requests.post(f"{BASE_URL}/session/start", json=session_data)
        print(f"Status: {response.status_code}")
        start_result = response.json()
        print(json.dumps(start_result, indent=2))
        
        if response.status_code != 200:
            print("Failed to start session!")
            return
        
        session_id = start_result.get("session_id")
        
        # 5. Wait for initial verification
        print_section("5. Waiting for Initial Verification")
        print("(System is capturing frames and verifying user identity...)")
        time.sleep(5)
        
        # 6. Check Session Status
        print_section("6. Session Status After Verification")
        response = requests.get(f"{BASE_URL}/session/status")
        print(json.dumps(response.json(), indent=2))
        
        # 7. Get Face Detection Stats
        print_section("7. Face Detection Statistics")
        response = requests.get(f"{BASE_URL}/face-detection/stats")
        print(json.dumps(response.json(), indent=2))
        
        # 8. Get Eye Tracking Stats
        print_section("8. Eye Tracking Statistics")
        response = requests.get(f"{BASE_URL}/eye-tracking/stats")
        print(json.dumps(response.json(), indent=2))
        
        # 9. Get Current Frame
        print_section("9. Retrieving Current Frame")
        response = requests.get(f"{BASE_URL}/video/frame")
        if response.status_code == 200:
            frame_size = len(response.content)
            print(f"✓ Frame retrieved successfully")
            print(f"  Frame size: {frame_size} bytes")
            
            # Save frame to file
            with open("current_frame.jpg", "wb") as f:
                f.write(response.content)
            print(f"  Frame saved to: current_frame.jpg")
        else:
            print(f"✗ Failed to get frame: {response.status_code}")
        
        # 10. Simulate some session time
        print_section("10. Session Running")
        print("(Monitoring for 15 seconds...)")
        for i in range(15):
            time.sleep(1)
            print(f"  [{i+1}/15] Session active...", end='\r')
        print("\n  ✓ Monitoring complete")
        
        # 11. Get Warnings
        print_section("11. Session Warnings")
        response = requests.get(f"{BASE_URL}/warnings?limit=10")
        warnings_data = response.json()
        print(f"Total Warnings: {warnings_data.get('total_warnings', 0)}")
        warnings = warnings_data.get('warnings', [])
        if warnings:
            print("Recent Warnings:")
            for warning in warnings[-5:]:
                timestamp = warning.get('timestamp')
                if timestamp:
                    dt = datetime.fromtimestamp(timestamp)
                    time_str = dt.strftime('%H:%M:%S')
                else:
                    time_str = 'N/A'
                
                print(f"  [{time_str}] [{warning.get('level', 'unknown').upper()}] "
                      f"{warning.get('title', 'Unknown')}")
        else:
            print("  No warnings recorded")
        
        # 12. Get Session Report Before Stopping
        print_section("12. Current Session Report (Before Stopping)")
        response = requests.get(f"{BASE_URL}/session/report")
        report = response.json()
        
        session_info = report.get('session_info', {})
        stats = report.get('statistics', {})
        
        print(f"Session ID: {session_info.get('session_id', 'N/A')}")
        print(f"User ID: {session_info.get('user_id', 'N/A')}")
        print(f"Status: {session_info.get('status', 'N/A')}")
        print(f"Initial Verified: {session_info.get('initial_verified', False)}")
        print(f"\nStatistics:")
        print(f"  Total Events: {stats.get('total_events', 0)}")
        print(f"  Total Warnings: {stats.get('total_warnings', 0)}")
        print(f"  Face Detections: {stats.get('total_face_detections', 0)}")
        print(f"  Valid Detections: {stats.get('valid_face_detections', 0)}")
        print(f"  Eye Tracking Records: {stats.get('total_eye_tracking_records', 0)}")
        print(f"  Verifications: {stats.get('total_verifications', 0)}")
        
        # 13. Stop Session
        print_section("13. Stopping Session")
        response = requests.post(f"{BASE_URL}/session/stop")
        print(f"Status: {response.status_code}")
        stop_result = response.json()
        
        if 'reports' in stop_result:
            print("Reports Generated:")
            for report_type, path in stop_result.get('reports', {}).items():
                print(f"  - {report_type}: {path}")
        
        print("\n✓ Session completed successfully!")
        
        # 14. Display Final Report
        print_section("14. Final Report Summary")
        summary = stop_result.get('session_summary', {})
        print(json.dumps(summary, indent=2))
        
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Cannot connect to server!")
        print("  Make sure the Flask server is running on http://localhost:5000")
        print("\n  To start the server, run:")
        print("    python app.py")
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Proctoring System - Complete Session Demo".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    
    print("\n⚠  Make sure the Flask server is running!")
    print("    Run this first: python app.py")
    print("\n⏳ Starting demo in 3 seconds...\n")
    
    time.sleep(3)
    
    demo_complete_session()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60 + "\n")
