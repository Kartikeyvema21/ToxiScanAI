#!/usr/bin/env bash

pip install -r requirements.txt

mkdir -p /opt/render/nltk_data
python -m nltk.downloader -d /opt/render/nltk_data stopwords punkt