# How Yakumama works — brain and movement, as of 16 October 2026

Everything below is what actually runs today, with the file and the numbers, so each piece can be judged and changed.
Parameters that are "one number" are marked **[n]**: those are the cheapest places to improve.

## 0. The shape of it

```
   OAK-D camera ─► ballena3.py (face mesh, hands) ─┐
   pose model    ─► grabar_ballena.py ─────────────┤ one JSON packet per frame, 10-15/s, UDP 9998
   EmotiBit      ─► (optional) ────────────────────┘        │
                                                            ▼
                             receptor_ballena.py inside Blender, 30 frames/s
                             (mood → behaviour → face/fins/pulse/colour → bones)
                                                            │
                             ─► TouchDesigner / physical whale (same packet, --espejo)
```

Two processes. The **recorder** sees and decides (who, what mood, which style, memory, writing). The **receiver** moves
her. They only share the packet. Anything in the packet can be produced by something else: a replayed take, the style
net, a dancer skeleton, the JEPA.

## 1. What she senses (recorder, `grabar_ballena.py`)

| sense | source | channels in the packet | notes |
|---|---|---|---|
| face | MediaPipe FaceMesh in `ballena3.py` | `head_yaw head_pitch jaw_open blink brow_up brow_down mouth_sad` | ratios of mesh distances; smoothed in ballena3 |
| face, finer | MediaPipe Face Landmarker (own thread) | `face_*` (52 blendshapes) `mouth_smile tongue_out eye_yaw eye_pitch blink_bs` | drives the recognisers; skipped every other frame if slow |
| blink | both, combined (`parpadeo()`) | `blink` 0/1 | measured over each person's own open-eye level, needs a real closure, held 0.15 s **[n: 0.2 EAR jump, 0.3 blendshape jump]** |
| hands | ballena3 hand tracking | `l_palm_x/y r_palm_x/y` | 0 top … 1 bottom of the image |
| body | MediaPipe Pose (same thread, every other frame) | `cuerpo_pitch cuerpo_roll cuerpo_yaw cuerpo_profundidad cuerpo_energia cuerpo_suavidad` | from the 3D world landmarks via `cuerpo_cualidades.py`; crouch only with both ankles visible, capped ±0.6 |
| clothes | Pose torso box | `color_ropa` (only when she likes it) | median RGB of the box; "likes" = saturation ≥ 0.35, brightness ≥ 0.25, and 4 of 10 visits or curious/playful **[n]** |
| pulse, skin, temperature | EmotiBit over WiFi (`emotibit_cliente.py`) | `emotibit_hr emotibit_eda emotibit_therm …` | dropped if older than 2 s; absent in Barcelona |
| far faces | head crop from the pose, ×3 | — | when the full frame has no face, both readers retry on the enlarged head |

A **neutral** (key `n`) measures head, brows, mouth and blink relative to the person's relaxed face. Visitors have none:
everything is measured from their own first seconds.

## 2. What she decides (recorder)

Every 0.5 s, on the last 2 s of face+hands (`rasgos()` in `entrenar_animo.py`: means, spreads and speeds of the 52
blendshapes, head, hands = 163 numbers):

1. **Mood** — `modelos/animo_rf.pkl`, random forest, 10 moods. Trained on the four performers + 18 RAVDESS actors.
   Within a known person ≈ 70 %, on a stranger 37 %. A mood is adopted only after **6 consecutive wins (3 s) with ≥ 30 %**
   for visitors, 3 wins for a named performer **[n]**. Goes out as `actor_animo` and `actor_<mood>` probabilities.
2. **Resemblance** — `modelos/parecido_rf.pkl`, same features, label = which of the four performers. 90 % on unseen
   takes. Decided after 4 windows (2 s), **sticky for the whole encounter**; if < 45 % she uses `promedio` **[n]**; if the
   top changes to another performer for 8 windows (4 s) she treats it as a new person and re-decides. Goes out as `estilo`.
