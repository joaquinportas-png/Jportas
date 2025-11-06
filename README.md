# Space Blue Sky + (Invaders)

Juego de escritorio tipo Space Invaders con cielo azul y nubes (parallax), sonido chiptune generado por código, power-ups y **JEFES cada 3 oleadas**.

## Ejecutar desde código

```bash
pip install -r requirements.txt
python space_bluesky_plus.py
```

## Construir ejecutable

### Windows
1. Doble clic a `build_exe.bat` **o**:
   ```bash
   pip install pyinstaller pygame
   pyinstaller --onefile --windowed --name SpaceBlueSkyPlus space_bluesky_plus.py
   ```
2. El `.exe` queda en `dist/SpaceBlueSkyPlus.exe`.

### macOS / Linux
```bash
chmod +x build_exe.sh
./build_exe.sh
```

## Controles
- Flechas izquierda/derecha o A/D → mover
- Espacio → disparar (autofire con power-up Ráfaga)
- P → Pausa
- Enter/Espacio → Empezar/Reiniciar

## Notas de audio
- El audio se genera en tiempo real sin archivos externos (cuadradas/ruido). Si tu sistema no expone un dispositivo de audio válido, el juego seguirá funcionando en silencio.
