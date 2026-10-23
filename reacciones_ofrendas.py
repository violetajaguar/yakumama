#!/usr/bin/env python3
"""reacciones_ofrendas.py - las 29 reacciones de Violeta a las 29 ofrendas, en lo que el cerebro ya sabe mover.

Cada reaccion n (la lista de docs/OFRENDAS.md, emparejada a mano el 20 oct) es una receta de unos segundos:
    animo      el animo que manda mientras dura (uno de los diez: calm singing playful curious feeding sad angry alert diving surfacing)
    segundos   cuanto dura
    come       si abre la boca y se la traga (y cuando: come_desde = segundo en que empieza a comer)
    color      None = el color del animo | "criatura" = el color de la ofrenda que vio el ojo | "arcoiris" = gira el matiz | (r, g, b)
    cuerpo(f, t, comp, st)   lo que hace con el cuerpo en la fase f (0..1): mandibula, profundidad, vueltas, aletas, cola, cara, y donde va
    voz        "poema" = le escribe una poesia (la decision de voz se fija en poema)
    dibujo     figura que dibuja en el salar al empezar (figuras_nazca)
    extra      palabras para el receptor y la hermana fisica, lo que este cuerpo no tiene todavia: lengua, panza, rayas, aletas_puntiagudas...

Uso (desde cerebro_ballena.py):
    R = Reacciones(); R.empezar(n, t, color_criatura, nombre)        # cuando el ojo ve la ofrenda
    animo = R.animo(t)                                               # None si no hay reaccion activa
    R.cuerpo(t, comp, st)                                            # modifica comp y st (posicion)
    R.paquete(t, pk, col_animo)                                      # come, jaw, color, latido, turbina, reaccion {...}
"""
import os, math, time

ONDA = lambda t, hz: math.sin(2 * math.pi * hz * t)
NARANJA = (1.0, 0.45, 0.05); ROJO = (0.95, 0.08, 0.05); ROSA = (1.0, 0.35, 0.65); AZUL_TRISTE = (0.15, 0.25, 0.6)
BOCA_MAX = 0.5   # como en el cerebro: la boca nunca pasa de esto


def _nada(f, t, comp, st): pass
def _tiembla_garganta(f, t, comp, st): comp["jaw"] = 0.15 + 0.15 * abs(ONDA(t, 6)); comp["head"] += 0.12 * ONDA(t, 5); comp["ladeo"] += 0.1 * ONDA(t, 3)
def _atraganta(f, t, comp, st): comp["jaw"] = 0.5 * abs(ONDA(t, 3)); comp["pitch"] += 0.25 * abs(ONDA(t, 1.5)); comp["spine"] = [v + 0.08 * ONDA(t, 3) for v in comp["spine"]]; comp["fluke"] += 0.2 * ONDA(t, 3)
def _cosquillas(f, t, comp, st): comp["roll"] += 0.25 * ONDA(t, 2.2); comp["ladeo"] += 0.2 * ONDA(t, 3.1); comp["flap"] += 0.35 * abs(ONDA(t, 4)); comp["spin"] += 0.004
def _salta(f, t, comp, st): comp["depth"] += 0.9 * max(0.0, ONDA(t, 1.2)) ** 2; comp["pitch"] -= 0.3 * ONDA(t, 1.2); comp["flap"] += 0.3 * abs(ONDA(t, 1.2))
def _feliz(f, t, comp, st): comp["flap"] += 0.25 * abs(ONDA(t, 1.5)); comp["roll"] += 0.12 * ONDA(t, 0.7); comp["depth"] += 0.1 * ONDA(t, 0.5)
def _huele(f, t, comp, st): comp["head"] += 0.25; comp["pitch"] -= 0.15; comp["jaw"] = 0.05 + 0.05 * abs(ONDA(t, 0.4)); comp["flap"] *= 0.4
def _huele_mal(f, t, comp, st): comp["ladeo"] += 0.5; comp["head"] -= 0.2; comp["jaw"] = 0.0; comp["cara"] = (0.2, 0.5, 0.2, 0.0); st["ay"] += (1.2 - st["ay"]) * 0.01
def _espiral_come(f, t, comp, st):
    if f < 0.6: comp["spin"] += 0.03 * (1 - f); comp["depth"] -= 0.4 * f; comp["roll"] += 0.2
    else: comp["jaw"] = BOCA_MAX
