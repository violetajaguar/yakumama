#!/usr/bin/env python3
"""comportamientos.py - los diez comportamientos del cuerpo de Yakumama, fuera de Blender: para medirlos, exportarlos a
Dan (TouchDesigner / la ballena fisica) y comprobar que son DISTINTOS entre si.

Lee las funciones comp_* tal cual estan en receptor_ballena.py (la fuente de verdad: lo que ella hace en Blender) y las
muestrea. Cada comportamiento da, por cuadro: pitch, roll, yaw, head (rad en el esqueleto de Blender), spine[6] (rad por
vertebra), fluke, flap, ladeo (aletas, rad), jaw (0..1), cara (parpado, rabia, tristeza, asombro: 0..1), mirada (yaw,
pitch: -1..1), spin (rad, vueltas sobre su eje), depth (sube +, baja -, unidades de Blender), y por animo: color RGB,
turbina (rad/s), latido (0..1).

    venv/bin/python comportamientos.py                 -> matriz de distancias entre animos (cuanto se parecen)
    venv/bin/python comportamientos.py --exportar DIR  -> DIR/<animo>.csv + DIR/comportamientos.json (40 s a 30/s)
"""
import os, re, sys, json, math, argparse, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
def cargar():
    """exec del tramo de receptor_ballena.py que define _onda .. COMPORTAMIENTOS (sin bpy)."""
    src = open(os.path.join(AQUI, "receptor_ballena.py"), encoding="utf-8").read()
    a = src.index("def _onda("); b = src.index("COMP_CERO = ")
    ns = {"math": math}; exec(src[a:b], ns)
    extra = {}
    for k in ("TURBINA_ANIMO", "LATIDO_ANIMO", "MOOD_RGB", "PLAYFUL_VUELTAS"):
        m = re.search(r"^%s\s*=\s*(\{.*?\}|\d+)" % k, src, re.S | re.M)
        if m:
            txt = m.group(1)
            if txt.startswith("{"): txt = txt[:txt.index("}") + 1]
            try: extra[k] = eval(txt, {})
            except Exception: pass
    return ns["COMPORTAMIENTOS"], extra
CANALES = ["pitch", "roll", "yaw", "head"] + [f"spine{i}" for i in range(6)] + ["fluke", "flap", "ladeo", "jaw", "parpado", "rabia", "tristeza", "asombro", "mirada_yaw", "mirada_pitch", "spin", "depth"]
def aplanar(c):
    return [c["pitch"], c["roll"], c["yaw"], c["head"], *c["spine"], c["fluke"], c["flap"], c["ladeo"], c["jaw"], *c["cara"], *c["mirada"], c["spin"], c["depth"]]
def muestrear(fn, dur=40.0, fps=30.0):
    return np.array([aplanar(fn(i / fps)) for i in range(int(dur * fps))], np.float64)
def rasgos(X, fps=30.0):
    """firma de un comportamiento: media, amplitud y periodo dominante por canal (el periodo en segundos, 0 si quieto)."""
    med = X.mean(0); amp = X.max(0) - X.min(0); per = np.zeros(X.shape[1])
    for j in range(X.shape[1]):
        v = X[:, j] - med[j]
        if v.std() < 1e-4: continue
        F = np.abs(np.fft.rfft(v)); f = np.fft.rfftfreq(len(v), 1 / fps); F[0] = 0; k = int(np.argmax(F)); per[j] = 1 / f[k] if f[k] > 0 else 0
    return med, amp, per
def distancias(COMP, dur=40.0, fps=30.0):
    """distancia entre cada par de animos sobre la firma (media y amplitud, canales normalizados a su rango entre animos)."""
    R = {}
    for m in MOODS:
        X = muestrear(COMP[m], dur, fps); med, amp, per = rasgos(X, fps); R[m] = (med, amp, per)
    M = np.array([np.concatenate([R[m][0], R[m][1]]) for m in MOODS]); esc = M.max(0) - M.min(0); esc[esc < 1e-6] = 1; Mn = M / esc
    D = np.sqrt(((Mn[:, None, :] - Mn[None, :, :]) ** 2).sum(-1)); return D, R
def informe(D, R):
    n = len(MOODS); print("distancia entre animos (0 = iguales; firma = media y amplitud de 24 canales):")
    print("            " + " ".join(f"{m[:5]:>5s}" for m in MOODS))
    for i, m in enumerate(MOODS): print(f"  {m:9s} " + " ".join(f"{D[i, j]:5.2f}" if i != j else "    ." for j in range(n)))
    pares = sorted(((D[i, j], MOODS[i], MOODS[j]) for i in range(n) for j in range(i + 1, n)))
    print("  los mas parecidos:", ", ".join(f"{a}-{b} {d:.2f}" for d, a, b in pares[:5])); print("  los mas distintos:", ", ".join(f"{a}-{b} {d:.2f}" for d, a, b in pares[-3:]))
    print("  cada animo, su vecino mas cercano: " + ", ".join(f"{m}->{MOODS[int(np.argsort(D[i])[1])]} {np.sort(D[i])[1]:.2f}" for i, m in enumerate(MOODS)))
    return pares
def exportar(COMP, extra, carpeta, dur=40.0, fps=30.0):
    os.makedirs(carpeta, exist_ok=True); todo = {"fps": fps, "segundos": dur, "canales": CANALES, "unidades": {"pitch roll yaw head spine* fluke flap ladeo spin": "radianes en el esqueleto de Blender (pitch < 0 = nariz abajo)", "jaw parpado rabia tristeza asombro": "0..1", "mirada_*": "-1..1", "depth": "unidades de Blender, + sube"},
            "por_animo": {}}
    for m in MOODS:
        X = muestrear(COMP[m], dur, fps); med, amp, per = rasgos(X, fps)
        with open(os.path.join(carpeta, f"{m}.csv"), "w") as fh:
            fh.write("t," + ",".join(CANALES) + "\n")
            for i, fila in enumerate(X): fh.write(f"{i / fps:.3f}," + ",".join(f"{v:.4f}" for v in fila) + "\n")
        todo["por_animo"][m] = {"color_rgb": extra.get("MOOD_RGB", {}).get(m), "turbina_rad_s": extra.get("TURBINA_ANIMO", {}).get(m), "latido": extra.get("LATIDO_ANIMO", {}).get(m),
                               "media": dict(zip(CANALES, np.round(med, 4).tolist())), "amplitud": dict(zip(CANALES, np.round(amp, 4).tolist())), "periodo_s": dict(zip(CANALES, np.round(per, 2).tolist()))}
    json.dump(todo, open(os.path.join(carpeta, "comportamientos.json"), "w"), indent=1, ensure_ascii=False); print("exportado", carpeta)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--exportar", default=None); a = ap.parse_args()
    COMP, extra = cargar(); D, R = distancias(COMP); informe(D, R)
    if a.exportar: exportar(COMP, extra, a.exportar)
