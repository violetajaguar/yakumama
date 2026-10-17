# Yakumama · update for Dan, 17 October 2026 (evening) · she now generates whale movement

Copy these files over the same paths inside `Yakumama_Barcelona_2026-10-17/Yakumama/` (the folder on the drive). Nothing else changes.

## What is new

**She was retrained in her own body space.** Every body she had (239 Paqarina dancers, 1500 bodies from video, the performers
head to toe, 400 face takes, 3 tagged humpbacks, her ten designed behaviours; 47.7 h) was translated onto HER articulations with
Violeta's mapping and the H-JEPA was trained there. So what it generates is whale channels, not six summary numbers:

| group | channels |
|---|---|
| body | `pitch roll yaw head` |
| spine | `spine0 … spine5` (head to tail) |
| tail | `fluke turbina` |
| fins, each side, link by link | `flap_l codo_l muneca_l` · `flap_r codo_r muneca_r` (shoulder, elbow, wrist of the dancer) |
| face | `jaw cara_parpado cara_rabia cara_tristeza cara_asombro mirada_yaw mirada_pitch` |
| space | `spin depth avance deriva giro` (forward, sideways and turning speed: she travels) |
| heart and skin | `pulso piel` |

Violeta's mapping (the translation, `retarget_ballena.py`): hands to fins, each arm's shoulder/elbow/wrist to the three links
of that side's fin; head and eyes to the face; spine to spine; the tail's beat and the turbine from the speed of the feet, its
amplitude from the body's energy; lean to pitch, side lean to roll, crouch/jump to depth; the dancer's path to her travel.
Constraints: every channel clamped to her ranges; the mouth never opens past 0.5; a head-down body is nose down.

Numbers (held-out bodies): the probe reads the mood from her body 86 %; the model beats "repeat the last frame" on tail and
spine; the decoder still shrinks amplitude, so generation keeps the dancer's amplitude per channel (`continuar(..., amplitud=True)`).
**Sampling head (added later the same evening).** `modelos/banco_frases.npz` is her phrase bank: 29,662 real 2-s phrases of movement
in her body space (dancers, swimmers, divers, performers, faces, behaviours), each with its level-1 latent. `HJepa.muestrear()` plans
the 16 sub-goals of the next 32 s in latent space and, for each one, retrieves a real phrase whose latent is close (random among the
12 closest, same mood favoured, continuity with the previous phrase). Every second she generates is real movement in whale form, never
an average; two draws differ; 32 s take 0.1 s on CPU. The brain uses it automatically when the bank file is present.

## New in the brain (`cerebro_ballena.py`, the one you run next to TouchDesigner)

- Loads `modelos/hjepa_ballena.pt` when present. Alone (nobody for 20 s) she continues her own last 32 s in whale channels,
  with a little randomness, and the designed behaviour of the mood underneath.
- **If the public dances, she dances back**: when the person's body energy stays above 0.35 for 1.5 s, their skeleton is
  translated live onto her (same mapping) until they stop for 3 s.
- Mouth capped at 0.5. Travel from the body itself (`avance deriva giro`), inside a circle of radius 2: the mountains of her salar.

New fields in every UDP 9994 packet: `aleta_l aleta_r` (three links each: shoulder, elbow, wrist angles, rad, when a body drives her),
`baila_de_vuelta` (1 while she dances back), `turbina_viva` (tail speed from the feet), `cuerpo_jepa` (1 when the model moves her),
`cuerpo` (its raw channels that frame). Everything else is as in `BARCELONA.md`.

## Files in this update

```
Yakumama/cerebro_ballena.py          the brain (new: whale-space model, dance back, mouth cap, travel)
Yakumama/hjepa_predecir.py           the H-JEPA runner (new: continuar from a real context, with noise and amplitude; generar from a mood)
Yakumama/retarget_ballena.py         Violeta's mapping: a 26-point skeleton -> her channels, with constraints; also plays a body on her
Yakumama/jepa_mueve.py               moves her with what the model generates (whale channels), each mood anchored on its behaviour
Yakumama/cuerpo_cualidades.py        body qualities (unchanged, needed by retarget)
Yakumama/comportamientos_animos.py   the ten behaviours (regenerated)
Yakumama/receptor_ballena.py         the 3D whale in Blender (new: raw channels, fins link by link, travel, dance back)
Yakumama/carrusel.py                 the app (new: 'traducida' switch, 'ella sola' group)
Yakumama/ballena_datos.py            builds the training set in her body space
Yakumama/hjepa_ballena.py            trains the H-JEPA in her body space (minutes on CPU)
Yakumama/modelos/hjepa_ballena.pt    the model (1.6 MB)
Yakumama/modelos/ballena_datos.npz   the training set (53 MB), to retrain:  venv/bin/python hjepa_ballena.py
Yakumama/modelos/banco_frases.npz    the phrase bank (20 MB), to rebuild after a retrain:  venv/bin/python banco_frases.py
Yakumama/banco_frases.py             builds the phrase bank
Yakumama/docs/ARTICULACIONES.md      map of all 30 bones of the rig, axes, what drives each, stream field, physical part
```

Run exactly as before: `instalacion.py --sin-blender --cerebro`. The brain picks the new model by itself.
