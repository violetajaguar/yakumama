#!/usr/bin/env python3
"""coreografias_extraer.py - la coreografia en el espacio de cada animo sale de los cuerpos reales: por donde se movieron
los bailarines de Paqarina (tinku -> angry, kullawada -> playful, suri -> curious, breaking -> alert), el ballet (sad) y el
jazz (singing) de ImperialDance, los nadadores de la CMU (mariposa/crol -> surfacing, pecho/espalda -> feeding), y la
yubarta real con etiqueta (diving: su rumbo y su profundidad en un buceo). De cada toma se toma el camino de la pelvis
(x, y en el piso, z la altura), a 10 cuadros/s, en tramos de hasta 45 s, centrado y escalado a radio 1; el receptor lo
reproduce a su escala y con el rumbo del camino. Guarda modelos/coreografias.json.

    venv/bin/python coreografias_extraer.py
"""
import os, glob, json, numpy as np, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from cuerpo_cualidades import cargar_npz
H26 = os.path.expanduser("~/Desktop/h26_limpio"); CV = os.path.join(AQUI, "datasets", "cuerpo_video"); FPS = 10.0; MAXSEG = 45.0; POR_ANIMO = 6
FUENTES = {"angry": glob.glob(H26 + "/*tinku*.npz"), "playful": glob.glob(H26 + "/*kullawada*.npz"), "curious": glob.glob(H26 + "/*suri*.npz"), "alert": glob.glob(H26 + "/*breaking*.npz") + glob.glob(H26 + "/*toprock*.npz"),
           "sad": sorted(glob.glob(CV + "/ballet_experta_*_000.npz")) + sorted(glob.glob(CV + "/ballet_intermedia_*_000.npz")), "singing": sorted(glob.glob(CV + "/jazz_experta_*_000.npz")) + sorted(glob.glob(CV + "/jazz_intermedia_*_000.npz")),
           "surfacing": glob.glob(CV + "/swim_cmu_butterfly_*.npz") + glob.glob(CV + "/swim_cmu_freestyle_*.npz"), "feeding": glob.glob(CV + "/swim_cmu_breaststroke_*.npz") + glob.glob(CV + "/swim_cmu_backstroke_*.npz")}
def limpiar(p, fps):
    """camino de la pelvis: sin NaN, sin saltos, a 10/s, centrado, radio 1 en el piso; z respecto de su mediana."""
    ok = np.isfinite(p).all(1); idx = np.arange(len(p))
    if ok.sum() < fps * 5: return None
    p = np.stack([np.interp(idx, idx[ok], p[ok, i]) for i in range(3)], 1)
    v = np.linalg.norm(np.diff(p, axis=0), axis=1); salto = np.flatnonzero(v > 0.5 * (30 / fps))   # un salto de mas de 0.5 m por cuadro (a 30/s) es ruido
    for i in salto: p[i + 1:] -= (p[i + 1] - p[i])
    paso = max(1, int(round(fps / FPS))); p = p[::paso]
    k = 5; p = np.stack([np.convolve(p[:, i], np.ones(k) / k, "same") for i in range(3)], 1)
    p[:, :2] -= p[:, :2].mean(0); p[:, 2] -= np.median(p[:, 2])
    r = np.percentile(np.linalg.norm(p[:, :2], axis=1), 95); p[:, :2] /= max(0.15, r); p[:, 2] /= max(0.15, r); p[:, 2] = np.clip(p[:, 2], -0.8, 0.8)
    return p
def tramos(p, nombre):
    n = int(MAXSEG * FPS); out = []
    for s in range(0, len(p), n):
        q = p[s:s + n]
        if len(q) >= 8 * FPS: out.append({"nombre": f"{nombre}:{s // n}", "fps": FPS, "pts": [[round(float(x), 3) for x in fila] for fila in q]})
    return out
def ballena_buceos():
    """diving: tramos de la yubarta real (buceos de mas de 10 m): el rumbo integrado da el camino en el piso, la profundidad la z."""
    out = []
    for f in sorted(glob.glob(os.path.join(AQUI, "datasets", "ballenas", "mn18*.npz")) + glob.glob(os.path.join(AQUI, "datasets", "ballenas", "mn12*.npz"))):
        b = np.load(f, allow_pickle=True); prof = np.nan_to_num(b["prof"]); rumbo = np.nan_to_num(b["rumbo"]); fps = float(b["fps"])
        hondo = prof > 10; i = 0
        while i < len(prof) and len(out) < POR_ANIMO:
            if hondo[i]:
                j = i
                while j < len(prof) and hondo[j]: j += 1
                if 20 * fps < (j - i) < 300 * fps:
                    s, e = max(0, i - int(10 * fps)), min(len(prof), j + int(10 * fps)); r = rumbo[s:e]; z = -prof[s:e]
                    x = np.cumsum(np.sin(r)) / fps; y = np.cumsum(np.cos(r)) / fps; p = np.stack([x, y, z], 1); q = limpiar(p, fps)
                    if q is not None: out += tramos(q, os.path.basename(f)[:-4] + f"_buceo{i // int(fps)}")[:1]
                i = j
            else: i += 1
    return out
if __name__ == "__main__":
    C = {}
    for animo, fs in FUENTES.items():
        C[animo] = []
        for f in sorted(fs):
            try: B, J, fps = cargar_npz(f)
            except Exception: continue
            q = limpiar(B[:, J["pelvis"]].astype(float), fps)
            if q is None: continue
            C[animo] += tramos(q, os.path.basename(f).replace("_limpio.npz", "").replace(".npz", ""))
            if len(C[animo]) >= POR_ANIMO: break
        C[animo] = C[animo][:POR_ANIMO]
    C["diving"] = ballena_buceos()
    json.dump(C, open(os.path.join(AQUI, "modelos", "coreografias.json"), "w")); print("coreografias por animo:", {k: f"{len(v)} tramos, {sum(len(t['pts']) for t in v) / FPS:.0f} s" for k, v in C.items()})
