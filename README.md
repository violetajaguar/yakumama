# Yakumama

La ballena. El personaje vive en `~/Desktop/Huk` (`whale.blend`, `ballena3.py`, `yakumama_alma.py`); este proyecto
guarda lo nuevo: los **datasets de cara y de cuerpo** grabados mientras actuás, como con la llama, y lo que se entrene
con ellos. `venv` es un enlace al venv de Huk: no instalar nada ahí.

## Arrancar todo con un doble clic
`Yakumama.command` (doble clic en el Finder) abre Blender con `whale.blend` y el receptor ya cargado, el EmotiBit
Oscilloscope, ollama, el grabador y el **panel web** en `http://localhost:8765`: botones grandes para ánimo, grabar,
guardar tramo, neutral y modo, con estado en vivo (cara vista, neutral, Blender recibiendo, EmotiBit, segundos por
ánimo). Hace lo mismo que las teclas. En el Oscilloscope hay que marcar Output List > OSC a mano.

## Arrancar la ballena (a mano)
```bash
/Applications/Blender.app/Contents/MacOS/Blender ~/Desktop/Huk/whale.blend     # y correr el receptor (Text.017)
ollama serve
cd ~/Desktop/Yakumama && venv/bin/python grabar_ballena.py                     # = python ballena3.py + grabador
```
`grabar_ballena.py` arranca `ballena3.py` sin modificarlo: Blender recibe todo igual, y cada paquete se copia
etiquetado con el ánimo que escribís en la terminal (`1`–`0`, `g` graba, `f` cierra el tramo, `r` resumen, `q` sale;
una tecla por vez, sin Enter).
Necesita la **OAK-D enchufada** (sin ella `ballena3.py` se cae en `dai.Device`).

## Modo SOLO CARA (para grabar la cara con la ballena quieta)
`receptor_ballena.py` es el receptor de Blender (`Text.017` de `whale.blend`) más un modo en que la ballena se queda
en su lugar y solo la cara sigue al actor: cabeza (nariz), boca (`jaw_open`, rango completo, ignora el slider Mouth),
parpadeo (`blink`), ojos hacia donde apunta la nariz, cejas (`brow_up` → asombrado, `brow_down` → angry) y
`mouth_sad` → sad. Sin poses de ánimo, ola de nado, aletas, turbina ni nado automático.
1. En Blender: Text editor > Open > `~/Desktop/Yakumama/receptor_ballena.py` > Run Script (Alt+P). Reemplaza al
   receptor que esté corriendo (no hace falta reiniciar Blender). Sin este modo se comporta igual que `Text.017`.
2. En la terminal de `grabar_ballena.py`: `c` enciende/apaga el modo (marca cada paquete con `solo_cara: 1`).
   El dataset se graba igual con o sin el modo: `solo_cara` no se guarda.
   `c` cicla: cuerpo entero → solo cara (la cabeza sigue la nariz) → solo cara con **cabeza fija** (solo boca,
   parpadeo y cejas, para ver la cara de frente) → cuerpo entero.
   `a` = ANCLADA (modo cuerpo): la ballena se mueve (poses, aletas, columna, cabeza) pero no viaja por el espacio:
   ni la mano, ni el joystick, ni el nado automático mueven su posición. Para grabar movimiento sin que se vaya.
   Alas: en modo cuerpo cada mano del actor levanta o baja la aleta de su lado (altura de la palma en cámara). Si
   la mano izquierda mueve la aleta derecha, poner `ALAS_CRUZADAS = True` en `receptor_ballena.py`.
   Latido: con el EmotiBit puesto, el cuerpo de la ballena late al ritmo del corazón del actor (`emotibit_hr`,
   un 3.5 % de escala en `spine.001`). También al reproducir un tramo grabado.
3. `n` = NEUTRAL: mirá a la cámara con la cara relajada y escribí `n`; toma 1 s de muestras y desde ahí cabeza, cejas,
   boca y parpadeo se miden respecto a esa cara. Sin esto, con la OAK-D de costado el yaw queda pegado en -1 (el
   receptor lo recorta ahí) y la ballena no sigue. Se aplica a lo que ve Blender y a `datasets/cara` (`todo` guarda
   el paquete crudo). Volvé a escribir `n` si movés la cámara o te sentás distinto. Si la cámara no ve la cara (valores congelados)
   el neutral se rechaza y hay que repetirlo.
