#!/usr/bin/env python3
"""experiencia_datos.py - every decision she logged, turned into what Laya and CatDecide can learn from (14 Nov 2026, Violeta: "use all the
data to train"). No model here, only the table.
    python3 pruebas_laya/experiencia_datos.py            # -> datasets/experiencia/{entrena,mide}.jsonl, efectos.json, and a printed summary
SOURCES: every decisiones.jsonl found (this repo, fuentes/Barcelona_2026-10-30, Desktop/MAC?Barcelona), merged and de-duplicated by time.
One line of her log = one decision (every 4 s): what she sensed, what she chose and with what probability, what happened in the next 4 s.

WHAT EACH QUESTION LEARNS (her eight production questions, laya_sentidos.Q):
  engaged    what the visitor DID: were they still in front of her 30 s later (visits rebuilt from the log: a visit ends after 12 s
             without a person, or when her count of seconds restarts).
  maltrato   what her senses read: a hard touch (> 0.85) or a pull on the crown = "a lot"; a non-fish in the mouth = "a little".   (Claude's reading)
  regalo     what her senses read: a fish in the mouth or a gentle touch.                                                          (Claude's reading)
  retirarse, perform, visit, imitate, speak   what WORKED: inside the same kind of situation (her own key `clave` + the stretch of the
             visit), how much more often the visitor was still there 30 s later when she did it (moved away / the show / cactus or
             mountains / imitated / poem or song) than when she did not. The answer taught is 0.50 + that difference: 0.50 = no
             difference, 0.55 = five points more visitors stay. Small kinds of situation are pulled toward the overall difference.
             Decisions her refusals forced (`fijo`) are left out. These are observed differences, not an experiment.
THE SENTENCE is laya_sentidos.describir plus what it does not write and Barcelona had: a touch on her back (zone `lomo`), a visitor
standing still, a visitor dancing (her own rule: body energy > 0.35, counted across lines). Phone, ear, air: not in the log.
15 % of the visits (whole visits, every day) are kept out of training, to measure on."""
import os, sys, json, time, math, random, collections, hashlib
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI); sys.path.insert(0, RAIZ)
from laya_sentidos import describir
FUENTES = [os.path.join(RAIZ, "datasets", "decisiones.jsonl"), os.path.join(RAIZ, "fuentes", "Barcelona_2026-10-30", "datasets", "decisiones.jsonl"),
           os.path.expanduser("~/Desktop/MAC?Barcelona/Yakumama/datasets/decisiones.jsonl")]
SALIDA = os.path.join(RAIZ, "datasets", "experiencia"); SIGUE_S = 30; TAU = 0.05     # TAU: how far a kind of situation may sit from the overall difference before its own data says so
ACCIONES = {"retirarse": ("distancia", ("alejarse",)), "perform": ("viaje", ("show",)), "visit": ("viaje", ("cactus", "montanas")), "imitate": ("imitar", ("si",)), "speak": ("voz", ("poema", "canto"))}
def lugar(t):
    d = time.strftime("%m-%d", time.gmtime(t + 3600))                            # Barcelona's clock
    return "barcelona" if "10-28" <= d <= "10-30" else "montaje" if d == "10-27" else "casa"
def tramo(seg): return 0 if seg < 10 else 1 if seg < 30 else 2 if seg < 90 else 3

def leer():
    vistas = {}; cuenta = {}
    for f in FUENTES:
        if not os.path.exists(f): continue
        n = 0
        for linea in open(f, encoding="utf-8"):
            try: d = json.loads(linea)
            except Exception: continue
            k = round(float(d.get("t", 0)), 2)
            if k and k not in vistas and isinstance(d.get("situacion"), dict) and isinstance(d.get("decision"), dict): vistas[k] = d; n += 1
        cuenta[f.replace(os.path.expanduser("~"), "~")] = n
    return [vistas[k] for k in sorted(vistas)], cuenta

