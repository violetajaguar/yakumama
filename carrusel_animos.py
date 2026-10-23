#!/usr/bin/env python3
"""carrusel_animos.py - her 10 moods one after another, on the invented body (20 Oct 2026): writes /tmp/ballena_animo_prueba.json every
second so cerebro_ballena.py holds that mood; prints what her brain reports. Watch TouchDesigner and her window.
    venv/bin/python carrusel_animos.py                 the ten, 30 s each
    venv/bin/python carrusel_animos.py sad angry 20    only these, 20 s each (a trailing number = seconds)"""
import os as _os, sys as _sys, atexit as _atexit, signal as _signal, json as _json, socket as _socket
_LOCK = "/tmp/ballena_prueba.lock"
def _tomar_lock(nombre):
    try:
        pid = int(open(_LOCK).read().split()[0]); _os.kill(pid, 0)
        _sys.exit(f"   otra prueba ya está corriendo (pid {pid}, {open(_LOCK).read().strip()}): párala primero (kill -TERM {pid}). Dos fuentes de ofrendas pelean por su boca.")
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError): pass
    open(_LOCK, "w").write(f"{_os.getpid()} {nombre}")
    def _limpiar(*a):
        try: _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM).sendto(_json.dumps({"ofrenda": "nada", "ofrenda_p": 0.0}).encode(), ("127.0.0.1", 9995))
        except Exception: pass
        try: _os.remove(_LOCK)
        except OSError: pass
        try: _os.remove("/tmp/ballena_animo_prueba.json")
        except OSError: pass
        if a: _sys.exit(0)
    _atexit.register(_limpiar); _signal.signal(_signal.SIGTERM, _limpiar); _signal.signal(_signal.SIGINT, _limpiar)
_tomar_lock("carrusel_animos")
import json, sys, time, os
MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
NOMBRES = {"calm": "logging · quieta en la superficie", "singing": "canto", "playful": "breach · salta", "curious": "spyhop · asoma la cabeza", "feeding": "lunge · embestida con la boca abierta",
           "sad": "hundida", "angry": "lobtail · golpea con la cola", "alert": "escaneo · vigila", "diving": "buceo · se hunde", "surfacing": "soplo · sube y respira"}
args = sys.argv[1:]; segs = 30.0
if args and args[-1].replace(".", "").isdigit(): segs = float(args.pop())
orden = [m for m in args if m in MOODS] or MOODS
F = "/tmp/ballena_animo_prueba.json"
def cerebro():
    try: return json.load(open("/tmp/ballena_cerebro.json"))
    except Exception: return {}
print(f"   carrusel de ánimos: {' → '.join(orden)}, {segs:.0f} s cada uno", flush=True)
try:
    for m in orden:
        print(f"\n{m.upper():10s} {NOMBRES[m]}", flush=True); t0 = time.time(); vistos = []
        while time.time() - t0 < segs:
            json.dump({"animo": m, "t": time.time()}, open(F, "w")); time.sleep(1.0)
            a = cerebro().get("animo")
            if a and (not vistos or vistos[-1] != a): vistos.append(a)
        print(f"   su cerebro: {' → '.join(vistos) or '-'}", flush=True)
finally:
    try: os.remove(F)
    except OSError: pass
print("\n   carrusel de ánimos terminado", flush=True)
