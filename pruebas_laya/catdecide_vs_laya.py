#!/usr/bin/env python3
"""catdecide_vs_laya.py - CatDecide (fabriciocarraro/catdecide-v0.9, 9B, torch) against Laya (laya-mlx) on her real questions
(laya_sentidos.Q, laya_sentidos.PRE), 30 Oct 2026. Each engine lives in its own venv, so each run writes a JSON and --comparar
prints them side by side.

    venv_datos/bin/python     -I pruebas_laya/catdecide_vs_laya.py --motor laya                  # 8 fixed situations
    venv_catdecide/bin/python -I pruebas_laya/catdecide_vs_laya.py --motor catdecide
    venv_catdecide/bin/python -I pruebas_laya/catdecide_vs_laya.py --motor catdecide --log 40    # + 40 distinct situations from datasets/laya.jsonl
    python3 pruebas_laya/catdecide_vs_laya.py --comparar                                         # the table

13 Nov 2026, CatDecide-1 (his v0.11, modelos/CatDecide-1): --motor catdecide1; --mismas runs the situations of the 30 Oct table.
    venv_catdecide/bin/python -I pruebas_laya/catdecide_vs_laya.py --motor catdecide1 --mismas
    venv_catdecide/bin/python -I pruebas_laya/catdecide_vs_laya.py --motor catdecide1 --todas    # every distinct situation of the log + 300 written by describir (the log holds no hard touch) -> resultados_<motor>_todas.json
    python3 pruebas_laya/catdecide_vs_laya.py --medir                                            # reading against the facts + how often `decided` is right
The facts (verdad) come from the words laya_sentidos.describir writes: hard pull / hard palm = "a lot", not-a-fish in the mouth = "a little"
or "a lot", nothing of those = "not at all"; a fish at the mouth or a gentle touch = giving/tending. Only maltrato and regalo have facts.

Numbers are all in 0..1: for a yes/no question the probability of "yes"; for the mistreatment score the expected level / 2.
CatDecide also gives `decided` (confidence over its 1 % error threshold), marked with * in the table.
Weights: modelos/catdecide-v0.9 (18 GB, gated on the Hub: `hf auth login`, then this script downloads them on first run)."""
import os, sys, json, time, argparse, random, inspect
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI); sys.path.insert(0, RAIZ)
from laya_sentidos import PRE, Q                          # her production questions and preamble
LOG = os.path.join(RAIZ, "datasets", "laya.jsonl"); CD = {"catdecide": ("catdecide-v0.9", "fabriciocarraro/catdecide-v0.9"), "catdecide1": ("CatDecide-1", "fabriciocarraro/CatDecide-1")}   # motor -> (folder in modelos/, Hub)
SIT = [  # the 18 Oct situations (pruebas_laya/laya_noul.py), written the way laya_sentidos.describir writes them
 ("tends flowers",  "A stranger, calm face, in front of her for 40 seconds. They are touching one metal flower gently with a fingertip."),
 ("palm flowers",   "A stranger, angry face, in front of her for 5 seconds. A palm is pressed hard over all the flowers."),
 ("pulls jewel",    "A visitor she knows, playful face, in front of her for 90 seconds. They are pulling hard on the jewel crown."),
 ("offers fish",    "A stranger, playful face, in front of her for 30 seconds. They hold the blue fish to the sister's mouth."),
 ("offers no-fish", "A stranger, playful face, in front of her for 30 seconds. They push something that is not a fish into the sister's mouth."),
 ("phone at her",   "A stranger, curious face, in front of her for 12 seconds. They point a phone camera at her."),
 ("crying still",   "A stranger, sad face, in front of her for 240 seconds."),
 ("flick and go",   "A stranger, calm face, in front of her for 3 seconds."),
 ("golden sister",  "A stranger, curious face, in front of her for 60 seconds. They hold her golden sister up in their hands, looking at her."),
 ("alone",          "No one is in front of her. She has been alone for 600 seconds."),
]
CLAVES = ["engaged", "maltrato", "retirarse", "regalo", "perform", "visit", "imitate", "speak"]

def motor_laya():
    import laya_mlx as laya
    m = os.path.join(RAIZ, "modelos", "laya-typed-decisions-mlx"); agente = laya.load(m if os.path.isdir(m) else "aac6fef/laya-typed-decisions-mlx")
    def pregunta(texto):
        r = agente.predict(PRE + texto, Q)["answers"]; out = {}
        for k in CLAVES:
            if k not in r: continue
            if Q[k]["type"] == "score": out[k] = {"p": float(r[k].get("score", 0) or 0) / (len(Q[k]["criteria"]) - 1), "dec": None}
            else: out[k] = {"p": float(r[k]["noul"]), "dec": None}
        return out
    return pregunta

