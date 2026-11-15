"""
rest_desde_fbx.py - rest_offsets.json straight from the FBX (23 Oct 2026). Dan's capture_rest_rotations.py reads each bone's
Rotate from TD right after import, which is the FBX node's Lcl Rotation; but once the Rename CHOP export exists, a capture reads
the LAST OSC VALUES instead (and Dan's brain adds the offsets to everything it sends, so captures compounded: fins 87 -> 102,
jaw 8 -> 11). This writes the same numbers from the file itself, deterministically, with Blender's FBX parser.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python /Users/jaguar/Desktop/Yakumama/docs/rest_desde_fbx.py -- <Paqarina_TD> [whale2.fbx]
"""
import sys, os, json
from io_scene_fbx import parse_fbx
OUT = sys.argv[sys.argv.index("--") + 1]; FBX = sys.argv[sys.argv.index("--") + 2] if len(sys.argv) > sys.argv.index("--") + 2 else "whale2.fbx"
root, version = parse_fbx.parse(os.path.join(OUT, FBX))
objs = next(e for e in root.elems if e.id == b"Objects"); rest = {}
for e in objs.elems:
    if e.id != b"Model" or e.props[2] != b"LimbNode": continue
    name = e.props[1].decode().split("\x00")[0]; rot = (0.0, 0.0, 0.0)
    for p70 in e.elems:
        if p70.id == b"Properties70":
            for p in p70.elems:
                if p.props[0].decode() == "Lcl Rotation": rot = tuple(float(x) for x in p.props[4:7])
    if name.startswith("j0"): continue   # jewel bones, if any
    rest[name] = {"rx": rot[0], "ry": rot[1], "rz": rot[2]}
json.dump(rest, open(os.path.join(OUT, "rest_offsets.json"), "w"), indent=2)
print("rest_offsets.json from", FBX, ":", len(rest), "bones |", {k: tuple(round(v, 2) for v in rest[k].values()) for k in ("spine.002", "side_fine.L", "head", "mouth_inf.001", "turbine") if k in rest})
