#!/bin/bash
# Yakumama.command - doble clic: abre Blender con el receptor ya cargado, el EmotiBit Oscilloscope, el grabador
# y el panel web (http://localhost:8765). Cierra un grabador o reproductor que estuviera corriendo.
Y="$HOME/Desktop/Yakumama"; H="$HOME/Desktop/Huk"
pkill -f reproducir.py 2>/dev/null; pkill -f grabar_ballena.py 2>/dev/null; sleep 1
if pgrep -x Blender >/dev/null; then
  echo ">>> Blender ya esta abierto. Si la ballena no reacciona, en su Python Console: exec(open('$Y/receptor_ballena.py').read())"
else
  echo ">>> abriendo Blender con whale.blend y el receptor"
  open -a /Applications/Blender.app --args "$H/whale.blend" --python "$Y/receptor_ballena.py"
fi
# El grabador se conecta directo al EmotiBit por WiFi; el Oscilloscope ya no hace falta (si esta abierto, lo cierra para que no compita)
pkill -f MacOS/EmotiBitOscilloscope 2>/dev/null
pgrep -f "ollama serve" >/dev/null || { echo ">>> arrancando ollama"; (ollama serve >/dev/null 2>&1 &); }
cd "$Y"; (sleep 5; open "http://localhost:8765") &
exec venv/bin/python grabar_ballena.py "$@"
