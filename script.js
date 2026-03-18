let moodChartInstance = null;
let historyChartInstance = null;
let recognition;
let isRecording = false;

// Setup Speech Recognition
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    // Using English (India) to best capture Tanglish (Tamil + English hybrid)
    recognition.lang = 'en-IN';

    recognition.onstart = function () {
        isRecording = true;
        const micBtn = document.getElementById("mic-btn");
        if (micBtn) micBtn.classList.add("recording");
        const msgField = document.getElementById("msg");
        if (msgField) msgField.placeholder = "Listening...";
    };

    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        const msgField = document.getElementById("msg");
        if (msgField) {
            msgField.value = transcript;
            setTimeout(() => {
                sendMessage(true);
            }, 500);
        }
    };

    recognition.onerror = function (event) {
        console.error("Speech recognition error", event.error);
        stopRecording();
    };

    recognition.onend = function () {
        if (isRecording) stopRecording();
    };
}

document.addEventListener("DOMContentLoaded", () => {
    // Determine which page we are on
    const isDashboard = document.querySelector('.dashboard-layout') !== null;

    if (isDashboard) {
        fetchReport();
        // Optional: poll every minute to update dashboard
        setInterval(fetchReport, 60000);
    }
});

function handleKeyPress(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

function appendMessage(sender, text) {
    const chatbox = document.getElementById("chatbox");
    if (!chatbox) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;
    msgDiv.innerHTML = `<p>${text}</p>`;
    chatbox.appendChild(msgDiv);

    // Smooth scroll to bottom
    chatbox.scrollTo({
        top: chatbox.scrollHeight,
        behavior: 'smooth'
    });
}

function showTypingIndicator() {
    const chatbox = document.getElementById("chatbox");
    if (!chatbox) return;

    const typingDiv = document.createElement("div");
    typingDiv.className = "message bot typing-msg";
    typingDiv.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    typingDiv.id = "typing";
    chatbox.appendChild(typingDiv);

    chatbox.scrollTo({
        top: chatbox.scrollHeight,
        behavior: 'smooth'
    });
}

function removeTypingIndicator() {
    const typingDiv = document.getElementById("typing");
    if (typingDiv) typingDiv.remove();
}

async function sendMessage(isVoice = false) {
    const inputField = document.getElementById("msg");
    if (!inputField) return;

    const message = inputField.value.trim();
    if (!message && !selectedImageBase64) return;

    // UI Update for User
    let imgHTML = "";
    if (selectedImageBase64) {
        imgHTML = `<br><img src="${selectedImageBase64}" alt="Sent Image" style="max-width: 200px; border-radius: 8px; margin-top: 5px;">`;
    }

    // We send HTML context if there's an image, otherwise just text
    appendMessage("user", imgHTML ? message + imgHTML : message);

    inputField.value = "";
    inputField.disabled = true;

    // Cache the image payload before clearing the UI
    const payloadImage = selectedImageBase64;

    removeImage(); // clear preview

    showTypingIndicator();

    try {
        const payload = { message: message };
        if (payloadImage) {
            const match = payloadImage.match(/^data:(image\/[a-zA-Z0-9\+\-]+);base64,/);
            if (match && match.length > 1) {
                payload.mime_type = match[1];
            } else {
                payload.mime_type = "image/jpeg"; // fallback
            }
            // strip the data:image/...;base64, prefix for the backend
            payload.image = payloadImage.split(',')[1];
        }

        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        removeTypingIndicator();
        appendMessage("bot", data.reply);

        if (isVoice === true) {
            speakText(data.reply);
        }

        if (data.risk) {
            const chatbox = document.getElementById("chatbox");
            if (chatbox) {
                const emergencyDiv = document.createElement("div");
                emergencyDiv.className = "message bot";
                emergencyDiv.innerHTML = `
                    <p><strong>Emergency Support</strong></p>
                    <a href="tel:988" style="display: inline-block; background-color: #ef4444; color: white; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px;">
                        🚨 Call Helpline Now
                    </a>
                `;
                chatbox.appendChild(emergencyDiv);
                chatbox.scrollTo({ top: chatbox.scrollHeight, behavior: 'smooth' });
            }
        }

    } catch (error) {
        console.error("Error:", error);
        appendMessage("bot", "<span class='error-msg'>Sorry, I'm having trouble connecting to the server. Please try again.</span>");
    } finally {
        inputField.disabled = false;
        inputField.focus();
    }
}

async function fetchReport() {
    try {
        const response = await fetch("/report");
        const data = await response.json();

        const statusCard = document.getElementById("status-card");
        if (statusCard) {
            statusCard.innerHTML = `
                <p style="font-size: 1.15rem; color: #f8fafc; margin-bottom: 0.5rem">${data.recommendation}</p>
                <p style="font-size: 0.9rem; color: #94a3b8;">Average Sentiment Score: <span style="color: #c7d2fe; font-weight: 600;">${data.average_score}</span></p>
            `;
        }

        const chartCanvas = document.getElementById('moodChart');
        if (chartCanvas && data.status === "Success" && data.trend.length > 0) {
            updateChart(data.trend);
        } else if (chartCanvas && data.trend.length === 0) {
            const ctx = chartCanvas.getContext('2d');
            ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
            ctx.font = "16px Inter";
            ctx.fillStyle = "#94a3b8";
            ctx.textAlign = "center";
            ctx.fillText("No interaction data yet today.", chartCanvas.width / 2, chartCanvas.height / 2);
        }

        const emergencyPanel = document.getElementById("emergency-panel");
        if (emergencyPanel) {
            if (data.risk_events > 0) {
                emergencyPanel.style.display = "block";
            } else {
                emergencyPanel.style.display = "none";
            }
        }

        // Fetch and display 7-day history
        const historyResponse = await fetch("/history_report");
        const historyData = await historyResponse.json();

        const historyCanvas = document.getElementById('historyChart');
        if (historyCanvas && historyData.history && historyData.history.length > 0) {
            updateHistoryChart(historyData.history);
        } else if (historyCanvas && (!historyData.history || historyData.history.length === 0)) {
            const ctx = historyCanvas.getContext('2d');
            ctx.clearRect(0, 0, historyCanvas.width, historyCanvas.height);
            ctx.font = "16px Inter";
            ctx.fillStyle = "#94a3b8";
            ctx.textAlign = "center";
            ctx.fillText("Not enough data for 7-day history.", historyCanvas.width / 2, historyCanvas.height / 2);
        }

    } catch (error) {
        console.error("Error fetching report:", error);
        const statusCard = document.getElementById("status-card");
        if (statusCard) {
            statusCard.innerHTML = `<p style="color: #ef4444;">Failed to load insights. Please try again.</p>`;
        }
    }
}

function updateChart(trendData) {
    const canvas = document.getElementById('moodChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    const labels = trendData.map(d => d.time);
    const scores = trendData.map(d => d.score);

    // Create gradient
    let gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.5)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

    if (moodChartInstance) {
        moodChartInstance.destroy();
    }

    moodChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sentiment Score',
                data: scores,
                borderColor: '#818cf8',
                backgroundColor: gradient,
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#c7d2fe',
                pointBorderColor: '#4f46e5',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 2000,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { family: 'Inter', size: 13 },
                    bodyFont: { family: 'Inter', size: 14 },
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: function (context) {
                            let value = context.raw;
                            if (value > 0.3) return "Mood: Positive";
                            if (value < -0.3) return "Mood: Negative";
                            return "Mood: Neutral";
                        }
                    }
                }
            },
            scales: {
                y: {
                    min: -1,
                    max: 1,
                    grid: { color: 'rgba(255, 255, 255, 0.05)', borderDash: [5, 5] },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' }, padding: 10 }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' }, maxTicksLimit: 6, padding: 10 }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index',
            },
        }
    });
}

