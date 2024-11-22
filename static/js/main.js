// Global variables
let isLive = false;
let currentEmotion = 'neutral';
let statusCheckInterval;
let moodChart = null;

// Emotion configuration
const emotionConfig = {
    'happy': {
        icon: 'bi-emoji-smile-fill',
        color: '#ffd93d',
        animation: 'pulse-animation'
    },
    'sad': {
        icon: 'bi-emoji-frown-fill',
        color: '#6c757d',
        animation: 'fade-animation'
    },
    'angry': {
        icon: 'bi-emoji-angry-fill',
        color: '#ff6b6b',
        animation: 'shake-animation'
    },
    'surprised': {
        icon: 'bi-emoji-surprise-fill',
        color: '#4ecdc4',
        animation: 'pop-animation'
    },
    'neutral': {
        icon: 'bi-emoji-neutral-fill',
        color: '#4895ef',
        animation: ''
    },
    'fearful': {
        icon: 'bi-emoji-dizzy-fill',
        color: '#845ef7',
        animation: 'shake-animation'
    }
};

// Initialize mood chart
function initMoodChart() {
    const ctx = document.getElementById('moodChart').getContext('2d');
    moodChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Emotion Confidence',
                data: [],
                borderColor: '#4361ee',
                backgroundColor: 'rgba(67, 97, 238, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: value => `${value}%`
                    }
                }
            },
            animation: {
                duration: 750,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Update mood chart
function updateMoodChart(emotion, confidence) {
    const timeLabel = new Date().toLocaleTimeString();
    
    if (moodChart.data.labels.length > 20) {
        moodChart.data.labels.shift();
        moodChart.data.datasets[0].data.shift();
    }
    
    moodChart.data.labels.push(timeLabel);
    moodChart.data.datasets[0].data.push(confidence);
    moodChart.update();
}

// Function to update status
async function updateStatus() {
    try {
        const response = await fetch('/get_status');
        const data = await response.json();
        
        // Update emotion display
        updateEmotionDisplay(data.emotion, data.confidence);
        
        // Update suggestions
        updateSuggestions(data.suggestions);
        
        // Update mood chart
        updateMoodChart(data.emotion, data.confidence);
        
        // Store current emotion for chat context
        currentEmotion = data.emotion;
        
    } catch (error) {
        console.error('Error updating status:', error);
    }
}

// Function to update emotion display
function updateEmotionDisplay(emotion, confidence) {
    const emotionStatus = document.getElementById('currentMood');
    const config = emotionConfig[emotion] || emotionConfig.neutral;
    
    // Update emotion text and icon
    emotionStatus.innerHTML = `
        <i class="bi ${config.icon}"></i> 
        ${emotion.charAt(0).toUpperCase() + emotion.slice(1)} (${confidence.toFixed(1)}%)
    `;
    
    // Update emotion styling
    emotionStatus.style.color = config.color;
    
    // Apply animation
    emotionStatus.classList.remove('pulse-animation', 'fade-animation', 'shake-animation', 'pop-animation');
    if (config.animation) {
        emotionStatus.classList.add(config.animation);
    }
    
    // Update emotion badge
    const emotionBadge = document.getElementById('emotionBadge');
    emotionBadge.className = `emotion-badge ${emotion}`;
    emotionBadge.innerHTML = `<i class="bi ${config.icon}"></i> ${emotion.charAt(0).toUpperCase() + emotion.slice(1)}`;
}

// Function to update suggestions with animations
function updateSuggestions(suggestions) {
    const container = document.getElementById('suggestionsList');
    container.innerHTML = '';
    
    suggestions.forEach((suggestion, index) => {
        const card = document.createElement('div');
        card.className = 'suggestion-card';
        card.style.animationDelay = `${index * 0.1}s`;
        
        const [emoji, text] = suggestion.split(' ');
        
        card.innerHTML = `
            <div class="suggestion-icon">
                ${emoji}
            </div>
            <div class="suggestion-text">
                ${text}
            </div>
        `;
        
        container.appendChild(card);
    });
}

// Function to add a message to the chat
function addMessage(message, isUser = false) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    
    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = new Date().toLocaleTimeString();
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    if (!isUser) {
        const config = emotionConfig[currentEmotion];
        content.innerHTML = `
            <div class="emotion-context">
                <i class="bi ${config.icon}" style="color: ${config.color}"></i> 
                Responding to your ${currentEmotion} mood
            </div>
            ${message}
        `;
    } else {
        content.textContent = message;
    }
    
    messageDiv.appendChild(timestamp);
    messageDiv.appendChild(content);
    chatContainer.appendChild(messageDiv);
    
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

// Function to send message to AI
async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();
    
    if (message === '') return;
    
    const sendButton = document.getElementById('sendButton');
    userInput.disabled = true;
    sendButton.disabled = true;
    
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
            addMessage(data.response);
            if (data.suggestions) {
                updateSuggestions(data.suggestions);
            }
        } else {
            addMessage('Sorry, there was an error processing your request.');
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, there was an error communicating with the server.');
    } finally {
        userInput.disabled = false;
        sendButton.disabled = false;
        userInput.focus();
    }
}

// Function to show welcome message
function showWelcomeMessage() {
    addMessage(`👋 Welcome! I'm your AI Emotion Assistant!

I can:
• 😊 Detect and understand your emotions
• 💡 Provide personalized suggestions
• 💭 Chat and offer support
• 🎯 Help you manage your mood

How are you feeling today?`);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    initMoodChart();
    statusCheckInterval = setInterval(updateStatus, 1000);
    showWelcomeMessage();
    
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    
    userInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
    
    sendButton.addEventListener('click', sendMessage);
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
});

// Animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse-animation {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    @keyframes fade-animation {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    
    @keyframes shake-animation {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    @keyframes pop-animation {
        0% { transform: scale(1); }
        50% { transform: scale(1.2); }
        100% { transform: scale(1); }
    }
`;
document.head.appendChild(style);
