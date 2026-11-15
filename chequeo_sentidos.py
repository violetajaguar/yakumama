#!/usr/bin/env python3
"""chequeo_sentidos.py - the two checks Barcelona lacked (15 Nov 2026, Violeta: "so we dont make the same mistake again").
In Barcelona (28-30 Oct) her phone sense never fired, the room camera gave no count on most of one day, her ear and the air temperature
never reached the log, and a restarted recorder turned her joystick clock negative for a whole night. Nobody saw any of it until the
data was read two weeks later.
    python3 chequeo_sentidos.py --abrir            before opening, with everything running: do what it asks during one minute; it ticks each sense as it fires
    python3 chequeo_sentidos.py --cerrar           at closing time: what today's log holds, with a warning beside what looks dead
    python3 chequeo_sentidos.py --cerrar 2026-10-29 --log fuentes/Barcelona_2026-10-30/datasets/decisiones.jsonl --utc 1      any day of any log
It only reads (her brain's state file, Laya's answer, the decision log, the saved visits). It changes nothing. Standard library only."""
import os, sys, json, time, glob, collections
AQUI = os.path.dirname(os.path.abspath(__file__)); CEREBRO = "/tmp/ballena_cerebro.json"; LAYA = "/tmp/ballena_laya.json"; CATDECIDE = "/tmp/ballena_catdecide.json"
LOG = os.path.join(AQUI, "datasets", "decisiones.jsonl"); OCHO = ("engaged", "maltrato", "retirarse", "regalo", "perform", "visit", "imitate", "speak")

def _json(ruta):
    try: return json.load(open(ruta))
    except Exception: return None
def _fresco(ruta, s): return os.path.exists(ruta) and time.time() - os.path.getmtime(ruta) < s
def _ultima(ruta):
    try:
        with open(ruta, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 20000)); return json.loads(f.read().decode("utf-8", "ignore").strip().split("\n")[-1])
    except Exception: return None

def abrir(segundos=60):
    """Each sense must be SEEN to fire once. The ones a person has to provoke say how."""
    S = collections.OrderedDict([   # name -> [seen, what to do, detail]
        ("cerebro", [False, "su cerebro no escribe: ¿corre cerebro_ballena.py? (logs/cerebro.log)", ""]),
        ("ojo", [False, "párate frente a ella (su ojo, la OAK-D Lite)", ""]),
        ("sala", [False, "la cámara de la sala no cuenta a nadie mientras su ojo te ve (ballena_crowd.py, logs/crowd.log)", ""]),
        ("telefono", [False, "apúntale con un teléfono, como para filmarla", ""]),
        ("tacto", [False, "toca a la hermana: el lomo, una flor, la joya", ""]),
        ("boca", [False, "acerca un pez pintado a la boca de la hermana", ""]),
        ("oido", [False, "habla o da una palmada cerca: su oído no llega al cerebro", ""]),
        ("movimiento", [False, "baila o muévete frente a ella unos segundos", ""]),
        ("aire", [False, "no llega la temperatura del aire (el clima viene del render de Dan)", ""]),
        ("laya", [False, "Laya no responde (logs/laya.log o logs/laya_puente.log)", ""]),
        ("registro", [False, "no se escriben decisiones en datasets/decisiones.jsonl", ""]),
        ("palanca", [False, "el reloj de la palanca salió negativo o no hay resultado todavía", ""])])
    print(f"CHEQUEO DE APERTURA: {segundos} s. Haz esto, en cualquier orden:")
    for k in ("ojo", "telefono", "tacto", "boca", "oido", "movimiento"): print(f"   - {S[k][1]}")
    print(); t0 = time.time(); ts = set(); zonas = set()
    def visto(k, detalle=""):
        if not S[k][0]: print(f"   ✓ {k:10s} {detalle}   ({time.time() - t0:.0f} s)", flush=True)
        S[k][0] = True; S[k][2] = detalle or S[k][2]
    while time.time() - t0 < segundos and not all(v[0] for v in S.values()):
        c = _json(CEREBRO) if _fresco(CEREBRO, 12) else None
        if c:
            ts.add(c.get("t"))
            if len(ts) >= 2: visto("cerebro", "decide cada 4 s")
            if c.get("persona"): visto("ojo", f"te ve, cara {c.get('animo')}")
            if c.get("persona") and (c.get("personas_n") or 0) >= 1: visto("sala", f"cuenta {c.get('personas_n')}")   # 29 Oct, Barcelona: it said 0 people on 91% of the decisions with a visitor at her eye
            if c.get("ve_telefono"): visto("telefono", "ve el teléfono")
            if float(c.get("tacto") or 0) > 0.3: zonas.add(str(c.get("tacto_zona"))); visto("tacto", f"zona {c.get('tacto_zona')}, fuerza {float(c.get('tacto')):.2f}")
            if c.get("ofrenda") in ("pez", "no_pez"): visto("boca", f"lee {c.get('ofrenda')}")
            if c.get("oye_nivel") is not None and float(c.get("oye_nivel") or 0) > 0.05: visto("oido", f"nivel {float(c.get('oye_nivel')):.2f}")
            if float(c.get("mueve_s") or 0) > 0 or float(c.get("baila_s") or 0) > 0: visto("movimiento", f"{c.get('mueve_s') or c.get('baila_s')} s")
            if (c.get("clima") or {}).get("temperatura") is not None: visto("aire", f"{c['clima']['temperatura']} C")
        l = _json(LAYA) if _fresco(LAYA, 12) else None
        if l and all(k in l for k in OCHO): visto("laya", f"sus ocho respuestas, pesos {l.get('pesos', 'originales (la mini)')}, {l.get('ms', '?')} ms")
        elif l: S["laya"][2] = "responde, pero faltan: " + ", ".join(k for k in OCHO if k not in l)
        if _fresco(LOG, 15): visto("registro", "se escribe")
        u = _ultima(LOG) if S["registro"][0] else None
        if u and isinstance(u.get("resultado"), dict) and float(u["resultado"].get("palanca_s") or 0) >= 0 and float(u.get("recompensa") or 0) > -1: visto("palanca", f"reloj {u['resultado'].get('palanca_s')} s, recompensa {u.get('recompensa')}")
        time.sleep(0.5)
    faltan = [k for k, v in S.items() if not v[0]]
    if _fresco(CATDECIDE, 12): print("   (CatDecide también responde)")
    print("\n" + ("TODO VIVO: puede abrir." if not faltan else f"FALTAN {len(faltan)} de {len(S)}:"))
    for k in faltan: print(f"   ✗ {k:10s} {S[k][2] + ' — ' if S[k][2] else ''}{S[k][1]}")
    return 1 if faltan else 0

