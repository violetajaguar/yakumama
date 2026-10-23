#!/usr/bin/env python3
"""entrenar_ofrendas.py - entrena el ojo de las manos con las fotos de ofrendas_fotos/ (una carpeta por clase).

    venv/bin/python entrenar_ofrendas.py [--fotos ofrendas_fotos] [--rasgos dino|mobilenet] [--solo-evaluar]

1. De cada foto busca la mano (una vez; queda en modelos/ofrendas_manos.npz) y saca 12 vistas: tres recortes ajustados
   (1.2, 1.35, 1.6 x la mano), cada uno normal y espejado, cada uno tal cual y "lejos" (bajado a 110 px y vuelto a subir,
   como se ve una mano a un metro). Los embeddings quedan en modelos/ofrendas_emb_<rasgos>.npz (se reusan; borralos si cambian las fotos).
2. Prueba honesta: entrena con todas las rafagas menos la ultima de cada clase y mide en la ultima. En la sesion del 20 oct
   la primera rafaga fue de cerca y la segunda a un metro, asi que esta prueba es "aprende de cerca, reconoce de lejos".
   Imprime el acierto por clase y las confusiones.
3. Entrena con todo y guarda modelos/ofrendas_clf.pkl (regresion logistica + nombres de clase + con que rasgos y pad se usa).
"""
import argparse, glob, os, pickle, re, sys, time
import numpy as np, cv2

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from ojo_ofrendas import Recorte, Rasgos, CLASIFICADOR, PAD
ap = argparse.ArgumentParser()
ap.add_argument("--fotos", default=os.path.join(AQUI, "ofrendas_fotos"))
ap.add_argument("--rasgos", default="dino+color", help="bloques separados por +: dino, mobilenet, color (cada bloque se extrae una vez y queda en modelos/ofrendas_emb_<bloque>.npz)")
ap.add_argument("--peso-color", type=float, default=1.0)
ap.add_argument("--solo-evaluar", action="store_true")
ap.add_argument("--rafaga-s", type=float, default=5.0, help="segundos sin foto que separan dos rafagas")
ap.add_argument("--C", type=float, default=2.0)
ap.add_argument("--prueba", default="mitad", choices=("mitad", "rafaga"), help="mitad = el ultimo 40%% de cada rafaga queda fuera (cerca y lejos); rafaga = la ultima rafaga entera de cada clase queda fuera")
a = ap.parse_args()
PADS = (1.2, PAD, 1.6); LEJOS = (0, 110); ESPEJOS = (False, True)
VISTAS = [(p, l, e) for p in PADS for l in LEJOS for e in ESPEJOS]          # 12, en este orden
VIVO = [i for i, (p, l, e) in enumerate(VISTAS) if p == PAD and l == 0]    # las dos que usa Ojo.ver en vivo
MANOS = os.path.join(AQUI, "modelos", "ofrendas_manos.npz"); CACHE = lambda b: os.path.join(AQUI, "modelos", f"ofrendas_emb_{b}.npz")


def momento(nombre):
    m = re.search(r"_(\d{8})_(\d{6})_(\d{3})", nombre)
    return time.mktime(time.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")) + int(m.group(3)) / 1000.0 if m else 0.0


def listar(base):
    """[(ruta, clase, rafaga)] con rafaga = indice de la rafaga dentro de la clase (por huecos de tiempo)."""
    out = []
    for clase in sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and not d.startswith((".", "_"))):
        fs = sorted(glob.glob(os.path.join(base, clase, "*.jpg")), key=momento); r = 0; prev = None
        for f in fs:
            t = momento(f)
            if prev is not None and t - prev > a.rafaga_s: r += 1
            out.append((f, clase, r)); prev = t
    return out


def cargar_si_sirve(ruta, rutas):
    if not os.path.exists(ruta): return None
    d = np.load(ruta); return d if len(d["rutas"]) == len(rutas) and (d["rutas"] == rutas).all() else None


def manos(rutas):
    d = cargar_si_sirve(MANOS, rutas)
    if d is not None: print(f"manos de {MANOS}"); return d["M"]
    rec = Recorte(estatico=True); M = np.full((len(rutas), 3), -1.0, np.float32); t0 = time.time()
    for i, f in enumerate(rutas):
        m = rec.mano(cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB))
        if m: M[i] = m
        if i % 300 == 0: print(f"   manos {i}/{len(rutas)}  {time.time() - t0:.0f}s")
    np.savez_compressed(MANOS, M=M, rutas=rutas); print(f"manos guardadas en {MANOS}: {int((M[:, 2] > 0).sum())}/{len(rutas)} con mano")
    return M


