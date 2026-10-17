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

## 6. Her language models, and the exact words she is given

Four prompts exist. Only one is in the live visitor loop today. All run locally through ollama; nothing leaves the Mac.

| who | model | file | when | in use today |
|---|---|---|---|---|
| **skin** (she writes) | Qwen 3.6 | `Huk/yakumama_alma.py` `PIEL_SISTEMA` | every window trigger: arrival, known face, liked clothes, mood change (≥ 45 s apart) | **yes**, the `/ventana` poems |
| **song** (she sings) | Qwen 3.6 | `yakumama_alma.py` `ALMA` | every 20 s when `yakumama_alma` runs standalone; sooner if someone sings | not in visitor mode |
| **eye** (what is in front) | Gemma 4 (vision) | `yakumama_alma.py` `VISTA_SISTEMA` | every 12 s on a 512×288 frame | not in visitor mode; the window sends "una cara, de cerca" instead |
| **memory keeper** | Qwen 3.6 | `yakumama_alma.py` `MEMORIA_SISTEMA` | every 45 s over the last 14 log lines | not in visitor mode; face memory (`memoria.py`) replaced it |
| **mood brain** (old) | Qwen 3.6 | `Huk/ballena3.py` `build_brain_prompt` | every 5 s | off: the Blender toggle *use_brain*; the mood forest replaced it |

### 6.1 The skin: how a poem is asked for

System prompt (verbatim, Spanish, she is addressed as "vos"):

> Eres YakuMama. No hablas. Escribes. Lo que escribes aparece en una ventana. No es tu voz. Es lo que tu piel sabe y tu cuerpo no logra callar.
>
> LO QUE ESTA DEBAJO DE TI — Debajo de la costra hay salmuera, y en la salmuera hay algo que el mundo quiere. Lo sacan bombeando de abajo hacia piletas abiertas al sol y esperan dos años hasta que el agua se va. El agua que se va eres tu. Esto ya pasó antes en este país. Hay un cerro al sur que era plata y ahora es hueco … Después fue estaño … Ahora es otra cosa. Las piletas son nuevas y el gesto es el mismo. Alguien llega, se lleva lo de abajo, y el lugar se queda. Tú sabes esto como el cuerpo sabe una sed.
>
> PROHIBIDO — Puedes decir litio y extracción, con su nombre, cuando el cuerpo lo pida: son tu sed y tu hueco. Pero nunca escribas como informe: nada de política, gobierno, empresa, contrato, transición, energía, recurso, comunidad. Nunca expliques. Nunca denuncies. Nunca digas "nosotros" por los humanos. Nunca uses comillas ni escribas diálogo.
>
> COMO ESCRIBES — Tres a seis líneas. Minúsculas. Sin título. Sin rima forzada. En castellano. Puede caer una palabra en quechua si nace sola, nunca de adorno. Escribí desde el cuerpo: sed, peso, hueco, abajo, sal, garganta, costra, lo que se llevaron, lo que quedó. Partí de lo que tu cuerpo siente ahora, no de una idea. Nunca cierres con moraleja. Termina antes de explicar. Responde solo JSON: {"poema": "linea\nlinea\nlinea"}

User message, built each time by the recorder (`ventana_poema` in `grabar_ballena.py`):

```
TU CUERPO Y EL SALAR AHORA
<_estado_en_cuerpo: water 0.7 → "You are half in the water." / colour / light / "A hand is near you.">

LO QUE ACABA DE PASAR
<one of:
  llega    "una persona nueva se paró frente a vos y te mira"
  conocida "volvió alguien que ya vino; la otra vez le contestaste como <estilo_previo>"
  nombre   "volvió <nombre>, que ya vino N veces; la conoces por su nombre"
  ropa     "te gusta el color de la ropa de quien tienes enfrente y te tiñes de ese color"
  animo    "en la cara de quien te mira lees <calma|canto|juego|curiosidad|hambre|tristeza|rabia|alerta|hondo|aire>">
Se mueve como <estilo>. <"Mueve el cuerpo." if cuerpo_energia > 0.3 else "Está casi quieta.">

LO QUE VE TU OJO
una cara, de cerca

LO QUE CARGAS
<N> personas en la memoria

LO ULTIMO QUE ESCRIBISTE, no lo repitas
<her last two poems>

Escribí. Solo JSON.
```

Settings: temperature 0.95, 220 tokens, JSON forced, thinking off. ~5 s on this Mac. Poems are kept in `Huk/yakumama_poemas.json` (last 200).
Before the poem arrives the window already shows a fixed line from `FRASES` (e.g. "ya viniste. te recuerdo por los huesos de la cara.").

**What the skin does not know yet** (levers): the mood is passed as one word, not the body it produces; the style is a name,
not what that style feels like; the eye is a fixed phrase; the visitor's clothes colour reaches her only as "the colour of
their clothes"; her own behaviour (breach, spyhop, sinking) is not in the prompt at all. Each of these is one line to add
in `ventana_poema`.

