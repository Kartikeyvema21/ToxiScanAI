import os
import re
import warnings
import json
import hashlib
from datetime import datetime
import joblib
import pandas as pd
import nltk
from flask import Flask, request, jsonify, render_template, session, redirect, send_from_directory
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from nltk.corpus import stopwords

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get('sk-0ab05714bf4a440dacf78b5e4ef38c95', 'sk-0ab05714bf4a440dacf78b5e4ef38c95')
CORS(app, supports_credentials=True)

# Configuration
MODEL_FILE = "toxic_model.pkl"
VECTORIZER_FILE = "vectorizer.pkl"
USERS_FILE = "users.json"
ANALYTICS_FILE = "analytics.json"

# Download NLTK data
try:
    nltk.data.find('corpora/stopwords')
except:
    nltk.download('stopwords', quiet=True)

# Explicit toxic words
EXPLICIT_TOXIC_WORDS = {
    "hate", "stupid", "suck", "terrible", "worst", "fuck", "shit", "bitch", 
    "asshole", "bastard", "idiot", "moron", "dumb", "loser", "pathetic", 
    "garbage", "worthless", "failure", "kill", "die", "damn", "hell"
}

# User management
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    users = {
        "admin": {"password": hashlib.sha256("admin123".encode()).hexdigest(), "email": "admin@toxiscan.com", "created_at": datetime.now().isoformat(), "role": "admin"},
        "demo": {"password": hashlib.sha256("demo123".encode()).hexdigest(), "email": "demo@toxiscan.com", "created_at": datetime.now().isoformat(), "role": "user"}
    }
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)
    return users

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r') as f:
            return json.load(f)
    return {"total_analyses": 0, "toxic_count": 0, "warning_count": 0, "safe_count": 0, "daily_stats": {}, "recent_analyses": []}

def save_analytics(analytics):
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(analytics, f, indent=2)

# ML Model
STOP_WORDS = None
df = None
model = None
vectorizer = None
_initialized = False

def initialize_app():
    global STOP_WORDS, df, model, vectorizer, _initialized
    if _initialized:
        return
    
    print("=" * 60)
    print("🔥 INITIALIZING TOXISCAN AI")
    print("=" * 60)
    
    STOP_WORDS = set(stopwords.words('english'))
    df = load_or_create_dataset()
    df["clean_text"] = df["comment_text"].apply(clean_text)
    
    if os.path.exists(MODEL_FILE) and os.path.exists(VECTORIZER_FILE):
        model = joblib.load(MODEL_FILE)
        vectorizer = joblib.load(VECTORIZER_FILE)
        print("✅ Model loaded")
    else:
        print("⚠️ Training new model...")
        train_model()
        print("✅ Model trained")
    
    _initialized = True
    print("🎉 APPLICATION READY!")
    print("=" * 60)

def load_or_create_dataset(file_name="sample_toxic_comments.csv"):
    if not os.path.exists(file_name):
        return create_fresh_dataset(file_name)
    try:
        df = pd.read_csv(file_name)
        if 'comment_text' in df.columns and 'toxic' in df.columns:
            return df[['comment_text', 'toxic']]
        if len(df.columns) >= 2:
            new_df = pd.DataFrame()
            new_df['comment_text'] = df.iloc[:, 0]
            new_df['toxic'] = df.iloc[:, 1]
            return new_df
    except Exception as e:
        print(f"Error: {e}")
    return create_fresh_dataset(file_name)

def create_fresh_dataset(file_name):
    data = {
        "comment_text": ["I hate you", "You are stupid", "Amazing work", "Well done", "You suck", "Excellent effort", "Terrible job", "Great performance", "Worst ever", "Keep it up", "You're an idiot", "This is garbage", "Wonderful presentation", "Brilliant idea", "Pathetic attempt", "Fantastic job", "Disappointing results", "You're worthless", "Outstanding work", "Complete failure", "I love this", "Nice try"],
        "toxic": [1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0]
    }
    df = pd.DataFrame(data)
    df.to_csv(file_name, index=False)
    return df

def train_model():
    global model, vectorizer, df
    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    X_vec = vectorizer.fit_transform(df["clean_text"])
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_vec, df["toxic"])
    joblib.dump(model, MODEL_FILE)
    joblib.dump(vectorizer, VECTORIZER_FILE)

