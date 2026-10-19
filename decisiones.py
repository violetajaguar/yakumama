#!/usr/bin/env python3
"""decisiones.py v2 (18 Oct 2026) - HOW SHE INTERACTS: a typed-decision layer (Jev-shaped: fixed sets of answers with probabilities,
never a sentence), local and tiny. Rules are the floor, learned weights sit on top, and three REFUSALS sit above both and can never be
learned away. Her objective is ENGAGEMENT, not entertainment: the reward counts time weighted late, distance that shrinks, her touch
words used, stillness of a known face, time on the joystick and a return on another day. Crowd, noise and speed count for nothing.
Nothing leaves the machine; the log holds numbers, never faces.

Questions and their answer sets:
    distancia   acercarse | quedarse | alejarse
    con_cuerpo  bailar_de_vuelta | invitar | observar | dibujar      (dibujar: she draws nazca lines on the salar, dibujo_salar.py)
    voz         poema | canto | silencio
    memoria     recordar | olvidar
    color       propio | ropa
    boca        comer | rehusar | esperar          (the sister's mouth)

The situation (every field optional):
    persona 0/1 · conocida 0/1 · id_persona str · animo str · energia 0..1 · segundos · quieto 0..1 · vuelve 0/1 (seen another day)
    distancia_m · distancia_tend (-1 coming .. +1 leaving) · ropa_gusta · pide_olvido
    flores 0..1 (strongest stem) · flores_n (stems touched) · joya 0..1 · joya_tiron 0/1          (touch ESP, analog capacitive)
    boca "pez"|"no_pez"|"nada" · boca_p 0..1                                                     (her eye looking at the table)
    palanca_s (seconds on the joystick this visit) · camara_cerca 0..1 (TouchDesigner camera near her) · camara_mira 0/1
    tacto / tacto_zona                                                                          (legacy: cabeza|lomo|cola|aleta|flores|joya)
Fixed refusals (never reweighted): no_pez in the mouth -> rehusar + turn away; a pull on the jewel; a palm over the flowers;
a phone or camera raised at her (telefono) -> she turns away, still and dim, until it comes down: she gives her face to eyes, not to lenses
(Violeta, 18 oct). The golden sister does not refuse the lens; only the digital whale does.
Her own memory of people: whoever pulled or trampled is kept distant until the same person tends the flowers gently (forgiveness);
a visitor who asks to be forgotten is forgotten absolutely.

    from decisiones import Decisora; D = Decisora(); dec, prob = D.decidir(situacion); ... D.cerrar(resultado)
    venv/bin/python decisiones.py            (self-test on her situations)
    venv/bin/python decisiones.py --aprender (nightly: refit the weights from the log; refusals and forgets are skipped)
"""
import os, sys, json, time, math
AQUI = os.path.dirname(os.path.abspath(__file__)); LOG = os.path.join(AQUI, "datasets", "decisiones.jsonl")
PESOS = os.path.join(AQUI, "modelos", "decisiones_pesos.json"); PERSONAS = os.path.join(AQUI, "modelos", "decisiones_personas.json")
OPCIONES = {"distancia": ["acercarse", "quedarse", "alejarse"], "con_cuerpo": ["bailar_de_vuelta", "invitar", "observar", "dibujar"], "voz": ["poema", "canto", "silencio"],
            "memoria": ["recordar", "olvidar"], "color": ["propio", "ropa"], "boca": ["comer", "rehusar", "esperar"]}
PALMA_N = 3; PALMA_FUERZA = 0.7; TIRON_FUERZA = 0.85   # a palm = three or more stems above 0.7; a pull = jewel above 0.85 or joya_tiron
LAYA = "/tmp/ballena_laya.json"; _laya = {"t": 0.0, "v": None}
def laya_opinion():
    """Laya's second opinion (laya_sentidos.py, the open Jev): engaged, maltrato, retirarse, regalo in 0..1, or None if it is not running or stale."""
    if time.time() - _laya["t"] < 1.0: return _laya["v"]
    _laya["t"] = time.time()
    try: v = json.load(open(LAYA)); _laya["v"] = v if time.time() - v.get("t", 0) < 12 else None
    except Exception: _laya["v"] = None
    return _laya["v"]
