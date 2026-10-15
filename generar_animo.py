#!/usr/bin/env python3
"""generar_animo.py - la ballena ACTUA un animo sola, con lo que aprendio del actor (modelos/movimiento.pt).

    venv/bin/python generar_animo.py playful              # 60 s de playful a Blender (UDP 9998), anclada
    venv/bin/python generar_animo.py sad --segundos 30 --modo cuerpo
    venv/bin/python generar_animo.py --todos               # los diez seguidos, 30 s cada uno

Manda a 30 cuadros/s los canales del actor que la red genera (cabeza, boca, parpadeo, cejas, mirada, manos, pulso,
piel) + actor_animo, igual que si el actor estuviera: el receptor pone el cuerpo del comportamiento NOAA y encima
la cara y las manos aprendidas. Escribe /tmp/ballena_reproduciendo.json para el panel de Blender.
"""
import os, sys, json, time, socket, argparse, math, numpy as np, torch
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from entrenar_movimiento import Red, entrada, MOODS, SALIDAS, PERIODOS
ap = argparse.ArgumentParser(); ap.add_argument("animo", nargs="?", default=None); ap.add_argument("--segundos", type=float, default=60); ap.add_argument("--modo", default="anclada", choices=["anclada", "cuerpo", "cara"])
ap.add_argument("--todos", action="store_true"); ap.add_argument("--puerto", type=int, default=9998); ap.add_argument("--seco", action="store_true", help="no manda: imprime estadisticas por animo")
ap.add_argument("--espejo", action="append", default=[], help="host:puerto que recibe una copia (TouchDesigner / ballena fisica)")
ap.add_argument("--actor", default="promedio", help="con el estilo de quien: un actor grabado (violeta, sanam, suri, dan...) o 'promedio'")
a = ap.parse_args()
m = torch.load(os.path.join(AQUI, "modelos", "movimiento.pt"), map_location="cpu", weights_only=False)
red = Red(m["n_in"], m["n_out"]); red.load_state_dict(m["estado"]); red.eval()
ACTORES = list(m.get("actores", [])); ACTOR = a.actor if a.actor in ACTORES else None   # None = promedio
if a.actor not in ACTORES and a.actor != "promedio": print(f"   (actor '{a.actor}' no esta en el modelo {ACTORES}: uso el promedio)")
_hr = m.get("hr_animo") or {}
def hr_ancla(animo):
    """pulso mediano del actor elegido en ese animo (o la media de todos los actores)"""
    vals = [_hr[ACTOR][animo]] if ACTOR and _hr.get(ACTOR, {}).get(animo) else [d[animo] for d in _hr.values() if d.get(animo)]
    return float(np.mean(vals)) if vals else None
flags = {"anclada": {"anclada": 1}, "cuerpo": {}, "cara": {"solo_cara": 1}}[a.modo]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
HR_ANIMO = {"calm": 84, "singing": 88, "playful": 86, "curious": 89, "feeding": 118, "sad": 101, "angry": 87, "alert": 102, "diving": 57, "surfacing": 78}   # medianas medidas al actor
def generar(animo, segundos, dur_ref=120.0):
    ai = MOODS.index(animo); ancla = hr_ancla(animo) or HR_ANIMO[animo]; hr_prev = float(ancla); t0 = time.time(); ult = 0.0; salida = []; ult_parpadeo = -9.0; prox = 3.0
    for i in range(int(segundos * 30)):
        t = i / 30.0
        with torch.no_grad(): y = red(torch.tensor([entrada(ai, t % dur_ref, dur_ref, hr_prev, ACTOR, ACTORES)], dtype=torch.float32))[0].numpy()
        v = dict(zip(SALIDAS, [float(x) for x in y]))
        hr = max(ancla - 15, min(ancla + 20, 85.0 + 30.0 * v["hr"]))   # la red modula alrededor del pulso medido del actor en ese animo
        blink = 1.0 if v["blink"] > 0.6 else 0.0
        if t - ult_parpadeo > prox: blink = 1.0   # parpadeo forzado cada 3-5 s si la red no lo da
        if blink and t - ult_parpadeo > 1.5: ult_parpadeo = t; prox = 3.0 + (hash((animo, i)) % 20) / 10.0   # nunca mas de uno cada 1.5 s
        pkt = {"head_yaw": max(-1, min(1, v["head_yaw"])), "head_pitch": max(-1, min(1, v["head_pitch"])), "jaw_open": max(0, min(1, v["jaw_open"])), "blink": 1.0 if (t - ult_parpadeo) < 0.17 else 0.0,
               "brow_up": max(0, min(1, v["brow_up"])), "brow_down": max(0, min(1, v["brow_down"])), "mouth_sad": max(0, min(1, v["mouth_sad"])), "mouth_smile": max(0, min(1, v["mouth_smile"])),
               "eye_yaw": max(-1, min(1, v["eye_yaw"])), "eye_pitch": max(-1, min(1, v["eye_pitch"])), "emotibit_hr": round(max(40, min(180, hr)), 1), "emotibit_eda": round(max(0.2, v["eda"] * 10), 2),
               "actor_animo": animo, "soltar_manual": 1 if i < 30 else 0, "water": 0.8, **flags}
        if v["mano_l"] > 0.5: pkt["l_palm_y"] = max(0, min(1, v["l_palm_y"])); pkt["l_palm_x"] = max(0, min(1, v["l_palm_x"]))
        if v["mano_r"] > 0.5: pkt["r_palm_y"] = max(0, min(1, v["r_palm_y"])); pkt["r_palm_x"] = max(0, min(1, v["r_palm_x"]))
        salida.append(pkt)
        if a.seco: continue
        if time.time() - ult > 1.0:
            ult = time.time(); json.dump({"tramo": f"red:{animo}", "modo": a.modo, "t": round(t), "dur": round(segundos), "loop": False, "hora": time.time()}, open("/tmp/ballena_reproduciendo.json", "w"))
        datos_pkt = json.dumps(pkt).encode(); s.sendto(datos_pkt, ("127.0.0.1", a.puerto))
        for e in a.espejo:
            try: h, pt = e.rsplit(":", 1); s.sendto(datos_pkt, (h, int(pt)))
            except Exception: pass
        espera = t0 + t - time.time()
        if espera > 0: time.sleep(espera)
    return salida
try:
    animos = MOODS if a.todos else [a.animo or "calm"]
    for an in animos:
        if an not in MOODS: sys.exit(f"animo desconocido: {an}")
        if not a.seco: print(f"la ballena actua {an} ({a.segundos:.0f} s, {a.modo})", flush=True)
        out = generar(an, a.segundos if not a.seco else 20)
        if a.seco:
            import statistics as st
            print(f"{an:10s} jaw med {st.median(p['jaw_open'] for p in out):.2f} max {max(p['jaw_open'] for p in out):.2f} | smile {st.median(p['mouth_smile'] for p in out):.2f} | brow {st.median(p['brow_up'] for p in out):.2f} | parpadeos {sum(1 for x, y in zip(out, out[1:]) if y['blink'] > x['blink'])} | manos {sum('l_palm_y' in p or 'r_palm_y' in p for p in out)/len(out):.0%} | hr {st.median(p['emotibit_hr'] for p in out):.0f} | yaw var {st.pstdev(p['head_yaw'] for p in out):.2f}")
finally:
    try: os.remove("/tmp/ballena_reproduciendo.json")
    except Exception: pass
