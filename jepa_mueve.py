#!/usr/bin/env python3
"""jepa_mueve.py - she moves with what her H-JEPA generates, alone, no camera.
With modelos/hjepa_ballena.pt (trained in HER body space) the output IS whale movement: pitch, roll, head, spine, fins link by
link, tail, face, depth, travel; it goes to the receiver as raw channels (`canales`). With the old modelos/hjepa.pt it is six
body qualities that conduct her, as a dancer would.

    venv/bin/python jepa_mueve.py                         all ten moods, 32 s each, looping (whale-space model if present)
    venv/bin/python jepa_mueve.py playful sad --ruido 0.3  with variety
    venv/bin/python jepa_mueve.py --semilla ~/Desktop/h26_limpio/BF-Lucia_kullawada_limpio.npz --animo playful
                                                           start from a real body's last 32 s and keep going from there
    venv/bin/python jepa_mueve.py --modelo modelos/hjepa.pt   force the old model
"""
import sys, os, json, time, math, socket, argparse, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI); from hjepa_predecir import HJepa
ap = argparse.ArgumentParser(); ap.add_argument("animos", nargs="*"); ap.add_argument("--modelo", default=None); ap.add_argument("--ruido", type=float, default=0.0); ap.add_argument("--semilla", default=None, help="a skeleton .npz or a performer take: its last 32 s become her context"); ap.add_argument("--animo", default=None)
ap.add_argument("--quieta", action="store_true"); ap.add_argument("--hacia", default="libre", choices=["libre", "publico", "fondo", "izquierda", "derecha", "casa", "alrededor"], help="where she goes in the salar during this phrase"); ap.add_argument("--acro", type=int, default=1); ap.add_argument("--segundos", type=float, default=0.0, help="stop after this many seconds (0 = loop forever)"); ap.add_argument("--etiqueta", default=""); ap.add_argument("--modo", default="auto", choices=["auto", "inventa", "frases", "continuar"], help="inventa = diffusion (she invents, Paqarina's method); frases = real phrases along her plan; continuar = decoder; auto = inventa if the diffusion model exists, else frases"); ap.add_argument("--ancla", type=float, default=0.5, help="weight of the mood's designed behaviour under the generated body (0 = pure model, 1 = pure behaviour)"); ap.add_argument("--puerto", type=int, default=9998); a = ap.parse_args()
ruta = a.modelo or (os.path.join(AQUI, "modelos", "hjepa_ballena.pt") if os.path.exists(os.path.join(AQUI, "modelos", "hjepa_ballena.pt")) else os.path.join(AQUI, "modelos", "hjepa.pt"))
h = HJepa(ruta); ESPACIO_BALLENA = "pitch" in h.CUERPO; BANCO = ESPACIO_BALLENA and h.cargar_banco(); INV = None
if ESPACIO_BALLENA and a.modo in ("auto", "inventa") and os.path.exists(os.path.join(AQUI, "modelos", "difusion_ballena.pt")):
    try: from difusion_ballena import Inventora; INV = Inventora(); assert INV.CAN == h.CUERPO
    except Exception as e: INV = None; print(f"   (diffusion off: {e})")
MODO = "inventa" if INV is not None else ("frases" if (BANCO and a.modo != "continuar") else "continuar"); ultimo_cuerpo = None; moods = [m for m in a.animos if m in h.ACCIONES] or ([a.animo] if a.animo else h.ACCIONES[:10])
print(f"   model {os.path.basename(ruta)}: {len(h.CUERPO)} channels, {'HER BODY SPACE' if ESPACIO_BALLENA else 'six body qualities'}" + (f" | phrase bank: {len(h.banco['Z'])} real phrases" if BANCO else "") + (" | DIFFUSION: she invents" if INV is not None else "") + f" | mode {MODO}")
if a.semilla:   # a real body as context
    from retarget_ballena import esqueleto_a_ballena, CANALES_BALLENA, cargar_toma; from cuerpo_cualidades import cargar_npz, cualidades_toma
    if a.semilla.endswith(".npz"): B, J, fps = cargar_npz(a.semilla)
    else: B, J, fps, _, _ = cargar_toma(a.semilla)
    if ESPACIO_BALLENA: X = esqueleto_a_ballena(B, J, fps); filas = [{c: (None if not np.isfinite(v) else float(v)) for c, v in zip(CANALES_BALLENA, r)} for r in X]
    else: q = cualidades_toma(B, J, fps); filas = [{c: (None if not np.isfinite(q[c][i]) else float(q[c][i])) for c in h.CUERPO} for i in range(len(B))]
    paso = max(1, int(round(fps / h.fps)))
    for fr in filas[-h.largo * paso::paso]: h.empujar(fr)
    print(f"   context: last 32 s of {os.path.basename(a.semilla)} | body reads {h.leer().get('animo_cuerpo')}")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); FPS = 30.0; C = {c: i for i, c in enumerate(h.CUERPO)}; T_INICIO = time.time()
