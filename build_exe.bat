@echo off
REM Construye ejecutable Windows con PyInstaller
python -m pip install --upgrade pip
pip install pyinstaller pygame
pyinstaller --onefile --windowed --name SpaceBlueSkyPlus space_bluesky_plus.py
ECHO Listo. Busca el .exe en la carpeta dist\
pause
