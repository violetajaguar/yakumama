#!/usr/bin/env python3
"""decisiones.py - HOW SHE INTERACTS: a decision layer shaped like a typed-decision model (Jev-style: fixed sets of answers with
probabilities, never a sentence), local and tiny. From the situation she reads it returns one choice per question, and it LOGS every
decision with what happened next (how long the person stayed, whether they danced, whether they touched the sister), so the nightly
learning can fit those logs and her choices shift with what worked. Version 1 = rules + log; the fit (--aprender) reweights the
rules' options per situation from the outcomes. Nothing leaves the machine; the log holds numbers, never faces.

Questions and their answer sets:
    distancia   acercarse | quedarse | alejarse
    con_cuerpo  bailar_de_vuelta | invitar | observar
    voz         poema | canto | silencio
    memoria     recordar | olvidar
    color       propio | ropa

    from decisiones import Decisora; D = Decisora(); dec = D.decidir(situacion); ... D.cerrar(resultado)
    venv/bin/python decisiones.py --aprender        (nightly: refit from the log)
"""
import os, sys, json, time, math, random
AQUI = os.path.dirname(os.path.abspath(__file__)); LOG = os.path.join(AQUI, "datasets", "decisiones.jsonl"); PESOS = os.path.join(AQUI, "modelos", "decisiones_pesos.json")
OPCIONES = {"distancia": ["acercarse", "quedarse", "alejarse"], "con_cuerpo": ["bailar_de_vuelta", "invitar", "observar"], "voz": ["poema", "canto", "silencio"], "memoria": ["recordar", "olvidar"], "color": ["propio", "ropa"]}
def _softmax(d, temp=1.0):
    m = max(d.values()); e = {k: math.exp((v - m) / temp) for k, v in d.items()}; z = sum(e.values()); return {k: round(v / z, 3) for k, v in e.items()}
def situacion_clave(s):
    """the situation as a small discrete key, so the learned weights generalise: who, how they move, how long, touch."""
    return "|".join([("conocida" if s.get("conocida") else ("nueva" if s.get("persona") else "nadie")), s.get("animo") or "-", "mueve" if (s.get("energia") or 0) > 0.35 else "quieta",
                     "corta" if (s.get("segundos") or 0) < 20 else ("media" if (s.get("segundos") or 0) < 90 else "larga"), ("tacto_" + str(s.get("tacto_zona") or "")) if (s.get("tacto") or 0) > 0.3 else "sin_tacto"])
