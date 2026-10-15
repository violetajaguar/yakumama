#!/usr/bin/env python3
"""resumen.py - segundos grabados por animo: cara y cuerpo (de grabar_ballena.py) y cara_webcam (de grabar_cara.py)."""
import os, glob, json
def segundos(f):
    """segundos reales por los tiempos t de cada linea (sin huecos de pausa > 0.5 s); no supone 30 paquetes/s."""
    try: ts = [json.loads(l)["t"] for l in open(f, errors="ignore") if l.strip()]
    except Exception: return 0.0
    return sum(b - a for a, b in zip(ts, ts[1:]) if 0 <= b - a < 0.5)
AQUI = os.path.dirname(os.path.abspath(__file__))
ANIMOS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
def seg(carp):
    out = {}
    for f in glob.glob(os.path.join(AQUI, "datasets", carp, "*.jsonl")):
        a = os.path.basename(f).split("_")[0]; out[a] = out.get(a, 0) + segundos(f)
    return out
c, b, w = seg("cara"), seg("cuerpo"), seg("cara_webcam")
print(f"{'animo':10s} {'cara':>6s} {'cuerpo':>7s} {'webcam':>7s}   (segundos; meta 60 por animo)")
for a in ANIMOS: print(f"{a:10s} {c.get(a,0):6.0f} {b.get(a,0):7.0f} {w.get(a,0):7.0f}   {'ok' if c.get(a,0)>=60 else '..'}")
print(f"{'TOTAL':10s} {sum(c.values()):6.0f} {sum(b.values()):7.0f} {sum(w.values()):7.0f}")
