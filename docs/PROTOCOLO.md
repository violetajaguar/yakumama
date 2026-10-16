# Yakumama wire protocol (for TouchDesigner or any receiver)

Everything that drives the whale is **one JSON object per UDP datagram**, sent to `127.0.0.1:9998` at 30 packets per
second. Three senders exist and produce the same shape: the live recorder (`grabar_ballena.py`), the take player
(`reproducir.py`) and the neural net (`generar_animo.py` / `yakumama_modelo.py`). A receiver written in
TouchDesigner (UDP In DAT → JSON) can replace the Blender one, or sit next to it on another port.

## Fields

| field | range | source | meaning |
|---|---|---|---|
| `head_yaw`, `head_pitch` | −1..1 | face | head turn / nod, calibrated to the performer's neutral |
| `jaw_open`, `brow_up`, `brow_down`, `mouth_sad`, `mouth_smile` | 0..1 | face | expression channels |
| `blink` | 0 or 1 (held 5 frames) | face | eyelids closed |
| `eye_yaw`, `eye_pitch` | −1..1 | face | gaze (+ = performer's right / up) |
| `tongue_out` | 0..1 | face | always 0 at present (no tongue in MediaPipe) |
| `face_<name>` ×51 | 0..1 | face | raw MediaPipe blendshapes (`face_jawOpen`, `face_browInnerUp`, …) |
| `l_palm_x`, `l_palm_y`, `r_palm_x`, `r_palm_y`, `l_depth` | 0..1 | hands | palm position in the camera image, present only while that hand is in frame |
| `emotibit_hr`, `emotibit_ibi` | bpm, s | EmotiBit | pulse (absent if no reading in the last 2 s) |
| `emotibit_eda`, `emotibit_edl` | µS | EmotiBit | skin conductance (10000 or 0.03 = no skin contact) |
| `emotibit_therm`, `emotibit_temp1` | °C | EmotiBit | skin temperature |
| `emotibit_ppg_ir/red/grn` | raw | EmotiBit | pulse waveform |
| `emotibit_acc_x/y/z`, `gyro_*`, `mag_*` | g, °/s, µT | EmotiBit | wrist motion |
| `actor_animo` | one of 10 moods | recogniser / take label / net | the mood that drives the body behaviour |
| `actor_<mood>` ×10 | 0..1 | recogniser | mood probabilities |
| `solo_cara` | 0, 1, 2 | mode | 1 = body at rest, face only; 2 = head locked too |
| `anclada` | 0/1 | mode | body moves but does not travel |
| `soltar_manual` | 0/1 | player | first second of a take: release the panel's manual override |
| `scene_color`, `scene_hue/sat/bright` | name, 0..1 | camera | dominant colour the camera sees |
| `water`, `temp`, `humidity`, `pressure_delta` | 0..1, … | environment | whale's sensors (not connected: water = 1.0) |
| `joy_x`, `joy_y`, `joy_btn` | −1..1, 0/1 | joystick | not connected |
| `whale_<mood>` ×10 | 0..1 | Qwen brain | the whale's own mood guess |

Moods: `calm singing playful curious feeding sad angry alert diving surfacing`.

## How the Blender receiver turns a packet into the whale

1. **Mood** = panel override, else `actor_animo`, else Qwen (if Brain on), else `scene_color` map
   (red angry, orange playful, yellow curious, green feeding, cyan surfacing, blue calm, purple singing, pink alert, white diving, black sad).
2. **Body** = the mood's behaviour, a function of time: root pitch/roll/yaw, six spine bones, tail fluke, fin flap/bank,
   jaw, face expression, gaze, spin, depth. Clock runs at `hr/75` (0.6..1.6).
3. **Layers on top**: performer face = `max(performer, mood face)`; hands → fin flap (height) and bank (difference);
   heartbeat = scale pulse on the spine, strength `LATIDO_ANIMO[mood] × (0.5 + 0.5·arousal)` with
   arousal = `0.6·(hr−60)/60 + 0.4·(eda−2)/8`; tail turbine speed per mood, one turn per heartbeat in singing;
   skin colour → `colores_rgb_0_1[mood]` with a 1 s fade.
4. Every number lives in `docs/yakumama_parametros.json`.

## Running the net without PyTorch

`yakumama_modelo.py` + `modelos/movimiento_pesos.npz` need only NumPy:

```python
from yakumama_modelo import Modelo
m = Modelo("modelos/movimiento_pesos.npz")
pkt = m.paquete("angry", t)      # call 30× per second with t in seconds; send json.dumps(pkt) to UDP 9998
```

The mood recogniser is `modelos/animo_rf.pkl` (scikit‑learn random forest); its feature builder is `rasgos()` in
`entrenar_animo.py` (2‑second windows of the 51 blendshapes, head and hands).

## Estilo (desde el 15 oct)
- `estilo`: a cual de los actores grabados se parece quien esta frente a la camara (`violeta`, `sanam`, `suri`, `dan`).
  Lo decide el grabador a los 2 s de ver una cara y queda fijo mientras la cara siga (un encuentro = un estilo); si la
  cara se pierde 8 s, desaparece del paquete. `parecido_<actor>`: la probabilidad de cada uno (0-1).
- `red`: 1 cuando el paquete lo genera la red (generar_animo.py / yakumama_modelo.py) y no una persona.
- La ballena fisica puede usar `estilo` igual que Blender: con ese nombre, `Modelo().paquete(animo, t, actor=estilo)` da
  manos y pulso en ese estilo, y el cuerpo se mueve con su energia (violeta 0.7, sanam 1.0, suri 1.15, dan 1.35).
- `visita`: id de la persona en la memoria de la ballena (`v0007`) o `nueva`; `conocida`: 1 si ya habia venido. La memoria
  es una firma de 210 distancias de la cara (sin imagenes), solo en la Mac del grabador; ver memoria.py.
- `cuerpo_pitch cuerpo_roll cuerpo_yaw cuerpo_profundidad cuerpo_energia cuerpo_suavidad`: el cuerpo de quien esta frente a la
  camara (MediaPipe Pose), las mismas cualidades que bailar.py saca de un esqueleto. -1..1 (energia y suavidad 0..1).
