# Yakumama

La ballena. El personaje vive en `~/Desktop/Huk` (`whale.blend`, `ballena3.py`, `yakumama_alma.py`); este proyecto
guarda lo nuevo: los **datasets de cara y de cuerpo** grabados mientras actuás, como con la llama, y lo que se entrene
con ellos. `venv` es un enlace al venv de Huk: no instalar nada ahí.

## Arrancar la ballena (como siempre)
```bash
/Applications/Blender.app/Contents/MacOS/Blender ~/Desktop/Huk/whale.blend     # y correr el receptor (Text.017)
ollama serve
cd ~/Desktop/Yakumama && venv/bin/python grabar_ballena.py                     # = python ballena3.py + grabador
```
`grabar_ballena.py` arranca `ballena3.py` sin modificarlo: Blender recibe todo igual, y cada paquete se copia
etiquetado con el ánimo que escribís en la terminal (`1`–`0`, `g` graba, `f` cierra el tramo, `r` resumen, `q` sale).
Necesita la **OAK-D enchufada** (sin ella `ballena3.py` se cae en `dai.Device`).

## Qué se graba
- `datasets/cara/<ánimo>_NNN.jsonl`: head_yaw, head_pitch, jaw_open, blink, brow_up, brow_down, mouth_sad (y el
  paquete entero en `todo`).
- `datasets/cuerpo/<ánimo>_NNN.jsonl`: water, joy_x/joy_y/joy_btn, temp, humidity, pressure, l_palm_x/y, l_depth,
  cyber_*: todo lo que mueve columna, aletas, turbina y profundidad.
- `datasets/cara_webcam/<ánimo>_NNN.jsonl`: con `grabar_cara.py`, sin OAK-D: los 52 blendshapes de MediaPipe más la
  pose de la cabeza, y el mismo paquete de cara para Blender. Sirve para grabar la cara con más detalle o cuando la
  OAK-D no está. No correrlo junto con `ballena3.py` (los dos mandan al 9998).

Ánimos (los de `MOOD_KEYS` de `ballena3.py`): calm, singing, playful, curious, feeding, sad, angry, alert, diving,
surfacing. Meta: 60 s por ánimo. `python resumen.py` muestra cuánto hay.

## Mejor que la llama
La llama guardaba 23 números elegidos a mano y se enganchaba al mismo puerto que Blender. Aquí se guarda el paquete
entero, con la cara y el cuerpo separados pero con el mismo reloj y el mismo nombre de archivo, y la webcam agrega
52 blendshapes. Los entrenadores de la llama (`train_llama_body.py`, `train_llama_motion.py`) leen JSONL por línea con
claves con nombre: estos archivos se pueden leer igual cambiando la lista de claves.
