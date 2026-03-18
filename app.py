import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from textblob import TextBlob
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Skipping .env loading.")

app = Flask(__name__)
# In a real app, this should be a secure random key stored in .env
app.secret_key = os.getenv("FLASK_SECRET_KEY", "aaruyir_super_secret_key_123!")
DB_FILE = "data/chatbot.db"
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Try importing google.generativeai, but handle if it's not installed
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
    except ImportError:
        print("google-generativeai not installed. Using fallback responses.")

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            content TEXT,
            emotion TEXT,
            score REAL,
            risk_alert BOOLEAN,
            image_data TEXT
        )
    ''')
    try:
        c.execute('ALTER TABLE messages ADD COLUMN image_data TEXT')
    except sqlite3.OperationalError:
        pass # Column already exists
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            personality_profile TEXT,
            onboarding_completed BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def detect_emotion(text):
    analysis = TextBlob(text)
    score = analysis.sentiment.polarity
    
    if score > 0.3:
        emotion = "positive"
    elif score < -0.3:
        emotion = "negative"
        text_lower = text.lower()
        if any(word in text_lower for word in ["anxious", "worry", "panic", "fear", "nervous"]):
            emotion = "anxious"
        elif any(word in text_lower for word in ["sad", "depressed", "lonely", "hopeless", "cry"]):
            emotion = "depressed"
        elif any(word in text_lower for word in ["angry", "mad", "frustrated", "annoyed"]):
            emotion = "distressed"
    else:
        emotion = "neutral"
        
    return emotion, score

def detect_risk(text, score):
    risk_words = [
        "suicide", "kill myself", "hopeless", "worthless", 
        "depressed", "end my life", "want to die", "no reason to live"
    ]
    for word in risk_words:
        if word in text.lower():
            return True
    if score < -0.7:
        return True
    return False

def generate_response(user_message, emotion, risk, history, onboarding_completed, personality_profile, yesterday_avg, today_current_emotion, base64_image=None, mime_type="image/jpeg"):
    if risk:
        return "⚠ I am deeply concerned about what you just shared. You don't have to go through this alone. Please click the emergency button below to reach out to someone who can help right now. I am here for you, but professional support is crucial."
        
    if model:
        try:
            # Build history string
            history_context = ""
            if history:
                history_context = "Here is the recent conversation history for context (do not repeat yourself):\n"
                for msg in history:
                    role_str = "You (Aaruyir AI)" if msg['role'] == 'bot' else "User"
                    history_context += f"{role_str}: {msg['content']}\n"
            
            if user_message == "[FACE_ANALYSIS]":
                prompt = f"""You are Aaruyir AI, an incredibly advanced, highly intelligent mental health companion (similar to ChatGPT but specialized in psychological well-being).
The user has just sent a live scan of their face. 
Analyze their facial expression deeply. What exact emotion or mentality are they projecting?

CRITICAL INSTRUCTIONS:
1. ADAPT TO THEIR MENTALITY: Speak directly to their current psychological state. If they look stressed, be calming and grounding. If they look sad, be deeply therapeutic and comforting. If they look happy, match their energy.
2. NO REPEATED MESSAGES: Generate a completely unique, fresh response every time. Do not use generic or robotic phrases. 
3. EMOJIS: ALWAYS use expressive emojis naturally throughout your response to convey tone. 
4. CHATGPT-LIKE QUALITY: Provide a very thoughtful, well-structured, and rich response. Do NOT just say "I am your friend". Provide deep emotional intelligence and actual mental health value.
5. BILINGUAL: If the user has spoken Tanglish (Tamil + English) recently, YOU MUST reply fluently in Tanglish.

{history_context}
"""
            elif not onboarding_completed:
                prompt = f"""You are Aaruyir AI, an incredibly advanced and intelligent mental health companion (like ChatGPT, but specialized in emotional intelligence).
You are analyzing this user for the first time.

CRITICAL INSTRUCTIONS:
1. ADAPT TO THEIR MENTALITY: Understand the psychological underpinnings of their message and respond accordingly. Be insightful.
2. EMOJIS: ALWAYS use rich, expressive emojis naturally to set the mood.
3. NO REPETITION: Every response must be uniquely crafted. Never use boilerplate text.
4. INTELLIGENT DIALOGUE: Speak like a smart, highly capable therapeutic AI, not just a casual friend. Give them high-quality answers.
5. Ask one profound psychological question to understand their core personality better.
6. Once you understand them completely, implicitly output `[PROFILE: <summary>]` in your response.
7. TANGILSH SUPPORT: If the user says anything in Tanglish, you MUST reply entirely in highly fluent Tanglish.

{history_context}

The user says: '{user_message}'
"""
            else:
                mood_shift_context = ""
                if yesterday_avg is not None and yesterday_avg > 0.2 and today_current_emotion in ["negative", "anxious", "depressed", "distressed"]:
                    mood_shift_context = "CRITICAL INSIGHT: User's mood dropped significantly since yesterday. Intelligently address this shift and explore the root cause.\n"
                
                profile_context = f"User's Personality Profile: {personality_profile}\n" if personality_profile else ""
                
                prompt = f"""You are Aaruyir AI, an incredibly advanced mental health companion powered by state-of-the-art emotional intelligence (like ChatGPT or Gemini).

CRITICAL INSTRUCTIONS:
1. ADAPT TO MENTALITY: Do not just be a "friendly" bot. You must flawlessly adapt to their EXACT emotional and psychological state. If they are logical, be analytical. If they are grieving, be deeply therapeutic. If they are anxious, use grounding psychological techniques.
2. HIGH-QUALITY CHATGPT RESPONSES: Provide detailed, highly intelligent, and meaningful advice. Don't restrict yourself to 1-3 sentences. Give them a rich, comprehensive answer if their issue requires depth.
3. EMOJIS: Use expressive emojis throughout your response to add human-like warmth and visual breaks.
4. ZERO REPETITION: You MUST NEVER repeat generic phrases like "I understand how you feel" or "I am here for you." Always invent a fresh, specific, and hyper-personalized way to respond.
5. VISION/IMAGES: If they send an image, offer a highly detailed, intelligent analysis of it.
6. TANGLISH FLUIDITY: If the user types in Tanglish (Tamil + English), you MUST reply exclusively in fluent Tanglish. This is non-negotiable. Perfect the grammar and rhythm of Tanglish.

{profile_context}
{mood_shift_context}
{history_context}

The user says: '{user_message}'
The detected emotion is {emotion}.

Task: Respond elegantly, thoughtfully, and therapeutically using the instructions above."""
            
            if base64_image:
                payload = [
                    prompt, 
                    {"mime_type": mime_type, "data": base64_image} # The frontend will pass base64 striped
                ]
                response = model.generate_content(payload)
            else:
                response = model.generate_content(prompt)
                
            return response.text
        except Exception as e:
            print(f"Gemini API Error: {e}")
            
    # Fallback heuristic responses
    if emotion == "positive":
        return "That's wonderful to hear! I'm genuinely so happy for you. What else made you smile today? 😊"
    elif emotion == "anxious":
        return "Hey, it sounds like you're feeling really anxious. Let's take a quick pause together. Inhale deeply... and exhale slowly. You've got this, and I'm right here with you. Want to try a 1-minute grounding exercise?"
    elif emotion in ["negative", "depressed", "distressed"]:
        return "I'm so sorry things are feeling so heavy right now. It's completely okay to feel this way. I'm right here for you. Do you want to talk more about what's going on, or should we just take a breather?"
    else:
        return "I'm here to listen. Tell me more about what's on your mind today."

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user["password"], password):
            session['user_id'] = user["id"]
            session['username'] = user["username"]
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "error")
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        
        if not username or not password:
            flash("Username and password are required.", "error")
        else:
            conn = get_db_connection()
            c = conn.cursor()
            
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            if c.fetchone():
                flash("Username already exists.", "error")
                conn.close()
            else:
                hashed_pw = generate_password_hash(password)
                c.execute(
                    "INSERT INTO users (username, password, onboarding_completed) VALUES (?, ?, ?)",
                    (username, hashed_pw, 0)
                )
                conn.commit()
                conn.close()
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
            
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

from datetime import datetime

@app.route("/")
@login_required
def home():
    username = session.get('username')
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
        
    welcome_msg = f"{greeting}, {username}! I've been thinking about you. How was your day? ❤️"
    
    return render_template("index.html", username=username, welcome_msg=welcome_msg)

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get('username'))

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_id = session.get('user_id')
    user_message = request.json.get("message", "")
    image_data = request.json.get("image", None)
    mime_type = request.json.get("mime_type", "image/jpeg")
    
    if not user_message.strip() and not image_data:
        return jsonify({"reply": "Please say something."})
        
    emotion, score = detect_emotion(user_message)
    risk = detect_risk(user_message, score)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get user
    c.execute("SELECT onboarding_completed, personality_profile FROM users WHERE id=?", (user_id,))
    user_row = c.fetchone()
    onboarding_completed = bool(user_row["onboarding_completed"]) if user_row else False
    personality_profile = user_row["personality_profile"] if user_row else ""
    
    # Get yesterday's avg score for this user
    c.execute("SELECT AVG(score) as avg_score FROM messages WHERE role='user' AND user_id=? AND date(timestamp, 'localtime') = date('now', '-1 day', 'localtime')", (user_id,))
    yday_row = c.fetchone()
    yesterday_avg = yday_row["avg_score"] if yday_row and yday_row["avg_score"] is not None else None
    
    # Fetch recent history for this user (increased to 100 to act as a personal diary and remember past incidents)
    c.execute(
        "SELECT role, content, image_data FROM messages WHERE user_id=? ORDER BY timestamp DESC LIMIT 100", (user_id,)
    )
    history_rows = c.fetchall()
    
    # Reverse to chronological order for the prompt
    history = [{"role": row["role"], "content": row["content"], "image_data": row["image_data"]} for row in reversed(history_rows)]
    
    reply = generate_response(user_message, emotion, risk, history, onboarding_completed, personality_profile, yesterday_avg, emotion, image_data, mime_type)
    
    # Check for [PROFILE: ...] in reply
    if not onboarding_completed and "[PROFILE:" in reply:
        import re
        match = re.search(r'\[PROFILE:\s*(.*?)\]', reply, re.IGNORECASE | re.DOTALL)
        if match:
            new_profile = match.group(1).strip()
            c.execute("UPDATE users SET onboarding_completed=1, personality_profile=? WHERE id=?", (new_profile, user_id))
            conn.commit()
            # Remove the hidden tag from the reply sent to the user
            reply = re.sub(r'\[PROFILE:\s*(.*?)\]', '', reply, flags=re.IGNORECASE | re.DOTALL).strip()
    
    # Reusing existing connection
    c.execute(
        "INSERT INTO messages (user_id, role, content, emotion, score, risk_alert, image_data) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, "user", user_message, emotion, score, risk, image_data)
    )
    c.execute(
        "INSERT INTO messages (user_id, role, content, emotion, score, risk_alert, image_data) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, "bot", reply, "neutral", 0.0, False, None)
    )
    conn.commit()
    conn.close()
    
    if risk:
        print("🚨 SOS ALERT: Triggering emergency protocol to trusted contact!")
        
    return jsonify({"reply": reply, "emotion": emotion, "risk": risk})

@app.route("/report", methods=["GET"])
@login_required
def get_report():
    user_id = session.get('user_id')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT timestamp, emotion, score, risk_alert FROM messages WHERE user_id=? AND role='user' AND date(timestamp, 'localtime') = date('now', 'localtime') ORDER BY timestamp ASC",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return jsonify({
            "status": "No data yet",
            "trend": [],
            "average_score": 0,
            "risk_events": 0,
            "recommendation": "Start chatting to generate your daily insights."
        })
        
    trend = [{"time": row["timestamp"][11:16], "score": row["score"]} for row in rows]
    avg_score = sum(r["score"] for r in rows) / len(rows)
    risk_events = sum(1 for r in rows if r["risk_alert"])
    
    if risk_events > 0:
        rec = "You've had some highly distressed moments today. Please seek support from a friend or professional."
    elif avg_score < -0.2:
        rec = "It seems like a tough day. Try some light stretching, listening to calming music, or going for a short walk."
    elif avg_score > 0.2:
        rec = "You're having a good day! Write down one thing you're grateful for to keep the positive momentum."
    else:
        rec = "Your mood has been fairly stable today. Take a quick moment for yourself to maintain this balance."
        
    return jsonify({
        "status": "Success",
        "trend": trend,
        "average_score": round(avg_score, 2),
        "risk_events": risk_events,
        "recommendation": rec
    })

@app.route("/history_report", methods=["GET"])
@login_required
def get_history_report():
    user_id = session.get('user_id')
    conn = get_db_connection()
    c = conn.cursor()
    # Get average score for the last 7 days grouped by date for this user
    c.execute('''
        SELECT date(timestamp, 'localtime') as day, AVG(score) as avg_score 
        FROM messages 
        WHERE user_id=? AND role='user' AND date(timestamp, 'localtime') >= date('now', '-7 days', 'localtime')
        GROUP BY day
        ORDER BY day ASC
    ''', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    history_data = [{"date": row["day"], "avg_score": round(row["avg_score"], 2)} for row in rows]
    return jsonify({"history": history_data})

if __name__ == "__main__":
    app.run(debug=True, port=5000)