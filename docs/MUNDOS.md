# Her worlds: the salar, Tiupampa, Mars (23 Oct 2026)

Violeta: "can we also set another world like el Salar, in Tiupampa por Vila Vila, and Mars, red earth."

The salar was the only world: its colours were constants inside five shaders, its site a pair of coordinates in `ballena_sun.py`,
its sound a wind. A world is now ONE dict in `fuentes/Yaku_PC_2026-10-20/Paqarina_TD/ballena_mundo.py`, chosen at launch. Everything
else reads from it, so adding a fourth world is adding one dict.

## The three

| key | place | sky | ground | water | cacti | haze | sound |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `salar` | Salar de Uyuni (clock and weather: Barcelona, or `BALLENA_SITIO=uyuni`) | Dan's Altiplano anchors | white salt polygons, glitter | the seasonal mirror | yes | 1.2 | Mars wind under the beds |
| `tiupampa` | Tiupampa, near Vila Vila (Mizque, Cochabamba), 18.0128 S 65.4065 W, La Paz clock, Open-Meteo weather there | a valley at 2,700 m, horizon warmed by the red bounce | red siltstone with fine dark cracks, gravel, almost no glitter | puddles after real rain (35 %) | yes | 1.0 | same |
| `marte` | Jezero crater, on the audience's clock (a sol cannot be told on an Earth clock) | butterscotch by day, BLUE glow at sunset, darker night | red regolith, soft cells, stones everywhere, no glitter | none | no | 2.2 (dust) | the Perseverance wind doubled |

Tiupampa is the type locality of the Santa Lucía Formation: reddish sandy shales, marls and siltstones, the ground of the oldest
Paleocene mammals of South America. Mars has no weather service: `clima_fijo` gives her brain a fixed climate (7.3 hPa, humidity 0,
no rain, gusts 15 m/s, uv 11) with the temperature following the sun from −80 to −20 °C.

## How to run

1. Once, in the running TouchDesigner (textport), then Cmd+S:

       exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_mundo.py').read())

   It reloads the ground, island and mountain shaders from `td/shaders` (now with guarded world uniforms), binds `uTierraA-D`,
   `uIslaA-C`, `uMtnA-B` to the brain's `/ballena/env/*` channels, makes `uFog.x` follow `fog_mult`, the cacti's render flag follow
   `cactus`, and re-runs `td/setup_env.py` so the env map that lights her takes the ground's colour. In the salar nothing visible
   changes. Dan's setup scripts carry the same bindings, so a rebuild (`docs/td_todo_3.py`) keeps the worlds.

2. Launch the world:

       MUNDO=marte ./correr_todo.sh        # or MUNDO=tiupampa; default salar
       MUNDO=marte ./correr_td.sh          # the renderer alone

   Dan's renderer prints the site at start; her brain's `[weather]` line ends with `world marte`, and every decision in
   `datasets/decisiones.jsonl` records `situacion.mundo`, so the measure can later compare how she lives in each world.

## What reads the world

- `ballena_sun.py`: the site (Tiupampa added to `SITIOS`); `BALLENA_SITIO` still wins if set.
- `ballena_palette.py`: the world's sky anchors replace `ANCHORS` when it has its own (Tiupampa, Mars).
- `ballena_td.py`: sends `ballena_mundo.env()` every frame (tierra_*, isla_*, mtn_*, cactus, fog_mult, mundo_i); multiplies the water
  index by the world's allowance; applies Mars's fixed climate and wind; puts `mundo` in her brain's packet.
- `ballena_sound.py`: the Mars wind's weight (`marte_viento`).
- Shaders: `salar_ground.frag` (`uTierraA` base, `uTierraB` light tone + water allowance, `uTierraC` dark tone, `uTierraD` = cell
  scale, crests (+1 bright ridges / −1 dark cracks), glitter, rocks), `salar_island.frag` (`uIslaA-C`), `salar_mtn.frag`
  (`uMtnA-B`), `setup_env.py` (`uTierraA`). Every one is guarded on `.w`: unbound (old TD, brain down) reads 0 and the salt is
  exactly what it was.
- Her brain: `_clima["mundo"]`, the situation and the decision log.

## Tuning