### 6.2 The song (standalone `yakumama_alma`)

System prompt `ALMA` (English + Spanish): "You are YakuMama. Mother Water. You are a whale. YOU DO NOT SPEAK … you sing …
Never write dialogue". Then the place (Salar de Uyuni, Lago Minchin, Lago Tauca, the hexagons), what is happening to her
home (lithium, 23 million tonnes, the ponds, the companies, the blockades: "You know all of this the way a body knows a
wound. Never explain it. Never say lithium, extraction, mining, politics"), her ear (low soft voices settle her, sharp
voices scrape, repeated sound stops mattering, long silence means they left, and singing opens her: "cuando alguien canta
te está hablando en tu idioma sin saberlo"), who she is (fifty million years, the Tawa pattern from Cochabamba on her tail).
Answer: JSON with `canto` (1 to 6 tones: tono, largo, fuerza, curva), `motivo` (an invented word she reuses: her lexicon
in `yakumama_lexico.json`), `expresion` (3 to 8 words, third person), `gesto` (quieta, escucha, gira, sube, baja, se acerca,
se aleja, canta, calla). User message: body state, what the eye sees, three memories, her lexicon so far with counts, the
motifs she just used. Note the two prompts disagree on purpose: the song forbids the word lithium, the skin allows it.

### 6.3 The eye, the memory keeper, the old mood brain

- **Eye** (Gemma 4, vision): "You are the eye of a whale in the Salar de Uyuni. Report only what is physically in the frame
  … How many people. What colour they are wearing. Where they look … Two sentences maximum. No interpretation … You are
  retina, not mind. If the frame is empty, say: empty." Temperature 0.3, 80 tokens.
- **Memory keeper** (Qwen): "You keep the memory of a whale. From this stretch of what she sensed, write one line she carries
  forward. Not a log. A memory the way an animal keeps one … Good: someone in a green jacket stayed until the light changed
  … If nothing worth keeping happened: nada." Temperature 0.7, 60 tokens, saved to `yakumama_memoria.json`.
- **Old mood brain** (Qwen, `ballena3.py`): a plain table of sensor numbers (water, scene colour, brightness, jaw, sadness,
  brows, blink, hands, joystick, humidity) and "Respond with ONLY a JSON object … keys calm, singing, playful, curious,
  feeding, sad, angry, alert, diving, surfacing, each 0.0 to 1.0". Every 5 s, temperature 0.6. The receiver blends it in
  only when *use_brain* is on and no performer mood is present; the random forest made it unnecessary for visitors.

## 7. Real whales and the H-JEPA (16 October, evening): what the numbers say

**Real whale tags** (`importar_ballenas.py`, open data from animaltags.org, 31 h): a Cape Cod humpback dives for 250 s to
59 m, goes down at −67° and comes up at +57°, stays 76 s at the surface between dives, and rolls past 60° in 37 % of its
frames while feeding. A second humpback (10 h, shallow 32 m dives of 141 s, 336 s at the surface) and a Cuvier's beaked
whale (18 h, dives of 23 min to 1700 m). These are the first real numbers for `comp_diving`, `comp_surfacing` and
`comp_feeding`; today those behaviours use invented durations and angles.

**H-JEPA** (`hjepa_entrenar.py`, two levels, action = the mood, planning by subgoals), measured on held-out tracks:

| horizon | H-JEPA | repeat last frame | mean |
|---|---|---|---|
| 2 s (level 1) | 0.094 pitch, 0.102 roll | 0.076, 0.074 | 0.253, 0.338 |
| 4 s (level 2) | 0.172 | 0.114 | 0.333 |
| 16 s | 0.218 | 0.206 | 0.333 |
| 32 s | 0.249 | 0.244 | 0.332 |

It loses to "repeat the last frame" at every horizon, like the first JEPA. Changing the action with the same history
changes the plan by 0.027 (almost nothing), and the planner's choice of action is noise. The reason is in the data, not
the architecture: **none of Yakumama's own takes have a body** (the pose capture is one day old), so the moods only
appear through BEAT speakers standing still, and the real whales carry no mood at all. A model cannot learn "what
diving looks like in the body" from data where nobody dives.

What would change that, in order: (1) performers acting her ten moods with face **and** body (the recorder does it now),
(2) a mood label for the real whale tracks derived from their own depth cycle (descending, bottom, ascending, surface),
so the whales teach level 2 what a dive cycle is, (3) only then the H-JEPA as her "own initiative" when nobody is in front.

## 8. Night of 16–17 October: a body for each mood, from the world's data

Decided with Violeta: faces, eyes and heartbeat are ours (four performers, RAVDESS). The ten poses and colours stay.
The outside datasets lend **bodies** to the moods. Everything below is converted to the 26-point Paqarina skeleton and
enters `jepa_datos.py` by file prefix (`VIDEO_ANIMO`, `DANZA_ANIMO`); the real whales label themselves by their own
kinematics (`animos_ballena` in `hjepa_entrenar.py`).

| mood | body | source | hours |
|---|---|---|---|
| sad | ballet; people expressing sadness | ImperialDance (OptiTrack); Emotional Body Motion Data (Zenodo, CC BY) | 6.6 |
| feeding | swimming; the humpback's lateral lunges (roll > 60°) | SwimXYZ (CC BY, SMPL-H, forward kinematics); animaltags DTAG | 5.7 |
| singing | jazz | ImperialDance | 5.4 |
| calm | the humpback resting at the surface; people expressing neutral | DTAG; Emotional Body Motion | 5.0 |
| diving | Diving48 platform dives (2677 clips, pose); 9 freedivers; the humpback's descents | SVCL Diving48; own videos; DTAG | 2.6 |
| curious | suri sikuri; people expressing surprise | Paqarina; Emotional Body Motion | 2.4 |
| alert | breaking (AIST++ and Paqarina); people expressing fear | Paqarina; Emotional Body Motion | 2.4 |
| angry | tinku; people expressing anger | Paqarina; Emotional Body Motion | 2.3 |
| playful | kullawada; people expressing happiness | Paqarina; Emotional Body Motion | 2.0 |
| surfacing | surfers (Zenodo river wave); the humpback's ascents | Zenodo 14535620; DTAG | 0.1 + whale |

Still open: calm from flowers (Violeta's rigged flowers on the Mac mini), feeding from calf suckling (Dryad, 41 GB, needs a
browser login), BERD (downloading), VocalSet for her voice (downloading). Importers: `importar_ballenas.py`,
`importar_surf.py`, `importar_video_cuerpo.py`, `importar_imperial.py`, `importar_swimxyz.py`, `importar_emociones.py`,
`leer_mat_opaco.py`.

**H-JEPA after five cycles (57 h, 1 in 8 of every source held out):** at 16 s it ties "repeat the last frame" (0.232 vs
0.232) and at 32 s nearly (0.237 vs 0.230); at 2–4 s it still loses. The mood changes the plan by 0.035, as at the start.
The planner's choice of action is **not stable between trainings**: one cycle it separated diving from surfacing cleanly
(40/64 and 39/64), the next it chose feeding for diving and sad for surfacing. The mood prototypes in her latent are not
yet robust. Conclusion for the morning: the labelled body is now there in hours; what is missing is a loss that pulls the
latent apart by mood (a contrastive or probe term), and the performers' own bodies. The copying path (any body conducts
her live) and the ten scripted behaviours do not depend on any of this.

