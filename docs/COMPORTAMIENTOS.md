# Yakumama — the ten body behaviours / los diez comportamientos del cuerpo

For Dan, for the physical whale and TouchDesigner. 16 October 2026. Source of truth: `receptor_ballena.py` (version 16g),
exported by `comportamientos.py` into `curvas/<mood>.csv` (40 s at 30 frames/s) and `curvas/comportamientos.json`.

Para Dan, para la ballena física y TouchDesigner. Fuente de verdad: `receptor_ballena.py` (versión 16g), exportado por
`comportamientos.py` a `curvas/<ánimo>.csv` (40 s a 30 cuadros/s) y `curvas/comportamientos.json`.

## Channels / canales

| channel | what it is | unit | physical whale |
|---|---|---|---|
| `pitch` | nose down (−) / up (+) of the whole body | rad, Blender clamps to −0.7…+0.45 | body pitch (the whole spine base) |
| `roll` | lean to one side | rad | body roll |
| `yaw` | turning | rad | body turn / base rotation |
| `head` | head pitch, on top of the body | rad, clamp −0.5…+0.35 | head servo |
| `spine0…spine5` | six vertebrae, head to tail, pitch each | rad | vertebrae servos (positive = tail up) |
| `fluke` | tail fin pitch | rad (negative = flukes raised) | tail fin |
| `flap` | pectoral fins up/down, both | rad | pectoral fins |
| `ladeo` | left fin higher than right | rad | pectoral asymmetry |
| `jaw` | mouth | 0…1 | jaw |
| `parpado rabia tristeza asombro` | the face: eyelid, anger, sadness, surprise | 0…1 | eyes / LEDs if any |
| `mirada_yaw mirada_pitch` | eyes | −1…1 | eyes |
| `spin` | full turns about her own axis (playful only) | rad | ignore if the body cannot roll over |
| `depth` | rise (+) / sink (−) | Blender units | vertical travel, or light intensity if she cannot move |
| per mood: `color_rgb` | her skin colour | 0…1 | LEDs under the skin |
| per mood: `turbina_rad_s` | tail turbine speed | rad/s (`pulso` = one turn per heartbeat) | turbine |
| per mood: `latido` | how visible the heartbeat is | 0…1 | pulse amplitude on fins/head |

On top of every behaviour the live layer adds: the performer's face (mouth, blink, brows), the heartbeat (a short pulse
through fins and head at the performer's pulse, `latido` × arousal), tempo (pulse/75 speeds every rhythm 0.6…1.6×), and
the style energy (0.7…1.35 scales amplitudes). The curves here are the behaviour alone, at 75 bpm, energy 1.0.

Encima de cada comportamiento va, en vivo: la cara de quien la mueve, el latido (un pulso corto por aletas y cabeza al
pulso de la persona), el tempo (pulso/75 acelera todo 0,6…1,6×) y la energía del estilo (0,7…1,35). Las curvas son el
comportamiento solo, a 75 lpm, energía 1.

## The ten, each with one signature / los diez, cada uno con una firma

Numbers are the mean / swing of the exported curves, in degrees, and the period in seconds.
Los números son media / amplitud de las curvas exportadas, en grados, y el período en segundos.