The colours are linear, pre-tonemap (see `ballena_palette.py` on what that means); `BALLENA_MUNDO=marte python ballena_palette.py`
prints a world's sky as it lands on screen. The panel's palette sliders still offset any world live. To make the world HER decision
(she travels between them) the channels are already live from the brain: a `mundo` field in her packet to Dan's renderer would
switch `MUNDO` at run time; not built yet.

## El exilio a Marte (23 Oct 2026, Violeta: "cuando se enoja porque es muy caliente, con la data de NASA FIRMS, se va al mundo de Marte y ahí muere de una manera épica")

The heat of her world (`cerebro_ballena.calor_del_mundo`) is the air (Open-Meteo, 28 → 38 °C), the active fires NASA FIRMS counts in
a day within ±1.5° of the site (20 → 150), and her own servos (55 → 70 °C). Hot (> 0.6) she is angry. Angry and hot, her decision
`mundo` (salar / tiupampa / marte) leans to Mars. Once she chooses it and has been angry 20 s, the arc runs (`EX` in her brain, every
phase in `datasets/exilios.jsonl`):

1. **viaje** (45 s): she burns red; Dan's renderer switches the world to Mars live (her packet's `mundo`).
2. **muriendo** (240 s): her body slows and shrinks, her tail stops, her colour goes red to black, she sinks to the ground, her eyes close
   (from 60 %), the dust storm rises (her own wind + the haze ×3.5), no voice, no texture, no journey, no imitation.
3. **muerta**: still and dark until sunrise (sun > 2° after at least 2 min) or 15 min, whichever first.
4. **renace** (90 s): the salar returns, the wind-up sounds, her colour comes back, she lives.

Set-up: a free FIRMS MAP_KEY (https://firms.modaps.eosdis.nasa.gov/api/map_key/) exported as `NASA_FIRMS_KEY` before `./correr_todo.sh`.
Without it the fires read none and only the air and her servos can make her hot. Rehearsal: `YAKUMAMA_CALOR=1 ./correr_todo.sh` forces
the heat (or `YAKUMAMA_FUEGOS=300` fakes the fire count); `YAKUMAMA_EXILIO_VIAJE_S`, `_MUERTE_S`, `_MUERTA_S`, `_RENACE_S` shorten the
phases. TD must have run `docs/td_mundo.py` once for the world and the dust to show.

## El mar bajo el salar (26 Oct 2026, Violeta: "a sea as a setting so the salt can break and the whale can go down into the sea when she is overwhelmed"; "Mars just copies the salar and that's no good"; "needs to have coral fishes")

Mars and Tiupampa are the salt recoloured: the same polygons, island and range. The sea is another world, and it was born the way
the salar was: first a standalone page, `fuentes/Yaku_PC_2026-10-20/Paqarina_TD/mar.html` beside `salar.html`, later TD.

    open fuentes/Yaku_PC_2026-10-20/Paqarina_TD/mar.html      # its own browser window; Bajar; B breaks the salt

The sea lies UNDER the salar. The crust is the ceiling: the salar's own Voronoi polygons seen from below, the plates milky with the
sun above, the borders cracks the light comes through. **B** breaks it: the cracks around the break whiten and spread (the salt
crackles), then the plates give (a boom), fall slowly to the floor, and a jagged hole opens on the salar's real sky (the same
`skyColor`, the same palette anchors, the real sun for Incahuasi on the Uyuni clock) with a shaft of light under it. **B** again
closes it. Everything fogs into a water colour that follows the view, the depth and the sun through the salt. The floor at 46 m: sand
with dunes and ripples, stones, caustics. The reef: coral heads (noise-displaced icosahedra), branching coral, sea fans swaying;
four schools of fish swim as schools in the vertex shader (clownfish and yellow around the light, blue chromis over the reef,
angelfish slow between, one school passing far). Marine snow sinks; at night it is plankton. Sound: a low brown-noise swell; the
cracks and the boom are synthesised. Zero assets.

Keys: WASD swim · E/Q up/down · Shift fast · B break/close · 1/2 time · M sound · R origin. Checking stills without a hand:
`mar.html?auto&rota&pos=x,y,z&yaw=deg&pitch=deg&min=minutes` (headless Chrome with `--use-angle=swiftshader`).

### In TouchDesigner (26 Oct, "can we test it on TD, to see how it will look")

