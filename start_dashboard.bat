@echo off
echo Starting AlgoTrade-India Dashboard...
cd /d "%~dp0"
python -m streamlit run dashboard/app.py
pause
