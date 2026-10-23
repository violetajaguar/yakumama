"""
td_isla.py - run INSIDE TouchDesigner, in the textport (22 Oct 2026). The island and its cacti stopped showing in the render
(they were there on 21 Oct, Paqarina_mac.3.toe; on the .9 project the cactus visit shows only water). This lists every operator
whose name mentions the island, the cacti, the mountains or the salt, with its render/display flags and the file it loads, and
whether that file exists on this Mac. If an island or cactus operator has its render flag OFF, it turns it on and says so.
Then Cmd+S.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_isla.py').read())
"""
import os, re
PATRON = re.compile(r"isla|island|cact|mtn|mountain|montan|salt|salar", re.I)
print("=" * 78)
for o in op('/').findChildren(maxDepth=8):
    if not PATRON.search(o.name): continue
    flags = []
    for f in ("render", "display", "bypass", "lock"):
        if hasattr(o, f):
            try: flags.append(f"{f}={'ON' if getattr(o, f) else 'off'}")
            except Exception: pass
    archivo = ""
    for pn in ("file", "sopfile", "obj", "filepath"):
        if hasattr(o.par, pn):
            try:
                v = str(getattr(o.par, pn).eval()); archivo = f"file={v} ({'exists' if os.path.exists(v) else 'MISSING'})" if v else ""
            except Exception: pass
            break
    err = ""
    try: err = o.errors() or o.warnings() or ""
    except Exception: pass
    print(f"  {o.path:46s} {o.family:5s} {o.type:12s} {' '.join(flags):40s} {archivo} {('ERR: ' + str(err)[:80]) if err else ''}")
    if o.family == "COMP" and hasattr(o, "render") and re.search(r"isla|island|cact", o.name, re.I):
        try:
            if not o.render: o.render = True; print(f"     -> {o.path}: render flag was OFF, turned ON")
        except Exception as e: print(f"     (could not set render on {o.path}: {e})")
print("=" * 78); print("project:", project.name, "| folder:", project.folder)
print("If an island/cactus COMP says file MISSING, the path broke on the Mac (the C:/ link); tell Claude the path printed.")