def _lengua(f, t, comp, st): comp["jaw"] = 0.4; comp["head"] += 0.1
def _disgusto(f, t, comp, st): comp["cara"] = (0.3, 0.7, 0.4, 0.0); comp["head"] -= 0.15; comp["ladeo"] += 0.25; comp["jaw"] = 0.0
def _traga_despacio(f, t, comp, st): comp["jaw"] = BOCA_MAX * min(1.0, f * 2.5); st["ay"] += (-1.4 - st["ay"]) * 0.004; comp["flap"] *= 0.3
def _come_bailando(f, t, comp, st): comp["jaw"] = BOCA_MAX * abs(ONDA(t, 0.8)); comp["ladeo"] += 0.3 * ONDA(t, 1.6); comp["roll"] += 0.2 * ONDA(t, 0.8); comp["flap"] += 0.3 * abs(ONDA(t, 1.6)); comp["fluke"] += 0.2 * ONDA(t, 1.6)
def _vuela_alto(f, t, comp, st):   # 21 Oct (Violeta, pajaro azul: "que la ballena vuele alto"): a steep climb, nose up, fins beating, eyes wide; the spiral flight carries her up
    sube = min(1.0, f / 0.3); comp["depth"] += 1.6 * sube + 0.4 * abs(ONDA(t, 1.0)); comp["pitch"] -= 0.5 * sube; comp["head"] += 0.3; comp["flap"] += 0.7 * abs(ONDA(t, 1.0)); comp["fluke"] -= 0.2 * abs(ONDA(t, 1.0)); comp["cara"] = (0.0, 0.0, 0.0, 0.6)
def _vuela(f, t, comp, st): comp["pitch"] -= 0.45; comp["head"] += 0.3; comp["depth"] += 0.6 + 0.3 * abs(ONDA(t, 1.0)); comp["flap"] += 0.6 * abs(ONDA(t, 1.0)); comp["cara"] = (0.0, 0.0, 0.0, 0.5)
def _susto(f, t, comp, st): comp["cara"] = (0.0, 0.0, 0.0, 0.8); comp["pitch"] += 0.3; comp["flap"] += 0.4; st["ay"] += (1.6 - st["ay"]) * (0.05 if f < 0.4 else 0.01); comp["jaw"] = 0.0
def _coletazo(f, t, comp, st):
    if f < 0.3: comp["fluke"] += 0.9 * ONDA(t, 2.5); comp["spine"] = [v + 0.15 * ONDA(t, 2.5) * (i / 5.0) for i, v in enumerate(comp["spine"])]
def _admira(f, t, comp, st): comp["head"] += 0.2; comp["flap"] *= 0.2; comp["fluke"] *= 0.3; comp["cara"] = (0.0, 0.0, 0.0, 0.4); comp["jaw"] = 0.08
def _poesia(f, t, comp, st): comp["flap"] *= 0.5; comp["head"] += 0.1 * ONDA(t, 0.3)
def _sigue(f, t, comp, st): comp["head"] += 0.25 * ONDA(t, 0.35); comp["ladeo"] += 0.4 * ONDA(t, 0.35); comp["yaw"] += 0.3 * ONDA(t, 0.35); comp["depth"] += 0.2 * ONDA(t, 0.25)
def _lengua_vueltas(f, t, comp, st): comp["jaw"] = 0.4; comp["spin"] += 0.035; comp["roll"] += 0.15
def _caras_locas(f, t, comp, st):
    k = int(t * 3) % 4; comp["cara"] = [(0.0, 0.0, 0.0, 0.9), (0.6, 0.8, 0.0, 0.0), (0.9, 0.0, 0.0, 0.0), (0.0, 0.0, 0.7, 0.6)][k]
    comp["head"] += 0.2 * ONDA(t, 2.3); comp["ladeo"] += 0.25 * ONDA(t, 1.7); st["ay"] += (1.0 - st["ay"]) * 0.01