def visitas(L):
    """Mark every line with a person: its visit, how long the visitor still stays (resta), how long they have been dancing (baila_s)."""
    enc = []; cur = []
    for d in L:
        s = d["situacion"]
        if not s.get("persona"):
            if cur and d["t"] - cur[-1]["t"] > 12: enc.append(cur); cur = []
            continue
        if cur and (d["t"] - cur[-1]["t"] > 12 or float(s.get("segundos") or 0) < float(cur[-1]["situacion"].get("segundos") or 0) - 8): enc.append(cur); cur = []
        cur.append(d)
    if cur: enc.append(cur)
    for i, e in enumerate(enc):
        fin = e[-1]["t"]; b0 = None; ant = None
        for d in e:
            if float(d["situacion"].get("energia") or 0) > 0.35:
                if b0 is None or d["t"] - ant > 9: b0 = d["t"]
                ant = d["t"]; d["_baila"] = d["t"] - b0 + 4
            else: b0 = None; d["_baila"] = 0
            d["_resta"] = fin - d["t"]; d["_enc"] = i; d["_mide"] = int(hashlib.sha256(str(e[0]["t"]).encode()).hexdigest(), 16) % 100 < 15
    return enc

def escribir(d, R=None):
    """The situation as a sentence: production's describir + back touch, stillness, dancing. With R, the last two are sometimes left out,
    so a model trained here also reads today's production sentences."""
    s = d["situacion"]; seg = float(s.get("segundos") or 0); seg = seg if seg < 1e5 else 0
    c = {"persona": s.get("persona"), "conocida": s.get("conocida"), "animo": s.get("animo"), "segundos": seg, "tacto": s.get("tacto"), "tacto_zona": s.get("tacto_zona"),
         "ofrenda": s.get("boca") if s.get("boca") in ("pez", "no_pez") else None, "ve_telefono": s.get("telefono"), "personas_n": s.get("personas_n"), "foco_razon": s.get("foco_razon")}
    o = [describir(c)]
    if s.get("persona"):
        tac = float(s.get("tacto") or 0)
        if s.get("tacto_zona") == "lomo" and tac > 0.3: o.append("They are pressing hard on her sister's back." if tac > 0.85 else "They are stroking her sister's back gently.")
        if R is None or R.random() > 0.2:
            if d.get("_baila", 0) >= 4: o.append(f"They have been dancing in front of her for {int(d['_baila'])} seconds.")
            elif float(s.get("quieto") or 0) > 0.6: o.append("They are standing still.")
    return " ".join(o)

def hechos(s):
    """What her senses read: (mistreatment level, gift). 15 Nov 2026, Violeta's go: mistreatment is only what her sister physically feels (a hard
    touch, a pull on the jewel). Something that is not a fish at the mouth is NOT mistreatment: her eye read it in 27% of the Barcelona decisions
    with a visitor, and she already refuses to eat it by her own rule. (Until 14 Nov it counted as "a little": the first trained copies learned that.)"""
    tac = float(s.get("tacto") or 0); return (2 if (tac > 0.85 or s.get("joya_tiron")) else 0), bool(s.get("boca") == "pez" or 0.3 < tac <= 0.85)

def efectos(P):
    """For each decision: the difference in 'still there 30 s later' between doing it and not, inside each kind of situation, pulled toward the overall one."""
    out = {}
    for q, (campo, si) in ACCIONES.items():
        g = collections.defaultdict(lambda: [0, 0, 0, 0]); por = collections.defaultdict(lambda: [0.0, 0.0, 0])
        for d in P:
            if d.get("fijo") or campo not in d["decision"]: continue
            k = d["clave"] + "|" + str(tramo(float(d["situacion"].get("segundos") or 0))); a = d["decision"][campo] in si; y = d["_resta"] >= SIGUE_S
            g[k][0 if a else 2] += 1; g[k][1 if a else 3] += y
        num = den = 0.0
        for k, (na, ya, nb, yb) in g.items():
            if na >= 3 and nb >= 3: w = na * nb / (na + nb); num += w * (ya / na - yb / nb); den += w
        glob = num / den if den else 0.0; tabla = {}
        for k, (na, ya, nb, yb) in g.items():
            if na >= 1 and nb >= 1:
                p = (ya + yb + 1) / (na + nb + 2); var = p * (1 - p) * (1 / na + 1 / nb); dif = ya / na - yb / nb
                tabla[k] = round((dif / var + glob / TAU ** 2) / (1 / var + 1 / TAU ** 2), 4)
        out[q] = {"general": round(glob, 4), "veces": sum(v[0] for v in g.values()), "comparables": sum(v[0] for v in g.values() if v[0] >= 3 and v[2] >= 3), "por_situacion": tabla}
    return out
