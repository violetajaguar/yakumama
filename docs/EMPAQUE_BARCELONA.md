# Packing her for Barcelona — two M5 machines, 64 GB each (written 23 Oct 2026)

What she is today lives on two computers (this MacBook and Violeta's Mac mini) plus the hardware on the table. In Barcelona she
runs on two M5 Macs. This is what has to travel, what has to be rebuilt on arrival, and what to decide before leaving.

## 1. The two machines and what goes on each

| Role | Today | Barcelona | Carries |
| --- | --- | --- | --- |
| **A — the whale** | this MacBook (M-series, macOS 26.5) | M5 #1 | TouchDesigner + Dan's package, her brain, her eye (OAK-D Lite), the ESP32 bridge, the panel, the watchdog, the data page, sound out |
| **B — the mind** | Violeta's Mac mini (192.168.50.104) | M5 #2 | Ollama (qwen35-local, her poems and Dan's cognition), Laya (MLX, 807 MB weights), the room camera (OAK-D Pro, ballena_crowd), the table screen (vista) |

Both machines on one router with fixed addresses. Today's addresses are hard-coded in four files (`correr_todo.sh`, `correr_td.sh`,
`grabar_ballena.py`, `prueba_datos.py`: 192.168.50.104 = mind, 192.168.50.172 = whale) and in the mini's `laya_puente.py mac <ip>`.
Either keep the same subnet and addresses on the Barcelona router (simplest: bring the router), or change those four lines.

## 2. What to copy from THIS Mac (machine A)

| What | Where | Size | In git? |
| --- | --- | --- | --- |
| Her code | `~/Desktop/Yakumama` (repo violetajaguar/yakumama) | small | yes, push before leaving |
| Her models | `modelos/` | 1.5 GB | mostly NOT (jepa_datos 192 MB, ofrendas_emb 166 MB, hermana_dorada.blend 148 MB, ballena_datos 58 MB, animo_rf 38 MB, cara_banco 2 MB, difusion .pt 8 MB, hjepa, decisiones_pesos.json) — copy the whole folder |
| Her memory | `datasets/` | 2.7 GB | NO — decisiones.jsonl (her decisions and rewards), cara/ (426 faces), cuerpo/ (dances), dibujos/ (102 drawings: json + svg + png), memoria.json, visitas/ — copy whole |
| Dan's package | `fuentes/Yaku_PC_2026-10-20/Paqarina_TD` | 5.0 GB | NO (fuentes/ is ignored) — the .toe project, whale2.fbx/.glb/.blend, td/ (shaders, obj, setup scripts), ambiente/ (372 MB of sound), rest_offsets.json, td_name_overrides.json, rig.json, whale2.fbm textures, firmware/ |
| Offering photos | `ofrendas_fotos/`, `docs/ofrendas/` | ~30 MB | no |
| Music / sound library | `~/Desktop/Huk/whale sound/musica` | small | no |
| Blender files from Brian | `fuentes/blender/joya+ballena5.blend` (moved from the Desktop 23 Oct) | 65 MB | no |

Python environments do NOT travel: `venv` (symlink to Huk/venv, 4.6 GB), `venv_td` (212 MB), `venv_datos` (848 MB) are built for this
Mac's Homebrew Python 3.11. On the M5: install Homebrew, Python 3.11, Blender, TouchDesigner 2025.33230, ffmpeg; recreate the three
venvs from `requirements.txt` (hers) and Dan's requirements (`fuentes/.../requirements.txt`), plus depthai/blobconverter for the OAK-D
and `laya-mlx` for machine B. Plan half a day for this and test with `./correr_todo.sh --estado`.

## 3. What to copy from the MINI (machine B)

`~/DAN/Ballena` (Laya: `laya_sentidos.py` — the Mac's copy is the current one — `laya_puente.py`, its venv, `modelos/laya-typed-decisions-mlx`
807 MB if present, else the hub id downloads it), the Ollama models (`ollama pull qwen35-local` or copy `~/.ollama/models`, several GB),
`ballena_crowd.py` and the OAK-D Pro's blob, `ballena_panel.py`, `ballena_vista.py` + the vista ESP32. The mini was off the network at the
time of writing; inventory it before packing.

## 4. Hardware list

