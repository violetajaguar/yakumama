"""
construir_whale3.py - Dan's whale.blend as the base, Brian's additions appended (23 Oct 2026, v3).
v2 rebuilt the whale from Brian's file and applied the August pose, but the exported zero still differed from August's
(fins near vertical, jaw open in TD). v3 keeps the whale EXACTLY as Dan exported it in August: it opens whale.blend (posed, as
it was) and appends from Brian's file only what is new: the jewel pieces (baked static, placed on the posed spine.001),
and the skinned 'base flor' / 'base nariz' (re-bound to the old armature: same bone names). Then exports with Dan's settings.

    /Applications/Blender.app/Contents/MacOS/Blender --background "<Paqarina_TD>/whale.blend" \
        --python /Users/jaguar/Desktop/Yakumama/docs/construir_whale3.py -- <Paqarina_TD> "/Users/jaguar/Desktop/Yakumama/fuentes/blender/joya+ballena5.blend"
"""
import bpy, sys, os
from mathutils import Matrix
OUT, BRIAN = sys.argv[sys.argv.index("--") + 1], sys.argv[sys.argv.index("--") + 2]
WHALE_MESHES = ("aleta low", "ballena low", "cola turbina", "dientes low", "eye.L", "eye.R", "LENGUA.low")
old_arm = bpy.data.objects["side_fine.R"]
# what Brian's file holds
with bpy.data.libraries.load(BRIAN, link=False) as (src, dst):
    names = list(src.objects)
    quiere = [n for n in names if not any(n == w or (n.startswith(w + ".") and n[len(w) + 1:].isdigit()) for w in WHALE_MESHES)]
    quiere = [n for n in quiere if not (n.startswith("side_fine.R") )]  # not his copy of the whale armature (appended separately below)
    dst.objects = quiere + [n for n in names if n.startswith("side_fine.R")]
appended = [o for o in dst.objects if o is not None]
brian_arm = next(o for o in appended if o.type == "ARMATURE" and o.name.startswith("side_fine.R"))
for o in appended: bpy.context.scene.collection.objects.link(o) if o.name not in bpy.context.scene.collection.objects else None
rest_spine = brian_arm.matrix_world @ brian_arm.data.bones["spine.001"].matrix_local          # Brian's spine.001 at rest (world)
posed_spine = old_arm.matrix_world @ old_arm.pose.bones["spine.001"].matrix                    # Dan's spine.001 as posed (world)
# jewels: static pieces on the posed spine
jewel_arms = sorted([o for o in appended if o.type == "ARMATURE" and o is not brian_arm], key=lambda o: o.name); piezas = []
base_objs = [o for o in appended if o.type == "MESH" and o.name.startswith("base")]   # collected before anything is removed
for i, j in enumerate(jewel_arms):
    for k, m in enumerate(sorted([c for c in j.children if c.type == "MESH"], key=lambda c: c.name)):
        mw = m.matrix_world.copy()
        for mod in list(m.modifiers): m.modifiers.remove(mod)
        m.parent = None; m.data.transform(mw); m.matrix_world = Matrix.Identity(4)
        rel = rest_spine.inverted() @ Matrix.Identity(4)                                      # the piece in the rest bone's frame
        m.parent = old_arm; m.parent_type = "BONE"; m.parent_bone = "spine.001"; m.matrix_world = posed_spine @ rel
        m.name = f"joya_{i+1:02d}_{k+1:02d}"; m.data.name = m.name; piezas.append(m.name)
    bpy.data.objects.remove(j, do_unlink=True)
# Brian's skinned additions: bound to the old armature by bone names
bases = []
for o in base_objs:
    if True:
        for mod in list(o.modifiers): o.modifiers.remove(mod)
        mw = o.matrix_world.copy(); o.parent = old_arm; o.parent_type = "OBJECT"; o.matrix_world = mw
        mod = o.modifiers.new("Armature", "ARMATURE"); mod.object = old_arm; bases.append(o.name)
bpy.data.objects.remove(brian_arm, do_unlink=True)
for o in list(bpy.data.objects):
    if o.type == "EMPTY" or (o.type == "MESH" and o.name.endswith(".001") and o.name[:-4] in WHALE_MESHES): bpy.data.objects.remove(o, do_unlink=True)
for a, b in (("Material", "joya"), ("Material.001", "joya_flor")):
    if a in bpy.data.materials: bpy.data.materials[a].name = b
for m in list(bpy.data.materials):   # no stray body copies
    if m.name.startswith("ballena.") and m.users == 0: bpy.data.materials.remove(m)
print("JEWEL PIECES:", len(piezas), "| BASES:", bases, "| MATERIALS:", [m.name for m in bpy.data.materials])
print("MESHES:", [o.name for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("joya_")])
for o in bpy.data.objects: o.hide_set(False); o.hide_viewport = False; o.select_set(o.type in ("ARMATURE", "MESH"))
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "whale2.fbx"), use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, use_armature_deform_only=True, bake_anim=False, path_mode="COPY", embed_textures=True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "whale2.glb"), use_selection=True, export_format="GLB", export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "whale2.blend"), copy=True)
print("EXPORTED whale2.* to", OUT)
