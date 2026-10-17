# Yakumama · map of every articulation (whale.blend, armature `side_fine.R`, 30 bones) · 17 October 2026

Axes are the bone's local rotation axes as the receiver uses them (`rot(bone, angle, axis)`), radians. Picture: `Yakumama_articulaciones.png`.
Nose points to +Y; the viewer stands at −Y; +Z is up; her left fin (`side_fine.L`) is at −X, her right at +X.

| part | bone(s) | parent | what moves | axis | driven by (receiver) | stream field (9994) | physical whale |
|---|---|---|---|---|---|---|---|
| whole body | `root` | — | pitch nose up/down · roll · turn · position | 0 · 1 · 2 · loc | behaviour + body of the conductor + choreography | `pitch roll yaw x y z` (+`giro`) | base: pitch, roll, yaw; travel |
| spine, head side | `spine` → `spine.001` | root | bend of the front body | 0 (− = up) | behaviour `spine[0..1]`, swim wave | `spine[0] spine[1]` | vertebrae 1–2 |
| spine, tail side | `spine.002` → `.003` → `.004` → `.005` | root | bend of the tail body | 0 (− = tail up) | behaviour `spine[2..5]`, swim wave | `spine[2..5]` | vertebrae 3–6 |
| head | `head` | spine.001 | pitch (+ up) · yaw | 0 · 2 | behaviour `head` + performer's `head_pitch/yaw` (×0.8 / ×0.5) + heartbeat | `head`, `head_pitch head_yaw` | head servo(s) |
| eyes | `eye.L`, `eye.R` | head | look up/down · left/right (0.15 of the head) | 0 · 1 | performer's head/gaze | `eye_yaw eye_pitch` | eyes |
| eyelids | shape key `parpadeo` | mesh | blink | — | performer's `blink` | `blink` | eyelids / LEDs |
| face | shape keys `angry`, `sad`, `asombrado` | mesh | anger, sadness, surprise | — | behaviour `cara[1..3]` + performer's brows/mouth | `cara[4]` | optional |
| lower jaw | `mouth_inf.001` → `mouth_inf.002` | head | opens (+) | 0 | `jaw` ×1.2 / ×0.8 (behaviour + performer's `jaw_open`) | `jaw jaw_actor boca` | jaw |
| upper jaw | `mouth_sup.001` → `mouth_sup.002` | head | lifts (−) with the jaw, breath | 0 | `jaw` ×−0.4 / ×−0.3, breathing | `jaw` | upper lip (optional) |
| tongue | `tongue.001` → … → `tongue.006` | mouth_inf.001 | tongue out | 0 | performer's `tongue_out` (face mode) | — | blue tongue (fixed colour) |
| left fin | `side_fine.L` → `.L.001` → `.L.002` | spine.001 | flap up/down (1.0 / 0.35 / 0.15) · sweep | 1 · 2 | behaviour `flap` + `ladeo` + heartbeat + performer's left hand | `flap ladeo` (+`l_palm`) | left pectoral |
| right fin | `side_fine.R` → `.R.001` → `.R.002` | spine.001 | same, mirrored | 1 · 2 | `flap` − `ladeo`, right hand | `flap ladeo` | right pectoral |
| tail propeller | `turbine` | spine.005 | spins | 2 | mood speed `turbina`; one turn per heartbeat when singing | `turbina` | turbine |
| flukes | `back_fin.U` (+ `back_fin.L/.R` at half) | turbine | tilt (− = raised) | 0 | behaviour `fluke` + heartbeat + performer's energy | `fluke` | tail fin |
| skin | material tint | mesh | colour | — | mood colour, or the performer's clothes | `color[3]` | LEDs |
| fixed | teeth, tongue, eyes materials | mesh | gold · blue · black | — | never change | — | paint |

Behaviour channels per mood (`comportamientos_animos.py`): `pitch roll yaw head spine[6] fluke flap ladeo jaw cara[4] mirada[2] spin depth`.
That is the whale's own body space: 22 numbers per frame, the space a movement model for her must be trained in.
