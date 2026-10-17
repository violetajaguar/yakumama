#!/usr/bin/env python3
"""aprender.py - la ballena aprende de las visitas.

Toma los encuentros guardados por el grabador (datasets/visitas/*.jsonl: caras, manos, pulso de la gente que se puso
frente a ella, con el animo que ella les vio y la confianza con que lo vio) y reentrena el reconocedor de animo con las
tomas de los actores MAS las ventanas de visitas en las que estuvo segura (confianza >= 0.7). Las visitas nunca pesan
mas que la mitad del conjunto. El parecido (quien es quien) no se toca: sigue siendo entre los actores grabados.

    venv/bin/python aprender.py            reentrena y muestra que cambio
    venv/bin/python aprender.py --seco     solo cuenta lo que hay, no reentrena
Corre cuando quieras (por ejemplo al cerrar la instalacion cada noche). memoria.py muestra a quien conoce.
"""
import os, sys, json, glob, pickle, argparse, numpy as np
sys.argv_backup = list(sys.argv); sys.argv = [sys.argv[0]]
import entrenar_animo as E
sys.argv = sys.argv_backup
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_predict, GroupKFold
AQUI = E.AQUI; W = E.W; MOODS = E.MOODS; CONF = 0.7
def ventanas_actores(BS=None):
    X, y, grp = [], [], []
    for f in sorted(os.listdir(os.path.join(AQUI, "datasets", "cara"))):
        if not f.endswith(".jsonl"): continue
        cara = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cara", f))]; cuerpo = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cuerpo", f))]
        if BS is None: BS = sorted(k for k in next(r for r in cara if any(k.startswith("face_") for k in r)) if k.startswith("face_"))
        n = min(len(cara), len(cuerpo))
        for i in range(0, n - W, W // 2):
            v = E.rasgos(cara[i:i+W], cuerpo[i:i+W], BS)
            if v is not None: X.append(v); y.append(MOODS.index(f.split("_")[0])); grp.append(f[:-6])
    return X, y, grp, BS
def ventanas_visitas(BS):
    """ventanas de 2 s de cada encuentro, etiquetadas con el animo que la ballena vio si estuvo segura."""
    X, y, grp, total = [], [], [], 0
    for f in sorted(glob.glob(os.path.join(AQUI, "datasets", "visitas", "*.jsonl"))):
        lineas = [json.loads(l) for l in open(f)]; regs = [r for r in lineas if "t" in r]; total += len(regs)
        for i in range(0, len(regs) - W, W // 2):
            w = regs[i:i+W]; animos = [r.get("actor_animo") for r in w if r.get("actor_animo")]
            if len(animos) < W * 0.8: continue
            top = max(set(animos), key=animos.count); conf = np.mean([float(r.get("actor_" + top, 0)) for r in w])
            if animos.count(top) < W * 0.8 or conf < CONF: continue
            v = E.rasgos(w, w, BS)
            if v is not None: X.append(v); y.append(MOODS.index(top)); grp.append(os.path.basename(f)[:-6])
    return X, y, grp, total
# ============================================================
# APRENDER EL CUERPO DE LAS VISITAS (17 oct): cada persona que se para frente a ella es un performer que no hubo que
# citar. El reconocedor le pone el animo a la cara; la pose le da el cuerpo. Cuando el animo se sostuvo >= 3 s con
# confianza >= CONF y hay cuerpo, ese tramo entra como pista con animo (datasets/visitas_cuerpo/<encuentro>_<k>.npz)
# y jepa_datos lo toma como fuente "visita". Tope: las visitas nunca pesan mas que los performers en cada animo.
# ============================================================
def cuerpo_visitas(seco=False):
    sal = os.path.join(AQUI, "datasets", "visitas_cuerpo"); os.makedirs(sal, exist_ok=True); hechas = set(os.listdir(sal)); n_nuevas = 0; seg = {}
    for f in sorted(glob.glob(os.path.join(AQUI, "datasets", "visitas", "*.jsonl"))):
        base = os.path.basename(f)[:-6]
        if any(h.startswith(base + "_") for h in hechas): continue
        L = [json.loads(l) for l in open(f)][1:]
        if len(L) < 30: continue
        tramos = []; ini = None; animo = None
        for i, r in enumerate(L):
            p = {m: float(r.get("actor_" + m, 0) or 0) for m in MOODS}; m_ = max(p, key=p.get); ok = p[m_] >= CONF and "cuerpo_pitch" in r
            if ok and m_ == animo: continue
            if animo is not None and ini is not None and L[i - 1]["t"] - L[ini]["t"] >= 3.0: tramos.append((ini, i, animo))
            ini, animo = (i, m_) if ok else (None, None)
        if animo is not None and ini is not None and L[-1]["t"] - L[ini]["t"] >= 3.0: tramos.append((ini, len(L), animo))
        for k, (s_, e_, m_) in enumerate(tramos):
            X = np.array([[float(r.get(c, 0)) for c in ("cuerpo_pitch", "cuerpo_roll", "cuerpo_yaw", "cuerpo_profundidad", "cuerpo_energia", "cuerpo_suavidad")] for r in L[s_:e_]], np.float32)
            t = np.array([r["t"] for r in L[s_:e_]]); fps = (len(t) - 1) / max(0.1, t[-1] - t[0]); seg[m_] = seg.get(m_, 0) + (t[-1] - t[0])
            if not seco: np.savez_compressed(os.path.join(sal, f"{base}_{k:02d}.npz"), X=X, M=np.ones_like(X, bool), fps=fps, animo=m_, canales=np.array(["cuerpo_pitch", "cuerpo_roll", "cuerpo_yaw", "cuerpo_profundidad", "cuerpo_energia", "cuerpo_suavidad"]))
            n_nuevas += 1
    print(f"  cuerpo de visitas: {n_nuevas} tramos nuevos con animo (>= 3 s, confianza >= {CONF}): " + (", ".join(f"{m} {s:.0f} s" for m, s in sorted(seg.items())) or "ninguno"))
    return n_nuevas
def noche():
    """lo que corre cada noche al cerrar: aprende la cara y el cuerpo de las visitas del dia y reentrena; deja registro."""
    import subprocess, datetime
    linea = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]
    n = cuerpo_visitas(); linea.append(f"tramos de cuerpo nuevos {n}")
    if n:
        subprocess.run([sys.executable, os.path.join(AQUI, "jepa_datos.py")], cwd=AQUI, capture_output=True)
        r = subprocess.run([sys.executable, os.path.join(AQUI, "hjepa_entrenar.py"), "--epochs1", "6", "--epochs2", "20"], cwd=AQUI, capture_output=True, text=True)
        for l in r.stdout.splitlines():
            if l.startswith("SONDA") or "meta diving" in l: linea.append(l.strip()[:120])
    with open(os.path.join(AQUI, "datasets", "aprendizaje.log"), "a") as fh: fh.write(" | ".join(linea) + "\n")
    print("  noche:", " | ".join(linea))
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seco", action="store_true"); ap.add_argument("--cuerpo", action="store_true", help="solo sacar los tramos de cuerpo con animo de las visitas"); ap.add_argument("--noche", action="store_true", help="lo de cada noche: cuerpo de visitas + reentrenar + registro"); a = ap.parse_args()
    if a.noche: noche(); sys.exit(0)
    if a.cuerpo: cuerpo_visitas(seco=a.seco); sys.exit(0)
    Xa, ya, ga, BS = ventanas_actores(); Xv, yv, gv, total = ventanas_visitas(BS)
    print(f"actores: {len(Xa)} ventanas de {len(set(ga))} tomas | visitas: {total} paquetes en {len(glob.glob(os.path.join(AQUI, 'datasets', 'visitas', '*.jsonl')))} encuentros -> {len(Xv)} ventanas seguras (confianza >= {CONF})")
    if Xv:
        c = np.bincount(yv, minlength=10); print("  animos que trajeron las visitas:", {MOODS[i]: int(n) for i, n in enumerate(c) if n})
    if a.seco or not Xv: print("(nada que aprender)" if not Xv else "seco: no se reentrena"); sys.exit(0)
    k = min(len(Xv), len(Xa))   # las visitas nunca pesan mas que los actores
    idx = np.random.default_rng(0).choice(len(Xv), k, replace=False)
    X = np.array(Xa + [Xv[i] for i in idx]); y = np.array(ya + [yv[i] for i in idx]); grp = np.array(ga + [gv[i] for i in idx])
    rf = lambda: RandomForestClassifier(n_estimators=300, random_state=0, class_weight="balanced")
    p = cross_val_predict(rf(), X, y, groups=grp, cv=GroupKFold(5)); es_v = np.arange(len(y)) >= len(ya)
    print(f"acierto con tomas/encuentros enteros fuera: actores {(p[~es_v] == y[~es_v]).mean():.0%} | visitas {(p[es_v] == y[es_v]).mean():.0%}")
    modelo = rf().fit(X, y); viejo = pickle.load(open(os.path.join(AQUI, "modelos", "animo_rf.pkl"), "rb"))
    pickle.dump({**viejo, "modelo": modelo, "BS": BS, "moods": MOODS, "W": W, "visitas": int(k)}, open(os.path.join(AQUI, "modelos", "animo_rf.pkl"), "wb"))
    print(f"guardado modelos/animo_rf.pkl con {k} ventanas de visitas (el grabador lo carga al arrancar)")


