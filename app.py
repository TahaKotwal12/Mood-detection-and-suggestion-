from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv
import os
from datetime import datetime
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

try:
    # Configure Gemini AI
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    logger.error(f"Error configuring Gemini AI: {str(e)}")
    model = None

app = Flask(__name__)

# Initialize camera
try:
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        logger.error("Could not open camera")
except Exception as e:
    logger.error(f"Error initializing camera: {str(e)}")
    camera = None

# Global variables for detection
blink_counter = 0
blink_threshold = 3
last_blink_time = time.time()
eye_state = True
face_direction = "center"
liveness_status = "Checking..."
last_face_direction = "center"
direction_changes = 0
last_direction_change_time = time.time()
current_activity = "neutral"
activity_confidence = 0
last_activity_time = time.time()
last_frame = None
frame_height = 100  # Fixed height for ROI comparison

# Activity-based assistance prompts
activity_suggestions = {
    "active": [
        "Channel your energy positively",
        "Take on a challenge",
        "Exercise or dance",
        "Start a project",
        "Join group activities"
    ],
    "happy": [
        "Share your joy with others",
        "Try something creative",
        "Plan something exciting",
        "Express gratitude",
        "Spread positivity"
    ],
    "neutral": [
        "Set new goals",
        "Learn something new",
        "Connect with friends",
        "Organize your space",
        "Start a new hobby"
    ],
    "calm": [
        "Practice mindfulness",
        "Read a book",
        "Listen to soothing music",
        "Take a peaceful walk",
        "Try gentle stretching"
    ]
}

def safe_cv2_operation(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

@safe_cv2_operation
def detect_blink(frame, face_cascade, eye_cascade):
    global blink_counter, last_blink_time, eye_state
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        
        if len(eyes) >= 2:
            if eye_state and time.time() - last_blink_time > 1:
                eye_state = False
                blink_counter += 1
                last_blink_time = time.time()
        else:
            eye_state = True
    
    return blink_counter

@safe_cv2_operation
def detect_face_direction(frame, face_cascade):
    global face_direction, last_face_direction, direction_changes, last_direction_change_time
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    if len(faces) > 0:
        (x, y, w, h) = faces[0]
        face_center = x + w//2
        frame_center = frame.shape[1]//2
        
        if face_center < frame_center - 50:
            new_direction = "left"
        elif face_center > frame_center + 50:
            new_direction = "right"
        else:
            new_direction = "center"
        
        if new_direction != last_face_direction and time.time() - last_direction_change_time > 1:
            direction_changes += 1
            last_direction_change_time = time.time()
            last_face_direction = new_direction
        
        face_direction = new_direction
    
    return direction_changes

@safe_cv2_operation
def detect_activity_level(frame, face_cascade):
    global current_activity, activity_confidence, last_activity_time, last_frame
    
    if time.time() - last_activity_time < 1:
        return current_activity, activity_confidence
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    if len(faces) > 0:
        (x, y, w, h) = faces[0]
        # Extract face ROI and resize to fixed height while maintaining aspect ratio
        face_roi = gray[y:y+h, x:x+w]
        aspect_ratio = w / h
        new_width = int(frame_height * aspect_ratio)
        resized_roi = cv2.resize(face_roi, (new_width, frame_height))
        
        if last_frame is not None and last_frame.shape == resized_roi.shape:
            # Calculate frame difference
            frame_diff = cv2.absdiff(last_frame, resized_roi)
            movement = np.mean(frame_diff)
            
            # Determine activity level based on movement
            if movement > 30:
                current_activity = "active"
                activity_confidence = min(movement / 50 * 100, 100)
            elif movement > 15:
                current_activity = "happy"
                activity_confidence = min(movement / 30 * 100, 100)
            elif movement > 5:
                current_activity = "neutral"
                activity_confidence = min(movement / 15 * 100, 100)
            else:
                current_activity = "calm"
                activity_confidence = min((5 - movement) / 5 * 100, 100)
        
        last_frame = resized_roi
        last_activity_time = time.time()
    
    return current_activity, activity_confidence

def generate_frames():
    if not camera or not camera.isOpened():
        logger.error("Camera is not available")
        return

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    
    while True:
        try:
            success, frame = camera.read()
            if not success:
                logger.error("Failed to read frame from camera")
                break
            
            # Detect face, eyes, and activity level
            blinks = detect_blink(frame, face_cascade, eye_cascade)
            movements = detect_face_direction(frame, face_cascade)
            activity, conf = detect_activity_level(frame, face_cascade)
            
            # Update liveness status
            global liveness_status
            if blinks >= blink_threshold and movements >= 2:
                liveness_status = "Live Person Detected!"
            elif blinks >= blink_threshold:
                liveness_status = "Blink Check Passed! Now turn your head slightly."
            else:
                liveness_status = f"Please blink naturally ({blinks}/{blink_threshold}) and turn your head slightly"
            
            # Draw status on frame
            cv2.putText(frame, f"Status: {liveness_status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Activity: {activity} ({conf:.1f}%)", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Face Direction: {face_direction}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            logger.error(f"Error in generate_frames: {str(e)}")
            break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    if not camera or not camera.isOpened():
        return "Camera not available", 503
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_status')
def get_status():
    try:
        suggestions = activity_suggestions.get(current_activity, activity_suggestions['neutral'])
        return jsonify({
            'status': liveness_status,
            'blinks': blink_counter,
            'face_direction': face_direction,
            'activity': current_activity,
            'activity_confidence': activity_confidence,
            'suggestions': suggestions
        })
    except Exception as e:
        logger.error(f"Error in get_status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/ask_gemini', methods=['POST'])
def ask_gemini():
    if not model:
        return jsonify({'error': 'Gemini AI not configured'}), 503

    try:
        data = request.json
        question = data.get('question', '')
        
        context = (
            f"Current user status: {liveness_status}\n"
            f"Activity level: {current_activity} (confidence: {activity_confidence:.1f}%)\n"
            f"Suggested activities for this state:\n"
            f"{', '.join(activity_suggestions[current_activity])}\n\n"
        )
        
        enhanced_prompt = (
            f"{context}\n"
            f"Based on the user's current activity level and their question: {question}\n"
            "Please provide a supportive response that:\n"
            "1. Acknowledges their current state\n"
            "2. Addresses their question\n"
            "3. Suggests relevant activities based on their energy level\n"
            "4. Offers encouragement and support\n"
            "Make the response conversational but professional."
        )
        
        response = model.generate_content(enhanced_prompt)
        
        return jsonify({
            'success': True,
            'response': response.text,
            'activity': current_activity,
            'suggestions': activity_suggestions[current_activity]
        })
    except Exception as e:
        logger.error(f"Error in ask_gemini: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Unhandled error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
