#!/usr/bin/env python3
"""entrenar_animo.py - entrena el reconocedor de animo con datasets/cara + cuerpo y lo guarda en modelos/animo_rf.pkl.

Rasgos por ventana de 2 s (60 cuadros): media, variacion y velocidad de los 51 blendshapes, variacion y velocidad de
la cabeza (yaw/pitch crudos), altura y presencia de las manos. Random forest. Reporta el acierto dejando fuera
trozos de 20 s de cada toma (dentro de sesion) y el acierto dejando fuera tomas enteras (entre sesiones).
"""
import json, os, pickle, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, cross_val_predict
AQUI = os.path.dirname(os.path.abspath(__file__))
MOODS = ["calm","singing","playful","curious","feeding","sad","angry","alert","diving","surfacing"]
W = 60
def rasgos(cw, bw, BS):
    """cw/bw: listas de 60 dicts (cara, cuerpo). Devuelve el vector de rasgos o None si no hay cara."""
    if sum(1 for r in cw if "face_jawOpen" in r) < W * 0.8: return None
    raw = [float((r.get("todo") or r).get("head_yaw", 0)) for r in cw]
    if sum(1 for a, b in zip(raw, raw[1:]) if a == b) > W * 0.3: return None
    M = np.array([[float(r.get(k, 0)) for k in BS] for r in cw]); H = np.array([[float((r.get("todo") or r).get(k, 0)) for k in ("head_yaw", "head_pitch")] for r in cw])
    hands = np.array([[float(r.get("l_palm_y", 0.5)), float(r.get("r_palm_y", 0.5)), ("l_palm_y" in r) + ("r_palm_y" in r)] for r in bw])
    return np.concatenate([M.mean(0), M.std(0), np.abs(np.diff(M, axis=0)).mean(0), H.std(0), np.abs(np.diff(H, axis=0)).mean(0), hands.mean(0), hands.std(0)])
if __name__ == "__main__":
    BS = None; X, y, grp = [], [], []
    for f in sorted(os.listdir(os.path.join(AQUI, "datasets", "cara"))):
        if not f.endswith(".jsonl"): continue
        cara = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cara", f))]; cuerpo = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cuerpo", f))]
        if BS is None: BS = sorted(k for k in next(r for r in cara if any(k.startswith("face_") for k in r)) if k.startswith("face_"))
        n = min(len(cara), len(cuerpo))
        for i in range(0, n - W, W // 2):
            v = rasgos(cara[i:i+W], cuerpo[i:i+W], BS)
            if v is not None: X.append(v); y.append(MOODS.index(f.rsplit("_", 1)[0])); grp.append(f[:-6])
    X, y, grp = np.array(X), np.array(y), np.array(grp)
    rf = lambda: RandomForestClassifier(n_estimators=300, random_state=0, class_weight="balanced")
    bloques = np.array([f"{g}_{i//10}" for i, g in enumerate(grp)])
    p = cross_val_predict(rf(), X, y, groups=bloques, cv=GroupKFold(5)); print(f"ventanas {len(X)} | acierto dentro de sesion (trozos de 20 s fuera): {(p==y).mean():.0%}")
    p2 = cross_val_predict(rf(), X, y, groups=grp, cv=LeaveOneGroupOut()); print(f"acierto con tomas enteras fuera (entre sesiones): {(p2==y).mean():.0%}")
    modelo = rf().fit(X, y)
    pickle.dump({"modelo": modelo, "BS": BS, "moods": MOODS, "W": W}, open(os.path.join(AQUI, "modelos", "animo_rf.pkl"), "wb"))
    print("guardado modelos/animo_rf.pkl")