3. **Memory** — `memoria.py`. From the face mesh at rest (mouth closed, no smile, no blink) she takes 210 distances between
   21 fixed mesh points normalised by the eye distance; the median over ≥ 25 frames is the signature. Match if mean
   difference < **0.038** **[n, calibrated on real faces 16 Oct: same person 0.013-0.036, other ≥ 0.040]**. Known people can have a
   name; a named performer gets her own style directly. Encounter files go to `datasets/visitas/`; nothing is saved while a
   named performer records. `aprender.py` retrains the mood forest with confident visitor windows (never more than half the set).
4. **Writing** — the window at `/ventana`. Events (arrival, known face, style chosen, mood change, liked clothes, departure)
   put a short line in her voice at once and, through `yakumama_alma.py` (Qwen 3.6 on ollama, ~5 s), a poem under the rules
   of her soul: from the body, lithium and extraction allowed, no report words, three to six lowercase lines.

## 3. What she does (receiver, `receptor_ballena.py`, 30 fps)

Order inside `breathe()` each frame:

1. **Read the packet**, smooth the inputs (`SUAVE`: head 0.15, mouth 0.25 … **[n]**).
2. **Fill what is missing** (`completar_con_red`): if a style is known and the packet has no hands or no pulse, the style
   net (`yakumama_modelo.py`, NumPy, trained by `entrenar_movimiento.py`) produces them for that performer's style.
3. **Mood** (`compute_mood` + override): the senses propose a mix (water level, scene colour, brightness, performer's sad/brows/mouth);
   then **the performer's recognised mood replaces the mix entirely** (`actor_animo` → that mood = 1.0); the Blender menu
   *Comportamiento* overrides everything if not "auto"; the Qwen brain can pick a mood when enabled. `dominant` = the max.
4. **Behaviour** (`comportamiento()` → `comp_<mood>`): each mood is a motion in time modelled on a NOAA humpback behaviour,
   returning pitch, roll, yaw, head, six spine values, fluke, flap, bank, jaw, face, gaze, spin, depth:

   | mood | behaviour | the shape |
   |---|---|---|
   | calm | logging | still at the surface, slow breath |
   | singing | song | head down, nearly still, sways with the mouth |
   | playful | breach | pec slaps, rolls, a leap every 12 s with **2 full rolls [n: PLAYFUL_VUELTAS]** |
   | curious | spyhop | vertical, slow turn, rises |
   | feeding | lunge | open-mouth lunge, then filtering |
   | sad | sinking | head and tail down, sinks |
   | angry | lobtail | tail raised and slammed |
   | alert | scanning | arched back, head sweeping |
   | diving | high-fluking dive | nose down, flukes up, descends 1.6 and returns |
   | surfacing | blow | rises 1.0, blows, levels |

5. **Scaling the behaviour**: by the style's energy (`ESTILO_ENERGIA`: violeta 0.7, sanam 1.0, suri 1.15, dan 1.35 **[n]**);
   by a dancer's body if present (`cuerpo_*` from `bailar.py` or from the visitor's pose: pitch ×0.45, roll ×0.35, yaw ×0.5,
   depth ×0.6, energy 0.4…1.7 **[n]**); plus the heartbeat (head +0.03·beat, fins +0.06·beat) and tension (head tremor).
6. **Heartbeat and tempo**: `hr` from the packet or the style net. Visible strength = `LATIDO_ANIMO[mood] × (0.5 + 0.5·arousal)`
   (calm 0.1 … angry/feeding 1.0 **[n]**); `tempo = clamp(hr/75, 0.6, 1.6)` speeds every rhythm; `energia = (hr−60)/60` widens
   the fins; `tension = (eda−2)/8` adds the tremor. Tail turbine: `TURBINA_ANIMO` rad/s (calm 0.6 … angry 7.0; singing = one
   turn per heartbeat **[n]**).
