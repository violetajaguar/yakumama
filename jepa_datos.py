#!/usr/bin/env python3
"""jepa_datos.py - junta todo lo que la ballena puede aprender en UNA secuencia por toma, a 12 cuadros/s, con mascara.

24 canales por cuadro: los 18 del actor (cara, manos, pulso, piel: SALIDAS de entrenar_movimiento.py) + 6 cualidades
del cuerpo (cuerpo_cualidades.CUERPO). Cada fuente trae una parte y le falta otra; la mascara dice que hay:
  - datasets/cara+cuerpo (4 actores, 10 animos): cara, manos, pulso; sin cuerpo (salvo la sesion de la llama, que
    trae el torso de Violeta: llama_spine/depth/yaw -> cuerpo_*)
  - esqueletos de Paqarina (~230 tomas): cuerpo, manos (brazos), cabeza; sin cara ni pulso ni animo
El JEPA aprende prediciendo lo que falta (el futuro, o la modalidad escondida).

    venv/bin/python jepa_datos.py                 -> modelos/jepa_datos.npz
    venv/bin/python jepa_datos.py --bailarines ~/Desktop/h26_limpio
"""
import os, sys, json, glob, argparse, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from entrenar_movimiento import SALIDAS, MOODS, salida_de, parpadeo_offline, actor_de
from cuerpo_cualidades import CUERPO, cualidades_toma, cargar_npz
FPS = 12.0; CANALES = SALIDAS + CUERPO; NC = len(CANALES)
def rejilla(t, series, presencia, fps=FPS, tol=0.15):
    """series: dict canal -> array por cuadro (NaN = ausente); t: tiempos. Devuelve X, M en la rejilla a fps."""
    t = np.asarray(t, float); tg = np.arange(t[0], t[-1], 1 / fps)
    X = np.zeros((len(tg), NC), np.float32); M = np.zeros((len(tg), NC), bool)
    idx = np.searchsorted(t, tg); idx = np.clip(idx, 1, len(t) - 1); cerca = np.where(np.abs(t[idx] - tg) < np.abs(t[idx - 1] - tg), idx, idx - 1)
    ok = np.abs(t[cerca] - tg) < tol
    for j, c in enumerate(CANALES):
        if c not in series: continue
        v = np.asarray(series[c], float); vi = np.interp(tg, t, np.where(np.isfinite(v), v, 0.0)); pres = np.isfinite(v)[cerca] & ok & presencia.get(c, np.ones(len(t), bool))[cerca]
        X[:, j] = np.where(pres, vi, 0.0); M[:, j] = pres
    return X, M
def toma_yakumama(f):
    cara = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cara", f))]; cuerpo = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cuerpo", f))]
    n = min(len(cara), len(cuerpo)); cara, cuerpo = cara[:n], cuerpo[:n]
    if n < 24: return None
    parp = parpadeo_offline(cara); t = np.array([r["t"] for r in cara]); t = t + np.arange(n) * 1e-6
    S = {c: np.full(n, np.nan) for c in CANALES}; P = {c: np.ones(n, bool) for c in CANALES}
    llama = "origen" in cara[0] and str(cara[0]["origen"]).startswith("llama")
    for i, (c, b) in enumerate(zip(cara, cuerpo)):
        vista = ("jaw_open" in c) and not (i > 0 and (c.get("todo") or {}).get("head_yaw") == (cara[i-1].get("todo") or {}).get("head_yaw"))   # cara vista y no congelada
        y = salida_de({**c, "blink": parp[i]}, b)
        for j, k in enumerate(SALIDAS):
            S[k][i] = y[j]
        bs = any(kk.startswith("face_") for kk in c)
        for k in ("head_yaw", "head_pitch", "jaw_open", "blink", "brow_up", "brow_down", "mouth_sad"): P[k][i] = vista
        for k in ("mouth_smile", "eye_yaw", "eye_pitch"): P[k][i] = vista and bs
        manos = ("l_palm_y" in b) or ("r_palm_y" in b)
        for k in ("l_palm_y", "r_palm_y", "l_palm_x", "r_palm_x"): P[k][i] = manos
        emo = bool(b.get("emotibit_hr")) and 35 < float(b.get("emotibit_hr") or 0) < 190
        P["hr"][i] = emo; P["eda"][i] = emo and bool(b.get("emotibit_eda"))
        if llama:   # el torso de la llama -> cualidades del cuerpo (aproximado)
            S["cuerpo_pitch"][i] = max(-1, min(1, float(b.get("llama_spine_y", 0)) / 0.5)); S["cuerpo_roll"][i] = max(-1, min(1, float(b.get("llama_spine_x", 0)) / 0.5))
            S["cuerpo_profundidad"][i] = max(-1, min(1, float(b.get("llama_body_depth", 0)) / 0.3))
            S["cuerpo_yaw"][i] = 0.0 if i == 0 else max(-1, min(1, (float(b.get("llama_body_yaw", 0)) - float(cuerpo[i-1].get("llama_body_yaw", 0))) * 12 / 3.0))
    if llama:
        mov = np.abs(np.diff(S["head_yaw"], prepend=S["head_yaw"][0])) + np.abs(np.diff(S["head_pitch"], prepend=S["head_pitch"][0])) + np.abs(np.diff(S["l_palm_y"], prepend=S["l_palm_y"][0]))
        mov = np.where(np.isfinite(mov), mov, 0); e = 0.0; en = np.zeros(n)
        for i, v in enumerate(mov): e = 0.9 * e + 0.1 * v; en[i] = e
        S["cuerpo_energia"] = np.clip(en / max(1e-6, np.percentile(en, 90)), 0, 1)
        hy = np.where(np.isfinite(S["head_yaw"]), S["head_yaw"], 0); F = np.abs(np.fft.rfft(hy - hy.mean())) ** 2; fr = np.fft.rfftfreq(n, 1 / 12.0)
        hf = float(F[fr > 3].sum() / max(1e-9, F[1:].sum())); S["cuerpo_suavidad"] = np.full(n, float(np.clip(1 - (hf - 0.08) / 0.3, 0, 1)))
    else:
        for k in CUERPO: P[k][:] = False
    X, M = rejilla(t, S, P)
    return X, M, MOODS.index(f.split("_")[0]), actor_de(f), ("llama" if llama else "yakumama"), f[:-6]
