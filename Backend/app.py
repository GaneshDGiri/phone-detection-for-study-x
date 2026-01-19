from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
import cv2
from ultralytics import YOLO
import time
import os
import winsound
from datetime import datetime
import database
from twilio.rest import Client

# --- SAFE AUDIO IMPORT (Prevents Crash on Python 3.14) ---
try:
    from pydub import AudioSegment
    AUDIO_CONVERTER_AVAILABLE = True
except ImportError:
    AUDIO_CONVERTER_AVAILABLE = False
    print("⚠️ WARNING: Audio conversion disabled. Upload .WAV files only.")

app = Flask(__name__)
CORS(app)

# --- TWILIO CREDENTIALS ---
TWILIO_SID = "ORb5ea4037e53feb172e6924f807303a78"   
TWILIO_TOKEN = "6d17b36edba746f2c55e06ae919838db" 
TWILIO_FROM_NUM = "+919657838159"

# Initialize Database & AI
database.init_db()
model = YOLO('yolov8n.pt')

# --- CONFIGURATION ---
# 67 = Cell Phone, 63 = Laptop (Tablets are often detected as laptops)
ALLOWED_CLASSES = ["cell phone", "laptop"] 
CONFIDENCE_LEVEL = 0.55 

# Math Filters (Only applied to Phones to reject Mice/Wallets)
MIN_PHONE_AREA = 5000    
MAX_PHONE_AREA = 150000  
MIN_PHONE_ASPECT_RATIO = 1.35 

# Camera Setup
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    camera = cv2.VideoCapture(1)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILE = os.path.join(BASE_DIR, "alert.wav")
RECORDING_DIR = os.path.join(BASE_DIR, "recordings")
if not os.path.exists(RECORDING_DIR): os.makedirs(RECORDING_DIR)

# --- GLOBAL STATE ---
last_alert_time = 0
COOLDOWN = 15
summary_report_sent = False 

# Recording State
video_writer = None
is_recording = False
current_recording_file = None
is_manual_pause = False  # Allows user to pause recording while AI keeps running

def play_alert():
    if os.path.exists(AUDIO_FILE):
        try: winsound.PlaySound(AUDIO_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except: winsound.Beep(1000, 200)

def send_sms(to, body):
    try:
        if not to.startswith('+'): to = "+91" + to.strip()
        Client(TWILIO_SID, TWILIO_TOKEN).messages.create(body=body, from_=TWILIO_FROM_NUM, to=to)
        print(f"✅ SMS SENT: {body}")
    except Exception as e: print(f"❌ SMS FAILED: {e}")

def process_uploaded_audio(path):
    if AUDIO_CONVERTER_AVAILABLE:
        try:
            AudioSegment.from_file(path).export(AUDIO_FILE, format="wav")
            return True, "Converted to WAV."
        except Exception as e: return False, str(e)
    else:
        if path.lower().endswith(".wav"):
            if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)
            os.rename(path, AUDIO_FILE)
            return True, "WAV updated."
        return False, "Only .WAV allowed."

def check_phone_shape(box):
    """Math checks to reject Mice/Wallets detected as phones"""
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    w, h = x2 - x1, y2 - y1
    area = w * h
    
    if area < MIN_PHONE_AREA: return False, "Too Small"
    if area > MAX_PHONE_AREA: return False, "Too Big"
    
    short = min(w, h)
    if short == 0: return False, "Error"
    ratio = round(max(w, h) / short, 2)
    
    if ratio < MIN_PHONE_ASPECT_RATIO: return False, f"Too Square ({ratio})"
    return True, "Valid"

