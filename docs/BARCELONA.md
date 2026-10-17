# Yakumama in Barcelona · the complete folder to copy onto the festival computers (17 October 2026)

Everything she is, ready to run without Violeta's machine. Copy this whole folder. Keep `Yakumama/` and `Huk/` side by side.

```
Yakumama/                  her code and models (the GitHub repo as of today, tag dan-2026-10-17)
  grabar_ballena.py          the recorder: OAK-D camera -> face, hands, whole body, mood, who the person is  -> UDP 9998
  cerebro_ballena.py         THE BRAIN without Blender: 9998 -> mood, behaviour, choreography, heartbeat, colour, eyes, H-JEPA -> UDP 9994
  comportamientos_animos.py  the ten behaviours, tables and choreography (generated from receptor_ballena.py, the 3D whale's receiver)
  hjepa_predecir.py          the H-JEPA on its own (used by the brain; usable alone)
  instalacion.py             one command to run recorder + brain (+ Blender if you want the 3D whale too)
  receptor_ballena.py        the 3D whale in Blender (optional here: TouchDesigner is the whale)
  modelos/                   hjepa.pt (H-JEPA) · coreografias.json (paths) · animo_rf.pkl (mood from face) · parecido_rf.pkl (style)
                             movimiento_pesos.npz (style net: pulse/hands without EmotiBit) · face/pose landmarker .task
                             jepa_datos.npz (201 MB: the assembled training set, so you can RETRAIN the H-JEPA)
  hjepa_entrenar.py jepa_datos.py cuerpo_cualidades.py entrenar_*.py importar_*.py   the whole training pipeline
  aprender.py memoria.py     nightly learning from visitors, her memory of faces (numbers, never images)
  docs/                      HOW_SHE_WORKS.md (everything, with the honest numbers), PROTOCOLO.md, COMPORTAMIENTOS.md ...
Huk/                       ballena3.py (camera script the recorder drives), yakumama_alma.py + lengua.py + palabras/ (her words),
                           whale.blend (the 3D whale), whale sound/ (a sound per mood + base music)
comportamientos_y_docs/    the package you already have: curves, eyes, choreography CSVs, a recorded minute of 9994, voice, videos, hjepa/
```

## 1. Install (Windows, Mac or Linux), once per computer

1. Python 3.11. Inside `Yakumama/`:
   ```
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt        (Mac/Linux: venv/bin/pip install -r requirements.txt)
   ```
   `torch` is only for the H-JEPA; if it will not install, run with `--sin-jepa` and she still does everything else.
2. OAK-D on a USB3 port. Check: `venv\Scripts\python -c "import depthai as dai; print(dai.Device.getAllAvailableDevices())"`.

## 2. Run, every day: one command

