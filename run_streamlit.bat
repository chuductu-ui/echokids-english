@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title EchoKids Streamlit Edition
echo ==============================================================
echo   EchoKids English - Streamlit Edition
echo ==============================================================
echo.
echo Starting Streamlit local server...
echo.
streamlit run streamlit_app.py
pause
