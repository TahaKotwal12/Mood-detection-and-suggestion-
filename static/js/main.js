// Global variables
let isLive = false;
let currentEmotion = 'neutral';
let statusCheckInterval;

// Emotion icons mapping
const emotionIcons = {
    'happy': 'bi-emoji-smile',
    'sad': 'bi-emoji-frown',
    'angry': 'bi-emoji-angry',
    'neutral': 'bi-emoji-neutral',
    'fear': 'bi-emoji-dizzy',
    'surprise': 'bi-emoji-astonished',
    'disgust': 'bi-emoji-expressionless'
};

// Function to update status including emotions and suggestions
async function updateStatus() {
    try {
        const response = await fetch('/get_status');
        const data = await response.json();
        
        // Update status elements
        updateLivenessStatus(data.status);
        updateEmotionDisplay(data.emotion, data.emotion_confidence);
        updateSuggestions(data.suggestions);
        updateMetrics(data);
        
        // Update chat availability
        const sendButton = document.getElementById('sendButton');
        const userInput = document.getElementById('userInput');
        
        if (data.status.includes("Live Person Detected")) {
            isLive = true;
            sendButton.disabled = false;
            userInput.disabled = false;
        } else {
            isLive = false;
            sendButton.disabled = true;
            userInput.disabled = true;
        }
        
        // Update current emotion
        currentEmotion = data.emotion;
        
    } catch (error) {
        console.error('Error updating status:', error);
    }
}

// Function to update liveness status
function updateLivenessStatus(status) {
    const statusElement = document.getElementById('livenessStatus');
    statusElement.textContent = status;
    
    if (status.includes("Live Person Detected")) {
        statusElement.className = 'alert alert-success';
    } else if (status.includes("Blink Check Passed")) {
        statusElement.className = 'alert alert-warning';
    } else {
        statusElement.className = 'alert alert-info';
    }
}

// Function to update emotion display
function updateEmotionDisplay(emotion, confidence) {
    const emotionStatus = document.getElementById('emotionStatus');
    const icon = emotionIcons[emotion] || 'bi-emoji-neutral';
    emotionStatus.innerHTML = `
        <i class="bi ${icon}"></i> 
        ${emotion} (${confidence.toFixed(1)}%)
    `;
}

// Function to update metrics
function updateMetrics(data) {
    document.getElementById('blinkCount').textContent = data.blinks;
    document.getElementById('faceDirection').textContent = data.face_direction;
}

// Function to update suggestions
function updateSuggestions(suggestions) {
    const suggestionsContainer = document.getElementById('suggestionsList');
    suggestionsContainer.innerHTML = suggestions.map(suggestion => `
        <div class="suggestion-item">
            <i class="bi bi-lightbulb"></i>
            <span>${suggestion}</span>
        </div>
    `).join('');
}

// Function to add a message to the chat
function addMessage(message, isUser = false) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    
    // Create timestamp
    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = new Date().toLocaleTimeString();
    
    // Create message content with emotion context for AI messages
    const content = document.createElement('div');
    content.className = 'message-content';
    
    if (!isUser) {
        const emotionIcon = emotionIcons[currentEmotion] || 'bi-emoji-neutral';
        content.innerHTML = `
            <div class="emotion-context">
                <i class="bi ${emotionIcon}"></i> Responding to your ${currentEmotion} mood
            </div>
            ${message}
        `;
    } else {
        content.textContent = message;
    }
    
    // Append elements
    messageDiv.appendChild(timestamp);
    messageDiv.appendChild(content);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Function to send message to AI
async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();
    
    if (message === '') return;
    
    // Add user message to chat
    addMessage(message, true);
    userInput.value = '';
    
    try {
        const response = await fetch('/ask_gemini', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: message })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Add AI response to chat
            addMessage(data.response);
            
            // Update suggestions if they changed
            if (data.suggestions) {
                updateSuggestions(data.suggestions);
            }
        } else {
            addMessage('Sorry, there was an error processing your request.');
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, there was an error communicating with the server.');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize status updates
    statusCheckInterval = setInterval(updateStatus, 1000);
    
    // Add welcome message
    addMessage(`Welcome! I'm your emotion-aware AI assistant. I can:
    • Detect your emotional state
    • Provide mood-based suggestions
    • Offer emotional support
    • Answer your questions
    
    Please complete the liveness check to begin our conversation.`);
    
    // Input event listeners
    const userInput = document.getElementById('userInput');
    userInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            if (isLive) {
                sendMessage();
            } else {
                addMessage('Please complete the liveness check before sending messages.');
            }
        }
    });
    
    // Initially disable input
    userInput.disabled = true;
    document.getElementById('sendButton').disabled = true;
});

// Clean up interval on page unload
window.addEventListener('beforeunload', function() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
});
