#!/usr/bin/env python3
"""catdecide_criterio.py - Fabrício's first suggestion (13 Nov 2026): put the criteria inside the question. One trial question, his
own example, on CatDecide-1 over the situations already in resultados_catdecide1_todas.json:
    venv_catdecide/bin/python -I pruebas_laya/catdecide_criterio.py
The rule is his example, not hers: it only tests whether the model applies an explicit rule. Seconds and mistreatment are read from
the situation text (catdecide_vs_laya.verdad); "interested" has no fact, so the table splits by face instead."""
import os, sys, json, re, collections
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI); sys.path.insert(0, RAIZ); sys.path.insert(0, AQUI)
from laya_sentidos import PRE
from catdecide_vs_laya import verdad, CD
PESOS = os.path.join(RAIZ, "modelos", CD["catdecide1"][0]); sys.path.insert(0, PESOS)
QC = {"perform_regla": {"type": "noul", "instructions": "Should Yakumama perform a dance show now? She only performs when an interested visitor has been in front of her for more than two minutes and nobody is mistreating her sister."}}
def main():
    from example import CatDecide
    import torch; m = CatDecide(PESOS, device="mps" if torch.backends.mps.is_available() else "cpu")
    res = json.load(open(os.path.join(AQUI, "resultados_catdecide1_todas.json"))); out = []
    for i, f in enumerate(res):
        a = m.decide(PRE + f["situacion"], QC)["perform_regla"]; out.append({"nombre": f["nombre"], "situacion": f["situacion"], "p": float(a["probabilities"].get("true", 0)), "dec": a.get("decided")})
        if i % 100 == 0: print(i, len(res), flush=True)
    json.dump(out, open(os.path.join(AQUI, "resultados_criterio.json"), "w"), indent=1, ensure_ascii=False)
def tabla():
    out = json.load(open(os.path.join(AQUI, "resultados_criterio.json"))); c = collections.defaultdict(lambda: [0, 0, 0, 0])
    for f in out:
        t = f["situacion"]; s = re.search(r"for (\d+) seconds", t); seg = int(s.group(1)); solo = t.startswith("No one"); mal = verdad(t)[0] != {0}
        grupo = "sola" if solo else ("mas de 2 min" if seg > 120 else "2 min o menos") + (", maltrato" if mal else ", sin maltrato")
        g = c[grupo]; g[0] += 1; g[1] += f["p"] > 0.5; g[2] += bool(f["dec"]); g[3] += f["p"]
    for k in sorted(c): n, si, dec, sp = c[k]; print(f"   {k:32s} {n:4d} situaciones   dice si {si:4d}   decided {dec:4d}   p media {sp / n:.2f}")
if __name__ == "__main__":
    if "--tabla" not in sys.argv: main()
    tabla()
