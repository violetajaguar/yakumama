# Yakumama · update for Dan · 18 October 2026 · how she interacts, the sister's senses, the crowd, her voice, the lens, the drawing

Copy `Yakumama/` over the same folder inside `Yakumama_Barcelona_2026-10-17/` on the drive (files are added or replaced; nothing
else changes). `Huk/` holds two small files for her voice (`lengua.py`, `voz_ella.py`); put them next to the others from the voice zip.
Read `docs/HERMANA_ESP32_PAQUETES.md` for the three ESP32s and every packet field in both directions. This page is what changed today.

## 1. She decides, typed (decisiones.py v2)

Every 4 s, and at once when a touch or an offering changes, her brain answers seven fixed questions with a probability each, never a
sentence (Jev-shaped, local, rules + a nightly fit of her own log):

| question | answers |
|---|---|
| distancia | acercarse · quedarse · alejarse |
| con_cuerpo | bailar_de_vuelta · invitar · observar · **dibujar** |
| voz | poema · canto · silencio |
| memoria | recordar · olvidar |
| color | propio · ropa |
| boca | comer · rehusar · esperar |
| (whom, in a crowd) | feeder · jewel crown · known face · flowers · joystick · closest still · closest |

Her objective is to keep people **engaged, not entertained**: the reward counts time weighted late, distance that shrinks, her touch
words used, stillness of a known face, time on the joystick, a return another day. Crowd, noise, speed and filming count for nothing.

**Fixed refusals, never learned away** (`fijo` in the packet): something in the mouth that is not one of her fish (`no_pez`); a pull on
the jewel (`tiron`); a palm over the flowers (`palma`); **a phone or camera raised at her (`lente`)**: she turns away, still and dim,
silent, until it comes down. She gives her face to eyes, not to lenses. **The sister on the table never refuses the lens**; only the
digital whale does. A forget request is absolute. Whoever pulled or trampled is kept at a distance until the same person tends the
flowers gently (forgiveness).

## 2. What your side sends her (UDP 9995 on the Mac; details and pins in HERMANA_ESP32_PAQUETES.md)

```
{"flores": [0..1 per stem], "joya": 0..1, "joya_tiron": 0/1, "presencia": 0..1}     touch ESP32, ~20/s, analog capacitive
{"camara": {"cerca": 0..1, "mira": 0/1}, "palanca": 0/1}                              TouchDesigner: the joystick camera
{"ofrenda": "pez" | "no_pez" | "nada", "ofrenda_p": 0..1}                              by hand, for tests, until her eye recognises the fish
```
Touch ages out one second after the ESP goes quiet, so a stale reading can never fire a refusal.

## 3. What she sends you (UDP 9994, 30/s, from cerebro_ballena.py) · new fields

