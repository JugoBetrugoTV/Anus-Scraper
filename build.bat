@echo off
echo === Unzensierter KI Chat - Build ===

pip install -r requirements.txt

pyinstaller --onefile --name "KI-Chat" --windowed --clean main.py

echo.
echo Fertig! Executable: dist\KI-Chat.exe
pause