def efecto_de(E, q, d):
    k = d["clave"] + "|" + str(tramo(float(d["situacion"].get("segundos") or 0))); return E[q]["por_situacion"].get(k, E[q]["general"])

def main():
    L, cuenta = leer(); enc = visitas(L); P = [d for e in enc for d in e]; solos = [d for d in L if not d["situacion"].get("persona")]
    print("FUENTES (lineas nuevas que aporta cada una):"); [print(f"   {n:6d}  {f}") for f, n in cuenta.items()]
    print(f"{len(L)} decisiones, {len(P)} con una persona en {len(enc)} visitas reconstruidas, {len(solos)} sola")
    for lg in ("casa", "montaje", "barcelona"):
        E = [e for e in enc if lugar(e[0]["t"]) == lg]; n = sum(len(e) for e in E)
        if E: print(f"   {lg:9s} {len(E):4d} visitas, {n:5d} lineas; sigue {SIGUE_S} s despues en {100 * sum(d['_resta'] >= SIGUE_S for e in E for d in e) / n:.0f} %; para medir quedan {sum(e[0]['_mide'] for e in E)} visitas")
    entrena = [d for d in P if not d["_mide"]]; E = efectos(entrena)
    print("\nLO QUE FUNCIONO (visitas de entrenamiento): puntos de diferencia en 'sigue 30 s despues' cuando ella lo hace, dentro de la misma situacion")
    for q in ACCIONES:
        partes = [f"{lg} {100 * efectos([d for d in entrena if lugar(d['t']) == lg])[q]['general']:+5.1f}" for lg in ("casa", "barcelona")]
        tabla = sorted(E[q]["por_situacion"].values()); print(f"   {q:9s} todo {100 * E[q]['general']:+5.1f}   ({'  '.join(partes)})   elegido {E[q]['veces']} veces, {E[q]['comparables']} comparables; por situacion va de {100 * tabla[0]:+.1f} a {100 * tabla[-1]:+.1f}")
    os.makedirs(SALIDA, exist_ok=True); R = random.Random(11); n = {"entrena": 0, "mide": 0}
    with open(os.path.join(SALIDA, "entrena.jsonl"), "w") as fe, open(os.path.join(SALIDA, "mide.jsonl"), "w") as fm:
        for d in P:
            s = d["situacion"]; mal, reg = hechos(s); y = {"engaged": int(d["_resta"] >= SIGUE_S), "maltrato": mal, "regalo": int(reg)}; a = {}; pr = {}
            for q, (campo, si) in ACCIONES.items():
                if campo in d["decision"]:
                    y[q] = round(min(0.95, max(0.05, 0.5 + efecto_de(E, q, d))), 4); a[q] = int(d["decision"][campo] in si)
                    pr[q] = round(sum(float((d.get("prob") or {}).get(campo, {}).get(o, 0)) for o in si), 4)
            fila = {"t": d["t"], "lugar": lugar(d["t"]), "enc": d["_enc"], "texto": escribir(d, None if d["_mide"] else R), "y": y, "a": a, "prob": pr, "fijo": d.get("fijo") or "", "resta": round(d["_resta"], 1), "seg": round(float(s.get("segundos") or 0), 1)}
            (fm if d["_mide"] else fe).write(json.dumps(fila, ensure_ascii=False) + "\n"); n["mide" if d["_mide"] else "entrena"] += 1
        for d in R.sample(solos, min(len(solos), 1500)):                          # alone: nobody is engaged, mistreating or giving; the five decisions are not taught there
            mide = int(hashlib.sha256(str(d["t"]).encode()).hexdigest(), 16) % 100 < 15
            fila = {"t": d["t"], "lugar": lugar(d["t"]), "enc": -1, "texto": escribir(d), "y": {"engaged": 0, "maltrato": 0, "regalo": 0}, "a": {}, "prob": {}, "fijo": "", "resta": 0, "seg": 0}
            (fm if mide else fe).write(json.dumps(fila, ensure_ascii=False) + "\n"); n["mide" if mide else "entrena"] += 1
    json.dump({"hecho": time.strftime("%Y-%m-%d %H:%M"), "fuentes": cuenta, "sigue_s": SIGUE_S, "tau": TAU, "efectos": E}, open(os.path.join(SALIDA, "efectos.json"), "w"), indent=1)
    print(f"\n   -> {SALIDA}: entrena.jsonl {n['entrena']} filas, mide.jsonl {n['mide']} filas, efectos.json")
    for q in ("maltrato", "regalo"):
        c = collections.Counter(hechos(d["situacion"])[0 if q == "maltrato" else 1] for d in P); print(f"   {q}: {dict(c)}")
    R2 = random.Random(1); print("EJEMPLOS:"); [print("   ", escribir(d)) for d in R2.sample([d for d in P if lugar(d["t"]) == "barcelona"], 5)]
