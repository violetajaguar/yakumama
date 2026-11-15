# Brian's new model (joya+ballena2.blend) into TouchDesigner — 23 Oct 2026

The file on the Desktop, `joya+ballena2.blend`, is the same whale (30 bones, the four face shapes, 2,566 body vertices) plus
**eight copper jewels** (five cogollos and three flowers, each a small armature of `tallo` bones with petal planes) placed on
her back, 1.3 to 1.7 m behind the head at the height of her skin. It was built in Blender 5.1 from Sketchfab glTF imports,
so the whale's objects carried `.001` suffixes and the jewels were parented to nothing (they would have stayed in place while
she bends).

## What was prepared (done, in `fuentes/Yaku_PC_2026-10-20/Paqarina_TD/`)

- `whale2.blend` — a cleaned copy: the whale's objects, armature and materials back to their original names (`ballena low`,
  `eye.L`, `side_fine.R`, `ballena`, `ojo`…), so every path the project uses still holds (`/project1/whale/ballena_low`,
  the MATs `ballena` and `ojo`, `td_name_overrides.json`, `rest_offsets.json`); the eight jewels renamed `joya_01`…`joya_08`,
  their bones made unique (`j01_tallo.008`…), and **parented to the bone `spine.001`** with their transform kept, so they
  ride her back; the stray glTF empties removed; the jewel materials named `joya` and `joya_flor`.
- `whale2.fbx` — exported with Dan's settings (CLAUDE.md §2: Armature + Mesh only, no leaf bones, only deform bones, no
  baked animation, textures embedded, path mode Copy). 33 MB.
- `whale2.glb` — the same, for `ballena_body.py` / `ballena_rig_inspect.py`. Checked: all 30 whale joints present, the four
  morph targets `parpadeo / angry / sad / asombrado` present, 72 jewel joints added, materials `ballena, joya, joya_flor, ojo`.
- `rig_whale2.json` — the rig of the new file. `rig.json` still describes `whale.glb` (what the renderer reads today);
  swap them when the FBX is swapped (step 6).
- `td/shapes_fbx.json` stays valid: the body mesh and its four shapes are identical to `whale.fbx`.

## The swap, in TouchDesigner (Violeta, at the machine)

Order matters: the FBX reload rebuilds everything inside the COMP, so the scripts that dressed her must run again, and the
rest pose must be captured on a clean rig before any OSC reaches it.

