@echo off
cd /d "%~dp0"
echo Starting Zorex Knowledge Dashboard...
start http://localhost:8501
python -m streamlit run app.py --server.headless true