7. **Face**: the performer's face goes on top of the mood's face. Mouth = max(performer × 0.25, mood) — the performer is capped
   at a quarter turn (your "40 % smaller mouth"), the net acting a style gets 0.6 **[n]**. Head follows the performer at 0.5
   (0.8 for the net) **[n]**. Blinks held 5 frames. Eyes from `eye_yaw/pitch`, or the mood's gaze.
8. **Fins**: `l/r_palm_y` → flap `(0.5 − y) × 1.0` rad; left higher than right = bank; limits from the BVH grid so they never
   enter the body.
9. **Colour** (`tint_body`), in this priority: the visitor's clothes if she liked them (75 % clothes + 25 % mood, 2 s fade),
   **but on every mood change her mood colour shows for 6 s** **[n]**; otherwise the mood colour (`MOOD_RGB`, 1 s fade);
   the room's scene colour only when nobody is in front.
10. **Position**: anchored (`anclada`) in visitor mode and in dancer mode, so she moves without travelling; depth from the mood
    and the body. Root limits: pitch −0.7…0.45, head −0.5…0.35 (never bends backwards).
11. **Heartbeat file** `/tmp/ballena_receptor.json` every second: version, mood, style, colour, pose, fps, flags. The panel
    shows: moods, takes, senses, "Ahora es", "Te conozco", style field, mouth/turn sliders.

## 4. The learned pieces, what each is for, and its honest number

| model | file | learns | number |
|---|---|---|---|
| mood recogniser | `entrenar_animo.py` → `animo_rf.pkl` | face+hands → mood | 70 % known person, 37 % stranger |
| resemblance | `entrenar_parecido.py` → `parecido_rf.pkl` | face+hands → which performer | 90 % |
| style net | `entrenar_movimiento.py` → `movimiento.pt/.npz` | mood + phase + pulse + performer → 18 channels | beats a constant on hands, pulse, skin, brows; not on mouth/blink/gaze |
| JEPA | `jepa_datos.py` + `jepa_entrenar.py` → `jepa.pt/.npz` | 4 s of 24 channels → next 2 s, or hidden modality | ties "repeat last frame"; face→body better than the mean on 4 of 6 channels; **not in the live loop** |
| memory | `memoria.py` | face geometry → identity | threshold calibrated on 12 real faces |
| soul | `yakumama_alma.py` (Huk) + Qwen | state → poem | — |

Data: 4 performers (137 min incl. the llama session), 91 min of Violeta's free face, 18 RAVDESS actors, 6 BEAT speakers
with face and body (JEPA only), 239 Paqarina dancer skeletons (292 min), visitors from today on.

## 5. Where to improve, by expected effect

1. **Face and body recorded together, several people.** Now possible: the recorder captures both since today. This is the
   only thing that moves the JEPA and a learned body-conducting layer.
2. **Mood on strangers** (37 %). More RAVDESS-like actors help the universal moods; the whale's own moods (singing, feeding,
   diving, surfacing) only improve with more performers acting *her* vocabulary with the same spoken instructions.
3. **Behaviours are one script per mood.** Every style is an intensity of the same choreography. A second choreography per
   mood, or body poses recorded per performer, would make four whales rather than one with four faces.
4. **Mood switching for visitors** is a trade-off between stability (3 s, 30 %) and responsiveness; the right place to tune
   is in the recorder, and the window line "te leo …" tells you when it switched.
5. **Memory threshold** will drift with lighting and distance; the first real days calibrate it (`UMBRAL`).
6. **The face at distance**: the head crop is new and untested with a real standing visitor; if it works, the whole
   standing-visitor mode works; if not, the camera needs to be closer or a longer lens.
7. **Colour**: clothes-liking is a coin flip plus two thresholds; it could instead follow her mood (she likes colours when
   curious, refuses them when sad), which would make colour part of her language rather than chance.
