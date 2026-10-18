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

Her world is Violeta's own generative Salar de Uyuni (sala.red/laboratorio/salar-de-uyuni, embed sala.red/embeds/salar.html; a copy of the
page is `salar/salar_sala_red_embed.html`): zero models, zero textures, math and real data. Its exact functions are ported into Blender
(`whale.blend`, collection `Salar`; also `salar/salar.blend`) and `salar/salar_glb` + `salar/salar_spec.json` carry the same world for TouchDesigner.
All in metres; she is ~8 m long; +X east, +Y north; the viewer stands south.

| element | geometry (from her script) |
|---|---|
| salt | plane 12,000 m; crust = Voronoi distance-to-edge on p×0.55 (polygons ~2 m), ridge bump and dark lines; puddles are mirror where fbm > 0.72; wet apron around the island; seasonal water 0..1 (0.08 now) |
| island (Incahuasi) | centre (35, −20) salar coords, radius 78, height 15; heightfield `islandH` in the spec; cacti, paja brava, yareta, boulders live on it |
| mountains | a ring at R = 5,200 m, 220 segments, foot at −8, crest `mtnH(az)` 70-230 m with an open gap WNW (where the sun sets) and **Tunupa** rising to +820 at north; rock colours (0.33,0.21,0.30) to (0.48,0.30,0.33) |
| sky | a 7,000 m sphere; haze fog `1 − exp(−d·0.0011)`; the sun follows its real arc at Uyuni (lat −20.13) at live local time; wind from the hourly Uyuni record |
| her home | Blender origin = salar point (−60, 0): on the salt 40 m west of the island; the salt is at z = −2.6 under her; she travels inside 2 m of home |
| camera | (0, −14, 4.5), tilted 78°, lens 35 mm, clip 20 km |

In Blender today: salt with Voronoi crust and puddles, the island mesh, the mountain ring with Tunupa, sky, mist, a fixed afternoon sun.
Not yet: the cacti and plants, the live sun and wind. `salar/salar_vista.png` is a frame from her camera.

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