def _rie(f, t, comp, st): comp["jaw"] = 0.3 * abs(ONDA(t, 4)); comp["spine"] = [v + 0.06 * ONDA(t, 4) for v in comp["spine"]]; comp["flap"] += 0.25 * abs(ONDA(t, 4)); comp["roll"] += 0.1 * ONDA(t, 2)
def _baila(f, t, comp, st): comp["ladeo"] += 0.35 * ONDA(t, 1.6); comp["roll"] += 0.25 * ONDA(t, 0.8); comp["flap"] += 0.35 * abs(ONDA(t, 1.6)); comp["fluke"] += 0.25 * ONDA(t, 1.6); comp["depth"] += 0.15 * ONDA(t, 0.8)
def _rabia(f, t, comp, st): comp["cara"] = (0.4, 1.0, 0.0, 0.0); comp["flap"] += 0.5; comp["fluke"] += 0.3 * ONDA(t, 3); comp["jaw"] = 0.2
def _llora(f, t, comp, st): comp["cara"] = (0.6, 0.0, 1.0, 0.0); comp["head"] -= 0.3; comp["depth"] -= 0.2; comp["flap"] *= 0.3; comp["spine"] = [v + 0.03 * ONDA(t, 0.5) for v in comp["spine"]]
def _escapa(f, t, comp, st): comp["fluke"] += 0.6 * ONDA(t, 3); comp["depth"] -= 0.3; st["ay"] += (1.8 - st["ay"]) * 0.04; comp["jaw"] = 0.0
def _come_y_baja(f, t, comp, st):
    if f < 0.3: comp["jaw"] = BOCA_MAX
    else: comp["depth"] -= 1.2 * (f - 0.3) / 0.7; comp["pitch"] += 0.45; comp["fluke"] += 0.3 * ONDA(t, 1.2)
def _panza_baila(f, t, comp, st):
    if f < 0.25: comp["jaw"] = BOCA_MAX
    else: _baila(f, t, comp, st)