| mood | humpback behaviour (NOAA) | signature / firma | body | timing | colour · turbine · beat |
|---|---|---|---|---|---|
| **calm** | logging | stillness, flat at the surface, breathing · quietud, plana, respira | pitch 0 ±2°, fins ±9°, nothing else | breath 7 s | silver (0.92,0.94,0.98) · 0.6 rad/s · 0.1 |
| **singing** | song posture | hangs head-down, motionless, mouth pulsing · cuelga de cabeza, inmóvil, la boca pulsa | pitch −36°, head −11°, depth −0.6, jaw 0.23 ±0.25, fins still | mouth 2.5 s, body static | violet (0.62,0.10,0.95) · one turn per heartbeat · 0.3 |
| **playful** | breach + flipper slapping | the leap with two full rolls, fins slapping · el salto con dos vueltas, aletas que golpean | pitch to +26°, fins +24° ±57°, spin 2 turns, depth +0.9 | leap every 12 s, slaps 1.6 s | bright orange (1.00,0.50,0.00) · 4.0 · 0.8 |
| **curious** | spyhop | vertical, high, turning the whole body slowly · vertical, alta, gira lenta todo el cuerpo | pitch +26°, head +11°, depth +0.7, yaw ±29° | turn 14 s | lime yellow (0.70,1.00,0.00) · 1.4 · 0.5 |
| **feeding** | lateral lunge | mouth and roll together: lunges open-mouthed rolling on her side, then filters · boca y rolido juntos | jaw to 0.7, roll to +37°, pitch +20°, depth +0.3 | lunge every 6 s | light fluo pink (1.00,0.55,0.85) · 2.5 · 1.0 |
| **sad** | — | listing and drooping: head, tail and fins down, a fixed lean, sinking · escorada, caída, se hunde | pitch −11°, head −20°, tail +14°, fins −20°, roll +8° constant, depth −0.85 ±0.3 | sink 20 s, nothing else moves | near-black (0.10,0.12,0.20) · 0.25 · 0.2 |
| **angry** | lobtail | the tail slam, with a head shake · el golpe de cola con sacudida | tail −13° ±48°, fluke ±39°, head shake, jaw snaps | slam every 3.2 s | red (0.95,0.08,0.06) · 7.0 · 1.0 |
| **alert** | rounding out | tense, fast, low: back arched, fins tucked, head scanning, a startle · tensa, rápida, baja, respingo | back +8…15°, head ±23° fast, fins −6°, no rise | scan 1.2 s, startle every 5 s | green (0.10,0.90,0.25) · 3.0 · 0.8 |
| **diving** | high fluking dive | the arch and the raised flukes, then down · el arco y las colas arriba, y baja | arch, then pitch −40° (clamped; real whale −67°), tail −16° ±23°, flukes −20° ±29°, depth to −1.8 | cycle 14 s: arch, dive, hold, return | navy (0.02,0.10,0.55) · 0.9 · 0.3 |
| **surfacing** | blow | the rise and the blow: up at 45°, blow at the top, level, rest · la subida y el soplo | pitch to +26°, head +25° at the blow, fins +16° ±23°, jaw 0.4 at the blow, depth to +1.2 | cycle 9 s: rise 3 s, blow, level, rest | cyan (0.00,0.90,0.95) · 1.8 · 0.5 |

Measured distinctness (distance between signatures, bigger = more different): the closest pairs are calm–singing 1.37,
calm–surfacing 2.11 and curious–alert 2.30; everything else is above 2.4. Calm is near everything because calm is the
absence of movement; what separates singing from calm is the head-down hang and the pulsing mouth.

Real numbers behind diving, surfacing and feeding come from a tagged Cape Cod humpback (dives of 250 s to 59 m, down at
67°, up at 57°, 76 s at the surface, rolls past 60° in a third of its feeding frames). The Blender skeleton clamps pitch
at 40°; the physical whale can go further if the body allows it.

## Using the files / cómo usar los archivos

- `curvas/<mood>.csv`: one row per frame (`t` in seconds, then the 24 channels). Loop them; they are periodic.
- `curvas/comportamientos.json`: per mood, colour, turbine, beat, and the mean / swing / period of every channel.
- `videos/<mood>.mp4`: the Blender render of each behaviour, 14 s, for reference.
- Live, the same values arrive inside the UDP packets described in `PROTOCOLO.md` (`--espejo host:port` mirrors them).
- To change a behaviour: edit its `comp_<mood>` function in `receptor_ballena.py`, run `comportamientos.py` to re-measure
  and `comportamientos.py --exportar DIR` to re-export. Blender reloads the file on save.
