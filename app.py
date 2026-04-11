import os
import re
import warnings
import joblib
import pandas as pd
import nltk
from flask import Flask, request, jsonify, render_template
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder="static", template_folder="templates")

# Download NLTK data if needed


STOP_WORDS = set(stopwords.words("english"))

EXPLICIT_TOXIC_WORDS = {
    "hate", "stupid", "suck", "terrible", "worst",
    "fuck", "shit", "bitch", "asshole",
    "bastard", "slut", "whore", "idiot",
    "moron", "retard", "dumb", "loser", "pathetic",
    "garbage", "worthless", "failure"
}

MODEL_FILE = "toxic_model.pkl"
VECTORIZER_FILE = "vectorizer.pkl"


def load_or_create_dataset(file_name="sample_toxic_comments.csv"):
    create_sample = False

    if not os.path.exists(file_name) or os.stat(file_name).st_size == 0:
        create_sample = True
    else:
        try:
            df = pd.read_csv(file_name)
            if df.empty:
                create_sample = True
        except Exception:
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
            "toxic": [1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1]
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

if os.path.exists(MODEL_FILE) and os.path.exists(VECTORIZER_FILE):
    print("Loading pre-trained model...")
    model = joblib.load(MODEL_FILE)
    vectorizer = joblib.load(VECTORIZER_FILE)
else:
    print("Training new model...")
    X_train, X_test, y_train, y_test = train_test_split(
        df["comment_text"],
        df["toxic"],
        test_size=0.3,
        random_state=42,
    )
    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), min_df=1)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy:.2%}")
    print(classification_report(y_test, y_pred))

    joblib.dump(model, MODEL_FILE)
    joblib.dump(vectorizer, VECTORIZER_FILE)
    print("Model saved successfully!")

print("Toxicity Detector is ready!")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/api/stats")
def get_stats():
    return jsonify({
        "model_type": "Logistic Regression",
        "features": "TF-IDF with n-grams",
        "explicit_words_count": len(EXPLICIT_TOXIC_WORDS),
        "dataset_size": len(df),
    })


@app.route("/api/analyze", methods=["POST", "OPTIONS"])
def analyze_text():
    try:
        if request.method == "OPTIONS":
            return jsonify({}), 200

        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400

        comment = data["text"]
        cleaned = clean_text(comment)
        words = [w for w in cleaned.split() if w]

        found_explicit_words = [word for word in words if word in EXPLICIT_TOXIC_WORDS]
        result = {
            "original_text": comment,
            "cleaned_text": cleaned,
            "explicit_toxic_words": found_explicit_words,
            "analysis": {},
        }

        if len(words) > 0:
            vec = vectorizer.transform([cleaned])
            probs = model.predict_proba(vec)[0]
            prediction = model.predict(vec)[0]
            confidence = float(probs[prediction])

            toxicity_score = confidence * 70 if prediction == 1 else 0
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
                "word_count": len(words),
            }
        else:
            result["analysis"] = {
                "toxicity_score": 0,
                "toxicity_level": "Safe",
                "color": "#00c853",
                "ml_confidence": 0,
                "ml_prediction": "Non-Toxic",
                "word_count": 0,
            }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("TOXICITY DETECTOR - Web Application")
    print("=" * 50)
    print("\nAccess the website at: http://localhost:5000")
    print("\nAPI Endpoints:")
    print("  - http://localhost:5000/api/analyze (POST)")
    print("  - http://localhost:5000/api/health")
    print("  - http://lo calhost:5000/api/stats")
    print("\nStarting server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