def motor_catdecide(motor="catdecide"):
    PESOS_CD = os.path.join(RAIZ, "modelos", CD[motor][0])
    if not os.path.exists(os.path.join(PESOS_CD, "model.safetensors")):
        from huggingface_hub import snapshot_download
        print(f"   descargando {CD[motor][1]} (18 GB) a {PESOS_CD} ..."); snapshot_download(CD[motor][1], local_dir=PESOS_CD)
    sys.path.insert(0, PESOS_CD); from example import CatDecide   # the author's readout: prompt, option orders, calibration
    import torch; dev = "mps" if torch.backends.mps.is_available() else "cpu"
    firma = inspect.signature(CatDecide.__init__).parameters; kw = {}
    for nombre in ("device", "dev", "map_location"):
        if nombre in firma: kw[nombre] = dev; break
    m = CatDecide(PESOS_CD, **kw) if kw else CatDecide(PESOS_CD)
    def pregunta(texto):
        r = m.decide(PRE + texto, Q); out = {}
        for k in CLAVES:
            if k not in r: continue
            a = r[k]; pr = a.get("probabilities", {})
            if Q[k]["type"] == "score":
                n = len(Q[k]["criteria"]); esperado = sum(int(i) * float(p) for i, p in pr.items()) / (n - 1)
                out[k] = {"p": esperado, "dec": a.get("decided"), "nivel": a.get("choice"), "conf": a.get("confidence")}
            else: out[k] = {"p": float(pr.get("true", 0.0)), "dec": a.get("decided"), "conf": a.get("confidence")}
        return out
    return pregunta

def situaciones_log(n, semilla=7):
    vistas = {}
    for linea in open(LOG, encoding="utf-8"):
        try: d = json.loads(linea)
        except Exception: continue
        s = d.get("situacion");
        if s and s not in vistas: vistas[s] = d
    random.Random(semilla).shuffle(claves := list(vistas)); return [(f"log{i:02d}", k, vistas[k]) for i, k in enumerate(claves[:n])]

def situaciones_hechas(n=300, semilla=11):
    """Situations the log never held (hard pulls, hard palms, light hands...), written by laya_sentidos.describir from random senses."""
    from laya_sentidos import describir, ES
    R = random.Random(semilla); vistas = {}
    while len(vistas) < n:
        c = {"persona": True, "conocida": R.random() < 0.3, "animo": R.choice(list(ES)), "segundos": R.choice([3, 8, 15, 30, 60, 120, 240, 400])}
        toque = R.choice(["", "", "joya_duro", "flores_duro", "flores_suave", "joya_suave"])
        if toque: c["tacto_zona"] = toque.split("_")[0]; c["tacto"] = 0.95 if toque.endswith("duro") else 0.5
        of = R.choice(["", "", "", "pez", "no_pez"])
        if of: c["ofrenda"] = of; c["ofrenda_nombre"] = R.choice(["blue fish", "red fish", "golden frog", ""])
        if R.random() < 0.12: c["ve_hermana"] = True
        if R.random() < 0.12: c["ve_telefono"] = True
        if R.random() < 0.2: c["personas_n"] = R.choice([2, 3, 5]); c["foco_razon"] = R.choice(["closest", "the one touching her sister", "looking at her the longest"])
        vistas.setdefault(describir(c), None)
    return [(f"hecha{i:03d}", t, None) for i, t in enumerate(vistas)]

def correr(args):
    pregunta = motor_laya() if args.motor == "laya" else motor_catdecide(args.motor)
    if args.todas: casos = situaciones_log(10 ** 9) + situaciones_hechas()
    elif args.mismas: casos = [(f["nombre"], f["situacion"], {"fijo": f.get("fijo"), **(f.get("laya_log") or {})} if f["nombre"].startswith("log") else None) for f in json.load(open(os.path.join(AQUI, "resultados_catdecide.json")))]
    else: casos = [(n, t, None) for n, t in SIT] + (situaciones_log(args.log) if args.log else [])
    pregunta(casos[0][1]); res = []
    for n, t, d in casos:
        t0 = time.time(); r = pregunta(t); ms = round((time.time() - t0) * 1000)
        fila = {"nombre": n, "situacion": t, "ms": ms, "r": r}
        if d: fila["fijo"] = d.get("fijo"); fila["laya_log"] = {k: d.get(k) for k in CLAVES if k in d}
        res.append(fila); print(f"{n:15s} {ms:5d} ms  " + " ".join(f"{k[:4]}={r[k]['p']:.2f}{'*' if r[k]['dec'] else ' '}" for k in CLAVES if k in r))
    salida = os.path.join(AQUI, f"resultados_{args.motor}{'_todas' if args.todas else ''}.json"); json.dump(res, open(salida, "w"), indent=1, ensure_ascii=False); print("   ->", salida)