```
venv\Scripts\python instalacion.py --sin-blender --cerebro
venv\Scripts\python instalacion.py --sin-blender --cerebro --salida 192.168.1.80:9994 --salida 127.0.0.1:9994
```
This starts the recorder (packets on UDP 9998, panel at http://localhost:8765) and the brain (what she does, UDP 9994, 30/s).
`--salida` adds every machine that must receive her: the TouchDesigner computer, the physical whale's controller.
Add `--espejo host:9998` if some machine also wants the raw person stream. No EmotiBit there: "EmotiBit: apagado" is expected;
pulse and skin come from the style net in the style of the performer the visitor resembles.

To run the brain alone (for example against a recording): `venv\Scripts\python cerebro_ballena.py --salida <ip>:9994`.
To hear her mood sounds on that computer, play `Huk/whale sound/<animo>.wav` when `animo` changes.

## 3. What TouchDesigner receives: UDP 9994, one JSON per datagram, 30 per second

UDP In DAT on 9994 -> JSON DAT (or a Script DAT with `json.loads` per row). Fields:

| field | what it is |
|---|---|
| `animo`, `secundario`, `fuente` | her mood (calm singing playful curious feeding sad angry alert diving surfacing); the second; where it came from: `actor` = the person's face, `escena` = the room, `ella` = her own initiative (nobody there) |
| `x y z yaw` | where she is in the space (units: the 3D stage, about ±2; viewer is at -y; yaw ±π = facing the viewer) |
| `pitch roll giro` | whole-body pitch (nose up +), roll, turn, radians |
| `head`, `spine[6]`, `fluke`, `flap`, `ladeo` | head pitch; six vertebrae head to tail; tail fin; pectoral fins up/down; left-right fin asymmetry (rad) |
| `jaw`, `jaw_actor`, `boca` | mouth from the behaviour; from the person's face; the max of both (0..1) |
| `cara[4]` | eyelid, anger, sadness, surprise (0..1) · `mirada[2]` gaze from the behaviour |
| `spin`, `depth` | full turns (playful breach); rise/sink from the behaviour |
| `color[3]` | her skin colour for this mood (0..1 RGB) · `turbina` tail speed rad/s · `latido` heartbeat strength 0..1 |
| `beat`, `tempo`, `energia`, `tension`, `pulso` | the heartbeat pulse right now (0..1), speed factor (pulse/75), arousal, skin tension, bpm |
| `blink eye_yaw eye_pitch head_yaw head_pitch brow_up mouth_smile` | the person's face, passed through (eyes and blink: use them) |
| `estilo visita conocida persona` | who they move like (violeta/sanam/suri/dan), the visit id, 1 if she knows them, 1 if someone is in front |
| `tacto tacto_zona` | what the physical whale sent back on UDP 9995 (`{"tacto":0.8,"zona":"lomo","presencia":1}`) |
| `animo_cuerpo p_cuerpo` | H-JEPA: the mood read from the body alone and its confidence |
| `prevision` | H-JEPA: the six body qualities 4 s and 16 s ahead, and the mood she will look like at 16 s (after 32 s of body) |
| `iniciativa meta` | 1 when she acts on her own; the goal mood she planned toward |

Minimum for the physical whale: `animo`, `pitch roll`, `head`, `spine`, `fluke flap`, `boca`, `color`, `turbina`, `beat`, `blink eye_yaw eye_pitch`.
Minimum for the digital whale in TouchDesigner: all of the above plus `x y z yaw`. The behaviours as 40 s curves per mood are
in `comportamientos_y_docs/curvas/` if you prefer to play them yourself and only take `animo` from the stream.

## 4. Her own initiative

When nobody has been in front for 20 s (`--iniciativa`, 0 = never), every 32 s she picks the mood she has done least lately
as a goal and asks the H-JEPA which mood-action leads there; `fuente` becomes `ella`. With a person in front, their face rules.

## 5. Rebuilding the model (if you ever need to)

The H-JEPA is retrained from the assembled training set in a few minutes on CPU:
```
venv\Scripts\python hjepa_entrenar.py            -> modelos/hjepa.pt   (prints the honest evaluation at the end)
```
`modelos/jepa_datos.npz` is that set (60 h of bodies: dancers, swimmers, divers, tagged whales, emotion datasets, the
performers). To add new bodies, `jepa_datos.py` rebuilds it from the raw datasets (not included: ~10 GB; Violeta has them).
The mood-from-face recogniser retrains nightly with `aprender.py` from that day's visitors. `docs/HOW_SHE_WORKS.md` has it all.

## 6. Updates from Violeta later

Her code lives at github.com/violetajaguar/yakumama; today's state is the tag `dan-2026-10-17`. Two ways to get updates:
- she adds you as a collaborator on that repo and you run `git pull` inside `Yakumama/` (models included, they are in the repo);
- or she sends a zip of what changed since the tag (`git archive` of the changed files) and you copy it over `Yakumama/`.
`cerebro_ballena.py` regenerates `comportamientos_animos.py` from `receptor_ballena.py` automatically when both are present,
so a new receiver from her is enough to update the behaviours.

## 7. If something fails

- Camera not found: USB3 cable, another port, close other apps using it.
- "cara NO VISTA": the person is too far, too dark or off-centre; about 1 m works. Body needs the whole person in frame.
- No `prevision` in the packet: the H-JEPA needs 32 s of body first, or torch is missing (run with `--sin-jepa`).
- Low rate (< 8 packets/s on 9998): close GPU/CPU work. The brain always sends 30/s regardless.
- Nothing on 9994: start `cerebro_ballena.py` by hand in a terminal to read its one-line-per-second log.
