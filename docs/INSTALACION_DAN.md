# Yakumama in Barcelona · running her on your machine (TouchDesigner + the physical whale)

No EmotiBit there, no Blender needed on your machine. The camera and the recorder run on your computer; TouchDesigner
and the physical whale listen to the packets. Everything the 3D whale does, yours can do from the same packet.

## 1. What runs where

```
 OAK-D camera ──► grabar_ballena.py (visitor mode) ──► UDP 127.0.0.1:9998  ──► TouchDesigner (UDP In DAT, same machine)
                     │  mood of the visitor · who they resemble · memory          └─► --espejo host:port ──► the physical whale
                     └─ saves each encounter · remembers faces as numbers
```

One JSON packet per UDP datagram, ~10 to 15 per second. Fields in `PROTOCOLO.md`; the ones that matter for you:

| field | meaning |
|---|---|
| `actor_animo` | the mood she sees in the visitor's face: `calm singing playful curious feeding sad angry alert diving surfacing` |
| `actor_<mood>` | probability of each mood (0‑1) |
| `estilo` | which recorded performer the visitor resembles: `violeta`, `sanam`, `suri`, `dan`. Decided 2 s after a face appears, fixed for the encounter, gone 8 s after the face leaves |
| `parecido_<name>` | probability per performer |
| `visita`, `conocida` | her memory: the person's id (`v0007`) or `nueva`; `conocida` = 1 if they came before |
| `head_yaw head_pitch jaw_open blink brow_up brow_down mouth_smile mouth_sad eye_yaw eye_pitch` | the visitor's face |
| `l_palm_x/y r_palm_x/y` | hands, when seen (0 top … 1 bottom of the image) |

**Pulse and skin without the sensor.** There is no `emotibit_hr` in the packet in Barcelona. Get them from the net in
the visitor's style, exactly as the 3D whale does:

```python
from yakumama_modelo import Modelo            # NumPy only, no torch
m = Modelo("modelos/movimiento_pesos.npz")
v = m.paso(mood, t, actor=estilo)              # t = seconds since the encounter began; estilo from the packet (None = average)
v["hr_bpm"], v["eda_uS"]                       # heartbeat and skin conductance in that performer's style
m.paquete(mood, t, actor=estilo)               # or the whole synthetic packet (hands too)
```

Then the same mapping as before: colour per mood (`yakumama_parametros.json`), heartbeat visible strength
`LATIDO_ANIMO[mood] × (0.5 + 0.5·arousal)`, tail speed per mood, one turn per heartbeat in singing. New since the 15th:
**body energy per style** — scale your amplitudes by `violeta 0.7 · sanam 1.0 · suri 1.15 · dan 1.35` when `estilo`
is set, so the physical whale moves more as Dan and less as Violeta.

## 2. Install (Windows, Mac or Linux)

1. Unzip. You get `Yakumama/` (code + models + docs) and `Huk/` (the camera script `ballena3.py`, its soul module,
   `whale.blend` and the sounds, in case you ever want the 3D whale too). Keep them side by side.
2. Python 3.11, then inside `Yakumama/`:
   ```
   python -m venv venv
   venv\Scripts\pip install depthai==2.32.0.0 mediapipe==0.10.14 opencv-python opencv-contrib-python numpy scikit-learn pyserial sounddevice
   ```
   (Mac/Linux: `venv/bin/pip ...`). `torch` is not needed on your machine.
3. Plug the OAK‑D into a USB3 port. Check: `venv\Scripts\python -c "import depthai as dai; print(dai.Device.getAllAvailableDevices())"`.

## 3. Run (every day)

```
venv\Scripts\python instalacion.py --sin-blender                              # camera + recorder, packets to 127.0.0.1:9998
venv\Scripts\python instalacion.py --sin-blender --espejo 192.168.1.80:9998   # and a copy to the physical whale's controller
```

A browser panel opens at http://localhost:8765: it shows the face, the mood she sees, who the visitor resembles,
her memory ("te conozco · visita 3"), and a button **Olvidar a esta persona** that erases someone from her memory.
"EmotiBit: apagado" on the panel is expected.

In TouchDesigner: UDP In DAT on port 9998 → JSON DAT (or a Script DAT with `json.loads` per row). If you prefer another
port: `--puerto` is not a flag of the recorder; keep 9998 and let TD listen there.

## 4. At closing time

```
venv\Scripts\python aprender.py      # she retrains her mood recogniser with what visitors brought that day
venv\Scripts\python memoria.py       # who she knows, how many visits each
```

Both read `datasets/visitas/` and `datasets/memoria.json`, which only exist on your machine. The memory is a 210‑number
signature of each face at rest, not an image, and it never leaves the machine. Please put a sign saying she remembers
faces as numbers and that anyone can ask to be forgotten.

## 5. If something fails

- Camera not found: USB3 cable, another port, close any other app using it.
- Panel shows "cara NO VISTA": the visitor is too far, too dark, or off‑centre; she needs the face about 1 m away.
- Low frame rate (< 8 packets/s): close other GPU/CPU work; the face landmarker already runs in its own thread.
- Nobody is ever "conocida": the match threshold is `UMBRAL` in `memoria.py` (0.025); raise it a little if real faces
  come back as "nueva" every time. The first days calibrate it.
- Windows: `ballena3.py` opens an OpenCV window with the camera view; it is fine to minimise it.
