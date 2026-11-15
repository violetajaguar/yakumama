"""
construir_whale2.py - Brian's Blender file -> whale2.fbx / whale2.glb / whale2.blend for TouchDesigner (23 Oct 2026).
Run OUTSIDE TD, with Blender on the command line (no need to open Blender):

    /Applications/Blender.app/Contents/MacOS/Blender --background "/Users/jaguar/Desktop/Yakumama/fuentes/blender/joya+ballena2.blend" \
        --python /Users/jaguar/Desktop/Yakumama/docs/construir_whale2.py -- /Users/jaguar/Desktop/Yakumama/fuentes/Yaku_PC_2026-10-20/Paqarina_TD

What it does, every time, so a new file from Brian needs nothing by hand:
  1. the whale's objects, armature and materials back to their original names (TD's paths: ballena_low, eye_L1, MAT ballena/ojo);
  2. every jewel turned into static meshes (world transform baked, no armature: their 0.03-scaled rigs came out 30x long in TD),
     parented to the whale's bone spine.001, named joya_NN_MM, materials joya / joya_flor;
  3. the stray glTF empties removed;
  4. THE OLD POSE APPLIED (whale_pose_aug2026.json, next to the package): whale.fbx (Aug 2026) was exported with the armature in a
     saved pose (root 2.7 back along the body, head +8.5 / -9 deg, jaw open, the left fin folded 15 and 10 deg...). TD's rest
     offsets, Dan's by-eye tuning and the floor model (whale.glb) all sit on that zero. Brian's file is at true rest, so without
     this she leans, the left fin starts unfolded and her belly dips under the salt (seen 23 Oct). Same pose = same zero.
  5. export with Dan's FBX settings (CLAUDE.md §2) + a GLB + a copy of the cleaned .blend.
Then in TD: docs/td_modelo2.py (file + import pulse), td/capture_rest_rotations.py, the face scripts, setup_skin, setup_whale_light,
docs/td_colores.py; see docs/MODELO_NUEVO_TD.md.
"""
import bpy, sys, os, json, math
OUT = sys.argv[sys.argv.index("--") + 1]
POSE = os.path.join(OUT, "whale_pose_aug2026.json")
WHALE_NAMES = ("aleta low", "ballena low", "cola turbina", "dientes low", "eye.L", "eye.R", "LENGUA.low", "side_fine.R")
# 1. names
for o in list(bpy.data.objects):
    for base in WHALE_NAMES:
        if o.name != base and o.name.startswith(base + ".") and o.name[len(base) + 1:].isdigit():
            if base in bpy.data.objects: bpy.data.objects[base].name = base + ".old"
            o.name = base
for m in list(bpy.data.materials):
    for base in ("ballena", "ojo"):
        if m.name != base and m.name.startswith(base + ".") and m.name[len(base) + 1:].isdigit():
            if base in bpy.data.materials and bpy.data.materials[base].users == 0: bpy.data.materials.remove(bpy.data.materials[base])
            if base not in bpy.data.materials: m.name = base
# one body material named 'ballena' on every whale mesh (23 Oct: Brian's file carried a duplicate 'ballena.002' on the body; TD's
# setup_skin.py tints only MATs named 'ballena', so the body would not have followed her moods)
_ball = bpy.data.materials.get("ballena") or next((m for m in bpy.data.materials if m.name.startswith("ballena")), None)
if _ball is not None:
    _ball.name = "ballena"
    for o in bpy.data.objects:
        if o.type == "MESH":
            for sl in o.material_slots:
                if sl.material is not None and sl.material.name.startswith("ballena.") : sl.material = _ball
if "Material" in bpy.data.materials: bpy.data.materials["Material"].name = "joya"
if "Material.001" in bpy.data.materials: bpy.data.materials["Material.001"].name = "joya_flor"
whale = bpy.data.objects["side_fine.R"]
# 2. jewels ride spine.001 as STATIC meshes (23 Oct: their own little armatures carried a 0.03 scale that TouchDesigner's flat import
#    dropped, so the stems came out ~30x long and ran through her body, out below the left fin). Each jewel mesh gets its world
#    transform baked into its points, loses its armature modifier, and is parented straight to the whale's bone spine.001.
joyas = sorted([o for o in bpy.data.objects if o.type == "ARMATURE" and o is not whale], key=lambda o: o.name)
piezas = []
for i, j in enumerate(joyas):
    for k, m in enumerate(sorted([c for c in j.children if c.type == "MESH"], key=lambda c: c.name)):
        mw = m.matrix_world.copy()
        for mod in list(m.modifiers): m.modifiers.remove(mod)
        m.parent = None; m.data.transform(mw); m.matrix_world.identity(); m.name = f"joya_{i+1:02d}_{k+1:02d}"; m.data.name = m.name
        m.parent = whale; m.parent_type = "BONE"; m.parent_bone = "spine.001"; m.matrix_world.identity()   # world kept: the points already carry it
        piezas.append(m.name)
    bpy.data.objects.remove(j, do_unlink=True)
print("JEWEL PIECES:", len(piezas), piezas[:6], "...")
# 3. empties out
for o in list(bpy.data.objects):
    if o.type == "EMPTY": bpy.data.objects.remove(o, do_unlink=True)
# 4. NO pose (23 Oct, 13:30): Dan's August whale.fbx, imported back into Blender, has every bone at zero and the mesh at rest:
#    the pose saved in whale.blend was never exported. Applying it moved her 2.7 m off the COMP origin (camera lost her), folded the
#    fins and opened the jaw. So: rest pose, exactly like August. (APLICAR_POSE=1 in the environment re-enables the old behaviour.)
pose = json.load(open(POSE)) if os.environ.get("APLICAR_POSE") == "1" else {}; aplicados = 0
for pb in whale.pose.bones:
    p = pose.get(pb.name)
    if not p: continue
    pb.rotation_mode = p["mode"] if p["mode"] != "QUATERNION" else "XYZ"
    pb.rotation_euler = [math.radians(a) for a in p["rot_deg"]]; pb.location = p["loc"]; pb.scale = p["scale"]; aplicados += 1
bpy.context.view_layer.update()
print("POSE applied to", aplicados, "bones from", POSE)
print("JEWELS: static pieces on spine.001:", len(piezas))
print("MATERIALS:", [m.name for m in bpy.data.materials])
# 5. export
for o in bpy.data.objects: o.hide_set(False); o.hide_viewport = False; o.select_set(o.type in ("ARMATURE", "MESH"))
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "whale2.fbx"), use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, use_armature_deform_only=True, bake_anim=False, path_mode="COPY", embed_textures=True, mesh_smooth_type="OFF")   # use_mesh_modifiers stays at Blender's default (True), as in Dan's August export: the mesh goes out posed
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "whale2.glb"), use_selection=True, export_format="GLB", export_apply=False, export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "whale2.blend"), copy=True)
print("EXPORTED whale2.fbx / whale2.glb / whale2.blend to", OUT)
