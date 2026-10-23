# What Dan's PC package contains · assessed 20 October 2026 (evening)

The package `Yaku_PC_2026-10-20.zip` (3.6 GB) is Dan's whole TouchDesigner project as it left the failed PC (CPU i7-14700K,
Intel diagnostic failures logged in `docs/cpu_rma_2026-10-20/`). It lives in `fuentes/Yaku_PC_2026-10-20/Paqarina_TD/`.
Integrity verified against its own git commit `44fdee5` (see COMO_CORRER_EN_MAC.md). This page says what is IN it, for Violeta.

## 1. Dan's side (TouchDesigner whale, the room)
- `ballena_td.py` (207 KB): THE renderer-brain. Modes `--idle --run --brain` and **`--violeta`** (her brain decides on UDP 9994,
  his renders into TD and the sculpture). In `--violeta` his crowd state machine, mood vector, Qwen vote and net stand down; what stays
  his: bone axes, salt floor, swim wave, joystick-camera, sculpture link, sound, touch reflex. Renderer-side fixes he made while
  watching her stream (17-19 Oct): heading averaged over 10 s (her ballet reversals turned her on the spot), 15°/s turn cap,
  1.5 s crossfade on mood change, the visitor's resting posture learned over 10 s and removed (she was nose-down mirroring a seated
  body), jaw chain sign (tongue through the jaw), propeller inertia (1.5 s up / 3 s down) and the sculpture tail's hysteresis,
  her rolls finishing to upright, fins link by link from `aleta_l/_r`, the tail from `turbina_viva`.
