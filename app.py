import pandas as pd
import re
import nltk
import warnings
import os
import joblib
from flask import Flask, request, jsonify, send_from_directory
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from nltk.corpus import stopwords

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder='templates/static', static_url_path='/static')

# Download NLTK data
try:
    nltk.data.find('corpora/stopwords')
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download("stopwords")
    nltk.download("punkt")

STOP_WORDS = set(stopwords.words("english"))

def load_or_create_dataset(file_name="sample_toxic_comments.csv"):
    create_sample = False

    if not os.path.exists(file_name) or os.stat(file_name).st_size == 0:
        create_sample = True
    else:
        try:
            df = pd.read_csv(file_name)
            if df.empty:
                create_sample = True
        except:
            create_sample = True

    if create_sample:
        print("Creating sample dataset...")
        data = {
            "TOXIC_WORDS": [
                "I hate you", "You are stupid", "Amazing work",
                "Well done", "You suck", "Excellent effort",
                "Terrible job", "Great performance", "Worst ever",
                "Keep it up", "You're an idiot", "This is garbage",
                "Wonderful presentation", "Brilliant idea", "Pathetic attempt",
                "Fantastic job", "Disappointing results", "You're worthless",
                "Outstanding work", "Complete failure"
            ],
            "toxic": [1,1,0,0,1,0,1,0,1,0,1,1,0,0,1,0,1,1,0,1]
        }
        df = pd.DataFrame(data)
        df.to_csv(file_name, index=False)

    return df

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    words = text.split()
    words = [w for w in words if w not in STOP_WORDS]
    return " ".join(words)

print("Initializing Toxicity Detector...")

df = load_or_create_dataset()
df.rename(columns={"TOXIC_WORDS": "comment_text"}, inplace=True)
df["comment_text"] = df["comment_text"].apply(clean_text)

EXPLICIT_TOXIC_WORDS = {"hate", "stupid", "suck", "terrible", "worst",
                        "fuck", "shit", "bitch", "asshole",
                        "bastard", "slut", "whore", "idiot",
                        "moron", "retard", "dumb", "loser", "pathetic",
                        "garbage", "worthless", "failure"}

model_file = "toxic_model.pkl"
vectorizer_file = "vectorizer.pkl"

if os.path.exists(model_file) and os.path.exists(vectorizer_file):
    print("Loading pre-trained model...")
    model = joblib.load(model_file)
    vectorizer = joblib.load(vectorizer_file)
else:
    print("Training new model...")
    X_train, X_test, y_train, y_test = train_test_split(
        df["comment_text"],
        df["toxic"],
        test_size=0.3,
        random_state=42
    )

    vectorizer = TfidfVectorizer(
        max_features=8000,
        ngram_range=(1, 2),
        min_df=1
    )

    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced"
    )

    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy:.2%}")
    print(classification_report(y_test, y_pred))

    joblib.dump(model, model_file)
    joblib.dump(vectorizer, vectorizer_file)
    print("Model saved successfully!")

print("Toxicity Detector is ready!")

@app.route('/')
def serve_index():
    return send_from_directory('templates', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('templates/static', path)

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "model_loaded": True,
        "service": "Toxicity Detector API"
    })

@app.route('/api/stats')
def get_stats():
    return jsonify({
        "model_type": "Logistic Regression",
        "features": "TF-IDF with n-grams",
        "explicit_words_count": len(EXPLICIT_TOXIC_WORDS),
        "dataset_size": len(df)
    })

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_text():
    try:
        if request.method == 'OPTIONS':
            return jsonify({}), 200
            
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400
        
        comment = data['text']
        cleaned = clean_text(comment)
        words = [w for w in cleaned.split() if w]
        
        result = {
            "original_text": comment,
            "cleaned_text": cleaned,
            "explicit_toxic_words": [],
            "analysis": {}
        }
        
        found_explicit_words = [word for word in words if word in EXPLICIT_TOXIC_WORDS]
        result["explicit_toxic_words"] = found_explicit_words
        
        if len(words) > 0:
            vec = vectorizer.transform([cleaned])
            probs = model.predict_proba(vec)[0]
            prediction = model.predict(vec)[0]
            confidence = float(probs[prediction])
            
            toxicity_score = 0
            
            if prediction == 1:
                toxicity_score = confidence * 70
            
            toxicity_score += min(len(found_explicit_words) * 15, 30)
            toxicity_score = min(toxicity_score, 100)
            
            if toxicity_score < 30:
                toxicity_level = "Safe"
                color = "#00c853"
            elif toxicity_score < 70:
                toxicity_level = "Warning"
                color = "#ff9800"
            else:
                toxicity_level = "Toxic"
                color = "#f44336"
            
            result["analysis"] = {
                "toxicity_score": round(toxicity_score, 2),
                "toxicity_level": toxicity_level,
                "color": color,
                "ml_confidence": round(confidence * 100, 2),
                "ml_prediction": "Toxic" if prediction == 1 else "Non-Toxic",
                "word_count": len(words)
            }
        else:
            result["analysis"] = {
                "toxicity_score": 0,
                "toxicity_level": "Safe",
                "color": "#00c853",
                "ml_confidence": 0,
                "ml_prediction": "Non-Toxic",
                "word_count": 0
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*50)
    print("TOXICITY DETECTOR - Web Application")
    print("="*50)
    print("\nAccess the website at: http://localhost:5000")
    print("\nAPI Endpoints:")
    print("  - http://localhost:5000/api/analyze (POST)")
    print("  - http://localhost:5000/api/health")
    print("  - http://localhost:5000/api/stats")
    print("\nStarting server...")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