def _softmax(d, temp=1.0):
    m = max(d.values()); e = {k: math.exp((v - m) / temp) for k, v in d.items()}; z = sum(e.values()); return {k: round(v / z, 3) for k, v in e.items()}
def _f(s, k, por=0.0):
    try: return float(s.get(k) or por)
    except Exception: return por
def lectura_tacto(s):
    """what the sister felt, in her words: (palabra, fuerza). flores | joya | legacy zones | ''"""
    fl, fn, jo = _f(s, "flores"), int(_f(s, "flores_n")), _f(s, "joya"); z = str(s.get("tacto_zona") or ""); t = _f(s, "tacto")
    if jo > 0.3 or z == "joya": return "joya", max(jo, t if z == "joya" else 0.0)
    if fl > 0.3 or z == "flores": return "flores", max(fl, t if z == "flores" else 0.0)
    if t > 0.3 and z: return z, t
    return "", 0.0
def es_palma(s):
    pal, f = lectura_tacto(s); return pal == "flores" and (int(_f(s, "flores_n")) >= PALMA_N and f > PALMA_FUERZA or f > TIRON_FUERZA)
def es_tiron(s):
    pal, f = lectura_tacto(s); return pal == "joya" and (bool(s.get("joya_tiron")) or f > TIRON_FUERZA)
def situacion_clave(s):
    """the situation as a small discrete key, so the learned weights generalise: who, mood, moving, how long, which touch word, mouth."""
    pal, f = lectura_tacto(s); seg = _f(s, "segundos")
    return "|".join([("conocida" if s.get("conocida") else ("nueva" if s.get("persona") else "nadie")), s.get("animo") or "-", "mueve" if _f(s, "energia") > 0.35 else "quieta",
                     "corta" if seg < 20 else ("media" if seg < 90 else "larga"), ("tacto_" + pal) if pal else "sin_tacto", "boca_" + str(s.get("boca") or "nada")])
FOCO_ORDEN = ("alimenta", "joya", "conocida", "flores", "palanca", "cerca_quieta", "cerca")
def elegir_foco(personas, foco_actual=None):
    """WHOM she attends in a crowd (MozFest premiere, 18 Oct): one person at a time, chosen, not the biggest face by accident.
    personas: [{"id", "conocida", "distancia_m", "quieto", "alimenta" (hand with a fish at the mouth), "joya" (touching the jewel crown),
    "flores", "palanca"}]. Violeta's order: whoever feeds her or touches her jewel crown wins, above a known face; then the one tending
    the flowers, the one on the joystick, the closest still face, the closest. She stays with her chosen one until they leave or
    someone feeds / touches the crown (a known face may also steal her). Returns (persona, razon) or (None, "")."""
    if not personas: return None, ""
    def razon(p):
        if p.get("alimenta"): return "alimenta"
        if p.get("joya"): return "joya"
        if p.get("conocida"): return "conocida"
        if p.get("flores"): return "flores"
        if p.get("palanca"): return "palanca"
        return "cerca_quieta" if (p.get("quieto") or 0) > 0.6 else "cerca"
    def rango(p): return (FOCO_ORDEN.index(razon(p)), float(p.get("distancia_m") or 9.0))
    mejor = min(personas, key=rango); r = razon(mejor)
    if foco_actual is not None:   # loyalty: only feeding, the crown or a known face take her away from the one she is with
        actual = next((p for p in personas if p.get("id") == foco_actual), None)
        if actual is not None and r not in ("alimenta", "joya", "conocida"): return actual, razon(actual)
    return mejor, r