# n: (texto, animo, segundos, come, come_desde, color, cuerpo, voz, dibujo, extra)
TABLA = {
    1: ("Le va a picar la garganta", "alert", 8, True, 0.0, None, _tiembla_garganta, None, None, ["garganta"]),
    2: ("Se atragante", "alert", 8, True, 0.0, None, _atraganta, None, None, ["atraganta"]),
    3: ("Se intoxique y le haga cosquillas", "playful", 10, True, 0.0, (0.5, 0.9, 0.3), _cosquillas, None, None, ["cosquillas"]),
    4: ("Empieza a saltar", "playful", 8, False, 0.0, None, _salta, None, None, ["salto"]),
    5: ("Se ponga feliz porque le gusta", "playful", 8, True, 0.0, None, _feliz, None, None, ["feliz"]),
    6: ("Le guste el olor", "calm", 8, False, 0.0, None, _huele, None, None, ["olor"]),
    7: ("No le gusta el olor", "alert", 6, False, 0.0, None, _huele_mal, None, None, ["olor_malo"]),
    8: ("Que vaya en espiral y despues se lo coma", "playful", 10, True, 0.6, None, _espiral_come, None, None, ["espiral"]),
    9: ("Que se vuelva de ese color", "calm", 15, True, 0.0, "criatura", _nada, None, None, ["color_criatura"]),
    10: ("Que saque la lengua y su lengua se vuelva rosada", "curious", 8, False, 0.0, None, _lengua, None, None, ["lengua", "lengua_rosada"]),
    11: ("Que le mire con cara de disgusto", "alert", 6, False, 0.0, None, _disgusto, None, None, ["disgusto"]),
    12: ("Que abra la boca grande y se acerque despacio y se trague", "feeding", 10, True, 0.0, None, _traga_despacio, None, None, ["traga"]),
    13: ("Se coma bailando", "playful", 10, True, 0.0, None, _come_bailando, None, None, ["baila"]),
    14: ("Que vuele alto, en espiral hacia el cielo", "surfacing", 12, False, 0.0, None, _vuela_alto, None, None, ["vuela_alto", "espiral"]),   # 21 Oct, Violeta (pajaro azul): "que la ballena vuele alto" (was: salute the bird and try to fly)
    15: ("Se asusta y vaya rapido hacia atras", "alert", 6, False, 0.0, None, _susto, None, None, ["susto"]),
    16: ("Que le de un coletazo y lo dibuje", "playful", 12, False, 0.0, None, _coletazo, None, "zigzag", ["coletazo", "dibuja"]),
    17: ("Que admire su belleza y quiera copiarle la forma", "curious", 12, False, 0.0, "criatura", _admira, None, None, ["copiar_forma"]),
    18: ("Que le escriba una poesia", "singing", 20, False, 0.0, None, _poesia, "poema", None, ["poesia"]),
    19: ("Que trate de seguirla en el espacio", "curious", 10, False, 0.0, None, _sigue, None, None, ["seguir"]),
    20: ("Cuando se lo coma tendra un super poder de volverse y va a imitar sus rayas de dibujo", "playful", 15, True, 0.0, "criatura", _feliz, None, None, ["rayas", "color_criatura"]),
    21: ("Cuando se le acerque le saque la lengua y de muchas vueltas", "playful", 10, False, 0.0, None, _lengua_vueltas, None, None, ["lengua", "vueltas"]),
    22: ("Que le tenga miedo y le haga caras locas", "alert", 8, False, 0.0, None, _caras_locas, None, None, ["caras_locas"]),
    23: ("Que se ria sin parar y despues se vuelva arcoiris de tanto reir", "playful", 12, False, 0.0, "arcoiris", _rie, None, None, ["risa", "arcoiris"]),
    24: ("Que baile y se vuelva de color naranja", "playful", 12, False, 0.0, NARANJA, _baila, None, None, ["baila", "naranja"]),
    25: ("Que sus aletas se pongan puntiagudas y se vuelva roja de rabia", "angry", 8, False, 0.0, ROJO, _rabia, None, None, ["aletas_puntiagudas", "rabia"]),
    26: ("Que con esta llore por la inquietud", "sad", 10, False, 0.0, AZUL_TRISTE, _llora, None, None, ["llora"]),
    27: ("Que intente escapar", "diving", 8, False, 0.0, None, _escapa, None, None, ["escapa"]),
    28: ("Que cuando se coma esta, diving deep", "diving", 12, True, 0.0, None, _come_y_baja, None, None, ["diving"]),
    29: ("Que se hinche la panza y baile", "playful", 12, True, 0.0, None, _panza_baila, None, None, ["panza", "baila"]),
}
CAMPOS = ("texto", "animo", "segundos", "come", "come_desde", "color", "cuerpo", "voz", "dibujo", "extra")

