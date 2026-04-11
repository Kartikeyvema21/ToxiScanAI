import pandas as pd
import re
import nltk
import warnings
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from nltk.corpus import stopwords

warnings.filterwarnings("ignore")

# -----------------------------
# Download NLTK data
# -----------------------------
-----------
# Dataset loader (safe)
# -----------------------------
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
                "Keep it up"
            ],
            "toxic": [1,1,0,0,1,0,1,0,1,0]
        }
        df = pd.DataFrame(data)
        df.to_csv(file_name, index=False)

    return df

# -----------------------------
# Text cleaning
# -----------------------------
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)       # remove URLs
    text = re.sub(r"@\w+", "", text)           # remove mentions
    text = re.sub(r"[^a-z\s]", " ", text)
    words = text.split()
    words = [w for w in words if w not in STOP_WORDS]
    return " ".join(words)

# -----------------------------
# Load data
# -----------------------------
df = load_or_create_dataset()
df.rename(columns={"TOXIC_WORDS": "comment_text"}, inplace=True)
df["comment_text"] = df["comment_text"].apply(clean_text)

# Extract toxic words from dataset for quick lookup
TOXIC_WORDS = set(df[df["toxic"] == 1]["comment_text"].str.split(expand=True).stack().unique())

# Define explicit toxic words for immediate detection
EXPLICIT_TOXIC_WORDS = {"hate", "stupid", "suck", "terrible", "worst",
                        "fuck", "fucking", "motherfucker",
                        "shit", "bitch", "asshole",
                        "bastard", "slut", "whore",
                        "idiot", "stupid", "moron","KUTTA"}

# -----------------------------
# Train-test split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    df["comment_text"],
    df["toxic"],
    test_size=0.3,
    random_state=42,
    stratify=df["toxic"] if len(df) > 5 else None
)

# -----------------------------
# TF-IDF with n-grams
# -----------------------------
vectorizer = TfidfVectorizer(
    max_features=8000,
    ngram_range=(1,2),      # unigrams + bigrams
    min_df=1
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# -----------------------------
# Train model (balanced)
# -----------------------------
model = LogisticRegression(
    max_iter=1000,
    class_weight="balanced"
)

model.fit(X_train_vec, y_train)

# -----------------------------
# Evaluation
# -----------------------------
y_pred = model.predict(X_test_vec)
print("\nAccuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(model, "toxic_model.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")

# -----------------------------
# Interactive detection
# -----------------------------
print("\n--- AUTO TOXIC COMMENT DETECTOR ---")

while True:
    comment = input("\nEnter a comment (or 'exit'): ")
    if comment.lower() == "exit":
        print("Exiting...")
        break

    cleaned = clean_text(comment)
    words = [w for w in cleaned.split() if w]  # filter out empty strings

    # CASE 1: Explicit toxic word anywhere → Toxic
    if words and any(word in EXPLICIT_TOXIC_WORDS for word in words):
        print("Toxic Comment (Reason: explicit abusive language)")
        continue

    # CASE 2: Single-word neutral or dataset toxic word
    if len(words) == 1:
        if words[0] in TOXIC_WORDS:
            print("Toxic Comment (Reason: dataset toxic word)")
        else:
            print("Non-Toxic Comment (Reason: neutral single word)")
        continue

    # CASE 3: Multi-word → ML model
    vec = vectorizer.transform([cleaned])
    probs = model.predict_proba(vec)[0]
    pred = probs.argmax()
    confidence = probs[pred]

    if pred == 1 and confidence >= 0.65:
        print(f"Toxic Comment (Confidence: {confidence:.2f})")
    else:
        print(f"Non-Toxic Comment (Confidence: {confidence:.2f})")
