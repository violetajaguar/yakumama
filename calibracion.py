#!/usr/bin/env python3
"""calibracion.py - are her decisions CALIBRATED? (21 Oct 2026, Violeta: RLCD, "a real representation of embodied AI")

Reads datasets/decisiones.jsonl (every decision she took: situation key, her probabilities, Laya's opinion, the outcome and its reward)
and prints, per question, a reliability table: when she chose an option with probability p, what reward followed on average. A calibrated
decider shows reward rising with p. It also prints how often she explored (chose a non-top option) and what each option earned overall.
Since 21 Oct she SAMPLES from her probabilities (decisiones.decidir), so these numbers mean something: before, she always took the top one.

    venv/bin/python calibracion.py [--dias 7] [--pregunta viaje]

THE MEASURE (21 Oct, Violeta: "a day of her decisions against a random policy, with the engagement numbers side by side"): run a day with
EVALUAR=1 ./correr_todo.sh (YAKUMAMA_EVALUAR=1 on her brain). Each encounter is then decided by a coin: "ella" (her decider) or "azar"
(a uniform pick per question, refusals still fixed). Both meet the same people the same afternoon. This report prints them side by
side: decisions, encounters, mean reward, how long people stayed, how often they left within 20 s, and per question. Rows older than
that day carry no politica and count as hers.
"""
import json, os, sys, time, collections
AQUI = os.path.dirname(os.path.abspath(__file__)); LOG = os.path.join(AQUI, "datasets", "decisiones.jsonl")
dias = float(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 1e9
solo = sys.argv[sys.argv.index("--pregunta") + 1] if "--pregunta" in sys.argv else None
desde = time.time() - dias * 86400.0
filas = []
for l in open(LOG, encoding="utf-8"):
    try: r = json.loads(l)
    except Exception: continue
    if float(r.get("t", 0)) < desde or r.get("fijo"): continue   # fixed refusals are not hers to calibrate
    filas.append(r)
print(f"{len(filas)} decisions of hers (no refusals){'' if dias > 1e8 else f', last {dias:g} days'}; reward = engagement (decisiones.Decisora.recompensa)")
# --- HER POLICY AGAINST CHANCE, side by side
pol = {"ella": [r for r in filas if r.get("politica", "ella") == "ella"], "azar": [r for r in filas if r.get("politica") == "azar"]}
if pol["azar"]:
    def col(rs):
        con = [r for r in rs if (r.get("situacion") or {}).get("persona")]; rec = [float(r.get("recompensa") or 0) for r in con]
        q = [float((r.get("resultado") or {}).get("quedo_s") or 0) for r in con]; fue = [r for r in con if (r.get("resultado") or {}).get("se_fue")]
        pronto = [r for r in fue if float((r.get("resultado") or {}).get("quedo_s") or 0) < 20]
        return {"decisions with someone": len(con), "encounters ended": len(fue), "mean reward": f"{sum(rec) / len(rec):+.3f}" if rec else "-",
                "mean seconds per decision": f"{sum(q) / len(q):.1f}" if q else "-", "left within 20 s": f"{100.0 * len(pronto) / len(fue):.0f}%" if fue else "-"}
    ce, ca = col(pol["ella"]), col(pol["azar"])
    print("\nHER DECISIONS AGAINST A RANDOM POLICY (same day, same people, a coin per encounter)")
    print(f"  {'':28s} {'ella':>12s} {'azar':>12s}")
    for k in ce: print(f"  {k:28s} {str(ce[k]):>12s} {str(ca[k]):>12s}")
    for q in sorted({q for r in filas for q in (r.get("decision") or {})}):
        if solo and q != solo: continue
        def por(rs):
            v = [float(r.get("recompensa") or 0) for r in rs if q in (r.get("decision") or {}) and (r.get("situacion") or {}).get("persona")]
            return f"{sum(v) / len(v):+.3f} ({len(v)})" if v else "-"
        print(f"  {q:28s} {por(pol['ella']):>12s} {por(pol['azar']):>12s}")
    print("  (if 'ella' is not clearly above 'azar' on mean reward, her decider is not yet earning its keep: more days, or the priors are wrong)")
else: print("  (no random-policy rows yet: run a day with EVALUAR=1 ./correr_todo.sh to measure her against chance)")
preguntas = sorted({q for r in filas for q in (r.get("decision") or {})})
for q in preguntas:
    if solo and q != solo: continue
    buckets = collections.defaultdict(list); por_opcion = collections.defaultdict(list); explor = 0; n = 0
    for r in filas:
        dec, prob = r.get("decision") or {}, r.get("prob") or {}
        if q not in dec or q not in prob: continue
        o = dec[q]; p = float(prob[q].get(o, 0.0)); rec = float(r.get("recompensa", 0.0) or 0.0); n += 1
        buckets[min(4, int(p * 5))].append(rec); por_opcion[o].append(rec)
        if o != max(prob[q], key=prob[q].get): explor += 1
    if not n: continue
    print(f"\n{q.upper()}  ({n} decisions, explored {100.0 * explor / n:.0f}%)")   # explored counts random-policy rows too
    print("  confidence p     n     mean reward")
    for b in range(5):
        v = buckets.get(b, [])
        if v: print(f"  {b / 5:.1f}-{(b + 1) / 5:.1f}      {len(v):6d}   {sum(v) / len(v):+.3f}")
    print("  option           n     mean reward")
    for o, v in sorted(por_opcion.items(), key=lambda kv: -len(kv[1])): print(f"  {o:14s} {len(v):6d}   {sum(v) / len(v):+.3f}")
laya = [r for r in filas if r.get("laya")]
if laya:
    eng = [(float(r["laya"].get("engaged", 0.5)), float(r.get("recompensa", 0.0) or 0.0)) for r in laya]
    lo = [v for e, v in eng if e < 0.4]; hi = [v for e, v in eng if e > 0.6]
    print(f"\nLAYA 'engaged' as a predictor: when Laya said < 0.4 the reward averaged {sum(lo) / len(lo) if lo else float('nan'):+.3f} ({len(lo)}), when > 0.6 it averaged {sum(hi) / len(hi) if hi else float('nan'):+.3f} ({len(hi)})")