# ---- LAS FASES (Violeta, 21 oct): "cada reacción es una combinación nueva de sus 10 movimientos". Cada reacción recorre fases
# (movimiento, segundos) de su repertorio: en cada fase manda ese ánimo, con su cuerpo inventado y SU COREOGRAFÍA EN EL ESPACIO
# (el cerebro deja la coreografía encendida durante una reacción). Suman la escena (30 s). Los VUELOS: una figura volada con la
# pluma arriba (figuras_nazca) para las reacciones que nombran un camino: la espiral es una espiral.
FASES = {
    1: [("alert", 10), ("calm", 20)], 2: [("alert", 10), ("calm", 20)], 3: [("playful", 30)], 4: [("playful", 30)], 5: [("playful", 20), ("calm", 10)],
    6: [("calm", 30)], 7: [("alert", 8), ("sad", 22)], 8: [("curious", 12), ("playful", 8), ("feeding", 10)], 9: [("calm", 30)], 10: [("curious", 30)],
    11: [("alert", 10), ("sad", 20)], 12: [("curious", 8), ("feeding", 22)], 13: [("playful", 30)], 14: [("surfacing", 14), ("playful", 10), ("curious", 6)],
    15: [("alert", 6), ("sad", 10), ("calm", 14)], 16: [("angry", 6), ("playful", 24)], 17: [("curious", 30)], 18: [("singing", 30)], 19: [("curious", 30)],
    20: [("feeding", 8), ("playful", 22)], 21: [("curious", 10), ("playful", 20)], 22: [("alert", 10), ("angry", 8), ("alert", 12)], 23: [("playful", 30)],
    24: [("playful", 30)], 25: [("angry", 30)], 26: [("sad", 30)], 27: [("alert", 5), ("diving", 25)], 28: [("feeding", 8), ("diving", 22)], 29: [("feeding", 8), ("playful", 22)],
}
VUELO = {8: "espiral", 14: "espiral", 19: "zigzag", 21: "espiral", 27: "laberinto"}   # flown with the pen up, fast and small (cerebro: dib rapido)
REACCIONES = {n: dict(zip(CAMPOS, v)) for n, v in TABLA.items()}


def _hsv_a_rgb(h, s, v):
    i = int(h * 6) % 6; f = h * 6 - int(h * 6); p, q_, t_ = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return [(v, t_, p), (q_, v, p), (p, v, t_), (p, q_, v), (t_, p, v), (v, p, q_)][i]


class Reacciones:
    ENFRIAR = 12.0   # segundos entre dos reacciones a la misma criatura
    ESCENA_S = float(os.environ.get("YAKUMAMA_OFRENDA_S", 30.0))   # Violeta's map (20 Oct): an offering lasts 30 s, "como una escena" (the recipes were 8-12 s)

    def __init__(self): self.r = None; self.ultimas = {}; self.ultima_id = None; self.soltada = True

    def soltar(self):
        """nothing in the mouth: the last creature may start a new scene when it comes back (21 Oct: a scene ends at 30 s and does not loop while the same creature is still held)."""
        self.soltada = True

    def empezar(self, n, t, color_criatura=None, nombre=None, ofrenda_id=None):
        """arranca la reaccion n si no hay otra activa y la criatura no acaba de reaccionar. Devuelve True si arranco."""
        n = int(n or 0)
        if n not in REACCIONES: return False
        if t - self.ultimas.get(ofrenda_id or n, -1e9) < self.ENFRIAR: return False
        if ofrenda_id and ofrenda_id == self.ultima_id and not self.soltada: return False   # the same creature, never lowered: her scene is over, she goes back to herself
        if self.activa(t):   # Violeta's map (20 Oct): a NEW creature replaces the one playing; the same one does not restart it
            if self.r.get("ofrenda_id") == ofrenda_id: return False
        self.ultimas[ofrenda_id or n] = t
        self.r = {"n": n, "t0": t, "color_criatura": color_criatura, "nombre": nombre, "ofrenda_id": ofrenda_id, "dibujo_pedido": bool(REACCIONES[n]["dibujo"]), "voz_pedida": bool(REACCIONES[n]["voz"]), **REACCIONES[n]}
        self.ultima_id = ofrenda_id; self.soltada = False
        self.r["fases"] = FASES.get(n, [(self.r["animo"], self.r.get("segundos") or 8)]); self.r["vuelo_pedido"] = n in VUELO; self.r["vuelo"] = VUELO.get(n)
        self.r["segundos"] = max(float(self.r.get("segundos") or 8.0), self.ESCENA_S)
        return True

    def cortar(self): self.r = None

    def activa(self, t): return self.r is not None and (t - self.r["t0"]) < self.r["segundos"]

    def fase(self, t): return min(1.0, max(0.0, (t - self.r["t0"]) / self.r["segundos"])) if self.r else 1.0

    def animo(self, t):
        """the movement of the current phase (FASES), or the recipe's single mood."""
        if not self.activa(t): return None
        e = t - self.r["t0"]; acum = 0.0
        for a_, seg in self.r.get("fases") or []:
            acum += float(seg)
            if e < acum: return a_
        return (self.r.get("fases") or [(self.r["animo"], 0)])[-1][0]

    def vuelo(self):
        """the figure to FLY (pen up), once."""
        if self.r and self.r.get("vuelo_pedido"): self.r["vuelo_pedido"] = False; return self.r.get("vuelo")
        return None

    def cuerpo(self, t, comp, st):
        if not self.activa(t): return
        self.r["cuerpo"](self.fase(t), t - self.r["t0"], comp, st)
        comp["jaw"] = max(0.0, min(BOCA_MAX, comp["jaw"]))

    def dibujo(self):
        """la figura que pide dibujar, una sola vez."""
        if self.r and self.r["dibujo_pedido"]: self.r["dibujo_pedido"] = False; return self.r["dibujo"]
        return None

    def voz(self):
        if self.r and self.r["voz_pedida"]: self.r["voz_pedida"] = False; return self.r["voz"]
        return None

    def color(self, t, col_animo):
        if not self.activa(t) or not self.r["color"]: return col_animo
        c = self.r["color"]; f = self.fase(t); mezcla = min(1.0, f * 3.0)   # entra en el primer tercio
        if c == "criatura": c = self.r["color_criatura"] or col_animo
        elif c == "arcoiris": c = _hsv_a_rgb(((t - self.r["t0"]) * 0.25) % 1.0, 0.9, 1.0) if f > 0.5 else col_animo
        return [round(a * (1 - mezcla) + b * mezcla, 3) for a, b in zip(col_animo, c)]

    def paquete(self, t, pk, col_animo):
        """escribe en el paquete: reaccion {...}, come, jaw, color, latido. Sin reaccion activa deja come como venia."""
        if not self.activa(t): pk["reaccion"] = None; return pk
        f = self.fase(t); come = int(self.r["come"] and f >= self.r["come_desde"])
        pk["come"] = come; pk["rehusa"] = 0
        if come: pk["jaw"] = pk["boca"] = max(float(pk.get("jaw") or 0), 0.3); pk["turbina"] = round(float(pk.get("turbina") or 1.0) * 1.5, 3)
        pk["color"] = self.color(t, col_animo)
        pk["reaccion"] = {"n": self.r["n"], "texto": self.r["texto"], "ofrenda_id": self.r["ofrenda_id"], "nombre": self.r["nombre"], "fase": round(f, 2), "come": come, "extra": self.r["extra"]}
        return pk