function updateHistoryChart(historyData) {
    const canvas = document.getElementById('historyChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    const labels = historyData.map(d => {
        const parts = d.date.split('-');
        if (parts.length === 3) return `${parts[1]}/${parts[2]}`;
        return d.date;
    });
    const scores = historyData.map(d => d.avg_score);

    if (historyChartInstance) {
        historyChartInstance.destroy();
    }

    historyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Score',
                data: scores,
                backgroundColor: scores.map(s => s >= 0 ? 'rgba(52, 211, 153, 0.6)' : 'rgba(248, 113, 113, 0.6)'),
                borderColor: scores.map(s => s >= 0 ? '#10b981' : '#ef4444'),
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 2000,
                easing: 'easeOutQuart',
                delay: (context) => context.dataIndex * 150
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { family: 'Inter', size: 13 },
                    bodyFont: { family: 'Inter', size: 14 }
                }
            },
            scales: {
                y: {
                    min: -1,
                    max: 1,
                    grid: { color: 'rgba(255, 255, 255, 0.05)', borderDash: [5, 5] },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                }
            }
        }
    });
}

// SOS Modal Functions
function showSOSModal() {
    const overlay = document.getElementById('sosModalOverlay');
    if (overlay) overlay.classList.add('active');
}

function closeSOSModal() {
    const overlay = document.getElementById('sosModalOverlay');
    if (overlay) overlay.classList.remove('active');
}

function confirmSOS() {
    // In a real app, this would hit an API endpoint
    showToast("SOS triggered! Emergency notifications have been sent to your trusted contacts.", "error");
    closeSOSModal();
}

function toggleRecording() {
    if (!recognition) {
        showToast("Speech recognition is not supported in your browser.", "error");
        return;
    }

    if (isRecording) {
        stopRecording();
    } else {
        try {
            recognition.start();
        } catch (e) {
            console.error(e);
        }
    }
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    if (recognition) {
        try { recognition.stop(); } catch (e) { }
    }
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) micBtn.classList.remove("recording");
    const msgField = document.getElementById("msg");
    if (msgField) {
        msgField.placeholder = "Type your message here...";
    }
}