DESTINOS = {"publico": (0.0, -1.8), "fondo": (0.0, 1.8), "izquierda": (-1.8, -0.4), "derecha": (1.8, -0.4), "casa": (0.0, 0.0)}   # the salar: the viewer is at -Y
try: import comportamientos_animos as CA
except Exception: CA = None
def anclar(can, m, t, w):
    """blend the mood's designed behaviour (comp_<mood>) under the generated channels: pitch, roll, head, spine, fluke, depth, jaw, face."""
    if CA is None or w <= 0 or m not in CA.COMPORTAMIENTOS: return can
    c = CA.COMPORTAMIENTOS[m](t); mix = lambda a_, b_: (1 - w) * a_ + w * b_
    for k in ("pitch", "roll", "head", "fluke", "depth", "jaw", "spin"): can[k] = mix(can[k], float(c[k]))
    can["spine"] = [mix(a_, b_) for a_, b_ in zip(can["spine"], c["spine"])]; can["cara"] = [mix(a_, b_) for a_, b_ in zip(can["cara"], c["cara"])]
    for lado in ("aleta_l", "aleta_r"): can[lado] = [mix(can[lado][0], float(c["flap"])), mix(can[lado][1], 0.35 * float(c["flap"])), mix(can[lado][2], 0.15 * float(c["flap"]))]
    tb = CA.TURBINA_ANIMO.get(m, 1.0); can["turbina"] = mix(can["turbina"], 1.2 if tb == "pulso" else float(tb))
    if m == "diving":   # DIVING turns down and INSIDE: away from the viewer, nose down, deep, flukes up
        tt = t % 20.0; baja = min(1.0, tt / 8.0) if tt < 14 else max(0.0, 1 - (tt - 14) / 6.0)
        can["pitch"] = min(can["pitch"], -0.25 - 0.4 * baja); can["depth"] = -1.8 * baja; can["spine"] = [min(v, 0.0) - 0.1 * k * baja for k, v in enumerate(can["spine"])]; can["fluke"] = min(can["fluke"], -0.45 * baja); can["_rumbo"] = 0.0; can["_y"] = 1.2 * baja   # TAIL UP (Violeta, jepa moods): tail vertebrae and flukes raised as she goes down
    if m == "surfacing":   # SURFACING comes up from below towards the viewer
        tt = t % 12.0; sube = min(1.0, tt / 5.0); arriba = max(0.0, 1 - abs(tt - 6.0) / 2.0)   # 5 s up from deep, a blow at the top, then rests at the surface
        can["pitch"] = max(can["pitch"], 0.45 * (1 - sube) + 0.1 * arriba); can["depth"] = -1.6 + 1.8 * sube; can["head"] = can["head"] + 0.3 * arriba; can["jaw"] = max(can["jaw"], 0.4 * arriba)
        can["aleta_l"] = [can["aleta_l"][0] + 0.35 * arriba, can["aleta_l"][1], can["aleta_l"][2]]; can["aleta_r"] = [can["aleta_r"][0] + 0.35 * arriba, can["aleta_r"][1], can["aleta_r"][2]]; can["_rumbo"] = math.pi; can["_y"] = -1.2 * sube
    return can