class Decisora:
    def __init__(self):
        try: self.pesos = json.load(open(PESOS))
        except Exception: self.pesos = {}
        self.abierta = None; os.makedirs(os.path.dirname(LOG), exist_ok=True)
    def puntajes(self, s):
        """the rules: a score per option, from the situation. Positive = she leans that way."""
        p = {q: {o: 0.0 for o in ops} for q, ops in OPCIONES.items()}; e = float(s.get("energia") or 0); seg = float(s.get("segundos") or 0); tacto = float(s.get("tacto") or 0); zona = s.get("tacto_zona") or ""
        if not s.get("persona"):
            p["distancia"]["quedarse"] += 1.0; p["con_cuerpo"]["observar"] += 1.0; p["voz"]["poema"] += 0.6 if seg > 60 else 0.0; p["voz"]["silencio"] += 0.5; p["memoria"]["recordar"] += 0.2; p["color"]["propio"] += 1.0
        else:
            p["distancia"]["acercarse"] += (1.2 if s.get("conocida") else 0.6) + (0.5 if e > 0.35 else 0.0); p["distancia"]["quedarse"] += 0.6; p["distancia"]["alejarse"] += (1.0 if (s.get("animo") == "angry" and e > 0.6) else 0.0) + (0.6 if tacto > 0.8 else 0.0)
            p["con_cuerpo"]["bailar_de_vuelta"] += 1.5 if e > 0.35 else 0.0; p["con_cuerpo"]["invitar"] += 0.8 if (e < 0.2 and seg > 10) else 0.2; p["con_cuerpo"]["observar"] += 0.7 if seg < 5 else 0.3
            p["voz"]["canto"] += 1.0 if s.get("animo") == "singing" else 0.1; p["voz"]["poema"] += 0.8 if (seg > 45 and e < 0.3) else 0.0; p["voz"]["silencio"] += 0.6
            p["memoria"]["recordar"] += 1.0 if seg > 30 else 0.3; p["memoria"]["olvidar"] += 1.0 if s.get("pide_olvido") else 0.0
            p["color"]["ropa"] += 1.0 if s.get("ropa_gusta") else 0.0; p["color"]["propio"] += 0.8
        if tacto > 0.3:   # the sister is touched: head -> she comes closer and looks; back -> she settles; tail -> she plays; too hard -> she startles away
            if zona == "cabeza": p["distancia"]["acercarse"] += 0.8; p["con_cuerpo"]["invitar"] += 0.5
            elif zona == "lomo": p["distancia"]["quedarse"] += 0.8; p["voz"]["canto"] += 0.3
            elif zona == "cola": p["con_cuerpo"]["bailar_de_vuelta"] += 0.8; p["distancia"]["acercarse"] += 0.3
            if tacto > 0.85: p["distancia"]["alejarse"] += 1.2
        clave = situacion_clave(s)   # learned adjustments from the log, per situation
        for q in p:
            for o, w in self.pesos.get(clave, {}).get(q, {}).items(): p[q][o] += float(w)
        return p
    def decidir(self, s, temp=0.8):
        p = self.puntajes(s); dec = {}; prob = {}
        for q in p:
            pr = _softmax(p[q], temp); prob[q] = pr; dec[q] = max(pr, key=pr.get)
        self.abierta = {"t": time.time(), "clave": situacion_clave(s), "situacion": {k: s.get(k) for k in ("persona", "conocida", "animo", "energia", "segundos", "tacto", "tacto_zona")}, "decision": dec, "prob": prob}
        return dec, prob
    def cerrar(self, resultado):
        """log the open decision with its outcome: {"quedo_s": seconds the person stayed after, "bailo": 0/1, "toco": 0/1, "se_fue": 0/1}."""
        if not self.abierta: return
        r = dict(self.abierta); r["resultado"] = resultado; r["recompensa"] = round(min(1.0, float(resultado.get("quedo_s", 0)) / 60.0) + 0.5 * float(resultado.get("bailo", 0)) + 0.3 * float(resultado.get("toco", 0)) - 0.5 * float(resultado.get("se_fue", 0)), 3)
        with open(LOG, "a") as f: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        self.abierta = None
def aprender():
    """nightly: for each situation key and question, the options that preceded better outcomes get weight (a small contextual bandit)."""
    try: filas = [json.loads(l) for l in open(LOG)]
    except Exception: print("no log yet"); return
    acum = {}
    for r in filas:
        k = r["clave"]
        for q, o in r["decision"].items(): acum.setdefault(k, {}).setdefault(q, {}).setdefault(o, []).append(r.get("recompensa", 0.0))
    pesos = {}
    for k, qs in acum.items():
        for q, os_ in qs.items():
            medias = {o: sum(v) / len(v) for o, v in os_.items() if len(v) >= 3}
            if len(medias) >= 2:
                base = sum(medias.values()) / len(medias); pesos.setdefault(k, {})[q] = {o: round(1.5 * (m - base), 3) for o, m in medias.items()}
    os.makedirs(os.path.dirname(PESOS), exist_ok=True); json.dump(pesos, open(PESOS, "w"), indent=1); print(f"decisiones: {len(filas)} logged, weights for {len(pesos)} situations -> {PESOS}")
if __name__ == "__main__":
    if "--aprender" in sys.argv: aprender()
    else:
        D = Decisora()
        for s in ({"persona": 0, "segundos": 90}, {"persona": 1, "conocida": 1, "animo": "playful", "energia": 0.6, "segundos": 30}, {"persona": 1, "animo": "sad", "energia": 0.1, "segundos": 60}, {"persona": 1, "animo": "angry", "energia": 0.7, "tacto": 0.9, "tacto_zona": "cola", "segundos": 5}):
            d, p = D.decidir(s); print(situacion_clave(s), "->", d)