# ---- shared by the two trainers (laya_de_ella.py, catdecide_de_ella.py): the same rows, the same examples, the same table of results
DECISIONES = list(ACCIONES); HECHOS = ("engaged", "maltrato", "regalo")
def cargar(nombre): return [json.loads(l) for l in open(os.path.join(SALIDA, nombre + ".jsonl"), encoding="utf-8")]
def ejemplos(n_todo, n_eng, n_solo, semilla=5, tope=40):
    """Training examples (text, question, target): target = the level for maltrato, the probability of "yes" for the rest.
    n_todo rows with a visitor get all their questions (at most `tope` rows of one visit, so a 20-minute visit does not drown the others);
    n_eng more rows are asked only "engaged" (the question with the most to learn from what visitors did); n_solo rows alone."""
    R = random.Random(semilla); F = cargar("entrena"); pers = [f for f in F if f["enc"] >= 0]; solos = [f for f in F if f["enc"] < 0]; R.shuffle(pers); por = collections.Counter(); todo = []; resto = []
    for f in pers:
        if len(todo) < n_todo and por[f["enc"]] < tope: todo.append(f); por[f["enc"]] += 1
        else: resto.append(f)
    out = [(f["texto"], q, v) for f in todo for q, v in f["y"].items()] + [(f["texto"], "engaged", f["y"]["engaged"]) for f in resto[:n_eng]]
    out += [(f["texto"], q, v) for f in R.sample(solos, min(n_solo, len(solos))) for q, v in f["y"].items()]
    return out, {"filas con todas las preguntas": len(todo), "filas solo engaged": min(n_eng, len(resto)), "filas sola": min(n_solo, len(solos)), "ejemplos": len(out)}
def muestra_mide(n=None, semilla=9):
    F = cargar("mide"); R = random.Random(semilla); R.shuffle(F); return F[:n] if n else F