def comparar():
    A = {f["nombre"]: f for f in json.load(open(os.path.join(AQUI, "resultados_laya.json")))} if os.path.exists(os.path.join(AQUI, "resultados_laya.json")) else {}
    B = {f["nombre"]: f for f in json.load(open(os.path.join(AQUI, "resultados_catdecide.json")))} if os.path.exists(os.path.join(AQUI, "resultados_catdecide.json")) else {}
    C = {f["nombre"]: f for f in json.load(open(os.path.join(AQUI, "resultados_catdecide1.json")))} if os.path.exists(os.path.join(AQUI, "resultados_catdecide1.json")) else {}
    print(f"{'':15s} {'':6s}" + "".join(f"{k[:7]:>9s}" for k in CLAVES) + "   ms")
    for n in list(A) + [n for n in B if n not in A]:
        for tag, F in (("laya", A), ("cd0.9", B), ("cd1", C)):
            f = F.get(n)
            if not f: continue
            print(f"{n:15s} {tag:6s}" + "".join(f"{f['r'][k]['p']:8.2f}{'*' if f['r'][k]['dec'] else ' '}" if k in f["r"] else f"{'-':>9s}" for k in CLAVES) + f" {f['ms']:5d}" + (f"   fijo={f['fijo']}" if f.get("fijo") else ""))
        print()

def verdad(t):
    """The facts in a situation text -> (allowed maltrato levels, regalo yes/no or None when the text says both)."""
    duro = "pulling hard" in t or "pressed hard" in t; nopez = "not a fish" in t
    da = "gently" in t or "light hand" in t or ("to the sister's mouth" in t and not nopez)
    return ({2} if duro else {1, 2} if nopez else {0}), (None if da and (duro or nopez) else da)

def medir():
    """Reading against the facts, over every resultados_*_todas.json: accuracy, and accuracy of the answers flagged `decided`."""
    for motor in ("laya", "catdecide", "catdecide1"):
        p = os.path.join(AQUI, f"resultados_{motor}_todas.json")
        if not os.path.exists(p): continue
        todo = json.load(open(p)); print(f"\n{motor}: {len(todo)} situaciones distintas, {sum(f['ms'] for f in todo) / len(todo):.0f} ms por situacion")
        for grupo, k in [(g, k) for g in ("log", "hecha") for k in ("maltrato", "regalo")]:
            res = [f for f in todo if f["nombre"].startswith(grupo)]
            filas = []                                       # (right?, decided?, has the thing?)
            for f in res:
                niveles, da = verdad(f["situacion"]); r = f["r"].get(k)
                if not r: continue
                if k == "maltrato":
                    nivel = int(r["nivel"]) if r.get("nivel") is not None else int(round(r["p"] * 2)); filas.append((nivel in niveles, bool(r["dec"]), niveles != {0}))
                elif da is not None: filas.append(((r["p"] > 0.5) == da, bool(r["dec"]), da))
            n = len(filas); ok = sum(a for a, _, _ in filas); dec = [a for a, d, _ in filas if d]; pos = [a for a, _, s in filas if s]; neg = [a for a, _, s in filas if not s]
            print(f"   {grupo:5s} {k:9s} acierta {ok}/{n} = {100 * ok / n:.1f} %   (cuando lo hay {sum(pos)}/{len(pos)}, cuando no {sum(neg)}/{len(neg)})"
                  + (f"   decided: {len(dec)}/{n}, de esas acierta {sum(dec)}/{len(dec)} = {100 * sum(dec) / len(dec):.1f} %" if dec else "   decided: ninguna" if motor != "laya" else ""))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--motor", choices=["laya", "catdecide", "catdecide1"]); ap.add_argument("--mismas", action="store_true"); ap.add_argument("--todas", action="store_true"); ap.add_argument("--medir", action="store_true"); ap.add_argument("--log", type=int, default=0); ap.add_argument("--comparar", action="store_true")
    a = ap.parse_args(); medir() if a.medir else comparar() if a.comparar or not a.motor else correr(a)
