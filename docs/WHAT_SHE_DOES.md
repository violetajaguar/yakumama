# Yakumama — what she does, for Dan (17 October 2026)

**One sentence:** she reads the person in front of her, decides a mood, and performs that mood with a whale's body,
colour and eyes; everything she decides arrives at your side as one JSON packet per frame over UDP, so the physical whale
can do the same thing at the same moment.

## What she senses
- A camera (OAK-D) gives her the face (52 expression values, head turn, gaze, blink), the hands, and the whole body
  (26 joints in 3D, pose). At distance she cuts the head out of the body box and reads the face from that.
- An EmotiBit on the performer's wrist gives pulse, skin conductance and temperature. In Barcelona there is no EmotiBit:
  her style net fills in a pulse from the mood and the performer's style.

## What she decides (recorder, `grabar_ballena.py`)
1. **Mood**, every 0.5 s, from 2 s of face + hands: a random forest over 10 moods (calm, singing, playful, curious,
   feeding, sad, angry, alert, diving, surfacing). ~70 % right on a person she knows, ~34 % on a stranger. For a
   visitor she only switches mood after 3 s of consistent reading. → packet field `actor_animo`.
2. **Who they move like**, among the four recorded performers (90 % right): → `estilo`. It sets how big she moves.
3. **Whether she knows them**: a face signature (210 distances between face points, no photo) matched against her memory.
4. **What to write**: a line and a poem in the window (Qwen, local), seeded with what people have said to her.

## What she does (receiver, `receptor_ballena.py`, 30 fps; the same packet you receive)
- The dominant mood picks one of ten **behaviours**, each modelled on a real humpback behaviour and measured so that no
  two look alike: logging, song posture, breach with two rolls, spyhop, lateral lunge, sinking, lobtail, scanning,
  high-fluking dive, blow. Curves for each are in `curvas/<mood>.csv` (40 s at 30 fps) and the numbers in
  `COMPORTAMIENTOS.md`.
- On top of the behaviour: the performer's face (mouth, blink, brows), the **eyes** (gaze and blink from the performer;
  per-mood eye curves from Dan's takes are in `ojos/<mood>.csv`), the heartbeat (a pulse through fins and head at the
  real pulse; tempo = pulse/75), and the body of whoever conducts her (lean, roll, turn, height, energy → `cuerpo_*`).
- **Colour**: one per mood, no two alike (see table in `COMPORTAMIENTOS.md`); the visitor's clothes if she likes them.
- **Tail turbine** speed per mood; **sounds** per mood (`whale sound/`), played outside Blender.

## What she is learning (not yet in the live loop)
- A hierarchical JEPA trained on 60 h of bodies (dancers, swimmers, divers, real tagged whales, people expressing
  emotions, and the performers head to toe) predicts her body 16 s ahead and plans "dive" correctly. A probe on it reads
  a mood from 4 s of body alone 55 % of the time (chance 10 %). When wired in, it becomes her own initiative when nobody
  is in front of her.

## What you receive
`PROTOCOLO.md` describes every field. Run the recorder with `--espejo <your-ip>:<port>` and you get the identical
stream. Minimum to drive the physical whale: `actor_animo` (mood), `cuerpo_pitch/roll/yaw/profundidad/energia`, `jaw_open`,
`blink`, `eye_yaw`, `eye_pitch`, `emotibit_hr`, plus the mood's colour and turbine speed from `curvas/comportamientos.json`.

## In this folder
`COMPORTAMIENTOS.md` (the ten behaviours, numbers, colours) · `curvas/` (per-mood CSV + JSON) · `ojos/` (per-mood eye
curves from a performer) · `videos/` (Blender renders of each behaviour; colours in the videos are from before the final
palette) · `capturas/contacto_animos.jpg` (the ten as they run today) · `PROTOCOLO.md` · `INSTALACION_DAN.md`.