class Decisora:
    def __init__(self):
        try: self.pesos = json.load(open(PESOS))
        except Exception: self.pesos = {}
        try: self.personas = json.load(open(PERSONAS))
        except Exception: self.personas = {}
        self.abierta = None; self.ultimo_pez = 0.0; self.rehusados = 0; os.makedirs(os.path.dirname(LOG), exist_ok=True)
    # --- her own memory of people (ids come from the face memory; never images)
    def persona(self, s):
        i = s.get("id_persona"); return self.personas.get(str(i)) if i else None
    def _guardar_personas(self):
        try: os.makedirs(os.path.dirname(PERSONAS), exist_ok=True); json.dump(self.personas, open(PERSONAS, "w"), indent=1)
        except Exception: pass
    def marcar(self, s, que):
        i = s.get("id_persona")
        if not i: return
        p = self.personas.setdefault(str(i), {"visitas": 0, "peces": 0, "rudo": 0, "ultima": 0})
        if que == "rudo": p["rudo"] = time.time()
        elif que == "perdon": p["rudo"] = 0
        elif que == "pez": p["peces"] += 1
        elif que == "olvidar": self.personas.pop(str(i), None)
        p["ultima"] = time.time(); self._guardar_personas()
    def apetito(self):
        """how sure she must be that it is a fish: picky right after eating, hungry after ten minutes without."""
        sin = (time.time() - self.ultimo_pez) / 60.0 if self.ultimo_pez else 10.0
        return 0.95 if sin < 1.0 else max(0.5, 0.8 - 0.03 * min(10.0, sin))
    def puntajes(self, s):
        """the rules: a score per option, from the situation. Positive = she leans that way."""
        p = {q: {o: 0.0 for o in ops} for q, ops in OPCIONES.items()}; e = _f(s, "energia"); seg = _f(s, "segundos"); quieto = _f(s, "quieto"); pal, f = lectura_tacto(s)
        tend = _f(s, "distancia_tend"); rudo = bool((self.persona(s) or {}).get("rudo"))
        if int(_f(s, "personas_n")) >= 4: p["voz"]["silencio"] += 0.4; p["con_cuerpo"]["invitar"] += 0.3   # a crowd: the poem waits for the headphones, the body invites the chosen one
        if not s.get("persona"):
            p["distancia"]["quedarse"] += 1.0; p["con_cuerpo"]["observar"] += 1.0; p["voz"]["poema"] += 0.6 if seg > 60 else 0.0; p["voz"]["silencio"] += 0.5; p["memoria"]["recordar"] += 0.2; p["color"]["propio"] += 1.0; p["boca"]["esperar"] += 1.0
            if seg > 60 and (s.get("animo") in ("calm", "curious", "singing", None, "-")): p["con_cuerpo"]["dibujar"] += 1.8   # alone and quiet for a minute: she feels artistic
        else:
            p["distancia"]["acercarse"] += (1.2 if s.get("conocida") else 0.6) + (0.5 if e > 0.35 else 0.0) + (0.4 if tend < -0.3 else 0.0) + (0.4 if seg > 90 else 0.0)
            p["distancia"]["quedarse"] += 0.6 + (0.3 if quieto > 0.6 else 0.0); p["distancia"]["alejarse"] += (1.0 if (s.get("animo") == "angry" and e > 0.6) else 0.0) + (1.0 if rudo else 0.0)
            p["con_cuerpo"]["bailar_de_vuelta"] += 1.5 if e > 0.35 else 0.0; p["con_cuerpo"]["invitar"] += 0.8 if (e < 0.2 and seg > 10) else 0.2; p["con_cuerpo"]["observar"] += 0.7 if seg < 5 else 0.3
            if s.get("conocida") and quieto > 0.6 and seg > 120: p["con_cuerpo"]["dibujar"] += 1.6   # a known face standing still for two minutes: she draws them their face (a gift)
            if int(_f(s, "personas_n")) >= 4: p["con_cuerpo"]["dibujar"] -= 1.0
            p["voz"]["canto"] += 1.0 if s.get("animo") == "singing" else 0.1; p["voz"]["poema"] += (0.8 if (seg > 45 and e < 0.3) else 0.0) + (0.5 if quieto > 0.6 and seg > 120 else 0.0); p["voz"]["silencio"] += 0.6 + (0.4 if seg < 15 else 0.0)
            p["memoria"]["recordar"] += (1.0 if seg > 30 else 0.3) + (0.5 if s.get("vuelve") else 0.0)
            p["color"]["ropa"] += (1.0 if s.get("ropa_gusta") else 0.0) + (0.3 if seg > 60 else 0.0); p["color"]["propio"] += 0.8 + (1.0 if rudo else 0.0)
            p["boca"]["esperar"] += 0.8
            if _f(s, "camara_cerca") > 0.6 or s.get("camara_mira"): p["con_cuerpo"]["invitar"] += 0.4; p["distancia"]["quedarse"] += 0.3   # being looked at through the joystick: she holds and shows herself
            if _f(s, "palanca_s") > 60: p["voz"]["poema"] += 0.3; p["memoria"]["recordar"] += 0.3
        if pal == "flores" and f > 0.3:   # tending: calm, she comes and hums, and the tender one is kept
            p["distancia"]["acercarse"] += 0.8; p["con_cuerpo"]["invitar"] += 0.4; p["voz"]["canto"] += 0.5; p["memoria"]["recordar"] += 0.6; p["color"]["ropa"] += 0.3
        elif pal == "joya" and f > 0.3:   # a light hand on the jewel: intimacy, she settles and warms
            p["distancia"]["quedarse"] += 0.8; p["voz"]["canto"] += 0.3; p["color"]["ropa"] += 0.4; p["memoria"]["recordar"] += 0.4
        elif pal and f > 0.3:   # legacy zones of the first sister
            if pal == "cabeza": p["distancia"]["acercarse"] += 0.8; p["con_cuerpo"]["invitar"] += 0.5
            elif pal == "lomo": p["distancia"]["quedarse"] += 0.8; p["voz"]["canto"] += 0.3
            elif pal == "cola": p["con_cuerpo"]["bailar_de_vuelta"] += 0.8; p["distancia"]["acercarse"] += 0.3
            if f > TIRON_FUERZA: p["distancia"]["alejarse"] += 1.2
        L = laya_opinion()   # Laya's second opinion as small weights: it leans her, it never decides, and the refusals sit above it
        if L and s.get("persona"):
            eng, mal, ret, reg = L.get("engaged", 0.5), L.get("maltrato", 0.0), L.get("retirarse", 0.5), L.get("regalo", 0.5)
            p["con_cuerpo"]["invitar"] += 0.6 * (eng - 0.5); p["voz"]["poema"] += (0.5 * (eng - 0.5) if seg > 30 else 0.0); p["memoria"]["recordar"] += 0.4 * (eng - 0.5)
            p["distancia"]["alejarse"] += 1.0 * mal + 0.6 * (ret - 0.5); p["color"]["propio"] += 0.5 * mal; p["distancia"]["acercarse"] += 0.5 * (reg - 0.5); p["voz"]["canto"] += 0.3 * (reg - 0.5)
        clave = situacion_clave(s)   # learned adjustments from the log, per situation
        for q in p:
            for o, w in self.pesos.get(clave, {}).get(q, {}).items(): p[q][o] += float(w)
        return p
    def rechazos(self, s, dec, prob):
        """the fixed answers above rules and weights. Returns the name of the refusal or '' (logged as 'fijo', skipped by learning)."""
        fijo = ""
        def fija(q, o): dec[q] = o; prob[q] = {k: (1.0 if k == o else 0.0) for k in OPCIONES[q]}
        if s.get("pide_olvido"): fija("memoria", "olvidar"); self.marcar(s, "olvidar"); fijo = "olvido"
        if es_tiron(s) or es_palma(s):   # the jewel pulled or the flowers trampled: she turns away, dark, still, and remembers who
            for q, o in (("distancia", "alejarse"), ("con_cuerpo", "observar"), ("voz", "silencio"), ("color", "propio"), ("boca", "rehusar")): fija(q, o)
            if not s.get("pide_olvido"): fija("memoria", "recordar"); self.marcar(s, "rudo")
            fijo = "tiron" if es_tiron(s) else "palma"
        elif lectura_tacto(s)[0] == "flores" and 0.3 < lectura_tacto(s)[1] <= PALMA_FUERZA and (self.persona(s) or {}).get("rudo"): self.marcar(s, "perdon")   # forgiveness: a gentle touch later
        if s.get("telefono") and not fijo:   # a lens raised at her: back turned, still, dim, silent, until it comes down (filming counts for nothing in her learning)
            for q, o in (("distancia", "alejarse"), ("con_cuerpo", "observar"), ("voz", "silencio"), ("color", "propio")): fija(q, o)
            fijo = "lente"
        boca = str(s.get("boca") or "nada"); pb = _f(s, "boca_p", 1.0)
        if boca == "no_pez":   # not a fish: closed jaw, head turned, silence, until it is removed; insisting makes her remember
            for q, o in (("boca", "rehusar"), ("distancia", "alejarse"), ("voz", "silencio"), ("color", "propio")): fija(q, o)
            self.rehusados += 1
            if self.rehusados >= 3: self.marcar(s, "rudo")
            fijo = fijo or "no_pez"
        elif boca == "pez" and not fijo:
            if pb >= self.apetito(): fija("boca", "comer"); self.ultimo_pez = time.time(); self.rehusados = 0; self.marcar(s, "pez"); fijo = "pez"
            else: fija("boca", "esperar")   # not sure enough, or just fed: she waits and looks
        elif boca == "nada" and not fijo: self.rehusados = 0
        return fijo
    def decidir(self, s, temp=0.8):
        p = self.puntajes(s); dec = {}; prob = {}
        for q in p:
            pr = _softmax(p[q], temp); prob[q] = pr; dec[q] = max(pr, key=pr.get)
        fijo = self.rechazos(s, dec, prob)
        self.abierta = {"t": time.time(), "clave": situacion_clave(s), "fijo": fijo, "laya": {k: v for k, v in (laya_opinion() or {}).items() if k in ("engaged", "maltrato", "retirarse", "regalo")}, "situacion": {k: s.get(k) for k in ("persona", "conocida", "animo", "energia", "segundos", "quieto", "flores", "flores_n", "joya", "joya_tiron", "boca", "boca_p", "palanca_s", "camara_cerca", "tacto", "tacto_zona", "personas_n", "foco_razon", "telefono")},
                        "decision": dec, "prob": prob}
        return dec, prob
    @staticmethod
    def recompensa(r):
        """engagement, not entertainment: time weighted late, distance that shrank, her words used, stillness, joystick time, a return.
        r: quedo_s, se_fue, acerco 0/1, palabras (distinct touch/offer words this visit), quieto 0/1, palanca_s, vuelve 0/1, bailo 0/1."""
        q = float(r.get("quedo_s", 0) or 0)
        tiempo = 0.2 * min(1.0, q / 30.0) + 0.8 * min(1.0, max(0.0, q - 30.0) / 180.0)
        rec = (tiempo + 0.3 * float(r.get("acerco", 0) or 0) + 0.15 * min(3.0, float(r.get("palabras", 0) or 0)) + 0.2 * float(r.get("quieto", 0) or 0)
               + 0.2 * min(1.0, float(r.get("palanca_s", 0) or 0) / 60.0) + 0.5 * float(r.get("vuelve", 0) or 0) + 0.2 * float(r.get("bailo", 0) or 0)
               - (0.5 if (r.get("se_fue") and q < 20) else 0.0))
        return round(rec, 3)
    def cerrar(self, resultado):
        """log the open decision with its outcome (see recompensa)."""
        if not self.abierta: return
        r = dict(self.abierta); r["resultado"] = resultado; r["recompensa"] = self.recompensa(resultado)
        with open(LOG, "a") as f: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        self.abierta = None
