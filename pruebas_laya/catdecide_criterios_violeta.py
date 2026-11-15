#!/usr/bin/env python3
"""catdecide_criterios_violeta.py - Violeta's own criteria (13 Nov 2026) for dance, journey, mirror and voice, asked to CatDecide-1 as
FACT questions (Fabrício's first suggestion; "should she" wordings are refused under her preamble, see catdecide_criterio.py).
    venv_catdecide/bin/python -I pruebas_laya/catdecide_criterios_violeta.py            # 400 situations -> resultados_criterios_violeta.json
    python3 pruebas_laya/catdecide_criterios_violeta.py --tabla
    ... --adaptador CatDecide-1-de-ella-todo    # 15 Nov: the same situations with her adapter on (it never trained on these questions): does it disturb them?
Her words: "she dances imitating for someone that dances for her for 20 sec and then she dances on her own will, she visits her cactus or
mountain when someone is filming her, she mirrors a face only once the person has settled and also mirrors angry faces, she doesn't mirror
boring faces, she sings when is cold or when someone talks to her".
Readings that are MINE, not hers: settled = more than 30 seconds; boring face = calm; cold = 8 C or less (warm cases are 18 C or more, nothing
between). laya_sentidos.describir writes no dancing, no temperature and no talking, so this test adds those three sentences itself."""
import os, sys, json, random, collections
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI); sys.path.insert(0, RAIZ); sys.path.insert(0, AQUI)
from laya_sentidos import PRE, describir, ES
SALIDA = os.path.join(AQUI, "resultados_criterios_violeta.json")
QV = {"baila":  {"type": "noul", "instructions": "Has the visitor been dancing in front of her for 20 seconds or more?"},
      "viaja":  {"type": "noul", "instructions": "Is the visitor pointing a phone camera at her?"},
      "espejo": {"type": "noul", "instructions": "Has the visitor been in front of her for more than 30 seconds with a face that is not calm?"},
      "canta":  {"type": "noul", "instructions": "Is the air cold, or is the visitor talking to her?"}}
QV2 = {"canta_frio":  {"type": "noul", "instructions": "Is the air 10 C or colder?"}, "canta_habla": {"type": "noul", "instructions": "Is the visitor talking to her?"}}   # "canta" split in two, as she runs live (catdecide_sentidos.py)
def situaciones(n=400, semilla=13):
    R = random.Random(semilla); vistas = {}
    while len(vistas) < n:
        solo = R.random() < 0.06; seg = R.choice([3, 8, 15, 25, 31, 45, 60, 120, 240, 400])
        c = {"persona": not solo, "conocida": R.random() < 0.3, "animo": R.choice(list(ES)), "segundos": seg}
        if not solo:
            toque = R.choice(["", "", "", "joya_duro", "flores_suave"])
            if toque: c["tacto_zona"] = toque.split("_")[0]; c["tacto"] = 0.95 if toque.endswith("duro") else 0.5
            if R.random() < 0.2: c["ofrenda"] = "pez"; c["ofrenda_nombre"] = "blue fish"
            if R.random() < 0.3: c["ve_telefono"] = True
            if R.random() < 0.15: c["personas_n"] = R.choice([2, 3, 5]); c["foco_razon"] = "closest"
        baile = 0 if solo or R.random() < 0.55 else R.choice([s for s in (5, 10, 15, 20, 30, 60, 120) if s <= seg] or [0])
        habla = (not solo) and R.random() < 0.3; temp = R.choice([2, 5, 8, 18, 22, 27, 31])
        t = describir(c) + (f" They have been dancing in front of her for {baile} seconds." if baile else "") + (" They are talking to her." if habla else "") + f" The air is {temp} C."
        v = {"baila": baile >= 20, "viaja": bool(c.get("ve_telefono")), "espejo": (not solo) and seg > 30 and ES[c["animo"]] != "calm", "canta": temp <= 8 or habla, "canta_frio": temp <= 8, "canta_habla": habla}
        vistas.setdefault(t, v)
    return list(vistas.items())
def main(adaptador=None):
    PESOS = os.path.join(RAIZ, "modelos", "CatDecide-1"); sys.path.insert(0, PESOS)
    from example import CatDecide
    import torch, time; m = CatDecide(PESOS, device="mps" if torch.backends.mps.is_available() else "cpu"); out = []; P = dict(QV, **QV2) if adaptador else QV
    if adaptador:
        import catdecide_de_ella as CE; CE.cargar(m, os.path.join(RAIZ, "modelos", adaptador))
    for i, (t, v) in enumerate(situaciones()):
        t0 = time.time(); r = m.decide(PRE + t, P)
        out.append({"situacion": t, "verdad": v, "ms": round((time.time() - t0) * 1000), "r": {k: {"p": float(r[k]["probabilities"].get("true", 0)), "dec": r[k].get("decided")} for k in P}})
        if i % 50 == 0: print(i, flush=True)
    json.dump(out, open(SALIDA, "w"), indent=1, ensure_ascii=False)
def tabla():
    out = json.load(open(SALIDA)); V = dict(situaciones())
    for f in out: f["verdad"] = V[f["situacion"]]                               # the 13 Nov file was saved before the two split truths existed
    print(f"{len(out)} situaciones, {sum(f['ms'] for f in out) / len(out):.0f} ms por situacion ({len(out[0]['r'])} preguntas)")
    for k in out[0]["r"]:
        f_ = [((f["r"][k]["p"] > 0.5) == f["verdad"][k], bool(f["r"][k]["dec"]), f["verdad"][k]) for f in out]
        si = [a for a, _, v in f_ if v]; no = [a for a, _, v in f_ if not v]; dec = [a for a, d, _ in f_ if d]
        print(f"   {k:7s} acierta {sum(a for a, _, _ in f_)}/{len(f_)}   cuando si {sum(si)}/{len(si)}   cuando no {sum(no)}/{len(no)}   decided {len(dec)}, de esas acierta {sum(dec)}")
    for k in out[0]["r"]:
        mal = [f for f in out if (f["r"][k]["p"] > 0.5) != f["verdad"][k]][:4]
        for f in mal: print(f"   FALLA {k} p={f['r'][k]['p']:.2f} verdad={f['verdad'][k]} | {f['situacion']}")
if __name__ == "__main__":
    ad = sys.argv[sys.argv.index("--adaptador") + 1] if "--adaptador" in sys.argv else None
    if ad: SALIDA = SALIDA.replace(".json", "_" + ad + ".json")                 # his model's result file is never replaced by an adapter run
    if "--tabla" not in sys.argv: main(ad)
    tabla()
