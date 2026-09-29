@echo off
title Reaktionsspiel RGB-Matrix
cd /d "%~dp0"
python "%~dp0reaktionsspiel.py" %*
echo.
echo ============================================================
echo  Das Spiel ist beendet. Fenster kann geschlossen werden.
echo ============================================================
pause
