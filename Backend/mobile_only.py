import cv2
from ultralytics import YOLO
import math

# --- CONFIGURATION ---
# 'yolov8n.pt' is the standard model.
print("⏳ Loading AI Model...")
model = YOLO('yolov8n.pt')

# Classes to Detect:
# Cell Phone = 67
# Laptop (Tablet) = 63
ALLOWED_CLASSES = ['cell phone', 'laptop']

# Confidence Threshold (0.55 = 55% sure)
CONFIDENCE = 0.55

# --- MATH FILTERS (For Phones Only) ---
# We use these to reject Mice, Wallets, and Earbuds.
MIN_PHONE_AREA = 5000     # Reject tiny objects
MAX_PHONE_AREA = 150000   # Reject giant objects
MIN_PHONE_RATIO = 1.35    # Reject square objects (Mice are ~1.1, Phones are ~2.0)

def check_phone_shape(box):
    """
    Returns (True/False, Reason) based on the shape of the box.
    """
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    w = x2 - x1
    h = y2 - y1
    area = w * h
    
    # 1. Size Check
    if area < MIN_PHONE_AREA: return False, "Too Small"
    if area > MAX_PHONE_AREA: return False, "Too Big"

    # 2. Ratio Check (Long side / Short side)
    long_side = max(w, h)
    short_side = min(w, h)
    
    if short_side == 0: return False, "Error"
    ratio = round(long_side / short_side, 2)
    
    # If ratio is small (like 1.0 or 1.2), it's a square (Mouse/Wallet)
    if ratio < MIN_PHONE_RATIO:
        return False, f"Too Square ({ratio})"

    return True, "Valid"

# Start Camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)

print("🚀 DETECTOR STARTED: Looking for Phones & Tablets...")
print("Press 'q' to exit.")

while True:
    success, frame = cap.read()
    if not success:
        print("❌ Camera disconnected")
        break

    # Run YOLO detection
    # verbose=False keeps console clean
    results = model(frame, stream=True, verbose=False, conf=CONFIDENCE)

    detected_count = 0

    for r in results:
        for box in r.boxes:
            # Get Class ID and Name
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]

            # 1. CHECK IF CLASS IS ALLOWED
            if class_name in ALLOWED_CLASSES:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                is_valid_object = True
                debug_label = class_name.upper()

                # 2. APPLY MATH FILTER (ONLY FOR PHONES)
                # We skip this for 'laptop' because Tablets vary in shape
                if class_name == 'cell phone':
                    is_valid, reason = check_phone_shape(box)
                    if not is_valid:
                        is_valid_object = False
                        # Draw RED Box for Ignored Objects (Mouse/Wallet)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, f"IGNORED: {reason}", (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                # 3. DRAW VALID OBJECTS
                if is_valid_object:
                    detected_count += 1
                    # Draw GREEN Box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 4)
                    
                    # Add background for text to make it readable
                    label_size = cv2.getTextSize(debug_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    cv2.rectangle(frame, (x1, y1 - 30), (x1 + label_size[0], y1), (0, 255, 0), -1)
                    
                    cv2.putText(frame, debug_label, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # UI Status Overlay
    if detected_count > 0:
        cv2.putText(frame, f"🚫 {detected_count} DEVICES DETECTED", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    else:
        cv2.putText(frame, "✅ CLEAN", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

    cv2.imshow("Strict Mobile/Tablet Detector", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()