#!/usr/bin/env python3
"""verificar.py - run her H-JEPA here on the example input and compare with the output it gave on Violeta's Mac.
    python3 verificar.py            (expects ../modelos/hjepa.pt and ../hjepa_predecir.py, or pass paths: verificar.py hjepa.pt hjepa_predecir_dir)
"""
import sys, os, json, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); modelo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "..", "modelos", "hjepa.pt")
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, "..")); from hjepa_predecir import HJepa, a_ballena
h = HJepa(modelo); ent = json.load(open(os.path.join(AQUI, "entrada.json"))); esp = json.load(open(os.path.join(AQUI, "salida_esperada.json")))
for fr in ent["cuadros"]: h.empujar(fr)
l = h.leer("angry"); fallas = []
def cmp(nombre, a, b, tol=2e-3):
    if isinstance(a, dict): [cmp(f"{nombre}.{k}", a[k], b.get(k)) for k in a]
    elif isinstance(a, list): [cmp(f"{nombre}[{i}]", x, y) for i, (x, y) in enumerate(zip(a, b))] if len(a) == len(b) else fallas.append(f"{nombre}: length {len(a)} vs {len(b)}")
    elif isinstance(a, (int, float)) and not isinstance(a, bool): (abs(float(a) - float(b)) > tol) and fallas.append(f"{nombre}: {a} vs {b}")
    elif a != b: fallas.append(f"{nombre}: {a} vs {b}")
cmp("leer", esp["leer_con_accion_angry"], l)
for m, p in esp["plan"].items(): cmp(f"plan.{m}", p, h.plan(m))
for m, g in esp["generar"].items():
    cu, ams = h.generar(m); cmp(f"generar.{m}.media_32s", g["media_32s"], [round(float(v), 4) for v in cu.mean(0)]); cmp(f"generar.{m}.animos", g["animos_submetas"], ams)
print(f"torch here {__import__('torch').__version__} (hers {esp['torch']}), numpy {np.__version__} (hers {esp['numpy']}), python {sys.version.split()[0]} (hers {esp['python']})")
print(f"body reads {l.get('animo_cuerpo')} ({l.get('p_cuerpo')}), at 16 s {l['prevision']['animo_16s']}, plan surfacing -> {h.plan('surfacing')['accion']}")
print("OK: same answers as on her Mac" if not fallas else f"DIFFERENCES ({len(fallas)}):\n  " + "\n  ".join(fallas[:20]))
