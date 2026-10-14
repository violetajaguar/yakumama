# Yakumama → TouchDesigner / physical whale

What's in this package and how the two whales stay in sync.

## 1. The live stream (both whales listen to the same thing)

Every sender in Yakumama emits one JSON packet per UDP datagram at 30 Hz (fields in `PROTOCOLO.md`). Each sender
takes `--espejo host:port` to send a copy to your machine at the same time as Blender, so the physical whale and
the 3D one react to the same packet:

```
venv/bin/python grabar_ballena.py --espejo 192.168.50.20:9998        # live performer (camera + EmotiBit)
venv/bin/python generar_animo.py angry --espejo 192.168.50.20:9998   # the net performing a mood
venv/bin/python reproducir.py sad_002 --espejo 192.168.50.20:9998    # a recorded take
```

In TouchDesigner: UDP In DAT on that port → JSON DAT (or a Script DAT with `json.loads` per row).

## 2. The mapping (what the Blender whale does with the packet, so yours can do the same)

- **Mood** (`actor_animo`): one of `calm singing playful curious feeding sad angry alert diving surfacing`.
- **Colour** per mood: `colores_rgb_0_1` in `yakumama_parametros.json` (calm silver, singing violet, playful orange,
  curious yellow, feeding green, sad near-black, angry red, alert pink, diving navy, surfacing cyan). Fade ≈ 1 s.
- **Heartbeat**: a pulse at `emotibit_hr` beats per minute, shape `max(0, sin(phase))^4`, visible strength
  `LATIDO_ANIMO[mood] × (0.5 + 0.5·arousal)` where `arousal = clamp(0.6·(hr−60)/60 + 0.4·(eda−2)/8)`.
  Calm ≈ 0.1, angry/feeding = 1.0. Values per mood in the JSON (`latido_fuerza_por_animo_0_1`).
- **Tail / turbine**: speed per mood in rad/s (`cola_turbina_rad_por_s_o_pulso`): calm 0.6 … angry 7.0; in singing
  **one turn per heartbeat**. Multiply by `tempo = clamp(hr/75, 0.6, 1.6)`.
- **Tempo and energy**: everything rhythmic runs at `tempo`; fin amplitude grows with `(hr−60)/60`; skin conductance
  above 2 µS adds a fine tremor to the head (`tension = (eda−2)/8`).
- **Face**: `jaw_open`, `blink` (0/1, held 5 frames), `brow_up/down`, `mouth_sad/smile`, `eye_yaw/pitch`.
  The mood also carries a base face (see `comportamientos_descripcion`), the performer's goes on top (`max`).
- **Fins**: `l_palm_y`/`r_palm_y` (0 top … 1 bottom of the camera image): fin flap = `(0.5 − y) × 1.0` rad;
  left higher than right = bank.

## 3. The neural net (performs a mood in the performer's style, no camera needed)

- `yakumama_modelo.py` + `modelos/movimiento_pesos.npz`: NumPy only. `Modelo().paquete(mood, t)` returns a packet.
- `modelos/movimiento.pt` (PyTorch) and `entrenar_movimiento.py` if you want to retrain.
- `modelos/animo_rf.pkl` + `entrenar_animo.py`: the mood recogniser (scikit‑learn) from 2 s of face/hands.

## 4. The data

`datasets/cara` and `datasets/cuerpo`: 26 takes, 63 min, 30 lines/s, face and body aligned by `t`. Biometrics valid
in the second‑session takes (`_002`+); see `datasets/NOTAS.md` for the per‑take verdicts. `docs/LOGICA.md` has the
whole logic in Spanish.

## 5. EmotiBit direct

`emotibit_cliente.py` talks to the EmotiBit over WiFi without the Oscilloscope (hello / connect / ping, CSV
packets). The physical whale can read the sensor directly with it if the recorder isn't running.
