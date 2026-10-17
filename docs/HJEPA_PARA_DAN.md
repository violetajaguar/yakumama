# Her H-JEPA · answers to Dan's four questions (17 October 2026)

## 1. Weights, code, exact versions

- Weights: `modelos/hjepa.pt` (1.5 MB, a plain `torch.save` dict: state_dicts + normalisation + prototypes + sizes).
- Code that runs them: `hjepa_predecir.py` (one file, defines the three small nets and the `HJepa` class). The brain
  `cerebro_ballena.py` imports it. To retrain: `hjepa_entrenar.py` with `modelos/jepa_datos.npz` (included, 201 MB).
- Versions it was trained and tested with, all on CPU: **Python 3.11.15 · torch 2.11.0 · numpy 2.4.4**. Pinned in
  `requirements.txt`. No GPU, no CUDA, nothing else.

## 2. What goes in, what comes out

**Input**: not a skeleton. Six **body qualities** per frame at 12 frames/s, each a number in -1..1 (energy and smoothness 0..1):

| channel | meaning |
|---|---|
| `cuerpo_pitch` | torso leaning forward (+) / back (−) |
| `cuerpo_roll` | torso leaning sideways / shoulder twist |
| `cuerpo_yaw` | turning speed of the body (left/right) |
| `cuerpo_profundidad` | crouch (−) / jump (+), pelvis height vs standing |
| `cuerpo_energia` | how much the whole body moves (0..1) |
| `cuerpo_suavidad` | smooth (1) vs jerky (0) |

They come from a 26-point skeleton (Paqarina order; MediaPipe Pose in the recorder) through `cuerpo_cualidades.cualidades_toma`.
The recorder already sends them live in every packet on UDP 9998 (`cuerpo_*`), so the brain never touches a skeleton.

**Does it need a live body?** Three modes:
- `leer()` **needs a body**: after 4 s it reads the mood from the body alone (`animo_cuerpo`, `p_cuerpo`); after 32 s it
  also foresees the body 4 s and 16 s ahead (`prevision`) and the mood that body will read as at 16 s.
- `plan(meta)` needs the 32 s context too: which mood-action brings her closest to the goal mood in 32 s.
- `generar(animo)` **needs nothing**: from a mood alone it produces 32 s of body (384 frames × 6 qualities), using the
  mood's prototype as context. Each 2-s sub-goal reads back as that mood (checked for all ten).

**Output format**: the same six qualities, 12 frames/s, in the units above. No joints, no skeleton: it predicts how a body
moves, not where its bones are.

## 3. How the output is mapped onto the whale

The six qualities are applied on top of the mood's behaviour exactly as the 3D receiver does for a live dancer
(`cerebro_ballena.py`, the block starting `if "cuerpo_pitch" in d`; `receptor_ballena.py` the same block):

```
pitch  -= 0.45 * cuerpo_pitch          leaning forward  -> nose down
roll   += 0.35 * cuerpo_roll           twisted          -> she heels over
turn   += 0.50 * cuerpo_yaw            body turning     -> she turns
depth  += 0.60 * cuerpo_profundidad    crouch -> sinks, jump -> rises
fins (flap, ladeo, fluke) and the six spine joints  ×  (0.4 + 1.3 * cuerpo_energia)
```
`hjepa_predecir.a_ballena(cuerpo6)` returns exactly those deltas for one frame, so you do not need to guess. The mood's
behaviour itself (the base she adds to) is `comportamientos_animos.py` (`comp_<mood>(t)`), and the brain's packet on
UDP 9994 is the finished result (pitch, roll, spine, fluke, flap, jaw, colour ...), so the simplest path is to take the
packet and not touch the model at all. The `prevision` field in that packet is the model's raw six-channel forecast.

## 4. One example input with her output, to confirm it gives the same answer

`hjepa_ejemplo/`:
- `entrada.json`: 384 frames (32 s at 12/s) of the six qualities from a real tinku dancer (Paqarina, "angry").
- `salida_esperada.json`: what the model answered here: body reads **angry 0.57**, at 16 s it will look **alert**,
  plan toward surfacing chooses **surfacing**; plus the plan for every goal and the 32-s generation for every mood.
- `verificar.py`: runs it on your machine and compares every number (tolerance 0.002). Expected last line:
  `OK: same answers as on her Mac`. It also prints your torch/numpy/python next to hers.

```
cd Yakumama
venv\Scripts\python hjepa_ejemplo\verificar.py
```

## Honest limits
Reads a mood from the body alone 55 % right on strangers (chance 10 %): singing ~85 %, sad ~70 %, playful/alert/curious
confused. Beats "repeat the last frame" only from 16 s on. Plans diving right 63/64, surfacing 26/64. The planner can
change between retrainings. It predicts a human body's qualities, not the whale's mechanics.
