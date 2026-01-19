import cv2
import os
import time
import winsound

print("--- 🔍 STARTING DIAGNOSTIC TEST ---")

# 1. TEST AUDIO
print("\n[1/3] Testing Audio...")
audio_path = "alert.wav"
if os.path.exists(audio_path):
    print(f"✅ Audio file found: {audio_path}")
    try:
        print("   Playing sound... (Listen for it)")
        winsound.PlaySound(audio_path, winsound.SND_FILENAME)
        print("✅ Audio driver is working.")
    except Exception as e:
        print(f"❌ Audio failed: {e}")
else:
    print("❌ 'alert.wav' is MISSING! Run the setup script again.")

# 2. TEST CAMERA
print("\n[2/3] Testing Camera...")
cap = cv2.VideoCapture(0) # Try 0 first, then 1 if this fails
if not cap.isOpened():
    print("❌ Camera Index 0 failed. Trying Index 1...")
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("❌ CRITICAL ERROR: No Camera found!")
    else:
        print("✅ Camera found at Index 1.")
else:
    print("✅ Camera found at Index 0.")

ret, frame = cap.read()
if ret:
    print(f"✅ Frame captured successfully. Resolution: {frame.shape}")
    cv2.imshow("TEST CAMERA (Press Q to close)", frame)
    cv2.waitKey(3000)
    cv2.destroyAllWindows()
else:
    print("❌ Camera opened, but failed to read frame (Black screen?).")
cap.release()

# 3. TEST AI MODEL
print("\n[3/3] Testing AI Model...")
try:
    from ultralytics import YOLO
    print("   Loading YOLO (This might take a moment)...")
    model = YOLO('yolov8n.pt')
    print("✅ Model loaded successfully.")
except Exception as e:
    print(f"❌ AI Model failed: {e}")

print("\n--- 🏁 TEST COMPLETE ---")