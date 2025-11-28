#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Starting Zorex Knowledge Dashboard..."
python3 -m streamlit run app.py --server.headless true &
sleep 3
open http://localhost:8501