The port keeps the design live from the brain: `ballena_mundo.py` has the world `mar` (sand floor, water palette, haze x20, no cacti,
water level 1 = deep/home, no rain, the crust 14 m above the salt plane, the break 9 m wide at the origin) and sends
`/ballena/env/mar, costra_h, rotura, rotura_r, rotura_x, rotura_z`. `salar_common.glsl` carries the sea (uMar, uRotura, uMarGeo,
waterCol, holeEdge; under the salt skyColor/skyHaze become water and the sky shows only through the hole), `salar_ground.frag` draws
the sea floor with caustics and the shaft, `salar_mtn.frag` dissolves, `td/shaders/mar_costra.frag` is the crust from below.

1. Once, in the running TD (textport), then Cmd+S:

       exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_mar.py').read())

   It reloads the four shaders, binds the three sea uniforms on their MATs, and builds `/project1/mar_costra` (a Grid SOP that
   renders only when `ballena/env/mar` is 1). Log: /tmp/td_out.txt. In the salar nothing changes.
2. `MUNDO=mar ./correr_td.sh` (or `./correr_todo.sh`). The salt is whole for 25 s, then breaks over 20 s (`BALLENA_ROTURA=1`
   opens it from the start, `0` keeps it whole; `ballena_mundo.set_rotura()` is for her brain, when the arc exists).

### The arc (27 Oct, Violeta: "I want to see how it breaks and how she goes down and once in the experience")

The salt plane IS the crust now: from above it is the salt (with the break's cracks opening onto dark water and the hole), from
below (the eye under the plane, `bajoSal()`) it is the ceiling; the sea floor is its own plane `/project1/mar_fondo` 14 m under it.
`ballena_mundo.ARCO` runs the phases and the renderer reads them every frame: **salar** -> **rotura** (the salt cracks around her
and the hole opens under her, 20 s) -> **descenso** (she leaves Dan's floor and sinks 8 m under the salt; the camera glides down
with her keeping its direction and stays under the crust, 40 s) -> **mar** (she lives there, 180 s by default) -> **ascenso** (she
rises through the hole, 40 s) -> **cierre** (the salt knits shut, 20 s) -> **salar**. Under the sea the frame gets the world's own
grade (saturation 1.45, exposure 0.55: the one tonemap greyed the water; Violeta: "render1 looks better than the final") blended
with her depth, the panel's sliders still multiply; her colour loses its reds with depth.

    MUNDO=salar BALLENA_MAR=auto ./correr_td.sh      # the cycle: 20 s on the salt, then break, down, 3 min, up, close, repeat
    MUNDO=mar ./correr_td.sh                         # already in the sea
    BALLENA_ESPERA_S BALLENA_ROTURA_S BALLENA_DESCENSO_S BALLENA_ESTANCIA_S BALLENA_ASCENSO_S BALLENA_CIERRE_S BALLENA_PROFUNDIDAD_M

Her brain will call `ballena_mundo.romper(px, pz)` when she is overwhelmed and `subir()` when she is calm again; until then the
timers. The renderer's clock for a daytime rehearsal: `{"time_offset_h": h}` on UDP 5006 (the panel's clock slider).

### To set it up on another computer

Dan's package (`fuentes/Yaku_PC_2026-10-20/Paqarina_TD`) with these files as they are here: `ballena_mundo.py`, `ballena_td.py`,
`td/shaders/salar_common.glsl`, `salar_ground.frag`, `salar_mtn.frag`, `mar_fondo.frag`, `mar_fondo.vert`, `mar.html`; from this
repo `docs/td_mar.py`, `correr_td.sh`, `correr_todo.sh`, `cerebro_ballena.py`. Then: run TD, `docs/td_mar.py` once in the textport
(it reloads four shaders, binds uMar / uRotura / uMarGeo, builds mar_fondo), Cmd+S, and launch as above.

The fish (27 Oct): `docs/td_peces.py` once in the textport, after td_mar.py: four instanced schools (mar_peces_0..3, one table of
places per school, td/shaders/mar_peces.vert swims the school on the GPU, mar_peces.frag lights them like the floor), rendered
only in the sea. Positions, counts, sizes and palettes are the SCHOOLS list at the top of the script.

Not in TD yet: coral, marine snow, the plates falling, the shaft as a volume, the sea sound (mar.html has them). Also found in
`ballena_mundo.py` on 26 Oct, from elsewhere: an open sea seen from above, kept as `mar_abierto`.
