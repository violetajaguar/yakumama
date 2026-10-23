#!/usr/bin/env python3
"""ojo_webcam.py - the hand eye on the Mac's own camera (21 Oct 2026, Violeta: "play it to my computer camera and I will show each animal").
Runs ojo_ofrendas.Ojo (the 29 creatures, Sanam's photos) on the laptop camera every ~1 s, votes 2 of 3 like the recorder, and hands the
winner to the recorder's port 9995 as the hand test ({"ofrenda_id": n}) so her brain reacts and Blender/TD show it. A window shows the camera
with the verdict. Nothing is saved.   venv/bin/python ojo_webcam.py [--camara 0] [--puerto 127.0.0.1:9995]   (q closes)"""
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
_tomar_lock("ojo_webcam")
import sys, os, time, json, socket, argparse, collections
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import cv2, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--camara", type=int, default=0); ap.add_argument("--puerto", default="127.0.0.1:9995"); ap.add_argument("--foto", type=int, default=0, help="creature id: s saves a frame into ofrendas_fotos/<carpeta>/, a toggles a burst (2/s)"); a = ap.parse_args()
from ojo_ofrendas import Ojo
import json as _j
CATF = {c["id"]: (c.get("carpeta") or c["archivo"][:-4]) for c in _j.load(open(os.path.join(AQUI, "docs", "ofrendas", "ofrendas.json")))["criaturas"]}
FOTO_DIR = os.path.join(AQUI, "ofrendas_fotos", CATF[a.foto]) if a.foto in CATF else None
if FOTO_DIR: os.makedirs(FOTO_DIR, exist_ok=True); print(f"   fotos: s guarda un cuadro en {os.path.relpath(FOTO_DIR, AQUI)}/, a = ráfaga 2/s", flush=True)
rafaga = False; t_foto = 0.0; n_fotos = 0
ojo = Ojo(); h, p = a.puerto.rsplit(":", 1); DEST = (h, int(p)); sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cap = cv2.VideoCapture(a.camara)
if not cap.isOpened(): sys.exit("   no camera (macOS may be asking for permission for the Terminal / Python)")
print(f"   ojo en la cámara {a.camara}: {len(ojo.clases)} clases -> {a.puerto}  (q cierra)", flush=True)
votos = collections.deque(maxlen=3); t_mira = 0.0; dicho = None; ult_ofrenda = None; t_env = 0.0; v = None
while True:
    ok, bgr = cap.read()
    if not ok: time.sleep(0.05); continue
    now = time.time()
    if now - t_mira >= 1.0:
        t_mira = now
        try: v = ojo.ver(np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
        except Exception as e: v = {"clase": "error", "p": 0.0, "id": None, "nombre": str(e)[:40], "mano": 0}
        votos.append(v); print(f"   mira: {v.get('clase')} p={float(v.get('p') or 0):.2f} mano={v.get('mano')}", flush=True)
        ids = [x.get("id") for x in votos if x.get("id")]
        gana = None
        if ids:
            top = max(set(ids), key=ids.count)
            if ids.count(top) >= 2 or (v.get("id") == top and float(v.get("p") or 0) >= 0.7): gana = top
        if gana and (gana != ult_ofrenda or now - t_env > 3.0):
            sock.sendto(json.dumps({"ofrenda_id": gana, "ofrenda_p": 1.0}).encode(), DEST); t_env = now
            if gana != ult_ofrenda: ult_ofrenda = gana; print(f"   {time.strftime('%H:%M:%S')}  -> ofrenda {gana:02d}  {str(v.get('nombre') or '').split(' (')[0]}", flush=True)
        elif not gana and ult_ofrenda and all(x.get("clase") in ("duda", "manos_vacias", "otras_cosas") for x in votos):
            sock.sendto(json.dumps({"ofrenda": "nada", "ofrenda_p": 0.0}).encode(), DEST); ult_ofrenda = None; print(f"   {time.strftime('%H:%M:%S')}  -> nada", flush=True)
    if v:
        txt = f"{v.get('clase')} p={float(v.get('p') or 0):.2f}" + (f"  -> {ult_ofrenda:02d}" if ult_ofrenda else "")
        cv2.rectangle(bgr, (0, 0), (bgr.shape[1], 34), (0, 0, 0), -1); cv2.putText(bgr, txt, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (90, 220, 255), 2, cv2.LINE_AA)
    cv2.imshow("Yakumama - ojo en la camara de la Mac (q cierra)", bgr)
    k = cv2.waitKey(10) & 0xFF
    if k == ord("q"): break
    if FOTO_DIR and (k == ord("s") or (rafaga and now - t_foto >= 0.5)):
        t_foto = now; n_fotos += 1; f = os.path.join(FOTO_DIR, f"webcam_{time.strftime('%Y%m%d_%H%M%S')}_{n_fotos:03d}.jpg"); cv2.imwrite(f, bgr); print(f"   foto {n_fotos}: {os.path.basename(f)}", flush=True)
    if FOTO_DIR and k == ord("a"): rafaga = not rafaga; print(f"   ráfaga {'ON' if rafaga else 'OFF'}", flush=True)
cap.release(); cv2.destroyAllWindows()
