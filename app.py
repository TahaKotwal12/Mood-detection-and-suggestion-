from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import time
import logging
import mediapipe as mp
import json
from collections import deque

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

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Initialize camera
try:
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        logger.error("Could not open camera")
except Exception as e:
    logger.error(f"Error initializing camera: {str(e)}")
    camera = None

# Emotion-specific suggestions
emotion_suggestions = {
    'happy': [
        "🌟 Share your joy with others!",
        "🎵 Create a happy playlist",
        "📸 Capture this moment",
        "🎨 Channel creativity",
        "🤝 Connect with friends"
    ],
    'sad': [
        "🧘‍♂️ Try deep breathing",
        "🎵 Listen to uplifting music",
        "🌳 Take a nature walk",
        "📞 Talk to a friend",
        "📝 Journal your feelings"
    ],
    'angry': [
        "🧘‍♂️ Practice meditation",
        "💪 Exercise to release tension",
        "🎵 Listen to calming music",
        "✍️ Write out your thoughts",
        "🌊 Try deep breathing"
    ],
    'surprised': [
        "📝 Write down what surprised you",
        "🤔 Reflect on the moment",
        "💭 Share the experience",
        "🎯 Channel the energy",
        "📸 Document the moment"
    ],
    'neutral': [
        "🎯 Set a new goal",
        "📚 Learn something new",
        "🌱 Start a project",
        "💪 Do some exercise",
        "🧘‍♂️ Try meditation"
    ],
    'fearful': [
        "🧘‍♂️ Practice grounding exercises",
        "💕 Talk to someone you trust",
        "📝 List your concerns",
        "🎵 Listen to soothing music",
        "🌈 Focus on positive thoughts"
    ]
}

class EmotionDetector:
    def __init__(self):
        self.emotions = ['happy', 'sad', 'angry', 'surprised', 'neutral', 'fearful']
        self.last_emotion = 'neutral'
        self.emotion_confidence = 0
        self.emotion_history = deque(maxlen=10)
        self.last_update = time.time()
        
    def detect_emotion(self, landmarks):
        # Extract facial features
        mouth_corners = [landmarks[61], landmarks[291]]  # Mouth corners
        eyebrows = [landmarks[66], landmarks[296]]  # Eyebrows
        eyes = [landmarks[159], landmarks[386]]  # Eyes
        
        # Calculate facial metrics
        mouth_width = abs(mouth_corners[0].x - mouth_corners[1].x)
        mouth_height = abs(mouth_corners[0].y - mouth_corners[1].y)
        eyebrow_height = (eyebrows[0].y + eyebrows[1].y) / 2
        eye_height = (eyes[0].y + eyes[1].y) / 2
        
        # Emotion detection logic
        smile_ratio = mouth_width / mouth_height if mouth_height > 0 else 0
        eyebrow_raise = eyebrow_height - eye_height
        
        # Determine emotion based on facial features
        if smile_ratio > 4.0:
            emotion = 'happy'
            confidence = min(100, smile_ratio * 20)
        elif eyebrow_raise < -0.02:
            emotion = 'sad'
            confidence = min(100, abs(eyebrow_raise) * 1000)
        elif eyebrow_raise > 0.03:
            emotion = 'surprised'
            confidence = min(100, eyebrow_raise * 1000)
        elif mouth_height > 0.1:
            emotion = 'angry'
            confidence = min(100, mouth_height * 500)
        elif abs(mouth_corners[0].y - mouth_corners[1].y) > 0.02:
            emotion = 'fearful'
            confidence = min(100, abs(mouth_corners[0].y - mouth_corners[1].y) * 1000)
        else:
            emotion = 'neutral'
            confidence = 70
        
        # Smooth emotion transitions
        if time.time() - self.last_update > 0.5:
            self.emotion_history.append(emotion)
            most_common = max(set(self.emotion_history), key=self.emotion_history.count)
            
            if most_common == self.last_emotion:
                self.emotion_confidence = min(100, self.emotion_confidence + 10)
            else:
                self.last_emotion = most_common
                self.emotion_confidence = confidence
            
            self.last_update = time.time()
        
        return self.last_emotion, self.emotion_confidence

emotion_detector = EmotionDetector()

def process_frame(frame):
    # Convert to RGB for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    emotion = 'neutral'
    confidence = 0
    
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark
        emotion, confidence = emotion_detector.detect_emotion(landmarks)
        
        # Draw facial landmarks
        h, w, _ = frame.shape
        for idx, lm in enumerate(landmarks):
            pos = (int(lm.x * w), int(lm.y * h))
            cv2.circle(frame, pos, 1, (0, 255, 0), -1)
        
        # Add emotion overlay
        emotion_text = f"Emotion: {emotion.title()} ({confidence:.0f}%)"
        cv2.putText(frame, emotion_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return frame, emotion, confidence

def generate_frames():
    if not camera or not camera.isOpened():
        logger.error("Camera is not available")
        return

    while True:
        try:
            success, frame = camera.read()
            if not success:
                logger.error("Failed to read frame from camera")
                break
            
            processed_frame, emotion, confidence = process_frame(frame)
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
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
        frame = None
        if camera and camera.isOpened():
            success, frame = camera.read()
            if success:
                _, emotion, confidence = process_frame(frame)
            else:
                emotion, confidence = 'neutral', 0
        else:
            emotion, confidence = 'neutral', 0
        
        suggestions = emotion_suggestions.get(emotion, emotion_suggestions['neutral'])
        
        return jsonify({
            'emotion': emotion,
            'confidence': confidence,
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
        
        # Get current emotion and suggestions
        frame = None
        if camera and camera.isOpened():
            success, frame = camera.read()
            if success:
                _, emotion, confidence = process_frame(frame)
            else:
                emotion, confidence = 'neutral', 0
        else:
            emotion, confidence = 'neutral', 0
        
        suggestions = emotion_suggestions.get(emotion, emotion_suggestions['neutral'])
        
        # Create context with emotional state
        context = (
            f"Current emotional state: {emotion} (confidence: {confidence:.0f}%)\n\n"
            f"Based on your current emotional state, here are some suggestions:\n"
            f"{', '.join(suggestions)}\n\n"
            f"User question: {question}\n\n"
            "Please provide a response that:\n"
            "1. Acknowledges and validates their current emotion\n"
            "2. Addresses their question with empathy\n"
            "3. Offers specific suggestions based on their emotional state\n"
            "4. Includes encouraging and supportive language\n"
            "5. Uses appropriate emojis to enhance engagement\n"
            "Keep the response warm and supportive."
        )
        
        response = model.generate_content(context)
        
        return jsonify({
            'success': True,
            'response': response.text,
            'emotion': emotion,
            'confidence': confidence,
            'suggestions': suggestions
        })
    except Exception as e:
        logger.error(f"Error in ask_gemini: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