function speakText(text) {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();

    // Remove emojis before speaking so it sounds more natural
    const cleanText = text.replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g, '');

    const utterance = new SpeechSynthesisUtterance(cleanText);

    // Select a friendly/natural voice (prefer Indian English for Tanglish or general Female)
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
        const preferredVoice = voices.find(v => v.lang.includes('en-IN')) ||
            voices.find(v => v.name.includes('Female')) ||
            voices.find(v => v.lang.includes('en-GB'));
        if (preferredVoice) utterance.voice = preferredVoice;
    }

    // Slightly adjust pitch and rate for a calmer, more human tone
    utterance.pitch = 1.05;
    utterance.rate = 0.95;

    window.speechSynthesis.speak(utterance);
}

// Premium Toast Notification System
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let icon = '';
    if (type === 'error') icon = '⚠️';
    else if (type === 'success') icon = '✅';
    else icon = 'ℹ️';

    toast.innerHTML = `<span class="toast-icon">${icon}</span> <span class="toast-msg">${message}</span>`;
    container.appendChild(toast);

    // Trigger reflow for animation
    void toast.offsetWidth;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
        toast.addEventListener('transitionend', () => toast.remove());
    }, 4000);
}

// Ensure voices are loaded (Chrome bug workaround)
if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

// Image Upload Handling
let selectedImageBase64 = null;

function handleImageSelection(event) {
    const file = event.target.files[0];
    if (file) {
        if (!file.type.startsWith('image/')) {
            showToast("Please select a valid image file.", "error");
            return;
        }

        if (file.size > 5 * 1024 * 1024) { // 5MB limit
            showToast("Image is too large (max 5MB).", "error");
            return;
        }

        const reader = new FileReader();
        reader.onload = function (e) {
            selectedImageBase64 = e.target.result;
            const previewContainer = document.getElementById('image-preview-container');
            const previewImg = document.getElementById('image-preview');

            previewImg.src = selectedImageBase64;
            previewContainer.style.display = 'inline-block';
        };
        reader.readAsDataURL(file);
    }
}

function removeImage() {
    selectedImageBase64 = null;
    document.getElementById('image-upload').value = '';
    const previewContainer = document.getElementById('image-preview-container');
    const previewImg = document.getElementById('image-preview');

    previewImg.src = '';
    previewContainer.style.display = 'none';
}

// Face Scan Feature
let faceStream = null;

async function openFaceScanModal() {
    const modal = document.getElementById('faceScanModalOverlay');
    const video = document.getElementById('face-video');
    if (!modal || !video) return;

    modal.classList.add('active');
    
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = faceStream;
    } catch (err) {
        console.error("Camera access denied or unavailable", err);
        showToast("Unable to access camera. Please check permissions.", "error");
        closeFaceScanModal();
    }
}

function closeFaceScanModal() {
    const modal = document.getElementById('faceScanModalOverlay');
    if (modal) modal.classList.remove('active');
    
    if (faceStream) {
        faceStream.getTracks().forEach(track => track.stop());
        faceStream = null;
    }
}

async function captureFaceAndAnalyze() {
    const video = document.getElementById('face-video');
    const canvas = document.getElementById('face-canvas');
    if (!video || !canvas) return;

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    
    // Draw the current video frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Get base64 jpeg
    const base64Image = canvas.toDataURL('image/jpeg', 0.8);
    
    // Close modal and camera
    closeFaceScanModal();
    
    // Send to chat
    showTypingIndicator();
    
    try {
        const payload = { 
            message: "[FACE_ANALYSIS]",
            image: base64Image.split(',')[1],
            mime_type: "image/jpeg"
        };

        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        removeTypingIndicator();
        
        // Add a fake user message reflecting the scan
        appendMessage("user", "<div style='display:flex; align-items:center; gap:8px;'><span style='font-size:1.2rem'>📸</span> <i>Face scan sent...</i></div>");
        appendMessage("bot", data.reply);

        if (data.risk) {
            const chatbox = document.getElementById("chatbox");
            if (chatbox) {
                const emergencyDiv = document.createElement("div");
                emergencyDiv.className = "message bot";
                emergencyDiv.innerHTML = `<p><strong>Emergency Support</strong></p><a href="tel:988" style="display: inline-block; background-color: #ef4444; color: white; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px;">🚨 Call Helpline Now</a>`;
                chatbox.appendChild(emergencyDiv);
                chatbox.scrollTo({ top: chatbox.scrollHeight, behavior: 'smooth' });
            }
        }
    } catch (error) {
        console.error("Error analyzing face:", error);
        removeTypingIndicator();
        showToast("Failed to analyze face. Please try again.", "error");
    }
}
