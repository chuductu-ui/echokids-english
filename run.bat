@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title EchoKids English SRS Server
echo ==============================================================
echo   EchoKids English - Listening & Speaking SRS Platform
echo   Teaching Kids (Ages 7 & 11) Collocations, Sentences, Words
echo ==============================================================
echo.
echo Starting local web server...
echo.
python app.py
pause