px = py_ = 0.0; rumbo = math.pi; ESCALA_PISO = 0.8; RADIO_MAX = 2.0
import random
acro = {"proximo": 4.0 + random.random() * 4.0, "tipo": None, "t0": 0.0}
def acrobacia(m, tt, energia):
    """PLAYFUL (Violeta): she turns to the side, goes upside down, barrel-rolls, when she invents. Every 5-9 s one of: lado (side, 1.3 rad held),
    panza (upside down, pi held), vuelta (a full barrel roll, 2 pi in 1.6 s), doble (two). Returns the absolute roll (spin channel) or 0."""
    if m != "playful" or not a.acro: return 0.0
    if acro["tipo"] is None and tt >= acro["proximo"]:
        acro["tipo"] = random.choices(["lado", "panza", "vuelta", "doble"], weights=[3, 2, 3, 1])[0]; acro["t0"] = tt; acro["lado"] = random.choice([-1, 1])
    if acro["tipo"] is None: return 0.0
    e = tt - acro["t0"]; suave = lambda x: x * x * (3 - 2 * x)
    if acro["tipo"] in ("lado", "panza"):
        meta = 1.3 if acro["tipo"] == "lado" else math.pi; sube, hold, baja = 0.7, 1.4, 0.9
        if e < sube: v = meta * suave(e / sube)
        elif e < sube + hold: v = meta
        elif e < sube + hold + baja: v = meta * (1 - suave((e - sube - hold) / baja))
        else: acro["tipo"] = None; acro["proximo"] = tt + 5.0 + random.random() * 4.0; return 0.0
        return acro["lado"] * v
    dur = 1.6 if acro["tipo"] == "vuelta" else 3.0; n = 1 if acro["tipo"] == "vuelta" else 2
    if e < dur: return acro["lado"] * 2 * math.pi * n * suave(e / dur)
    acro["tipo"] = None; acro["proximo"] = tt + 5.0 + random.random() * 4.0; return 0.0