def cerrar(dia=None, log=LOG, utc=None):
    """What one day of the decision log holds. Warnings mark what would have told us about Barcelona on the day itself."""
    def fecha(t): return time.strftime("%Y-%m-%d", time.gmtime(t + utc * 3600)) if utc is not None else time.strftime("%Y-%m-%d", time.localtime(t))
    dia = dia or fecha(time.time()); F = []
    try:
        for l in open(log, encoding="utf-8"):
            try: d = json.loads(l)
            except Exception: continue
            if fecha(d.get("t", 0)) == dia: F.append(d)
    except FileNotFoundError: print("no hay registro en", log); return 1
    con = [d for d in F if (d.get("situacion") or {}).get("persona")]; n = len(con); avisos = []
    print(f"CIERRE DEL DÍA {dia}: {len(F)} decisiones, {n} con visitante ({os.path.relpath(log)})")
    if not F: print("   ⚠ ninguna decisión ese día: ¿corrió?"); return 1
    if not n: print("   nadie frente a ella ese día; no hay sentidos que revisar"); return 0
    visitas = 0; ant = None
    for d in F:
        s = d.get("situacion") or {}; seg = float(s.get("segundos") or 0)
        if s.get("persona") and (ant is None or not ant[0] or seg < ant[1] - 8): visitas += 1
        ant = (bool(s.get("persona")), seg)
    guardadas = len(glob.glob(os.path.join(os.path.dirname(log), "visitas", dia.replace("-", "") + "_*.jsonl")))
    print(f"   visitas: {visitas} en el registro, {guardadas} grabadas (se graban las de 10 s o más)")
    if visitas and not guardadas: avisos.append("ninguna visita grabada en datasets/visitas")
    def S(d): return d.get("situacion") or {}
    def pct(k): return 100.0 * k / n
    sala = sum(1 for d in con if (S(d).get("personas_n") or 0) >= 1); tel = sum(1 for d in con if S(d).get("telefono")); oido = sum(1 for d in con if S(d).get("oye_nivel") is not None)
    aire = sum(1 for d in con if S(d).get("temperatura") is not None); zonas = collections.Counter(str(S(d).get("tacto_zona")) for d in con if float(S(d).get("tacto") or 0) > 0.3)
    boca = collections.Counter(S(d).get("boca") for d in con if S(d).get("boca") in ("pez", "no_pez")); caras = collections.Counter(S(d).get("animo") for d in con)
    laya = sum(1 for d in con if d.get("laya")); ocho = sum(1 for d in con if all(k in (d.get("laya") or {}) for k in OCHO)); pesos = collections.Counter((d.get("laya") or {}).get("pesos", "sin marca") for d in con if d.get("laya"))
    print(f"   sala (cuenta al menos a una persona): {pct(sala):.0f} %    teléfono visto: {tel} veces    oído en el registro: {pct(oido):.0f} %    temperatura del aire: {pct(aire):.0f} %")
    print(f"   tacto: {dict(zonas) or 'ninguno'}    boca: {dict(boca) or 'nada'}    caras: {', '.join(f'{k} {pct(v):.0f} %' for k, v in caras.most_common(3))}")
    print(f"   Laya: opinó en {pct(laya):.0f} % (sus ocho respuestas en {pct(ocho):.0f} %), pesos {dict(pesos)}")
    if n >= 200 and not tel: avisos.append("su sentido del teléfono no saltó ni una vez")
    if sala < 0.5 * n: avisos.append(f"la cámara de la sala no contó a nadie en {100 - pct(sala):.0f} % de las decisiones con visitante frente a su ojo")
    if oido < 0.5 * n: avisos.append("su oído no llegó al registro")
    if aire < 0.5 * n: avisos.append("la temperatura del aire no llegó al registro")
    if laya < 0.8 * n: avisos.append(f"Laya calló en {100 - pct(laya):.0f} % de las decisiones")
    elif ocho < 0.8 * n: avisos.append("Laya no registra sus ocho respuestas (falta perform, visit, imitate o speak)")
    if boca.get("no_pez", 0) > 0.2 * n: avisos.append(f"su ojo leyó 'no es un pez' en {pct(boca['no_pez']):.0f} % de las decisiones con visitante")
    if caras and caras.most_common(1)[0][1] > 0.7 * n: avisos.append(f"casi todas las caras son '{caras.most_common(1)[0][0]}'")
    neg = sum(1 for d in F if float((d.get("resultado") or {}).get("palanca_s") or 0) < 0); rec = [float(d.get("recompensa") or 0) for d in F]; bajas = sum(1 for r in rec if r < -1)
    print(f"   palanca negativa: {neg} resultados    recompensas: de {min(rec):+.2f} a {max(rec):+.2f} ({bajas} por debajo de -1)")
    if neg: avisos.append(f"el reloj de la palanca salió negativo en {neg} resultados")
    if bajas: avisos.append(f"{bajas} recompensas por debajo de -1 (no deberían existir)")
    dist = collections.Counter((d.get("decision") or {}).get("distancia") for d in con); voz = collections.Counter((d.get("decision") or {}).get("voz") for d in con); viaje = collections.Counter((d.get("decision") or {}).get("viaje") for d in con)
    print(f"   ella, con visitante: distancia {', '.join(f'{k} {pct(v):.0f} %' for k, v in dist.most_common())}    voz {', '.join(f'{k} {pct(v):.0f} %' for k, v in voz.most_common())}    show {viaje.get('show', 0)} veces")
    if dist.get("alejarse", 0) > 0.5 * n: avisos.append(f"se alejó en {pct(dist['alejarse']):.0f} % de sus decisiones con visitante")
    print("\n" + ("SIN AVISOS." if not avisos else f"{len(avisos)} AVISOS:"))
    for a in avisos: print("   ⚠", a)
    return 1 if avisos else 0

if __name__ == "__main__":
    a = sys.argv[1:]
    def valor(nombre, por=None): return a[a.index(nombre) + 1] if nombre in a and a.index(nombre) + 1 < len(a) else por
    if "--abrir" in a: sys.exit(abrir(int(valor("--segundos", 60))))
    elif "--cerrar" in a:
        dia = valor("--cerrar"); dia = None if (dia or "").startswith("--") else dia
        sys.exit(cerrar(dia, valor("--log", LOG), float(valor("--utc")) if valor("--utc") is not None else None))
    else: print(__doc__)
