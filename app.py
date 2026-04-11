import os
import re
import warnings
import joblib
import pandas as pd
import nltk
from flask import Flask, request, jsonify, render_template
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from nltk.corpus import stopwords

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder="static", template_folder="templates")

# ============================================
# CONFIGURATION
# ============================================
NLTK_DATA_PATH = "/opt/render/nltk_data"
MODEL_FILE = "toxic_model.pkl"
VECTORIZER_FILE = "vectorizer.pkl"

# Create NLTK data directory
os.makedirs(NLTK_DATA_PATH, exist_ok=True)
nltk.data.path.append(NLTK_DATA_PATH)

# Explicit toxic words list (doesn't need NLTK)
EXPLICIT_TOXIC_WORDS = {
    "hate", "stupid", "suck", "terrible", "worst",
    "fuck", "shit", "bitch", "asshole",
    "bastard", "slut", "whore", "idiot",
    "moron", "retard", "dumb", "loser", "pathetic",
    "garbage", "worthless", "failure"
}

# ============================================
# GLOBAL VARIABLES (Lazy Loaded)
# ============================================
STOP_WORDS = None
df = None
model = None
vectorizer = None
_initialized = False

# ============================================
# FUNCTIONS
# ============================================

def initialize_app():
    """Initialize everything ONCE - called at first request"""
    global STOP_WORDS, df, model, vectorizer, _initialized
    
    if _initialized:
        return
    
    print("=" * 60)
    print("🔥 INITIALIZING APPLICATION (First Request)")
    print("=" * 60)
    
    # 1. Load NLTK stopwords
    print("Step 1: Loading NLTK stopwords...")
    STOP_WORDS = set(stopwords.words('english'))
    print(f"   ✅ Loaded {len(STOP_WORDS)} stopwords")
    
    # 2. Load dataset
    print("Step 2: Loading dataset...")
    df = load_or_create_dataset()
    print(f"   ✅ Loaded {len(df)} rows")
    
    # 3. Clean text
    print("Step 3: Cleaning text data...")
    df["clean_text"] = df["comment_text"].apply(clean_text)
    print("   ✅ Text cleaning complete")
    
    # 4. Load or train model
    print("Step 4: Loading ML model...")
    if os.path.exists(MODEL_FILE) and os.path.exists(VECTORIZER_FILE):
        model = joblib.load(MODEL_FILE)
        vectorizer = joblib.load(VECTORIZER_FILE)
        print("   ✅ Model loaded from disk")
    else:
        print("   ⚠️ Model not found, training new model...")
        train_model()
        print("   ✅ Model trained and saved")
    
    _initialized = True
    print("=" * 60)
    print("🎉 APPLICATION READY! 🎉")
    print("=" * 60)


def load_or_create_dataset(file_name="sample_toxic_comments.csv"):
    """Load dataset - handles any CSV structure"""
    
    # If file doesn't exist, create it
    if not os.path.exists(file_name):
        return create_fresh_dataset(file_name)
    
    try:
        df = pd.read_csv(file_name)
        
        # Check if we have the right columns
        if 'comment_text' in df.columns and 'toxic' in df.columns:
            return df[['comment_text', 'toxic']]
        
        # Try to find text column (case insensitive)
        text_col = None
        for col in df.columns:
            if col.upper() in ['COMMENT_TEXT', 'TOXIC_WORDS', 'TEXT', 'COMMENT']:
                text_col = col
                break
        
        # Try to find label column
        label_col = None
        for col in df.columns:
            if col.upper() in ['TOXIC', 'LABEL', 'CLASS']:
                label_col = col
                break
        
        if text_col and label_col:
            df.rename(columns={text_col: 'comment_text', label_col: 'toxic'}, inplace=True)
            return df[['comment_text', 'toxic']]
        
        # Fallback: assume first column is text, second is label
        if len(df.columns) >= 2:
            new_df = pd.DataFrame()
            new_df['comment_text'] = df.iloc[:, 0]
            new_df['toxic'] = df.iloc[:, 1]
            return new_df
        
        raise ValueError(f"CSV has {len(df.columns)} columns, need at least 2")
        
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return create_fresh_dataset(file_name)


