"""
td_colores.py - run INSIDE TouchDesigner, in the textport (22 Oct 2026, Violeta: "her tongue needs to be blue and her teeth golden,
and that never changes").

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_colores.py').read())

First run: APLICAR = False below -> it only LISTS every material (MAT) and every geometry whose name mentions the tongue or the
teeth (lengua / tongue / diente / teeth / tooth), with its current colour. If the right ones are in the list, set APLICAR = True and
run again: tongue -> blue, teeth -> gold, on every colour parameter those materials have (Phong diffuse, PBR base colour, constant
colour, emit). Then Cmd+S so the project keeps it (the watchdog's save keeps it too).
If nothing is listed, the tongue and teeth share the body's material: say so to Claude and the names of the MATs printed at the end.
"""
import re
APLICAR = False
AZUL = (0.10, 0.30, 0.95)       # tongue
ORO = (1.00, 0.78, 0.20)        # teeth
PATRON = re.compile(r"lengua|tongue|diente|teeth|tooth", re.I)
PARAMS = (("diffr", "diffg", "diffb"), ("basecolorr", "basecolorg", "basecolorb"), ("colorr", "colorg", "colorb"), ("emitr", "emitg", "emitb"))
def _rgb(o):
    for trio in PARAMS:
        if all(hasattr(o.par, k) for k in trio): return trio, tuple(round(float(getattr(o.par, k).eval()), 2) for k in trio)
    return None, None
def _pinta(o, rgb):
    hecho = []
    for trio in PARAMS:
        if all(hasattr(o.par, k) for k in trio):
            for k, v in zip(trio, rgb): setattr(o.par, k, v)
            hecho.append(trio[0][:-1])
    return hecho
mats = [o for o in op('/').findChildren(maxDepth=8) if o.family == 'MAT']
print("=" * 70); print("MATERIALS in the project:", len(mats))
for m in mats:
    trio, rgb = _rgb(m); print(f"  {m.path:50s} {m.type:10s} {rgb}")
cand = [o for o in op('/').findChildren(maxDepth=8) if PATRON.search(o.name)]
print("-" * 70); print("TONGUE / TEETH by name:", len(cand))
for o in cand:
    mat = None
    try: mat = o.par.material.eval() if hasattr(o.par, 'material') else None
    except Exception: pass
    trio, rgb = _rgb(o)
    print(f"  {o.path:50s} {o.family:6s} {o.type:10s} colour {rgb}  material -> {mat.path if mat else '-'}")
    if APLICAR:
        quiere = AZUL if re.search(r"lengua|tongue", o.name, re.I) else ORO
        objetivos = [x for x in (o, mat) if x is not None]
        for x in objetivos:
            h = _pinta(x, quiere)
            if h: print(f"     -> {x.path}: set {h} to {quiere}")
print("=" * 70)
print("APLICAR is", APLICAR, "- set it True in the file and run again to paint; then Cmd+S." if not APLICAR else "- painted. Cmd+S to keep it.")
