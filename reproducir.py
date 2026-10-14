#!/usr/bin/env python3
"""reproducir.py - manda un tramo grabado a Blender (UDP 9998) con su tiempo original, para ver como queda en la ballena.

    venv/bin/python reproducir.py playful_001                 # modo solo cara (cuerpo quieto, cabeza sigue)
    venv/bin/python reproducir.py playful_001 --modo anclada  # cuerpo entero, sin viajar
    venv/bin/python reproducir.py playful_001 --modo cuerpo --velocidad 2 --loop

modos: cara (solo_cara 1) | fija (solo_cara 2) | cuerpo | anclada. Ctrl-C para parar.
Antes: cerrar el grabador (q) para que no manden los dos a la vez. Blender con receptor_ballena.py corriendo.
"""
import os, sys, json, time, socket, argparse
AQUI = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("tramo", help="p. ej. playful_001"); ap.add_argument("--modo", default="cara", choices=["cara", "fija", "cuerpo", "anclada"])
ap.add_argument("--velocidad", type=float, default=1.0); ap.add_argument("--loop", action="store_true"); ap.add_argument("--puerto", type=int, default=9998)
ap.add_argument("--espejo", action="append", default=[], help="host:puerto que recibe una copia (TouchDesigner / ballena fisica)")
a = ap.parse_args()
fc = os.path.join(AQUI, "datasets", "cara", a.tramo + ".jsonl"); fb = os.path.join(AQUI, "datasets", "cuerpo", a.tramo + ".jsonl")
if not os.path.exists(fc): sys.exit(f"no existe {fc}")
cara = [json.loads(l) for l in open(fc)]; cuerpo = [json.loads(l) for l in open(fb)] if os.path.exists(fb) else [{}] * len(cara)
flags = {"cara": {"solo_cara": 1}, "fija": {"solo_cara": 2}, "cuerpo": {}, "anclada": {"anclada": 1}}[a.modo]
flags["actor_animo"] = a.tramo.rsplit("_", 1)[0]   # el animo de la toma manda el comportamiento (cuerpo de las fotos NOAA)
flags["soltar_manual"] = 1                           # al arrancar, el panel vuelve a Automatico (si no, el menu manda sobre la toma)
def clamp(v, lo, hi): return max(lo, min(hi, v))
def mirada(r):
    g = lambda k: float(r.get("face_" + k, 0))
    return (((g("eyeLookInLeft") - g("eyeLookOutLeft")) + (g("eyeLookOutRight") - g("eyeLookInRight"))) / 2,
            ((g("eyeLookUpLeft") + g("eyeLookUpRight")) - (g("eyeLookDownLeft") + g("eyeLookDownRight"))) / 2)
con_bs = [r for r in cara if "face_eyeBlinkLeft" in r]
if con_bs:   # parpadeo con curva y mirada centrada en la mediana del tramo (no hubo neutral de ojos al grabar)
    ys = sorted(mirada(r)[0] for r in con_bs); ps = sorted(mirada(r)[1] for r in con_bs); y0, p0 = ys[len(ys) // 2], ps[len(ps) // 2]
    for r in cara:
        if "face_eyeBlinkLeft" in r:
            r["blink"] = round(clamp((max(r["face_eyeBlinkLeft"], r["face_eyeBlinkRight"]) - 0.55) / 0.3, 0, 1), 4)
            y, p = mirada(r); r["eye_yaw"] = round(clamp((y - y0) * 1.5, -1, 1), 4); r["eye_pitch"] = round(clamp((p - p0) * 1.5, -1, 1), 4)
    print(f"parpadeo y mirada recalculados de los blendshapes (mirada centrada en yaw {y0:+.2f}, pitch {p0:+.2f})")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"{a.tramo}: {len(cara)} cuadros, {cara[-1]['t'] - cara[0]['t']:.0f} s, modo {a.modo}, x{a.velocidad}{' en loop' if a.loop else ''}  (Ctrl-C para parar)")
ESTADO = "/tmp/ballena_reproduciendo.json"; _ult = 0.0
def estado(c):
    global _ult
    if time.time() - _ult < 1.0: return
    _ult = time.time()
    try: json.dump({"tramo": a.tramo, "modo": a.modo, "t": round(c["t"] - cara[0]["t"]), "dur": round(cara[-1]["t"] - cara[0]["t"]), "loop": a.loop, "hora": time.time()}, open(ESTADO, "w"))
    except Exception: pass
try:
    while True:
        t0 = time.time(); tb = cara[0]["t"]
        for c, b in zip(cara, cuerpo):
            estado(c)
            pkt = {**c.get("todo", {}), **{k: v for k, v in b.items() if k not in ("t", "animo", "video_t")}, **{k: v for k, v in c.items() if k not in ("t", "animo", "todo", "video_t")}, **flags}
            espera = (c["t"] - tb) / a.velocidad - (time.time() - t0)
            if espera > 0: time.sleep(min(espera, 0.5))
            datos_pkt = json.dumps(pkt).encode(); s.sendto(datos_pkt, ("127.0.0.1", a.puerto))
            for e in a.espejo:
                try: h, pt = e.rsplit(":", 1); s.sendto(datos_pkt, (h, int(pt)))
                except Exception: pass
        if not a.loop: break
except KeyboardInterrupt: pass
finally:
    try: os.remove(ESTADO)
    except Exception: pass
print("fin")