def create_fresh_dataset(file_name):
    """Create fresh dataset with correct structure"""
    data = {
        "comment_text": [
            "I hate you", "You are stupid", "Amazing work",
            "Well done", "You suck", "Excellent effort",
            "Terrible job", "Great performance", "Worst ever",
            "Keep it up", "You're an idiot", "This is garbage",
            "Wonderful presentation", "Brilliant idea", "Pathetic attempt",
            "Fantastic job", "Disappointing results", "You're worthless",
            "Outstanding work", "Complete failure"
        ],
        "toxic": [1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1]
    }
    df = pd.DataFrame(data)
    df.to_csv(file_name, index=False)
    print(f"✅ Created fresh dataset with {len(df)} rows")
    return df


def train_model():
    """Train the model from dataset"""
    global model, vectorizer, df
    
    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2))
    X_vec = vectorizer.fit_transform(df["clean_text"])
    
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_vec, df["toxic"])
    
    # Save for next time
    joblib.dump(model, MODEL_FILE)
    joblib.dump(vectorizer, VECTORIZER_FILE)


def clean_text(text):
    """Clean and preprocess text"""
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
    """Calculate toxicity score for text"""
    global model, vectorizer
    
    cleaned = clean_text(text)
    words = cleaned.split()
    
    # Check for explicit toxic words
    found_explicit = [w for w in words if w in EXPLICIT_TOXIC_WORDS]
    
    if len(words) == 0:
        return {
            "toxicity_score": 0,
            "toxicity_level": "Safe",
            "color": "#00c853",
            "ml_confidence": 0,
            "ml_prediction": "Non-Toxic",
            "explicit_words": found_explicit
        }
    
    # ML prediction
    vec = vectorizer.transform([cleaned])
    probs = model.predict_proba(vec)[0]
    prediction = model.predict(vec)[0]
    confidence = float(probs[prediction])
    
    # Calculate final score
    toxicity_score = confidence * 70 if prediction == 1 else 0
    toxicity_score += min(len(found_explicit) * 15, 30)
    toxicity_score = min(toxicity_score, 100)
    
    # Determine level
    if toxicity_score < 30:
        toxicity_level = "Safe"
        color = "#00c853"
    elif toxicity_score < 70:
        toxicity_level = "Warning"
        color = "#ff9800"
    else:
        toxicity_level = "Toxic"
        color = "#f44336"
    
    return {
        "toxicity_score": round(toxicity_score, 2),
        "toxicity_level": toxicity_level,
        "color": color,
        "ml_confidence": round(confidence * 100, 2),
        "ml_prediction": "Toxic" if prediction == 1 else "Non-Toxic",
        "explicit_words": found_explicit,
        "word_count": len(words)
    }


# ============================================
# FLASK ROUTES
# ============================================

@app.route("/")
def home():
    """Home page"""
    return render_template("index.html")


@app.route("/health")
def health():
    """Health check - returns immediately without initialization"""
    return {"status": "ok", "message": "Service is running"}, 200


@app.route("/api/stats")
def get_stats():
    """Get model statistics - triggers initialization"""
    initialize_app()
    return jsonify({
        "model_type": "Logistic Regression",
        "features": "TF-IDF with n-grams",
        "explicit_words_count": len(EXPLICIT_TOXIC_WORDS),
        "dataset_size": len(df) if df is not None else 0,
        "status": "active"
    })


@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def analyze_text():
    """Analyze text for toxicity - triggers initialization"""
    global model, vectorizer
    
    if request.method == "OPTIONS":
        return jsonify({}), 200
    
    # Lazy initialization - happens on first request
    initialize_app()
    
    # Ensure model is ready
    if model is None or vectorizer is None:
        return jsonify({"error": "Model not ready yet"}), 503
    
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400
        
        comment = data["text"]
        result = get_toxicity_score(comment)
        
        return jsonify({
            "original_text": comment,
            "cleaned_text": clean_text(comment),
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


# ============================================
# LOCAL DEVELOPMENT
# ============================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("TOXICITY DETECTOR - LOCAL DEVELOPMENT")
    print("=" * 50)
    
    # Initialize for local development
    initialize_app()
    
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🌐 Server running at: http://localhost:{port}")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(debug=False, host="0.0.0.0", port=port)