- `ballena_crowd.py` (OAK-D, MobileNet person detector + stereo → perception on UDP 5005), `ballena_joy.py` (the radio bridge,
  CP2102, ↔ her board over ESP-NOW), `ballena_alma.py` (his port of her alma: song, lexicon, memory, ear), `ballena_sound.py`,
  `ballena_panel.py` (tkinter operator panel), `ballena_ventana.py`, `ballena_vista.py` (relay to the 2.4" screen), `ballena_phys.py`
  (old Wi-Fi sculpture, unused), `ballena_body.py / sun / weather / palette`.
- `td/` (47 files): the scene builders (`setup_*.py`, run inside TD), `relocate_paths.py`, `td_bind_osc.py`, `setup_projector.py`
  (Epson full-screen), **`setup_dibujo.py` + `shaders/dibujo_paint.frag`: her Nazca lines on the salt (built 19 Oct, NEVER yet seen
  in TD)**, `setup_alma_text.py` (her words over the render), diagnostics `diag_*.py`, `scene_report.py`, recorders.
- `firmware/`: `ballena_joy_esp32` (HER BOARD: eyes, fins, N20 tail, touch strips, stick; USB serial protocol `E,...`), `vista_esp32`
  (the 2.4" ILI9341 "constellation" screen; flashed 19 Oct to DevKit MAC 68:09:47:b9:fe:a0; Wi-Fi UDP 4210 or USB 921600),
  `ballena_esp32` (old Wi-Fi sculpture). `hardware/`: the joystick grip (blend, stl, 3mf).
- `docs/`: **`RUNNING.md`** (every process, ports, env vars, the `--violeta` runbook §"Running with Violeta's brain", la vista §6b,
  Nazca §7b), `touchdesigner_setup.md` (gates, GLSL lessons), `first_connection_2026-10-07.md` (narrative, for funders),
  `skindeform_bug_report.md` (TD bug), `ctrl_story_resonite_worlds.md`, `mozfest_provides.html`, `paqarina_rider.html`.
- **`ROADMAP.md` (146 KB) is Dan's complete dated journal, 13 Sep → 19 Oct.** Everything he decided and measured is there. Entries that
  concern her directly: 2026-10-16 "Dan's three decisions", 10-17 night (option 1 live; her hops kept as a trait), 10-18 (joystick
  = camera; the departed visitor bug; propeller; her 18 Oct brain + voice installed), 10-19 (Laya on the mini; la vista; her words;
  Nazca lines).
- `CLAUDE.md` (his architecture rules), `Stages of Mood DEV.md`, `rig.json`, `rest_offsets.json`, `td_name_overrides.json`,
  `whale.fbx/glb/blend`, `Cacti_Models/`, `Backup/` (20 numbered .toe snapshots), `Violeta_Code/YakuMama.zip` (her old code).

## 2. Her side inside his package (`Neural_Net/`) — what she does NOT have on this Mac
Her deliveries to him, as received: `Yakumama_UPDATE_para_Dan` (17 Oct), `Yakumama_actualizacion_cerebro`, `_17oct_noche`, `_18oct`
(with Laya's 807 MB weights), `Yakumama_voz_lengua_poemas_Dan`, `Yakumama_palabras_Dan_19oct`, and `Yakumama/` (his working copy of
her 14 Oct Blender project; the Sanam motion net was copied in there on 20 Oct). The one that matters is
**`Yakumama_Barcelona/Yakumama_Barcelona_2026-10-17/`: her installed code with HIS changes (last 19 Oct 15:27).** Against this Mac's
files (20 Oct) the differences are, file by file:
- `cerebro_ballena.py` (+118 lines): **SHE INVENTS ALL THE TIME** (decided with Violeta 17 Oct: the diffusion drives her body for the
  mood of the moment, in a background thread, 12 s first then 32 s, 1 s crossfade); **WHO IS HERE NOW** (a field not received for 2 s
  expires; a face whose yaw/pitch/jaw do not move for 2 s is a lost face — fixes "she was never alone": the departed visitor kept
  her curious and nose-down for minutes; **this Mac's copy still has that bug**); refusals / lens / eat now also scale `turbina_viva`
  and fold `aleta_l/_r` (so a refusal stops the tail while the diffusion drives); **LA VISTA** (the line for the 2.4" screen, env
  `YAKUMAMA_VISTA`); `YAKUMAMA_DIBUJO_PRUEBA` (draw a figure on demand); a "[sees]" diagnostic line every 5 s.
- `grabar_ballena.py` (96 lines): `gente`/`gente_t` for the screen (everyone the crowd eye sees, chosen one marked); Ollama host +
  model from `YAKUMAMA_OLLAMA`/`OLLAMA_MODEL` for poems and English; voice through sounddevice on Windows (afplay on Mac, unchanged);
  MediaPipe model loaded from bytes (Windows path bug). Hers is newer on the offerings side (20 Oct: 29 creatures) — kept.
- `difusion_ballena.py` (Dan 20 Oct 13:38): device = cuda → mps → cpu (hers: cpu only; MPS helps on this Mac).
- `decisiones.py`, `laya_sentidos.py`: Dan's are OLDER than hers (hers have the 29 creatures, `ofrenda_id`, `reaccion`): keep hers.
- `comportamientos_animos.py`: identical (only line endings). `banco_frases.py`, `hjepa_ballena.py`: hers newer (CLI args, cuda).
- `Huk/ballena3.py`: `YAKUMAMA_SIN_SERIAL=1` skips the serial-port search (it stole the radio bridge's port). `Huk/voz_ella.py`: voices
  folder next to the file, then ~/Desktop/Huk/voces. `Huk/yakumama_alma.py`: Ollama host from `YAKUMAMA_OLLAMA`.
- **New file: `laya_puente.py`** (19 Oct): carries /tmp/ballena_cerebro.json → mini (UDP 9981) and Laya's answer back (9982). Copied to
  this folder 20 Oct; the mini's end is running (see COMO_CORRER_EN_MAC.md).
- The same changes as patches for her: `Neural_Net/para_Violeta_parches_17oct_noche.diff`, `_hasta_18oct.diff`,
  `_18oct_instalacion.diff`, `parche_dibujo_prueba_19oct.diff` (each with a header saying what and why).

**Merge, prepared 20 Oct 18:10, INSTALLED 20 Oct ~18:40** (backup of the replaced files in `entregas/respaldo_pre_merge_20oct/`): `entregas/merge_dan_20oct/` — three-way merge (base = her 18 Oct delivery) of
`cerebro_ballena.py`, `grabar_ballena.py`, `decisiones.py`, `laya_sentidos.py`: zero conflicts, all compile; plus Dan's
`difusion_ballena.py`. Install = copy over `~/Desktop/Yakumama/`, then `venv/bin/python decisiones.py` and `cerebro_ballena.py --prueba`.
The three Huk one-liners are applied by hand.

## 3. Dan's notes addressed to Violeta (from ROADMAP.md)
- **Laya's scores lean the wrong way** (19 Oct): a painted fish at the mouth → maltrato 0.64 / regalo 0.31; a gentle fingertip on a
  flower → maltrato 0.47; laya-mlx warns the checkpoint's temperatures are clamped. It only leans her, but backwards. (My own test
  20 Oct: a gentle flower touch → maltrato 0.48 again.) Fine-tune on her log after Barcelona, or lower its weights.
- **Keep her hops when alert** (toprock bounce ~1.2/s from the choreography): "cute, idiosyncratic"; do not smooth her height.
- **Posture baseline at the source**: her brain maps absolute lean, so a seated visitor reads as a crouch; he removes it renderer-side
  and suggests she do the same in `cerebro_ballena.py`.
- **The 18 Oct brain had the "never alone" bug** (fixed in his copy, see §2).
- Decisions shown on the screen: only `distancia` and `con_cuerpo=dibujar` act today; `voz` and the other body answers are stated
  intentions nobody reads yet.
- Two-machine layout as he ran it: PC = TD + his brain + her recorder + her brain; mini = qwen35-local + Laya. Her DOS_MAQUINAS plan
  (all of her on the mini with qwen3.6 23 GB) "does not fit a 24 GB Mac". Now the Mac (this one) takes the PC's role.

## 4. Devices he names (for the room)
- Mac mini `violetas-mini` 192.168.50.104 (wired, MAC d0:11:e5:03:a1:cb): Ollama `qwen35-local`, Laya end of the bridge.
- Radio bridge ESP32 (CP210x, MAC c8:85:41:c2:b0:fc) — here `/dev/cu.usbserial-0001`. Her board firmware v26/v29; handheld stick (ESP-NOW).
- La vista DevKit (MAC 68:09:47:b9:fe:a0), flashed 19 Oct, was on the bridge's cable.
- Epson projector on HDMI (TD `window1`, `td/setup_projector.py`); **table projector D013D (Android) 192.168.50.15** shows her window
  `http://<this Mac>:8765/ventana` in its browser (a USB mouse gets past the Google sign-in). Answers ping from here (20 Oct).
- Venue: a 95-inch screen and a table (ROADMAP 2026-09-19).

## 5. Not yet verified anywhere
~~Her Nazca lines in TD~~ (Violeta has seen her draw on the salar, with the camera rising to watch: verified 20 Oct); la vista live with her brain (only the test figure was seen); moondream
on the hands was off on the PC (`--ojo-objeto 0`); ~~the joystick camera → her 9995~~ (added to `ballena_td.py` 20 Oct, tested); a poem triggered live by a visitor.
