#!/usr/bin/env bash
# Construye binario para Linux/macOS con PyInstaller
python3 -m pip install --upgrade pip
pip3 install pyinstaller pygame
pyinstaller --onefile --windowed --name SpaceBlueSkyPlus space_bluesky_plus.py
echo "Listo. Binario en ./dist/"