def generate_frames():
    global video_writer, is_recording, current_recording_file, last_alert_time, summary_report_sent
    
    while True:
        success, frame = camera.read()
        if not success:
            camera.open(0)
            continue
        
        settings = database.get_settings()
        now_time = datetime.now().strftime("%H:%M")
        is_study_time = settings['start_time'] <= now_time <= settings['end_time']
        
        # --- RECORDING LOGIC ---
        # Record only if: Study Time AND Not Manually Paused
        if is_study_time and not is_manual_pause:
            if not is_recording:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = os.path.join(RECORDING_DIR, f"Study_Session_{timestamp}.avi")
                current_recording_file = filename
                
                fourcc = cv2.VideoWriter_fourcc(*'MJPG') 
                video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
                is_recording = True
                print(f"🎥 Started Recording: {filename}")
            
            if video_writer is not None:
                video_writer.write(cv2.resize(frame, (640, 480)))
        else:
            if is_recording:
                if video_writer: video_writer.release()
                video_writer = None
                is_recording = False
                current_recording_file = None
                print("⏹️ Stopped Recording.")

        # --- SMS REPORT ---
        if now_time > settings['end_time'] and not summary_report_sent:
            if settings['notify_enabled'] and settings['parent_phone']:
                send_sms(settings['parent_phone'], f"🏁 Session Done! Distractions: {database.get_today_count()}")
            summary_report_sent = True
        if is_study_time: summary_report_sent = False

        # --- AI DETECTION ---
        detected = False
        if is_study_time:
            # Detect everything first, then filter
            results = model(frame, verbose=False, stream=True, conf=0.55, imgsz=640)
            
            for r in results:
                for box in r.boxes:
                    cls_name = model.names[int(box.cls[0])]
                    
                    if cls_name in ALLOWED_CLASSES:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        valid = True
                        label = cls_name.upper()
                        
                        # Apply Math Filter ONLY to Phones (Tablets vary too much)
                        if cls_name == 'cell phone':
                            valid, reason = check_phone_shape(box)
                            if not valid:
                                # Show Ignored Object (Red Box)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0,0,255), 2)
                                cv2.putText(frame, f"IGNORED: {reason}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

                        if valid:
                            detected = True
                            # Show Valid Object (Green Box)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 4)
                            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            if detected:
                if time.time() - last_alert_time > COOLDOWN:
                    database.log_detection()
                    play_alert()
                    last_alert_time = time.time()
                cv2.putText(frame, "🚫 DETECTED!", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
            
            # Status Text
            status_text = "PAUSED (Manual)" if is_manual_pause else "REC ● ACTIVE"
            color = (0, 255, 255) if is_manual_pause else (0, 0, 255)
            cv2.putText(frame, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            cv2.putText(frame, "FREE TIME", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- RECORDING & CONTROL ROUTES ---
@app.route('/api/recordings', methods=['GET'])
def list_recordings():
    if not os.path.exists(RECORDING_DIR): return jsonify([])
    files = sorted([f for f in os.listdir(RECORDING_DIR) if f.endswith('.avi')], reverse=True)
    return jsonify(files)

@app.route('/api/recordings/<filename>', methods=['GET'])
def serve_recording(filename): return send_from_directory(RECORDING_DIR, filename)

@app.route('/api/recordings/<filename>', methods=['DELETE'])
def delete_recording(filename):
    global video_writer, is_recording, current_recording_file, is_manual_pause
    try:
        file_path = os.path.join(RECORDING_DIR, filename)
        
        # SMART DELETE: If deleting the active file, stop it first
        if current_recording_file and filename in current_recording_file:
            print(f"⚠️ Force stopping active recording to delete: {filename}")
            if video_writer: video_writer.release()
            video_writer = None
            is_recording = False
            current_recording_file = None
            is_manual_pause = True # Pause system
            time.sleep(0.5) # Release lock

        if os.path.exists(file_path):
            os.remove(file_path)
            # Return "paused": True so frontend knows to update the Pause button
            return jsonify({"status": "deleted", "paused": True})
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recording/toggle', methods=['POST'])
def toggle_recording():
    global is_manual_pause
    is_manual_pause = not is_manual_pause
    return jsonify({"is_paused": is_manual_pause})

@app.route('/api/recording/status', methods=['GET'])
def get_recording_status():
    return jsonify({"is_paused": is_manual_pause, "is_recording": is_recording})

# --- OTHER ROUTES ---
@app.route('/api/upload_audio', methods=['POST'])
def upload_audio():
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']
    temp_path = os.path.join(BASE_DIR, "temp_audio.wav")
    file.save(temp_path)
    success, msg = process_uploaded_audio(temp_path)
    if os.path.exists(temp_path) and temp_path != AUDIO_FILE: os.remove(temp_path)
    return jsonify({"status": msg}) if success else (jsonify({"error": msg}), 500)

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        database.update_settings(request.json)
        return jsonify({"status": "saved"})
    return jsonify(database.get_settings())

@app.route('/api/history')
def handle_history(): return jsonify(database.get_history())

if __name__ == '__main__':
    # Debug Mode ON to see errors
    app.run(host='0.0.0.0', port=5000, debug=True)