if __name__ == "__main__":   # prueba: cada reaccion 2 s en seco
    R = Reacciones(); comp0 = dict(pitch=0.0, roll=0.0, yaw=0.0, head=0.0, spine=[0.0] * 6, fluke=0.0, flap=0.0, ladeo=0.0, jaw=0.0, cara=(0, 0, 0, 0), mirada=(0, 0), spin=0.0, depth=0.0)
    for n in sorted(REACCIONES):
        R.r = None; R.ultimas = {}; t0 = time.time(); assert R.empezar(n, t0, (0.9, 0.2, 0.2), "prueba", n)
        st = {"ay": 0.0}; vistos = set()
        for k in range(60):
            t = t0 + REACCIONES[n]["segundos"] * k / 60.0; comp = dict(comp0); comp["spine"] = [0.0] * 6; R.cuerpo(t, comp, st); pk = R.paquete(t, {"jaw": comp["jaw"], "boca": comp["jaw"], "turbina": 1.0}, (0.2, 0.4, 0.9))
            vistos |= {kk for kk in ("depth", "spin", "jaw", "flap", "fluke", "ladeo", "head", "pitch", "roll", "yaw") if abs(comp[kk]) > 1e-6}
            if comp["cara"] != (0, 0, 0, 0): vistos.add("cara")
        print(f"{n:2d} {REACCIONES[n]['animo']:9s} {REACCIONES[n]['segundos']:2d}s come={int(REACCIONES[n]['come'])} color={pk['color']} mueve={sorted(vistos)} ay={st['ay']:+.2f}  {REACCIONES[n]['texto']}")