OAK-D Lite (her eye) + tripod; OAK-D Pro (the room) + tripod; the printed whale with its ESP32 board (USB cable to machine A, the
bridge `ballena_joy.py`), its servos' own 5 V supply; the golden sister with the touch board (flowers, jewel) if it travels; the vista ESP32
screen; the LED strips' supply; a projector or display (today 1920x1080); speakers (the JBL never paired with this Mac: bring a wired
speaker or test pairing on the M5 first); **a microphone** (new: see 6); the EmotiBit if a performer wears one; the router; power
strips; a UPS if the venue allows (Dan's rider).

## 5. Licences and limits

- TouchDesigner here runs **Non-Commercial**: output capped at 1280x1280, and Movie File Out blocked. A show on a projector wants the
  Commercial key (Dan's rider flags it). Decide before leaving; the key is per machine.
- Blender, ffmpeg, Ollama, Laya: free. Open-Meteo needs internet (weather); without it the salar falls back to climatology.
- Freesound sounds: all CC0 (credits in `ambiente/CREDITOS.md`); Björk's track is hers to clear.

## 6. The microphone (new)

Her ear is Dan's alma (`ballena_alma.oido()` in machine A's renderer): loudness, a bang, someone singing, read from the machine's
default input and sent to her brain as `oido`. A USB microphone on machine A works as soon as it is the default input (System
Settings → Sound → Input) or named with `BALLENA_MIC=<part of its name>` when launching (the alma was calibrated on an ATR2500x at a visitor's distance; a different mic may need its loudness floor re-trimmed); macOS must grant microphone access to the Terminal/app that launches
`correr_todo.sh` (this is the permission we could not grant from the remote session). Test: the data page's "her ear" row and the
`[sees]`/oido values in `logs/cerebro.log` while someone sings.

## 7. Known open items to carry on the list

- The printed whale's SERVO line: it sent `nan` while the servo bus was not answering; since the evening of 23 Oct it reports real
  degrees and temperatures and her brain reads them (`[body]` lines in `logs/cerebro.log`). If it goes `nan` again: power-cycle the
  board, check the servo bus wiring; the bridge ignores `nan` lines.
- Her worlds (23 Oct): `MUNDO=marte ./correr_todo.sh` or `MUNDO=tiupampa` (default salar); TD must have run `docs/td_mundo.py` once
  and been saved. See `docs/MUNDOS.md`.
- NASA FIRMS key for the exile to Mars: `NASA_FIRMS_KEY` (free, https://firms.modaps.eosdis.nasa.gov/api/map_key/), see `docs/MUNDOS.md`.
- Hearts and glitch on the eye screens on a jewel touch: the firmware that did it is not in the package (Dan / Brian).
- The LED strip of the printed whale ignores the colour fields since Dan's 21 Oct reflash and shows its start-up rainbow (fins and eyes obey the same E line; tested 14 and 15 fields on 21 and 23 Oct). Dan's firmware.
- The PBR look, tonemap, haze, shadows: done today; the dials are in `docs/td_ajuste.py`, `td/setup_whale_light.py`, the panel.
- Evaluation mode (`EVALUAR=1`) is on today; read it with `calibracion.py --dias 1` after a day of visitors.
- The TD watchdog relaunches TD at 9 GB when the room is empty for 2 minutes; raise `TD_SUAVE_GB` for long rehearsals.

## 8. Before you leave (checklist)

- [ ] `git push` (code) — the repo has everything except models, datasets, Dan's package.
- [ ] Copy `modelos/`, `datasets/`, `fuentes/Yaku_PC_2026-10-20/Paqarina_TD/`, `docs/ofrendas/`, `ofrendas_fotos/`, the music folder and the Blender files to an SSD (≈10 GB).
- [ ] Inventory and copy the mini (`~/DAN/Ballena`, Ollama models, crowd, panel, vista).
- [ ] Decide the TD licence; install TD + Blender + Homebrew + Python 3.11 on both M5s; rebuild the venvs; run `./correr_todo.sh --estado`.
- [ ] Router with the same addresses, or change the four files.
- [ ] Microphone and speaker tested on machine A with the permissions granted.
- [ ] Firmware sources (`fuentes/.../firmware/`) and the latest sketches from Dan/Brian on the SSD, with arduino-cli, in case a board needs reflashing.
