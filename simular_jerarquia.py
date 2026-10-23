#!/usr/bin/env python3
"""simular_jerarquia.py - the hierarchy, acted out (20 Oct 2026): the sister's senses sent by hand on the recorder's port 9995, in phases, while you
watch the salar, her window (/ventana) and the offerings screen (:8766). Prints what her brain does every 2 s (/tmp/ballena_cerebro.json).
Phases: alone -> offering 29 -> a gentle touch on the flowers DURING the scene (cosquillas interrupt, then the scene resumes) -> offering 14
replaces it -> a palm pressed over the flowers (fixed refusal) -> a gentle flower touch (forgiveness) -> a pull on the jewel (refusal) ->
something that is not a fish in the mouth (refusal) -> the joystick camera -> alone again.      venv/bin/python simular_jerarquia.py"""
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
_tomar_lock("simular_jerarquia")
import socket, json, time
S = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); DEST = ("127.0.0.1", 9995)
def manda(**kv): S.sendto(json.dumps(kv).encode(), DEST)
def cerebro():
    try: return json.load(open("/tmp/ballena_cerebro.json"))
    except Exception: return {}
def fase(titulo, segundos, cada_seg=None):
    print(f"\n=== {titulo}  ({segundos:.0f} s)", flush=True); t0 = time.time(); ult = -9
    while time.time() - t0 < segundos:
        if cada_seg: cada_seg()
        if time.time() - t0 - ult >= 2.0:
            ult = time.time() - t0; c = cerebro(); d = c.get("decision") or {}; rv = c.get("reaccion_viva") or {}
            print(f"   {ult:4.0f} s  ánimo {str(c.get('animo')):9s} | ofrenda {str(c.get('ofrenda_id') or '-'):>2s} reacción {str(rv.get('n') or '-'):>2s} fase {rv.get('fase', '-')} | "
                  f"rechazo {c.get('fijo') or '-':6s} | tacto {c.get('tacto') or 0:.2f} {c.get('tacto_zona') or '-':7s} | va: {d.get('distancia','-')} · {d.get('con_cuerpo','-')} · boca {d.get('boca','-')}", flush=True)
        time.sleep(1.0)
fase("1 · SOLA: el repertorio base (inventa, coreografía)", 16)
fase("2 · OFRENDA 29 (pez azul cola rosada): reacción 13, se come bailando — escena de 30 s", 14, lambda: manda(ofrenda_id=29, ofrenda_p=1.0))
fase("3 · COSQUILLAS durante la escena: una mano suave en sus flores — interrumpe todo mientras dura", 6, lambda: (manda(ofrenda_id=29, ofrenda_p=1.0), manda(flores=[0.6, 0.2, 0.0])))
manda(flores=[0.0, 0.0, 0.0])
fase("4 · suelta las flores: la escena de la 29 sigue donde iba", 8, lambda: manda(ofrenda_id=29, ofrenda_p=1.0))
fase("5 · OFRENDA 14 (escorpión) llega: reemplaza a la 29 — reacción 15, se asusta y va hacia atrás", 14, lambda: manda(ofrenda_id=14, ofrenda_p=1.0))
fase("6 · PALMA sobre las flores: rechazo fijo (sad, cola parada, color apagado); corta la escena", 6, lambda: manda(flores=[0.95, 0.95, 0.95]))
manda(flores=[0.0, 0.0, 0.0]); manda(ofrenda="nada", ofrenda_p=0.0)
fase("7 · suelta: vuelve al repertorio", 8)
fase("8 · toque suave en una flor: perdón, calma", 6, lambda: manda(flores=[0.5, 0.0, 0.0]))
manda(flores=[0.0, 0.0, 0.0])
fase("9 · TIRÓN de la joya: rechazo fijo (angry)", 5, lambda: manda(joya=0.9, joya_tiron=1))
manda(joya=0.0, joya_tiron=0)
fase("10 · suelta la joya", 6)
fase("11 · algo que NO es un pez en la boca: rechazo (alert, rehúsa)", 8, lambda: manda(ofrenda="no_pez", ofrenda_p=1.0))
manda(ofrenda="nada", ofrenda_p=0.0)
fase("12 · la PALANCA mueve la cámara, ella en cuadro y de cerca: se queda, invita", 10, lambda: manda(camara={"cerca": 0.9, "mira": 1}, palanca=1))
manda(camara={"cerca": 0.4, "mira": 1}, palanca=0)
fase("13 · SOLA de nuevo: el repertorio (y a los 2 min, dibuja)", 14)
print("\n=== fin de la simulación", flush=True)
