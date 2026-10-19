# Yakumama on two machines · Mac mini (M4) + PC with TouchDesigner · for Dan · 18 October 2026

The Mac mini is her: the eye, the brain, her voice, her memory. The PC is the room: TouchDesigner, the screen, the joystick.
Nothing of a visitor ever reaches the PC: only what she does, as numbers. The ESP32s talk to the Mac directly over WiFi.
Put the three on the same network and give the Mac and the PC fixed addresses. Below I use **MAC = 192.168.1.10** and
**PC = 192.168.1.20**; replace with yours.

```
 OAK-D ──► Mac mini: grabar_ballena.py (eye, visitor mode) ──► cerebro_ballena.py (brain) ──► UDP PC:9994 ──► TouchDesigner
                     ▲ UDP MAC:9995  ◄── touch ESP32 (flowers, jewel)              └──► UDP ESP:9994 (moves) and ESP:9994 (glows), if they listen directly
                     ▲ UDP MAC:9995  ◄── PC / TouchDesigner (joystick camera: cerca, mira, palanca)
                     laya_sentidos.py (second opinion) · ollama (poems, moondream) · her voice (speakers on the Mac, or the PC if you route audio)
```

## A. Mac mini, once

1. Unzip the three packages side by side: `Yakumama_Barcelona_2026-10-17` (base: code, models, `Huk/`), then copy today's
   `Yakumama_actualizacion_Dan_18oct/Yakumama/` over it, and `Yakumama_voz_lengua_poemas_Dan` (her voice: `Huk/voces` with the
   Kokoro files, `Huk/whale sound`, `lengua.py`, `voz_ella.py`, her poems). Keep `Yakumama/` and `Huk/` next to each other.
2. Python 3.11. Inside `Yakumama/`:
   ```
   python3.11 -m venv venv
   venv/bin/pip install depthai==2.32.0.0 mediapipe==0.10.14 opencv-python opencv-contrib-python numpy scikit-learn pyserial sounddevice torch
   python3.11 -m venv venv_datos
   venv_datos/bin/pip install kokoro-onnx onnxruntime soundfile opencv-python-headless depthai==2.32.0.0 blobconverter laya-mlx
   ```
   `torch` lets the brain load the H-JEPA; without it run the brain with `--jepa 0`. `laya-mlx` is Apple Silicon only (fine on the M4).
   **Laya's weights are in the package** (`Yakumama/modelos/laya-typed-decisions-mlx`, 807 MB), so `laya_sentidos.py` loads them from
   there with no download. (If that folder were ever missing it would fetch `aac6fef/laya-typed-decisions-mlx` from Hugging Face.)
3. `brew install ffmpeg ollama`, then `ollama pull qwen3.6` (her soul, 23 GB) and `ollama pull moondream` (her eye on the hands, 1.7 GB).
4. Plug the OAK-D into a USB3 port. Check: `venv/bin/python -c "import depthai as dai; print(dai.Device.getAllAvailableDevices())"`.
5. Firewall: allow incoming UDP 9995 on the Mac (System Settings → Network → Firewall → options, allow Python), or turn it off for the show.

## B. Mac mini, every day (four terminals, or one launcher)

```
ollama serve                                                                    # 1: her soul (poems) and her eye on the hands
venv/bin/python grabar_ballena.py --espejo 127.0.0.1:9997 --panel 8765          # 2: the eye; panel http://localhost:8765, window /ventana
venv/bin/python cerebro_ballena.py --entrada 9997 --salida 192.168.1.20:9994 --callado      # 3: the brain -> TouchDesigner (add --salida <esp>:9994 per ESP32 if they listen directly)
venv_datos/bin/python -I laya_sentidos.py                                       # 4: Laya, her second opinion (optional)
```
Recorder flags (all on by default): `--voz` (reads each poem aloud in her language), `--sonido` (mood sounds), `--ojo-objeto` (what the
hands hold), `--panel-red` (the panel and the window are served on the network), `--musica 0` (base track off). Her voice and sounds
come out of the Mac's audio output: plug the room's speakers there, or send the Mac's audio to the PC however you prefer.
**Her window on the PC's screen**: open `http://192.168.1.10:8765/ventana` in a browser on the PC (full screen, black background):
her poem in her language, large; Spanish and English small; her last line; and the strip with her mood, what she sees, what she decides,
what she draws. The Mac's firewall must allow 8765 as well as 9995.

## C. PC with TouchDesigner

- **UDP In DAT on port 9994** → JSON per row (one packet per frame, 30/s): `animo color turbina latido pulso x y z yaw pitch roll jaw
  flap fluke aleta_l aleta_r blink eye_yaw eye_pitch` and the new ones: `decision decision_prob come rehusa lente ve_hermana dibujo
  ofrenda tacto tacto_zona personas_n foco_razon distancia_m`. Fields in `PROTOCOLO.md`; how to map them in `ACTUALIZACION_DAN_18oct.md`.
- **UDP Out DAT to MAC:9995**, ~10/s or on change, the joystick camera:
  `{"camara": {"cerca": 0.8, "mira": 1}, "palanca": 1}` (cerca: 0 far … 1 on her face; mira: 1 if she is in view; palanca: 1 while the stick moves).
- Remember: `lente = 1` is for the digital whale only. The sister on the table never refuses a lens.

## D. The three ESP32s (WiFi, same network)

- **Feels** → `MAC:9995`, ~20/s: `{"flores": [0..1 per stem], "joya": 0..1, "joya_tiron": 0/1, "presencia": 0..1}`.
- **Moves** and **Glows**: they listen to her stream. Either the brain sends them a copy (`--salida 192.168.1.31:9994 --salida 192.168.1.32:9994`)
  or TouchDesigner forwards what it needs. Pins, calibration and fields in `HERMANA_ESP32_PAQUETES.md`.

## E. Test the whole loop without the sister built

On the Mac: `venv/bin/python pruebas/escena_hermana.py` plays the sister's senses in phases (gentle flower, palm, jewel pull, soft
jewel, fish, scorpion, joystick). On the PC you should see on 9994, in order: calm · sad with `rehusa 1` · angry with `rehusa 1` · calm ·
feeding with `come 1` · alert with `rehusa 1` · stay and invite. By hand from the PC, to the Mac: `{"ofrenda": "pez"}` feeds her,
`{"ofrenda": "no_pez"}` makes her refuse, `{"ofrenda": "nada"}` clears.

## F. What stays on the Mac and nowhere else

`datasets/visitas/`, `datasets/memoria.json` (faces as 210 numbers), `datasets/decisiones.jsonl` and `datasets/laya.jsonl` (what she
decided and what happened), `modelos/decisiones_personas.json`. Run `venv/bin/python decisiones.py --aprender` at closing time so she
learns from the day; `venv/bin/python aprender.py` retrains her mood recogniser as before.