while True:
    for m in moods:
        if MODO == "inventa": cuerpo = INV.inventar(m, segundos=32.0, prefijo=ultimo_cuerpo, temp=1.0 + 0.3 * a.ruido); ams = [m] * 4; ultimo_cuerpo = cuerpo[-12:]   # a new dance from noise, continuing her own last second
        elif MODO == "frases": cuerpo, ams = h.muestrear(m, ruido=a.ruido, desde_contexto=bool(a.semilla))
        elif a.semilla and h.n >= h.largo: cuerpo, ams = h.continuar(m, ruido=a.ruido)
        else:
            cuerpo, ams = h.generar(m)
            if a.ruido > 0: cuerpo = cuerpo + a.ruido * 0.05 * np.random.randn(*cuerpo.shape).astype(np.float32)
        n = len(cuerpo); t0 = time.time(); g = lambda i, c: float(cuerpo[i, C[c]]) if c in C else 0.0
        print(f"   {m:10s} 32 s generated | sub-goals {ams[:4]}... | " + (f"pitch {cuerpo[:, C['pitch']].mean():+.2f} fin L {cuerpo[:, C['flap_l']].mean():+.2f} tail amp {cuerpo[:, C['fluke']].std():.2f} travel {np.abs(cuerpo[:, C['avance']]).mean():.2f}" if ESPACIO_BALLENA else f"energy {cuerpo[:, 4].mean():.2f}"), flush=True)
        for i in range(int(n / h.fps * FPS)):
            f = min(n - 1, int(i / FPS * h.fps)); pk = {"actor_animo": m, "bailarin": "jepa:" + m, "water": 0.8, "red": 1, "soltar_manual": 1 if i < 30 else 0, "cuerpo_jepa": 1}
            if ESPACIO_BALLENA:
                can = {"pitch": g(f, "pitch"), "roll": g(f, "roll"), "yaw": g(f, "yaw"), "head": g(f, "head"), "spine": [g(f, f"spine{k}") for k in range(6)], "fluke": g(f, "fluke"), "flap": 0.0, "ladeo": 0.0,
                       "aleta_l": [g(f, "flap_l"), g(f, "codo_l"), g(f, "muneca_l")], "aleta_r": [g(f, "flap_r"), g(f, "codo_r"), g(f, "muneca_r")], "jaw": max(0.0, g(f, "jaw")),
                       "cara": [max(0.0, g(f, c)) for c in ("cara_parpado", "cara_rabia", "cara_tristeza", "cara_asombro")], "mirada": [g(f, "mirada_yaw"), g(f, "mirada_pitch")], "spin": g(f, "spin"), "depth": g(f, "depth"), "turbina": max(0.3, g(f, "turbina"))}
                if not a.quieta:
                    dt = 1.0 / FPS; giro_ = max(-0.8, min(0.8, g(f, "giro"))) * (0.5 if MODO == "inventa" else 1.0); rumbo += giro_ * dt
                    if MODO == "inventa": rumbo += ((math.pi - rumbo + math.pi) % (2 * math.pi) - math.pi) * 0.004   # and she slowly comes back to facing the viewer instead of circling
                    av, de = max(-0.6, min(0.8, g(f, "avance"))) * ESCALA_PISO, max(-0.5, min(0.5, g(f, "deriva"))) * ESCALA_PISO
                    px += (av * math.sin(rumbo) + de * math.cos(rumbo)) * dt; py_ += (av * math.cos(rumbo) - de * math.sin(rumbo)) * dt; r_ = math.hypot(px, py_)
                    if r_ > RADIO_MAX: px, py_ = px * RADIO_MAX / r_, py_ * RADIO_MAX / r_
                    can["x"], can["y"], can["z"], can["rumbo"] = round(px, 3), round(py_, 3), 0.0, round((rumbo + math.pi) % (2 * math.pi) - math.pi, 3)
                if "_rumbo" in can: can["rumbo"] = round(can.pop("_rumbo"), 3); can["x"], can["y"], can["z"] = round(px, 3), round(py_ + can.pop("_y"), 3), 0.0; rumbo = can["rumbo"]
                if a.hacia in DESTINOS and not a.quieta:   # the score says where: she drifts toward that place, keeping her invented sway around it
                    dx_, dy_ = DESTINOS[a.hacia]; px += (dx_ - px) * 0.012; py_ += (dy_ - py_) * 0.012; can["x"], can["y"] = round(px, 3), round(py_, 3)
                    if a.hacia == "publico": rumbo += ((math.pi - rumbo + math.pi) % (2 * math.pi) - math.pi) * 0.02; can["rumbo"] = round((rumbo + math.pi) % (2 * math.pi) - math.pi, 3)
                elif a.hacia == "alrededor" and not a.quieta:   # a slow round of the salar
                    ang = 2 * math.pi * (time.time() - T_INICIO) / 60.0; px += (1.6 * math.sin(ang) - px) * 0.02; py_ += (1.0 * math.cos(ang) - 0.4 - py_) * 0.02; can["x"], can["y"] = round(px, 3), round(py_, 3)
                w_ancla = {"calm": 0.85, "surfacing": 0.8, "diving": 0.7}.get(m, a.ancla)
                if MODO == "inventa": w_ancla = {"calm": 0.6, "surfacing": 0.6, "diving": 0.6}.get(m, 0.15)   # inventing: the script is only a light touch (Violeta: "let it be more free")
                can = anclar(can, m, i / FPS, w_ancla)
                if MODO == "inventa": can["spin"] = 0.0   # no scripted rounds on top of what she invents
                # MORE AXES when she invents (Violeta): sideways sway of the spine with her turning, head roll and yaw, fin sweep with her speed, flukes steering
                giro_ = max(-0.8, min(0.8, g(f, "giro"))); av_ = g(f, "avance"); ola = math.sin(2 * math.pi * (i / FPS) * (0.4 + 0.3 * max(0.0, g(f, "turbina")) / 3.0))
                can["spine_lado"] = [round(0.18 * giro_ * (k + 1) / 6 + 0.05 * ola * (k + 1) / 6, 3) for k in range(6)]
                can["head_roll"] = round(0.25 * g(f, "roll") + 0.06 * ola, 3); pk["head_yaw"] = round(0.5 * g(f, "mirada_yaw") - 0.3 * giro_, 3)
                can["barrido_l"] = round(0.25 * max(-1.0, min(1.0, av_)) + 0.1 * ola, 3); can["barrido_r"] = round(0.25 * max(-1.0, min(1.0, av_)) - 0.1 * ola, 3)
                can["fluke_lado"] = round(-0.3 * giro_, 3)
                giro_acro = acrobacia(m, i / FPS, g(f, "turbina"))
                if abs(giro_acro) > 0.001: can["spin"] = giro_acro; can["roll"] = 0.0   # her acrobatics: side, upside down, barrel rolls (absolute roll through the receiver's spin path)
                pk["canales"] = can;   # calm follows calm (mostly her behaviour); diving and surfacing lean on theirs pk["espacio"] = 0 if a.quieta else 1; pk["blink"] = 1.0 if g(f, "cara_parpado") > 0.5 else 0.0
                if "pulso" in C and np.isfinite(cuerpo[f, C["pulso"]]) and cuerpo[f, C["pulso"]] > 0.3: pk["emotibit_hr"] = round(100.0 * g(f, "pulso"), 1)
            else:
                pk.update({c: round(g(f, c), 4) for c in h.CUERPO})
            if a.etiqueta: pk["bailarin"] = a.etiqueta
            s.sendto(json.dumps(pk).encode(), ("127.0.0.1", a.puerto))
            if a.segundos and time.time() - T_INICIO >= a.segundos: sys.exit(0)
            if i % 30 == 0: json.dump({"tramo": "jepa:" + m, "modo": "cuerpo", "t": int(i / FPS), "dur": 32, "loop": True, "hora": time.time()}, open("/tmp/ballena_reproduciendo.json", "w"))
            esp = t0 + (i + 1) / FPS - time.time()
            if esp > 0: time.sleep(esp)
