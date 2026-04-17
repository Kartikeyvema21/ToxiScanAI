import os
import re
import secrets
import warnings
import json
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, send_from_directory
from flask_cors import CORS

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get('sk-0ab05714bf4a440dacf78b5e4ef38c95', secrets.token_hex(32))
CORS(app, supports_credentials=True)

# Configuration
USERS_FILE = "users.json"
ANALYTICS_FILE = "analytics.json"

# Toxic words list
TOXIC_WORDS = {
    'hate', 'stupid', 'suck', 'terrible', 'worst', 'fuck', 'shit', 'bitch',
    'asshole', 'bastard', 'idiot', 'moron', 'dumb', 'loser', 'pathetic',
    'garbage', 'worthless', 'failure', 'kill', 'die', 'damn', 'hell',
    'annoying', 'useless', 'crap', 'disgusting', 'awful', 'horrible',
    'fool', 'jerk', 'ridiculous', 'hopeless'
}

# Stylized patterns for repeated letters
STYLIZED_PATTERNS = [
    r'st+u+p+i+d+',      # stuupid, stupid, stuuupid
    r's+o+o+',           # sooo, soooo
    r'r+e+a+l+l+y+',     # reeeally, really
    r'b+a+a+a+d+',       # baaaad, baad
    r's+u+c+k+',         # suuck, suckkk
    r'd+a+m+n+',         # daaamn, damn
    r'h+e+l+l+',         # helll, hellll
    r's+h+i+t+',         # shitt, shit
    r'f+u+c+k+',         # fuckk, fuuck
    r'i+d+i+o+t+',       # idiot, idiot
    r'm+o+r+o+n+',       # moron, moroon
]

def normalize_repeated_letters(word):
    """Reduce repeated letters (e.g., 'stupidddd' -> 'stupid')"""
    return re.sub(r'(.)\1{2,}', r'\1\1', word)

def is_single_name(text):
    """Return True if text is a single word that is not toxic"""
    words = text.lower().strip().split()
    if len(words) != 1:
        return False
    
    word = words[0]
    normalized = normalize_repeated_letters(word)
    
    # Check if it contains any toxic word
    for toxic in TOXIC_WORDS:
        if toxic in normalized:
            return False
    
    # Check stylized patterns
    for pattern in STYLIZED_PATTERNS:
        if re.search(pattern, word):
            return False
    
    return True

def detect_toxicity(text):
    """Main toxicity detection using pattern matching"""
    original_text = text
    text_lower = text.lower()
    words = text_lower.split()
    
    # RULE 1: Single word name → 0% toxicity
    if is_single_name(text):
        return {
            "toxicity_score": 0,
            "toxicity_level": "Safe",
            "color": "#00c853",
            "ml_confidence": 100,
            "ml_prediction": "Non-Toxic",
            "explicit_words": [],
            "word_count": len(words),
            "toxic_probability": 0
        }
    
    # RULE 2: Detect stylized toxic patterns
    stylized_matches = []
    for pattern in STYLIZED_PATTERNS:
        matches = re.findall(pattern, text_lower)
        stylized_matches.extend(matches)
    
    # RULE 3: Detect explicit toxic words
    toxic_words_found = []
    for word in words:
        normalized = normalize_repeated_letters(word)
        for toxic in TOXIC_WORDS:
            if toxic in normalized:
                toxic_words_found.append(word)
                break
    
    toxic_words_found = list(set(toxic_words_found))
    total_toxic_count = len(toxic_words_found) + len(stylized_matches)
    
    if total_toxic_count == 0:
        # No toxic content
        if len(words) <= 3:
            toxicity_score = 5
        else:
            toxicity_score = 10
        toxicity_level = "Safe"
        color = "#00c853"
        prediction = "Non-Toxic"
    else:
        # Toxic content found
        base_score = 60
        base_score += min(total_toxic_count * 8, 35)
        if len(stylized_matches) > 0:
            base_score += 10
        if total_toxic_count >= 3:
            base_score += 10
        toxicity_score = min(base_score, 98)
        
        if toxicity_score >= 60:
            toxicity_level = "Toxic"
            color = "#f44336"
            prediction = "Toxic"
        elif toxicity_score >= 30:
            toxicity_level = "Warning"
            color = "#ff9800"
            prediction = "Warning"
        else:
            toxicity_level = "Safe"
            color = "#00c853"
            prediction = "Non-Toxic"
    
    return {
        "toxicity_score": round(toxicity_score, 2),
        "toxicity_level": toxicity_level,
        "color": color,
        "ml_confidence": round(toxicity_score, 2),
        "ml_prediction": prediction,
        "explicit_words": toxic_words_found,
        "word_count": len(words),
        "toxic_probability": round(toxicity_score, 2)
    }

# ============================================
# User & Analytics (same as before)
# ============================================

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

def update_analytics(text, result):
    analytics = load_analytics()
    today = datetime.now().strftime("%Y-%m-%d")
    analytics["total_analyses"] += 1
    level = result["toxicity_level"].lower()
    if level == "toxic":
        analytics["toxic_count"] += 1
    elif level == "warning":
        analytics["warning_count"] += 1
    else:
        analytics["safe_count"] += 1
    if today not in analytics["daily_stats"]:
        analytics["daily_stats"][today] = {"toxic": 0, "warning": 0, "safe": 0}
    analytics["daily_stats"][today][level] += 1
    analytics["recent_analyses"].insert(0, {
        "text": text[:100] + ("..." if len(text) > 100 else ""),
        "level": result["toxicity_level"],
        "score": result["toxicity_score"],
        "timestamp": datetime.now().isoformat()
    })
    analytics["recent_analyses"] = analytics["recent_analyses"][:50]
    save_analytics(analytics)

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

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "ToxiScan AI (Pattern Detection)",
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
    try:
        data = request.json
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400
        text = data["text"].strip()
        if not text:
            return jsonify({"error": "Empty text"}), 400
        
        result = detect_toxicity(text)
        update_analytics(text, result)
        
        return jsonify({
            "original_text": text,
            "explicit_toxic_words": result["explicit_words"],
            "analysis": {
                "toxicity_score": result["toxicity_score"],
                "toxicity_level": result["toxicity_level"],
                "color": result["color"],
                "ml_confidence": result["ml_confidence"],
                "ml_prediction": result["ml_prediction"],
                "word_count": result["word_count"],
                "toxic_probability": result.get("toxic_probability", 0)
            }
        })
    except Exception as e:
        print(f"Error: {e}")
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
    print("TOXISCAN AI - PATTERN DETECTION (NO ML MODEL)")
    print("=" * 50)
    print("\n✅ Any single word name → 0% toxicity (Safe)")
    print("✅ 'Kartikey', 'Rahul', 'Alice' → Safe")
    print("🔴 'stupidddd', 'sooo stupid' → Toxic")
    print("\n🌐 Server starting...")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)