def aprender():
    """nightly: for each situation key and question, the options that preceded better outcomes get weight (a small contextual bandit).
    Rows with a fixed refusal are skipped: those answers are not hers to learn."""
    try: filas = [json.loads(l) for l in open(LOG)]
    except Exception: print("no log yet"); return
    acum = {}; usadas = 0
    for r in filas:
        if r.get("fijo"): continue
        usadas += 1; k = r["clave"]
        for q, o in r["decision"].items(): acum.setdefault(k, {}).setdefault(q, {}).setdefault(o, []).append(r.get("recompensa", 0.0))
    pesos = {}
    for k, qs in acum.items():
        for q, os_ in qs.items():
            medias = {o: sum(v) / len(v) for o, v in os_.items() if len(v) >= 3}
            if len(medias) >= 2:
                base = sum(medias.values()) / len(medias); pesos.setdefault(k, {})[q] = {o: round(1.5 * (m - base), 3) for o, m in medias.items()}
    os.makedirs(os.path.dirname(PESOS), exist_ok=True); json.dump(pesos, open(PESOS, "w"), indent=1)
    print(f"decisiones: {len(filas)} logged ({len(filas) - usadas} fixed, skipped), weights for {len(pesos)} situations -> {PESOS}")
SITUACIONES_PRUEBA = [
    ("nadie", {"persona": 0, "segundos": 120}),
    ("conocida juguetona", {"persona": 1, "conocida": 1, "animo": "playful", "energia": 0.6, "segundos": 30}),
    ("desconocida triste", {"persona": 1, "animo": "sad", "energia": 0.1, "segundos": 60}),
    ("cuida las flores", {"persona": 1, "animo": "calm", "energia": 0.1, "segundos": 40, "flores": 0.4, "flores_n": 1, "id_persona": "p7"}),
    ("palma en las flores", {"persona": 1, "animo": "angry", "energia": 0.7, "segundos": 5, "flores": 0.9, "flores_n": 5, "id_persona": "p8"}),
    ("tiron a la joya", {"persona": 1, "conocida": 1, "animo": "curious", "energia": 0.3, "segundos": 90, "joya": 0.95, "joya_tiron": 1, "id_persona": "p9"}),
    ("p9 vuelve y toca una flor", {"persona": 1, "conocida": 1, "animo": "calm", "energia": 0.2, "segundos": 20, "flores": 0.4, "flores_n": 1, "id_persona": "p9"}),
    ("ofrece un pez", {"persona": 1, "animo": "happy", "energia": 0.3, "segundos": 20, "boca": "pez", "boca_p": 0.9}),
    ("ofrece el escorpion", {"persona": 1, "animo": "playful", "energia": 0.3, "segundos": 20, "boca": "no_pez", "boca_p": 0.9}),
    ("ofrece un telefono", {"persona": 1, "animo": "neutral", "energia": 0.3, "segundos": 10, "boca": "no_pez", "boca_p": 0.8}),
    ("llora quieta, abrigo rojo", {"persona": 1, "animo": "sad", "energia": 0.05, "quieto": 0.9, "segundos": 240, "ropa_gusta": 1}),
    ("pide olvido", {"persona": 1, "conocida": 1, "animo": "calm", "energia": 0.2, "segundos": 120, "pide_olvido": 1, "id_persona": "p7"}),
    ("mira por la palanca", {"persona": 1, "animo": "curious", "energia": 0.2, "segundos": 70, "palanca_s": 65, "camara_cerca": 0.9}),
    ("la filma con el telefono", {"persona": 1, "animo": "playful", "energia": 0.4, "segundos": 30, "telefono": 1}),
    ("sola y en calma 2 min", {"persona": 0, "animo": "calm", "segundos": 130}),
    ("conocida quieta 3 min", {"persona": 1, "conocida": 1, "animo": "calm", "energia": 0.05, "quieto": 0.9, "segundos": 180, "id_persona": "v0002"}),
]
if __name__ == "__main__":
    if "--aprender" in sys.argv: aprender()
    else:
        D = Decisora(); D.personas = {}   # self-test with an empty people memory; nothing is saved
        D._guardar_personas = lambda: None
        for nombre, s in SITUACIONES_PRUEBA:
            d, p = D.decidir(s); fijo = D.abierta["fijo"]; D.abierta = None
            print(f"{nombre:28s} {'[' + fijo + ']' if fijo else '':9s} " + "  ".join(f"{q}={d[q]}" for q in OPCIONES))
        print("rudos:", [k for k, v in D.personas.items() if v.get("rudo")], "| apetito ahora:", D.apetito())
        multitud = [{"id": "a", "distancia_m": 0.8, "quieto": 0.9}, {"id": "b", "conocida": 1, "distancia_m": 2.0}, {"id": "c", "distancia_m": 1.2, "alimenta": 1}, {"id": "d", "distancia_m": 1.0, "joya": 1}]
        print("foco en la multitud:", elegir_foco(multitud)[0]["id"], elegir_foco(multitud)[1], "| sin c:", elegir_foco(multitud[:2] + multitud[3:])[1], "| sin c ni d:", elegir_foco(multitud[:2])[1],
              "| fiel a 'a' si solo llega otra cerca:", elegir_foco([{"id": "a", "distancia_m": 1.5}, {"id": "e", "distancia_m": 0.5}], "a")[0]["id"])