def toma_bailarin(ruta):
    B, J, fps = cargar_npz(ruta)
    if len(B) < 48: return None
    q = cualidades_toma(B, J, fps); n = len(B); t = np.arange(n) / fps
    S = {k: v for k, v in q.items()}; P = {c: np.ones(n, bool) for c in CANALES}
    S["mano_l"] = np.where(np.isfinite(q["l_palm_y"]), 1.0, 0.0); S["mano_r"] = np.where(np.isfinite(q["r_palm_y"]), 1.0, 0.0)
    for k in ("jaw_open", "blink", "brow_up", "brow_down", "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch", "hr", "eda"): P[k][:] = False
    X, M = rejilla(t, S, P)
    nombre = os.path.basename(ruta).replace(".npz", ""); actor = nombre.split("_")[0].split("-")[-1].lower() if "-" in nombre.split("_")[0] else nombre.split("_")[0].lower()
    return X, M, -1, actor, "bailarin", nombre
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--bailarines", default=os.path.expanduser("~/Desktop/h26_limpio")); a = ap.parse_args()
    Xs, Ms, SEQ, ANIMO, ACTOR, FUENTE, NOMBRE = [], [], [], [], [], [], []; pos = 0
    for f in sorted(os.listdir(os.path.join(AQUI, "datasets", "cara"))):
        if not f.endswith(".jsonl"): continue
        r = toma_yakumama(f)
        if r is None: continue
        X, M, an, ac, fu, no = r; Xs.append(X); Ms.append(M); SEQ.append((pos, pos + len(X))); pos += len(X); ANIMO.append(an); ACTOR.append(ac); FUENTE.append(fu); NOMBRE.append(no)
    for ruta in sorted(glob.glob(os.path.join(a.bailarines, "*.npz"))):
        try: r = toma_bailarin(ruta)
        except Exception as e: print("  (salto", os.path.basename(ruta), e, ")"); continue
        if r is None: continue
        X, M, an, ac, fu, no = r; Xs.append(X); Ms.append(M); SEQ.append((pos, pos + len(X))); pos += len(X); ANIMO.append(an); ACTOR.append(ac); FUENTE.append(fu); NOMBRE.append(no)
    X = np.concatenate(Xs); M = np.concatenate(Ms); SEQ = np.array(SEQ); ANIMO = np.array(ANIMO); ACTOR = np.array(ACTOR); FUENTE = np.array(FUENTE); NOMBRE = np.array(NOMBRE)
    media = np.array([X[M[:, j], j].mean() if M[:, j].any() else 0.0 for j in range(NC)], np.float32); desvio = np.array([X[M[:, j], j].std() + 1e-3 if M[:, j].any() else 1.0 for j in range(NC)], np.float32)
    np.savez(os.path.join(AQUI, "modelos", "jepa_datos.npz"), X=X, M=M, SEQ=SEQ, ANIMO=ANIMO, ACTOR=ACTOR, FUENTE=FUENTE, NOMBRE=NOMBRE, CANALES=np.array(CANALES), media=media, desvio=desvio, fps=FPS)
    for fu in ("yakumama", "llama", "bailarin"):
        m = FUENTE == fu; n = sum(SEQ[m][:, 1] - SEQ[m][:, 0]) if m.any() else 0; print(f"  {fu:9s} {m.sum():4d} tomas  {n / FPS / 60:6.1f} min")
    print(f"total {len(X)} cuadros a {FPS:.0f}/s = {len(X) / FPS / 60:.0f} min | canales {NC} | presencia por canal:", " ".join(f"{c}:{M[:, j].mean():.0%}" for j, c in enumerate(CANALES)))
    print("guardado modelos/jepa_datos.npz")