Las líneas `yaw:...` de `ballena3.py` se esconden; el grabador imprime su propia línea de estado cada 2 s.

**Lengua y 52 blendshapes.** `grabar_ballena.py` corre el Face Landmarker (`modelos/face_landmarker.task`) sobre el
mismo cuadro de la OAK-D que `ballena3.py` le pasa a FaceMesh, sin tocar `ballena3.py`. Agrega al paquete (y a
`datasets/cara`): `tongue_out`, `mouth_smile`, `blink_l`, `blink_r`, `blink` (el mejor de los dos, reemplaza al de
ballena3, que casi siempre era 0) y `face_<nombre>` con los 52. En modo solo cara, `tongue_out` saca la lengua
(empuja la raíz hacia adelante y abre un poco la boca). Si tarda más de 20 ms por cuadro, corre cuadro por medio.

## La ballena reconoce el ánimo del actor
`venv/bin/python entrenar_animo.py` entrena un reconocedor (random forest sobre ventanas de 2 s: 51 blendshapes,
cabeza y manos) con todo `datasets/` y lo guarda en `modelos/animo_rf.pkl`. Con ese archivo presente, el grabador lo
corre en vivo: cada 0.5 s decide el ánimo que ve en tu cara (cambia solo si gana 3 veces seguidas) y se lo manda al
receptor como `actor_animo`, que entonces usa ese ánimo entero, sin mezclar con colores ni cerebro. El panel muestra
"La ballena ve". Acierto dentro de sesión ~75 %; entre sesiones distintas todavía ~5 % (falta una tercera sesión con
la cámara de frente y neutral tomado para que generalice).

## Ver un tramo en la ballena
`venv/bin/python reproducir.py playful_001` manda el tramo a Blender con su tiempo original (`--modo cara|fija|cuerpo|anclada`,
`--velocidad 2`, `--loop`). Cerrar antes el grabador (`q`) para que no manden los dos a la vez.

## Qué se graba
- `datasets/cara/<ánimo>_NNN.jsonl`: head_yaw, head_pitch, jaw_open, blink, brow_up, brow_down, mouth_sad (y el
  paquete entero en `todo`).
- `datasets/cuerpo/<ánimo>_NNN.jsonl`: water, joy_x/joy_y/joy_btn, temp, humidity, pressure, l_palm_x/y, l_depth,
  cyber_*: todo lo que mueve columna, aletas, turbina y profundidad.
- EmotiBit: el grabador se conecta **directo al EmotiBit por WiFi** (`emotibit_cliente.py`: hello, conectar, ping,
  parseo de los paquetes CSV del firmware; hr del firmware o por picos del PPG). No hace falta el Oscilloscope ni
  OSC. Cada línea de `cuerpo` lleva `emotibit_<señal>` (eda, edl, ppg_ir/red/grn, therm, temp, acc/gyro/mag, hr,
  ibi, scr_*) solo si llegó un dato en los últimos 2 s (nunca repite valores viejos). `--emotibit-ip 192.168.50.64`
  si no lo encuentra por broadcast; `--emotibit-directo 0` para usar OSC del Oscilloscope (puerto 12345) en su lugar.
  El panel web muestra pulso, conductancia y ritmo cardíaco en vivo. Si el EmotiBit se queda colgado, con el Feather
  por USB se reinicia solo (`venv/bin/python -c "import serial..."`, ver sesión) o con el botón reset.
- `datasets/video/<ánimo>_NNN.mov`: la ventana de Blender grabada de `g` a `f` (screencapture), mismo nombre que el
  tramo; cada línea de cara y cuerpo lleva `video_t` (segundos desde que arrancó el video) para alinear. La primera
  vez macOS pide permiso de Grabación de pantalla para la Terminal. Apagado por defecto: `--video 1` lo enciende.
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
