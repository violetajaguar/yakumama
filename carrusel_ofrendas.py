#!/usr/bin/env python3
"""carrusel_ofrendas.py - plays the 29 offerings one after another WITHOUT the creatures (20 Oct 2026): the hand test on the recorder's
port 9995 ({"ofrenda": "pez", "ofrenda_id": n}) for each creature, for the length of its reaction (reacciones_ofrendas.TABLA) plus a pause,
and prints what her brain does (/tmp/ballena_cerebro.json). Watch her in TouchDesigner and on http://localhost:8766.
    venv/bin/python carrusel_ofrendas.py              all 29, in order
    venv/bin/python carrusel_ofrendas.py 14 27 8      only these creatures
    venv/bin/python carrusel_ofrendas.py --pausa 12   seconds between creatures (default 8)"""
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
_tomar_lock("carrusel_ofrendas")
import os, sys, json, time, socket, argparse
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from reacciones_ofrendas import REACCIONES, Reacciones
ESCENA = Reacciones.ESCENA_S
CAT = {c["id"]: c for c in json.load(open(os.path.join(AQUI, "docs", "ofrendas", "ofrendas.json")))["criaturas"]}
ap = argparse.ArgumentParser(); ap.add_argument("ids", nargs="*", type=int); ap.add_argument("--pausa", type=float, default=6.0); ap.add_argument("--puerto", default="127.0.0.1:9995")
a = ap.parse_args(); h, p = a.puerto.rsplit(":", 1); DEST = (h, int(p)); sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def cerebro():
    try: return json.load(open("/tmp/ballena_cerebro.json"))
    except Exception: return {}
def manda(**kv): sock.sendto(json.dumps(kv).encode(), DEST)
ids = a.ids or sorted(CAT)
print(f"   carrusel: {len(ids)} ofrendas -> {a.puerto}; cada una dura su reacción + {a.pausa:.0f} s de pausa", flush=True)
for n in ids:
    c = CAT[n]; r = (c.get("reaccion") or {}); rn = r.get("n"); R = REACCIONES.get(rn, {}); dur = max(float(R.get("segundos", 8)), ESCENA) + 1.0   # the whole scene (30 s, Violeta's map)
    print(f"\n{n:02d} {c['nombre'][:60]}\n   reacción {rn}: {R.get('texto', r.get('texto', ''))}  ({R.get('animo', '?')}, {R.get('segundos', '?')} s{', come' if R.get('come') else ''}{', dibuja' if R.get('dibujo') else ''}{', ' + str(R.get('voz')) if R.get('voz') else ''})", flush=True)
    t0 = time.time(); visto = None; animos = []
    while time.time() - t0 < dur:
        manda(ofrenda="pez", ofrenda_p=1.0, ofrenda_id=n)
        time.sleep(1.0); d = cerebro(); rx = d.get("reaccion")
        if rx == rn or (isinstance(rx, dict) and rx.get("n") == rn): visto = visto or round(time.time() - t0, 1)
        if d.get("animo") and (not animos or animos[-1] != d["animo"]): animos.append(d["animo"])
    manda(ofrenda="nada", ofrenda_p=0.0)
    print(f"   {'✓ su cerebro la tomó a los %.1f s' % visto if visto else '✗ su cerebro no empezó la reacción'} | ánimos: {' → '.join(animos) or '-'} | boca: {(cerebro().get('decision') or {}).get('boca')}", flush=True)
    time.sleep(a.pausa)
print("\n   carrusel terminado", flush=True)
