# Activity-Aware AI Assistant with Liveness Detection

This Flask application combines real-time activity level detection, liveness verification, and Gemini AI to provide context-aware assistance and support.

## Features

- Real-time activity level detection (active, happy, neutral, calm)
- Liveness detection through blink counting and head movement
- Activity-based suggestions
- Context-aware AI responses using Google's Gemini
- Clean and responsive UI with real-time updates

## Prerequisites

- Python 3.8 or higher
- Webcam
- Google Gemini API key

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd Flask Project
```

2. Create a virtual environment and activate it:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
   - Copy `.env.example` to `.env`
   - Add your configuration:
```
GOOGLE_API_KEY=your_gemini_api_key_here
TF_ENABLE_ONEDNN_OPTS=0
TF_CPP_MIN_LOG_LEVEL=2
```

## Environment Variables

- `GOOGLE_API_KEY`: Your Google Gemini API key
- `TF_ENABLE_ONEDNN_OPTS`: Controls oneDNN optimization (set to 0 to disable)
- `TF_CPP_MIN_LOG_LEVEL`: Controls TensorFlow logging level (2 for info messages)

## Running the Application

1. Make sure your virtual environment is activated
2. Run the Flask application:
```bash
python app.py
```
3. Open your web browser and navigate to `http://localhost:5000`

## Usage

### Liveness Detection
- The system will verify your presence through:
  - Natural eye blinks (requires 3 blinks)
  - Head movement detection (left/right)

### Activity Level Detection
- Real-time activity analysis with confidence scoring
- Activity states:
  - Active: High movement/energy level
  - Happy: Moderate movement
  - Neutral: Light movement
  - Calm: Minimal movement

### Activity-Based Assistance
- Receives personalized activity suggestions based on detected state
- AI responses tailored to your activity level
- Real-time context tracking

### Chat Interface
- Interactive chat with context-aware AI
- Visual feedback for activity state
- Timestamp-enabled message history

## Project Structure

```
Flask Project/
├── app.py              # Main Flask application with activity detection
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── static/
│   ├── css/
│   │   └── style.css  # Custom styles
│   └── js/
│       └── main.js    # Client-side JavaScript
└── templates/
    └── index.html     # Main application template
```

## Security Notes

- Never commit your `.env` file containing your API key
- Keep your API keys secure and rotate them regularly
- Ensure your webcam access is properly secured
- Activity data is processed locally and not stored

## Technical Details

- Uses OpenCV for:
  - Face detection
  - Eye detection
  - Movement analysis
  - Liveness verification
- Flask for backend server
- Real-time updates using JavaScript
- Gemini AI for intelligent responses

## How Activity Detection Works

The system analyzes movement patterns to determine activity levels:
- High movement indicates active state
- Moderate movement suggests happy state
- Light movement indicates neutral state
- Minimal movement suggests calm state

This provides a non-invasive way to understand user state and provide relevant assistance.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
