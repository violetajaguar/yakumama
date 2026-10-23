#!/usr/bin/env python3
"""puente_blender.py - her brain's body, rendered in Blender (20 Oct 2026, Violeta: "the 29 in Blender").
Listens to a mirror of cerebro_ballena.py's packets (--salida 127.0.0.1:9996) and hands each one to receptor_ballena.py (UDP 9998, whale.blend)
as the "canales" body the receiver already renders link by link (its dance-back path): pitch, roll, yaw, head, spine, fluke, flap, ladeo, jaw,
face, gaze, spin, depth, both fins and the tail. Her mood goes along through /tmp/ballena_animo_blender.json so Blender's colour follows.
Position and heading go too (x, y, z, rumbo), so her flights and choreography show in Blender. Stop it and Blender returns to its own behaviours within 3 s.
    venv/bin/python puente_blender.py [--entrada 9996] [--blender 127.0.0.1:9998]"""
import socket, json, time, argparse, os
ap = argparse.ArgumentParser(); ap.add_argument("--entrada", type=int, default=9996); ap.add_argument("--blender", default="127.0.0.1:9998"); a = ap.parse_args()
h, p = a.blender.rsplit(":", 1); DEST = (h, int(p))
rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); rx.bind(("127.0.0.1", a.entrada)); rx.settimeout(1.0)
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); n = 0; t_an = 0.0; t_dicho = time.time()
print(f"   puente a Blender: su cerebro ({a.entrada}) -> canales -> receptor ({a.blender})", flush=True)
while True:
    try: b, _ = rx.recvfrom(65535)
    except socket.timeout: continue
    try: pk = json.loads(b)
    except Exception: continue
    c = {"pitch": pk.get("pitch", 0), "roll": pk.get("roll", 0), "yaw": pk.get("giro", 0), "head": pk.get("head", 0), "spine": pk.get("spine") or [0] * 6,
         "fluke": pk.get("fluke", 0), "flap": pk.get("flap", 0), "ladeo": pk.get("ladeo", 0), "jaw": pk.get("jaw", 0), "cara": pk.get("cara") or [0, 0, 0, 0],
         "mirada": pk.get("mirada") or [0, 0], "spin": pk.get("spin", 0), "depth": pk.get("depth", 0)}
    for k in ("aleta_l", "aleta_r"):
        if isinstance(pk.get(k), list): c[k] = pk[k]
    for k_, k2 in (("x", "x"), ("y", "y"), ("z", "z"), ("yaw", "rumbo")):   # 21 Oct: her place in space too (same stage units as the receiver's canales), so a flight is a flight in Blender
        if isinstance(pk.get(k_), (int, float)): c[k2] = float(pk[k_])
    tv = pk.get("turbina_viva") if pk.get("turbina_viva") is not None else pk.get("turbina")
    if isinstance(tv, (int, float)): c["turbina"] = float(tv)
    tx.sendto(json.dumps({"canales": c, "bailarin": 1, "cerebro_animo": pk.get("animo"), "reaccion_n": (pk.get("reaccion") or {}).get("n") if isinstance(pk.get("reaccion"), dict) else pk.get("reaccion")}).encode(), DEST); n += 1
    now = time.time()
    if now - t_an > 0.5 and pk.get("animo"):
        t_an = now
        try: json.dump({"animo": pk["animo"], "t": now}, open("/tmp/ballena_animo_blender.json", "w"))
        except Exception: pass
    if now - t_dicho > 30: t_dicho = now; print(f"   {n} packets -> Blender | mood {pk.get('animo')} | reaction {pk.get('reaccion') and (pk['reaccion'].get('n') if isinstance(pk['reaccion'], dict) else pk['reaccion'])}", flush=True)