def auc(p, y):
    o = sorted(range(len(p)), key=lambda i: p[i]); r = [0.0] * len(p); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and p[o[j + 1]] == p[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    n1 = sum(y); n0 = len(y) - n1
    return (sum(r[i] for i in range(len(y)) if y[i]) - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else float("nan")
def informe(nombre, F, resp):
    """The table for one model on the held-out visits. resp[i] = its answers to row F[i]: engaged, regalo and the five decisions as the
    probability of yes, maltrato as the level."""
    out = {}; pers = [(f, r) for f, r in zip(F, resp) if f["enc"] >= 0]; print(f"\n{nombre}  ({len(F)} situaciones de visitas que no vio, {len(pers)} con una persona)")
    for lg in ("todo", "barcelona", "casa"):
        g = [(f, r) for f, r in pers if lg == "todo" or f["lugar"] == lg]
        if not g: continue
        y = [f["y"]["engaged"] for f, _ in g]; a = auc([r["engaged"] for _, r in g], y); b = auc([f["seg"] for f, _ in g], y); out["auc_" + lg] = a
        print(f"   engaged ({lg:9s}) separa a quien se queda 30 s de quien se va: {a:.3f}   (0.5 = no separa, 1 = perfecto; solo mirar cuanto lleva: {b:.3f}); dice 'si' en {100 * sum(r['engaged'] > 0.5 for _, r in g) / len(g):.0f} %, se quedan {100 * sum(y) / len(y):.0f} %")
    g = sorted(pers, key=lambda x: x[1]["engaged"]); cu = [g[i * len(g) // 4:(i + 1) * len(g) // 4] for i in range(4)]
    print("   engaged por cuartos (lo que dice -> lo que paso): " + "   ".join(f"{sum(r['engaged'] for _, r in c) / len(c):.2f} -> {sum(f['y']['engaged'] for f, _ in c) / len(c):.2f}" for c in cu if c))
    ok = sum(int(r["maltrato"]) == f["y"]["maltrato"] for f, r in zip(F, resp)); niv = {n: [sum(int(r["maltrato"]) == n for f, r in zip(F, resp) if f["y"]["maltrato"] == n), sum(f["y"]["maltrato"] == n for f in F)] for n in (0, 1, 2)}
    print(f"   maltrato  acierta {ok}/{len(F)} = {100 * ok / len(F):.1f} %   (nada {niv[0][0]}/{niv[0][1]}, un poco {niv[1][0]}/{niv[1][1]}, mucho {niv[2][0]}/{niv[2][1]})"); out["maltrato"] = ok / len(F)
    ok = sum((r["regalo"] > 0.5) == bool(f["y"]["regalo"]) for f, r in zip(F, resp)); si = [(r["regalo"] > 0.5) for f, r in zip(F, resp) if f["y"]["regalo"]]
    print(f"   regalo    acierta {ok}/{len(F)} = {100 * ok / len(F):.1f} %   (cuando lo hay {sum(si)}/{len(si)})"); out["regalo"] = ok / len(F)
    for q in DECISIONES:
        g = [(f, r) for f, r in pers if q in f["y"]]
        if not g: continue
        err = sum(abs(r[q] - f["y"][q]) for f, r in g) / len(g); h = [(f, r) for f, r in g if not f["fijo"] and 0 < f["prob"].get(q, 0) < 1]; num = den = 0.0
        for f, r in h:
            pi = min(0.95, max(0.05, f["prob"][q])); m = int(r[q] > 0.5)
            if f["a"][q] == m: w = 1 / (pi if m else 1 - pi); num += w * f["y"]["engaged"]; den += w
        print(f"   {q:9s} dice {sum(r[q] for _, r in g) / len(g):.2f} de media (lo ensenado {sum(f['y'][q] for f, _ in g) / len(g):.2f}, distancia {err:.3f}); inclina al si en {100 * sum(r[q] > 0.5 for _, r in g) / len(g):3.0f} %."
              f" Se quedaron {100 * sum(f['y']['engaged'] for f, _ in h) / max(1, len(h)):.1f} %; si ella hubiera seguido a este modelo, estimado {100 * num / den if den else float('nan'):.1f} %")
        out[q] = {"error": err, "seguir": num / den if den else None}
    return out

if __name__ == "__main__": main()
