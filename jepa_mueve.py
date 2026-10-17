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
ap.add_argument("--quieta", action="store_true"); ap.add_argument("--puerto", type=int, default=9998); a = ap.parse_args()
ruta = a.modelo or (os.path.join(AQUI, "modelos", "hjepa_ballena.pt") if os.path.exists(os.path.join(AQUI, "modelos", "hjepa_ballena.pt")) else os.path.join(AQUI, "modelos", "hjepa.pt"))
h = HJepa(ruta); ESPACIO_BALLENA = "pitch" in h.CUERPO; moods = [m for m in a.animos if m in h.ACCIONES] or ([a.animo] if a.animo else h.ACCIONES[:10])
print(f"   model {os.path.basename(ruta)}: {len(h.CUERPO)} channels, {'HER BODY SPACE' if ESPACIO_BALLENA else 'six body qualities'}")
if a.semilla:   # a real body as context
    from retarget_ballena import esqueleto_a_ballena, CANALES_BALLENA, cargar_toma; from cuerpo_cualidades import cargar_npz, cualidades_toma
    if a.semilla.endswith(".npz"): B, J, fps = cargar_npz(a.semilla)
    else: B, J, fps, _, _ = cargar_toma(a.semilla)
    if ESPACIO_BALLENA: X = esqueleto_a_ballena(B, J, fps); filas = [{c: (None if not np.isfinite(v) else float(v)) for c, v in zip(CANALES_BALLENA, r)} for r in X]
    else: q = cualidades_toma(B, J, fps); filas = [{c: (None if not np.isfinite(q[c][i]) else float(q[c][i])) for c in h.CUERPO} for i in range(len(B))]
    paso = max(1, int(round(fps / h.fps)))
    for fr in filas[-h.largo * paso::paso]: h.empujar(fr)
    print(f"   context: last 32 s of {os.path.basename(a.semilla)} | body reads {h.leer().get('animo_cuerpo')}")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); FPS = 30.0; C = {c: i for i, c in enumerate(h.CUERPO)}
px = py_ = 0.0; rumbo = math.pi; ESCALA_PISO = 0.8; RADIO_MAX = 2.0
while True:
    for m in moods:
        if a.semilla and h.n >= h.largo: cuerpo, ams = h.continuar(m, ruido=a.ruido)
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
                    dt = 1.0 / FPS; rumbo += g(f, "giro") * dt; av, de = g(f, "avance") * ESCALA_PISO, g(f, "deriva") * ESCALA_PISO
                    px += (av * math.sin(rumbo) + de * math.cos(rumbo)) * dt; py_ += (av * math.cos(rumbo) - de * math.sin(rumbo)) * dt; r_ = math.hypot(px, py_)
                    if r_ > RADIO_MAX: px, py_ = px * RADIO_MAX / r_, py_ * RADIO_MAX / r_
                    can["x"], can["y"], can["z"], can["rumbo"] = round(px, 3), round(py_, 3), 0.0, round((rumbo + math.pi) % (2 * math.pi) - math.pi, 3)
                pk["canales"] = can; pk["espacio"] = 0 if a.quieta else 1; pk["blink"] = 1.0 if g(f, "cara_parpado") > 0.5 else 0.0
                if "pulso" in C and np.isfinite(cuerpo[f, C["pulso"]]) and cuerpo[f, C["pulso"]] > 0.3: pk["emotibit_hr"] = round(100.0 * g(f, "pulso"), 1)
            else:
                pk.update({c: round(g(f, c), 4) for c in h.CUERPO})
            s.sendto(json.dumps(pk).encode(), ("127.0.0.1", a.puerto))
            if i % 30 == 0: json.dump({"tramo": "jepa:" + m, "modo": "cuerpo", "t": int(i / FPS), "dur": 32, "loop": True, "hora": time.time()}, open("/tmp/ballena_reproduciendo.json", "w"))
            esp = t0 + (i + 1) / FPS - time.time()
            if esp > 0: time.sleep(esp)
