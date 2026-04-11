#!/bin/bash
echo "========================================="
echo "Building Toxicity Detector"
echo "========================================="

# Install dependencies
echo "Installing Python packages..."
pip install -r requirements.txt

# Download NLTK data
echo "Downloading NLTK data..."
python -c "import nltk; nltk.download('stopwords', download_dir='/opt/render/nltk_data')"

echo ""
echo "✅ Build complete!"