def extraer_bloque(bloque, rutas, M):
    d = cargar_si_sirve(CACHE(bloque), rutas)
    if d is not None: print(f"{bloque}: de {CACHE(bloque)}"); return d["X"]
    rs = Rasgos(bloque); X = np.zeros((len(rutas), len(VISTAS), rs.dims), np.float32); t0 = time.time()
    for i, f in enumerate(rutas):
        rgb = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB); cx, cy, tam = M[i]
        if tam > 0: vistas = [Recorte.cortar(rgb, Recorte.cuadrado(rgb, cx, cy, tam, pad=p), espejo=e, lejos=l) for p, l, e in VISTAS]
        else:
            c = Recorte.centro(rgb); vistas = [Recorte.cortar(rgb, c, espejo=e, lejos=l) for p, l, e in VISTAS]   # sin mano: el centro, con las mismas variantes
        X[i] = rs(vistas)
        if i % 300 == 0: print(f"   {bloque} {i}/{len(rutas)}  {time.time() - t0:.0f}s  {os.path.basename(os.path.dirname(f))} mano={int(tam > 0)}")
    np.savez_compressed(CACHE(bloque), X=X, rutas=rutas); print(f"{bloque}: guardado en {CACHE(bloque)}  {X.shape}  {time.time() - t0:.0f}s")
    return X


def extraer(rutas, M):
    """concatena los bloques de --rasgos como lo hace ojo_ofrendas.Rasgos (cada bloque ya viene normalizado; color x peso)."""
    partes = []
    for b in a.rasgos.split("+"):
        X = extraer_bloque(b, rutas, M); partes.append(X * (a.peso_color if b == "color" else 1.0))
    return np.concatenate(partes, axis=2)


fotos = listar(a.fotos); clases = sorted({c for _, c, _ in fotos}); ci = {c: i for i, c in enumerate(clases)}
y = np.array([ci[c] for _, c, _ in fotos]); raf = np.array([r for _, _, r in fotos]); rutas = np.array([f for f, _, _ in fotos])
print(f"{len(fotos)} fotos, {len(clases)} clases; rafagas por clase: " + " ".join(f"{c}:{raf[y == ci[c]].max() + 1}" for c in clases))
M = manos(rutas); X = extraer(rutas, M)

from sklearn.linear_model import LogisticRegression


def entrenar(idx):
    Xt = X[idx].reshape(-1, X.shape[-1]); yt = np.repeat(y[idx], X.shape[1])
    return LogisticRegression(C=a.C, max_iter=3000, class_weight="balanced").fit(Xt, yt)


def predecir(clf, idx):
    """como en vivo: pad PAD, normal + espejo, promedio de probabilidades."""
    return np.stack([clf.predict_proba(X[idx, k]) for k in VIVO]).mean(0)


# 2. prueba honesta. "rafaga": la ultima rafaga de cada clase queda fuera (el 20 oct la primera fue de cerca y la segunda a un metro:
# aprender de cerca y reconocer de lejos, que no se puede). "mitad": el ultimo 40% de cada rafaga queda fuera, cerca y lejos por igual
# (lo que vera en la instalacion si se entrena con todo). Se informa aparte el acierto con la mano lejos (< 180 px) y cerca.
test = np.zeros(len(y), bool)
for c in clases:
    k = np.where(y == ci[c])[0]
    if a.prueba == "rafaga" and raf[k].max() > 0: test[k[raf[k] == raf[k].max()]] = True
    else:
        for r in range(raf[k].max() + 1):
            kr = k[raf[k] == r]; test[kr[int(len(kr) * 0.6):]] = True
clf = entrenar(np.where(~test)[0]); it = np.where(test)[0]; pr = predecir(clf, it); yp = pr.argmax(1); yt = y[test]; conm = M[it, 2] > 0; lejos = conm & (M[it, 2] < 180); cerca = conm & ~lejos
ok = yp == yt; seguro = pr.max(1) >= 0.5
print(f"\nPRUEBA {a.prueba} ({a.rasgos}; entrena {int((~test).sum())}, prueba {int(test.sum())}): acierto {100 * ok.mean():.1f}%"
      f"   mano lejos: {100 * ok[lejos].mean():.1f}% de {int(lejos.sum())}   mano cerca: {100 * ok[cerca].mean():.1f}% de {int(cerca.sum())}   sin mano: {100 * ok[~conm].mean():.1f}% de {int((~conm).sum())}"
      f"\n   con p>=0.5 responde el {100 * seguro.mean():.1f}% y acierta el {100 * ok[seguro].mean():.1f}% de esas (lejos: responde {100 * seguro[lejos].mean():.1f}%, acierta {100 * ok[lejos & seguro].mean():.1f}%)")
print("por clase:")
for c in clases:
    m = yt == ci[c]; conf = {}
    for j in yp[m & (yp != yt)]: conf[clases[j]] = conf.get(clases[j], 0) + 1
    print(f"   {c:32s} {100 * (yp[m] == ci[c]).mean():5.1f}%  de {int(m.sum()):3d}" + (f"   confunde con: " + ", ".join(f"{k} x{v}" for k, v in sorted(conf.items(), key=lambda kv: -kv[1])[:3]) if conf else ""))
if a.solo_evaluar: sys.exit(0)

# 3. todo
clf = entrenar(np.arange(len(y)))
with open(CLASIFICADOR, "wb") as fh: pickle.dump({"clf": clf, "clases": clases, "espejo": True, "pad": PAD, "rasgos": a.rasgos, "peso_color": a.peso_color, "vistas": VISTAS, "fotos": len(y), "fecha": time.strftime("%Y-%m-%d %H:%M")}, fh)
print(f"\nguardado {CLASIFICADOR}  ({a.rasgos}, {len(clases)} clases, {len(y)} fotos)")
