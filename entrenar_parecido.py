#!/usr/bin/env python3
"""entrenar_parecido.py - a quien se parece la persona que esta frente a la camara.

Mismas ventanas de 2 s y mismos rasgos que entrenar_animo.py (cara, cabeza, manos), pero la etiqueta es el ACTOR.
Para una visita que nunca grabo, el modelo dice a cual de los actores grabados se parece mas en su forma de moverse,
y la ballena le contesta con el estilo de esa persona (yakumama_modelo.Modelo.paquete(..., actor=...)).

    venv/bin/python entrenar_parecido.py        -> modelos/parecido_rf.pkl
"""
import os, json, pickle, sys, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_predict, GroupKFold
sys.argv = [sys.argv[0]]; import entrenar_animo as E
from entrenar_movimiento import actor_de
AQUI = E.AQUI; W = E.W
if __name__ == "__main__":
    BS = None; X, y, grp = [], [], []
    for f in sorted(os.listdir(os.path.join(AQUI, "datasets", "cara"))):
        if not f.endswith(".jsonl"): continue
        cara = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cara", f))]; cuerpo = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cuerpo", f))]
        if BS is None: BS = sorted(k for k in next(r for r in cara if any(k.startswith("face_") for k in r)) if k.startswith("face_"))
        n = min(len(cara), len(cuerpo))
        for i in range(0, n - W, W // 2):
            v = E.rasgos(cara[i:i+W], cuerpo[i:i+W], BS)
            if v is not None: X.append(v); y.append(actor_de(f)); grp.append(f[:-6])
    X, y, grp = np.array(X), np.array(y), np.array(grp); actores = sorted(set(y))
    rf = lambda: RandomForestClassifier(n_estimators=300, random_state=0, class_weight="balanced")
    p = cross_val_predict(rf(), X, y, groups=grp, cv=GroupKFold(5))   # tomas enteras fuera: la persona en un animo que no vio
    print(f"ventanas {len(X)} | actores {actores} | acierto con tomas enteras fuera: {(p == y).mean():.0%}")
    for a in actores: print(f"  {a:8s} {(p[y == a] == a).mean():4.0%}  (se confunde con: {', '.join(f'{b} {(p[y == a] == b).mean():.0%}' for b in actores if b != a)})")
    modelo = rf().fit(X, y)
    pickle.dump({"modelo": modelo, "BS": BS, "actores": actores, "W": W}, open(os.path.join(AQUI, "modelos", "parecido_rf.pkl"), "wb"))
    print("guardado modelos/parecido_rf.pkl")