1. Stop everything: `bash correr_todo.sh --parar`. Open TD with the current project (`Paqarina_mac.11.toe`).
2. Textport, the file swap:
   ```
   w = op('/project1/whale'); w.par.file = project.folder + '/whale2.fbx'; w.par.reload.pulse()
   ```
   (or set **File** on the FBX COMP's parameters and press **Reload**). She should appear with the jewels on her back.
   If she faces the wrong way, the FBX COMP's Forward Direction is the knob (CLAUDE.md §2).
3. Text DAT → Run Script, on the CLEAN rig, nothing driving it: `td/capture_rest_rotations.py`
   (writes `rest_offsets.json` and `td_name_overrides.json` again).
4. Start Dan's brain only (from the project folder):
   `BALLENA_AUDIO_OUT=MacBook ../../../venv_td/bin/python -u ballena_td.py --violeta --brain`
   The Rename CHOP export binds every bone channel by name; the 30 whale bones have the same names, so they bind alone.
   The jewel bones receive nothing and stay still relative to `spine.001`.
5. Her face, in this order (the Mac build's blink path, same as 21 Oct):
   `td/setup_shapes_sop.py` → `td/fix_blendshape_names.py` → `td/setup_shapes_fbx.py`; then `td/diag_blink.py` must say
   the render flag is on `sop_deform` and the lids move.
6. Her look: `td/setup_pbr.py` (satin, the normal map), `td/setup_skin.py` (the tint follows the brain), `td/setup_whale_light.py`.
   Then `docs/td_colores.py` for the blue tongue and gold teeth. Copy `rig_whale2.json` over `rig.json` when happy.
7. Check: `ballena_td.py --test-world` and `--test-scale` (CLAUDE.md: ~100 units per metre), a visit to the cactus, a blink.
8. Save: Cmd+S (TD writes `Paqarina_mac.12.toe`). Then `AUDIO=MacBook bash correr_todo.sh`.

If anything in step 5 or 6 prints a Windows path, `td/relocate_paths.py` first (the setup scripts carry the PC's folders).

## What stays open after the swap

- The jewels import as Phong MATs; their copper (metallic/roughness maps from Sketchfab) needs a PBR MAT like hers
  (`setup_pbr.py` is written for the body only).
- The jewels do not move by themselves. If Violeta wants them to sway with her, a small tallo bone chain can be driven from
  the brain later (they already have bones).

## Done, 23 Oct 09:57 — what actually happened

- The swap ran from this session through the textport, with `docs/td_run.py` (runs the script named in /tmp/td_next.txt and writes its
  output to /tmp/td_out.txt, readable from outside TD). The FBX COMP's re-import is the pulse **`imp`** (`reloadcustom` / `reloadbuiltin`
  are toggles for the parameter pages and do nothing to the file); `docs/td_modelo2.py` sets the file, then `w.par.imp.pulse()`.
- After the import: 77 operators in the COMP (41 before), the 36 new ones are the jewel meshes; `ballena_low`, `spine_001`, `eye_L1`
  resolve; no errors. Then `capture_rest_rotations`, `setup_shapes_sop`, `fix_blendshape_names` (all four shapes move points),
  `setup_shapes_fbx` (2,562 of 2,566 points matched, 4 by nearest neighbour), Dan's brain, `setup_skin`, `setup_whale_light`
  (the jewels got the light too), `td_colores` (tongue and teeth painted on their own MAT copies, parameter mode set to constant so
  the brain's tint never touches them). Saved as `Paqarina_mac.13.toe`.
- **`td/setup_pbr.py` blocks TouchDesigner on this build**: it first failed on `par.lights.eval()` returning a list (patched), and on the
  second run it never returned, with TD's UI frozen for ten minutes (steady 34 % CPU). Force-quit and redo without it. She renders with
  the Phong look of the earlier days; the satin PBR look is still to be solved (probably the 43-mesh loop or the normal-map read).
- Jewels: copper Phong (`joya`, `joya_flor` MATs, 36 copies). The rig for the renderer stays `rig.json` of whale.glb (30 bones);
  `rig_whale2.json` holds the 104-bone rig if the jewel bones are ever driven.

## What the afternoon taught (23 Oct, 14:40) — the procedure that is actually right

1. **No pose.** Dan's August whale.fbx has every bone at zero and the mesh at rest (checked by re-importing it into Blender and by
   parsing it raw). The pose saved in whale.blend was never exported. `construir_whale2.py` now exports at rest (APLICAR_POSE=1 would
   re-enable the old mistake). Applying the pose had shifted her 2.7 m off the COMP origin (the camera lost her), folded the fins and
   opened the jaw.
2. **Jewels as static meshes on spine.001**, world transform baked: their own 0.03-scaled armatures came out 30x long in TD (stems through
   her body). Brian's `base flor` / `base nariz` are skinned to her armature by bone name and ride along.
3. **One body material named `ballena`**: Brian's file carried a duplicate (`ballena.002`) on the body; `setup_skin.py` tints only MATs
   named `ballena`, so the body would not have followed her moods. The build script merges it.
4. **Rest offsets come from the FBX, not from a capture** (`docs/rest_desde_fbx.py`): once the Rename CHOP export exists, a capture reads
   the OSC channels, and Dan's brain adds the offsets to everything it sends (even `--reset`), so captures compounded (fins 87 -> 102,
   jaw 8 -> 11). Parsed raw, whale2.fbx has exactly Dan's numbers (spine.002 -177.62, fins 0.26/4.65/94.91, jaw -4.61, turbine -87.45).
5. **The import pulse is `imp`** on the FBX COMP; `reloadcustom`/`reloadbuiltin` are parameter-page toggles.
6. **Typing into the textport from outside works only while no perform window has been opened**; after that, keystrokes go astray. The
   two-line path for a person at the machine: `docs/td_todo_1.py` (file + import, then the face scripts, stage by stage through
   /tmp/td_stage.txt) and `docs/td_todo_2.py` (skin, light, colours), with Dan's brain stopped for the first and running for the second;
   `docs/td_run.py` logs any script's output to /tmp/td_out.txt.
7. **`td/setup_pbr.py` blocks TD on this build** (a `par.lights.eval()` list, patched; then a hang). Left out; she renders Phong.
8. **Her eye's colour box sits on the printed sister, which is white, and white = diving in her colour map**: she dove all day, fins
   still (diving phrases), floor fighting her. `cerebro_ballena.compute_mood` now takes white/grey/black only from a person's clothes.
9. The printed whale's board sent `nan` for every SERVO field; the bridge ignores NaN lines now.

## Her look, the stack in order (23 Oct, afternoon) — one material model, one transform, coordinated
1. `docs/td_pbr.py` — PBR on all of her: body (mood colour from the brain, roughness, her normal map), eyes, tongue (blue) and teeth
   (gold) as constants, the jewels from their maps; plus the environment light on env_sky. Originals kept in /project1/pbr_originals.
2. `docs/td_tonemap_build.py` + `docs/td_todo_3.py` (world rebuilt) + `docs/td_interruptores.py` (switches) — ONE display transform
   for her and the world: everything renders linear, /project1/tonemap does exposure -> ACES -> grade -> gamma. Measured: the pass
   outputs exactly its maths (no double gamma); the pale midday is the content (high sun over white salt at expo 1.05) and is tuned
   from the panel (exposure bias, saturation, ambient).
3. `docs/td_niebla.py` — the world's haze on her (camera fog, same law and colour as the salar's).
4. `td/setup_whale_light.py` — her lights, post-tonemap (linear * LIGHT_GAIN 1.0; MOONLIGHT 0.012); `docs/td_ajuste.py` for
   roughness / env strength by eye.
5. `docs/td_sombras3.py` — the sun and the bounce as CONE lights (position kept: the glint sweeps; shadows possible) with soft shadow
   maps, casters = her geometry. (td_sombras / td_sombras2 were the two failed attempts: point lights cannot shadow; distant lights
   lose the sweep and gave the Phong tongue a white specular at night.)
Undo paths: REVERT = True in td_pbr; td_tonemap_build with MODE 'revert' + td_interruptores APAGAR; NIEBLA = 0; SOMBRAS = 0.
