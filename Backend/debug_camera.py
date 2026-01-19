import cv2

print("🔍 SCANNING CAMERAS...")

def test_camera(index):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        print(f"✅ Camera found at Index {index}!")
        ret, frame = cap.read()
        if ret:
            print(f"   - Frame captured successfully! Resolution: {frame.shape}")
            return True
        else:
            print(f"   - Camera opened, but returned blank frame.")
    else:
        print(f"❌ No camera at Index {index}.")
    return False

# Test Index 0, 1, and 2
for i in range(3):
    test_camera(i)

print("\n👉 If you found a working index (e.g., Index 1), update 'app.py' with that number.")