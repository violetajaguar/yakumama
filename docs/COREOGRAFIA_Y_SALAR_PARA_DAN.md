# Yakumama · choreography and her world, for Dan (17 October 2026, night)

## 1. Choreography: a score she performs

Violeta writes a piece as a text score, one line per phrase; `coreografia.py` performs it by driving the whale phrase after
phrase (it sends the same packets a dancer would, to UDP 9998, so the brain and TouchDesigner receive it like anything else).

```
<mood> <seconds>s [inventa | frases | cuerpo:<dancer file or performer take>] [hacia:publico|fondo|izquierda|derecha|casa|alrededor] [sin-acro] [poema]
```
- `inventa` (default): the diffusion invents her body for the phrase. `frases`: real phrases retrieved along her plan. `cuerpo:X`: a real body translated onto her.
- `hacia:` where she goes in the salar during the phrase. `publico` = toward the viewer and facing them; `fondo` = away; `izquierda` / `derecha`;
  `casa` = the centre; `alrededor` = a slow round of the salar (60 s). Without it she wanders where the invented body takes her.
- `sin-acro`: no acrobatics in playful (otherwise every 5-9 s she turns on her side, goes belly up or barrel-rolls).
- `poema`: she writes and reads a new poem during the phrase (through the app on Violeta's machine; harmless elsewhere).
- `repetir` as the last line loops the piece. `#` starts a comment. Scores live in `coreografias/<name>.txt`; `coreografias/ejemplo_salar.txt` is the example.

Run: `python coreografia.py coreografias/ejemplo_salar.txt` (next to the brain, with no recorder running, or in parallel: the packets
carry `canales` and the brain lets raw channels rule). Progress is written to `/tmp/ballena_coreografia.json`.

In the stream (UDP 9994) you see it as: `bailarin` = `coreo:<piece>:<phrase>`, `cuerpo_jepa` = 1 while she invents, `x y z yaw` = her travel.

## 2. Her world: the salar

She lives in the Salar de Uyuni: a white salt flat with crust lines, a ring of mountains, Tunupa to the north. In Blender it is
`Huk/salar.blend` (also merged into `whale.blend`); for TouchDesigner, `salar.glb` and `salar_spec.json` in this folder give the same
geometry. Everything in Blender units (her body is ~8 units long).

| element | geometry |
|---|---|
| salt | plane 400 × 400 at z = 0 (in whale.blend at z = −2.6: she floats 1.3 above it); colour (0.93, 0.94, 0.95), roughness 0.18, a little metallic (wet mirror) |
| crust lines | a 120 × 120 grid wireframe, thickness 0.06, 0.01 above the salt, colour (0.82, 0.84, 0.86) |
| mountains | 28 cones on a ring, radius 140-175, heights 18-45, base radius 30-60, random x-scale 0.8-1.5; colour (0.42, 0.33, 0.28) |
| Tunupa | the volcano: cone at (0, 190), height 70, base radius 90 |
| sky | flat colour (0.55, 0.72, 0.95); mist from 30 to 160 units so the mountains sit far |
| sun | energy 3.5-4, elevation 50°, azimuth 30° |
| her home | (0, 0, 1.5): where she returns; the viewer stands at −Y, she faces +Y at rest |
| camera | (0, −14, 4.5), tilted 78° (looking slightly down), lens 35 mm |
| her travel | inside a circle of radius 2.0 units around home (the mountains are the edge); 1 m of a dancer's floor = 0.8 units |

Mood colours, turbine speeds and heartbeat strengths are unchanged (`COMPORTAMIENTOS.md`). New since the evening: in sadness her
skin shifts through shades on a 16-s cycle and only the **fins** fade to transparent at the lightest point (the body never does);
the mouth never opens past 0.5; when she invents, the spine also sways sideways, the head rolls and yaws, the fins sweep forward and back
with her speed and the flukes steer: stream fields `spine_lado[6]`, `head_roll`, `barrido_l/r`, `fluke_lado` ride inside `canales` when present.

## 3. Files in this part
```
Yakumama/coreografia.py            the score player
Yakumama/coreografias/             the scores (ejemplo_salar.txt)
Yakumama/jepa_mueve.py             mover: --hacia, --acro, --segundos, acrobatics, more axes
Yakumama/carrusel.py               app: choreography panel
Yakumama/receptor_ballena.py       Blender: more axes, sadness shades, fins translucent, raw channels and travel
Yakumama/docs/COREOGRAFIA_Y_SALAR_PARA_DAN.md   this note
salar/salar.blend · salar.glb · salar_spec.json · salar_vista.png     her world
```