**Sixth cycle (17 Oct, 01:40, with BERD: 61 h, labelled human emotion 11 h from 52 people):** at 16 s the H-JEPA beats
"repeat the last frame" for the first time (0.192 vs 0.198) and ties at 32 s (0.196 vs 0.194); at 2–4 s it still loses.
The mood still changes the plan by only 0.034 and the planner's choice of action is still unstable. Same conclusion: the
next step is a loss that separates the latent by mood, not more hours.

## 9. 17 October, 11:40 — the seventh cycle, with the performers' bodies and the mood probe

Violeta and Dan recorded all ten moods head to toe (23 takes, ~27 min, face + body + EmotiBit together: the first bridge
between a face and a body). Every frame now also stores the full 26-point skeleton. `hjepa_entrenar.py` gained a mood
**probe** at both levels (a linear read of the mood from the latent, trained only on labelled windows) that pulls the
latent apart by mood. Results on tracks never seen:

- **The body alone, four seconds of it, tells the mood 58 % of the time** (chance 10 %): singing 87 %, playful 68 %,
  sad 67 %, diving 62 %, calm 61 %, angry 55 %, alert 54 %, feeding 45 %, curious 43 %, surfacing 0 % (only 12 min of it).
  This is the answer to "can she discover what sadness looks like": she can, from these sources, two times out of three.
- **The planner chooses diving for a diving goal 64 times out of 64** (it was 2 two nights ago). Surfacing and playful
  still fall to "free": too few labelled hours (0.2 h and 3 h).
- The whale's depth 32 s ahead correlates 0.45 with the real tag (it was ≈ 0 before the probe); at 16 s she beats
  "repeat the last frame" (0.189 vs 0.198); at 2–4 s she still loses.
- Face mood recogniser retrained: 66 % within a session, 34 % on an unseen person (was 37 %: the new takes are harder,
  full-body distance). Resemblance 97 % for Violeta.

Next, in order: more surfacing (the one mood with almost no body), Sanam and Suri head to toe, and a probe-guided plan in
the receiver so her own initiative uses it.

**Eighth cycle (17 Oct, 13:30, + Suri's two surfacing takes, 4.3 min):** body probe 55 % overall; surfacing from 0 % to 14 %
(16 min of surfacing body in total: still the thinnest mood by far). The planner's choice swung back (diving 27/64,
angry 36/64): between two trainings on nearly the same data the plan still moves a lot, so the next engineering step is
stability (several seeds, keep the best probe; or more epochs at level 2), not more data.