def clean_text(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    words = text.split()
    if STOP_WORDS:
        words = [w for w in words if w not in STOP_WORDS]
    return " ".join(words)

def get_toxicity_score(text):
    global model, vectorizer
    cleaned = clean_text(text)
    words = cleaned.split()
    found_explicit = [w for w in words if w in EXPLICIT_TOXIC_WORDS]
    
    if len(words) == 0:
        return {"toxicity_score": 0, "toxicity_level": "Safe", "color": "#00c853", "ml_confidence": 0, "ml_prediction": "Non-Toxic", "explicit_words": []}
    
    vec = vectorizer.transform([cleaned])
    probs = model.predict_proba(vec)[0]
    prediction = model.predict(vec)[0]
    confidence = float(probs[prediction])
    
    toxicity_score = confidence * 70 if prediction == 1 else 0
    toxicity_score += min(len(found_explicit) * 15, 30)
    toxicity_score = min(toxicity_score, 100)
    
    if toxicity_score < 30:
        toxicity_level, color = "Safe", "#00c853"
    elif toxicity_score < 70:
        toxicity_level, color = "Warning", "#ff9800"
    else:
        toxicity_level, color = "Toxic", "#f44336"
    
    # Update analytics
    analytics = load_analytics()
    today = datetime.now().strftime("%Y-%m-%d")
    analytics["total_analyses"] += 1
    if toxicity_level == "Toxic":
        analytics["toxic_count"] += 1
    elif toxicity_level == "Warning":
        analytics["warning_count"] += 1
    else:
        analytics["safe_count"] += 1
    
    if today not in analytics["daily_stats"]:
        analytics["daily_stats"][today] = {"toxic": 0, "warning": 0, "safe": 0}
    analytics["daily_stats"][today][toxicity_level.lower()] += 1
    
    analytics["recent_analyses"].insert(0, {"text": text[:100], "level": toxicity_level, "score": round(toxicity_score, 2), "timestamp": datetime.now().isoformat()})
    analytics["recent_analyses"] = analytics["recent_analyses"][:50]
    save_analytics(analytics)
    
    return {"toxicity_score": round(toxicity_score, 2), "toxicity_level": toxicity_level, "color": color, "ml_confidence": round(confidence * 100, 2), "ml_prediction": "Toxic" if prediction == 1 else "Non-Toxic", "explicit_words": found_explicit, "word_count": len(words)}

# ============================================
# ROUTES
# ============================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    return render_template("dashboard.html")

# IMPORTANT: Health check for Render
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "ToxiScan AI is running",
        "initialized": _initialized,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    username, password, email = data.get('username'), data.get('password'), data.get('email', '')
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    users = load_users()
    if username in users:
        return jsonify({"error": "Username already exists"}), 400
    users[username] = {"password": hashlib.sha256(password.encode()).hexdigest(), "email": email, "created_at": datetime.now().isoformat(), "role": "user"}
    save_users(users)
    return jsonify({"success": True, "message": "User created successfully"}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    username, password = data.get('username'), data.get('password')
    users = load_users()
    if username not in users:
        return jsonify({"error": "Invalid credentials"}), 401
    if users[username]["password"] != hashlib.sha256(password.encode()).hexdigest():
        return jsonify({"error": "Invalid credentials"}), 401
    session['username'] = username
    session['user_role'] = users[username].get('role', 'user')
    return jsonify({"success": True, "message": "Login successful", "user": {"username": username, "role": session['user_role']}})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/auth/me", methods=["GET"])
def get_current_user():
    if 'username' in session:
        return jsonify({"authenticated": True, "username": session['username'], "role": session.get('user_role', 'user')})
    return jsonify({"authenticated": False}), 401

@app.route("/api/analyze", methods=["POST"])
def analyze_text():
    initialize_app()
    try:
        data = request.json
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400
        result = get_toxicity_score(data["text"])
        return jsonify({
            "original_text": data["text"],
            "cleaned_text": clean_text(data["text"]),
            "explicit_toxic_words": result["explicit_words"],
            "analysis": {
                "toxicity_score": result["toxicity_score"],
                "toxicity_level": result["toxicity_level"],
                "color": result["color"],
                "ml_confidence": result["ml_confidence"],
                "ml_prediction": result["ml_prediction"],
                "word_count": result["word_count"]
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    analytics = load_analytics()
    dates = sorted(analytics["daily_stats"].keys())[-30:]
    return jsonify({
        "total": analytics["total_analyses"],
        "toxic_count": analytics["toxic_count"],
        "warning_count": analytics["warning_count"],
        "safe_count": analytics["safe_count"],
        "dates": dates,
        "toxic_data": [analytics["daily_stats"].get(d, {}).get("toxic", 0) for d in dates],
        "warning_data": [analytics["daily_stats"].get(d, {}).get("warning", 0) for d in dates],
        "safe_data": [analytics["daily_stats"].get(d, {}).get("safe", 0) for d in dates],
        "recent": analytics["recent_analyses"][:10]
    })

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("TOXISCAN AI - RUNNING")
    print("=" * 50)
    initialize_app()
    
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🌐 Server running on port: {port}")
    print("🔐 admin / admin123 | demo / demo123")
    print("✅ Health check: /health")
    print("\n" + "=" * 50 + "\n")
    
    app.run(debug=False, host="0.0.0.0", port=port)