| field | meaning |
|---|---|
| `decision`, `decision_prob` | her seven answers and their probabilities |
| `come` | 1 while she eats: jaw at its maximum, `turbina` ×1.5 |
| `rehusa` | 1 while she refuses the mouth / the jewel / the flowers: `jaw 0 turbina 0 flap 0`, `color` almost black, `latido 0.1`, she turns away through `yaw` |
| `lente` | 1 while a lens is raised at her: `turbina` ×0.15, `flap 0`, `color` ×0.25, `latido 0.2`. **Do not apply this one to the sister.** |
| `ve_hermana` | 1 while someone holds the golden sister up in front of her eye (she goes curious; the sister's lights may glow) |
| `ofrenda`, `tacto`, `tacto_zona`, `personas_n`, `foco_razon`, `distancia_m` | what she read: the mouth, the touch word, how many people, why she chose her person, their distance |
| `dibujo` | while she draws: `{"figura", "persona", "i", "n", "x", "y", "pluma", "progreso"}` (below) |

Moods pushed by the senses: a pull on the jewel → `angry`; trampled flowers → `sad`; a fish → `feeding`; a non-fish → `alert`;
a gentle flower or a soft hand on the jewel → `calm`; her sister in someone's hands → `curious`; a lens → `sad` (dark, still, hanging).

## 4. She draws Nazca lines on the salar (and the face of someone she remembers)

When her body decides `dibujar` (alone and quiet for a minute; or a known face standing still for two minutes), she flies low along
the waypoints of a figure with straight runs and sharp turns, and a line of salt and gold grows behind her. Figures (`figuras_nazca.py`):
`espiral`, `zigzag`, `laberinto` (hexagonal), `ballena` (the Nazca whale), `cara`. **The face**: her memory keeps only the 210 distances
between 21 face points of a person (never an image); classical scaling recovers the shape, and she draws it as eight straight strokes
in that person's own proportions. The forget button erases the memory, so the face can never be drawn again. A drawing takes minutes,
fades after an hour, a refusal interrupts it, and she rests 8 minutes between two.

**For TouchDesigner**: while she draws, every packet carries `dibujo`: the current waypoint `x y` (her space, same units as her `x y`),
`pluma` 1 = the line is being drawn toward it, 0 = she flies there without drawing (a new stroke starts), `i/n` and `progreso`, and a
last packet with `"fin": 1`. Draw the line under her with her own `x y` while `pluma` is 1; lift the pen while it is 0. The physical
sister can trace the same figure on her LED lines.

## 5. Her voice, her language, her sounds (the recorder, visitor mode)

Each new poem (Qwen, local) is turned into her language (`lengua.py`) and read aloud in her voice (`voz_ella.py` via `venv_datos`),
only in her language; Spanish and English are written in the window `http://localhost:8765/ventana`. The mood sound plays when her
mood changes; the base track is off by default. Flags on the recorder: `--voz --sonido --musica --ojo-objeto` (1/0).
Needs on the machine: `ollama` with `qwen3.6` and `moondream`; in `venv_datos`: `kokoro-onnx`, `onnxruntime`, `soundfile`,
`opencv-python-headless`, `depthai`, `blobconverter`; `ffmpeg`; the Kokoro voice files in `Huk/voces`.

## 6. Her eye on the hands (the recorder)

Every 3 s, while someone has been seen in the last 15 s, a local vision model (moondream) names what the hands hold (`ve_objeto`); a
phone or camera raised = `ve_telefono` (the lens refusal); a fish = `ofrenda pez`. **The golden prototype is seen by its colour**: a gold
blob above the floor line = `ve_hermana`. The painted fish recogniser is still to come: until then test the mouth by hand (section 2).

## 7. A crowd (MozFest)

`ojo_multitud.py` is the jaguar's camera with the cloud removed: OpenPose on the OAK-D for everyone in view, a stereo depth per person,
sent to the recorder as `{"personas": [...]}`; she attends ONE person, chosen in the order of section 1. It needs the OAK-D for itself,
so today it runs **instead of** the recorder's own camera; folding it into the recorder's pipeline is next. Blob in `modelos/`.

## 8. Test by hand, as we did here tonight

`pruebas/escena_hermana.py` plays the sister's senses on 9995 in phases (gentle flower, palm, jewel pull, soft jewel, fish, scorpion,
joystick) and prints her mood and decisions. With TouchDesigner listening on 9994 you should see: calm · sad+refuse · angry+refuse ·
calm · feeding+eat · alert+refuse · stay+invite. Every one of those matched here, in Blender and in the brain.

## 9. What she keeps about people

Numbers only: a face id, visits, fish given, whether and when they were rough (`modelos/decisiones_personas.json`), and the 210
distances of the face (`datasets/memoria.json`). Never an image. Nothing of a visitor leaves the Mac; the sister only ever receives
what she does.

## 10. Laya, the open Jev, as her second opinion (`laya_sentidos.py`)

Laya (Convai Innovations, Apache-2.0) is a typed-decision model: it never writes a sentence, it answers fixed questions with a
probability. It runs next to the brain, reads the same situation every 2 s and answers four questions: is this visitor engaged, is the
sister being mistreated, should she move away, is she being gifted something. `decisiones.py` adds those four numbers as small weights
to its rules. It leans her; it never decides; the refusals and the forget sit above it. Each reading is logged (`datasets/laya.jsonl`)
beside her own decision, so after Barcelona we can see where it was right and fine-tune it on her log. It needs Apple Silicon
(`laya-mlx` in `venv_datos`, model `aac6fef/laya-typed-decisions-mlx`, ~90 ms a reading). Without it she runs exactly as before.
```
venv_datos/bin/python -I laya_sentidos.py        # keep it running next to cerebro_ballena.py
```
