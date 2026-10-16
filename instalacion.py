#!/usr/bin/env python3
"""instalacion.py - arranca Yakumama como instalacion (Barcelona): camara + Blender + panel, SIN EmotiBit.

    python instalacion.py                       Mac, Windows o Linux
    python instalacion.py --espejo 192.168.1.50:9998   ademas manda cada paquete a la ballena fisica / TouchDesigner
    python instalacion.py --sin-blender         solo el grabador (si Blender ya esta abierto con whale.blend)

Que hace: abre Blender con whale.blend y el receptor cargado, y el grabador en modo visitas (reconoce el animo y el
parecido de quien se sienta, guarda cada encuentro, recuerda a la gente). El pulso y la piel los pone la red con el
estilo de la persona a la que se parece la visita: no hace falta ningun sensor en la muneca.

Rutas: este archivo vive en la carpeta Yakumama; whale.blend y ballena3.py en la carpeta Huk al lado (o --huk ruta).
Blender: se busca en los lugares habituales, o --blender ruta/al/ejecutable.
"""
import os, sys, subprocess, argparse, time, shutil, platform, webbrowser
AQUI = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--huk", default="", help="carpeta con whale.blend y ballena3.py (por defecto ../Huk o ~/Desktop/Huk)")
ap.add_argument("--blender", default="", help="ejecutable de Blender")
ap.add_argument("--espejo", action="append", default=[], help="host:puerto que recibe una copia de cada paquete")
ap.add_argument("--sin-blender", action="store_true"); ap.add_argument("--panel", type=int, default=8765)
ap.add_argument("--con-emotibit", action="store_true", help="si en algun lugar si hay EmotiBit")
a = ap.parse_args()
HUK = a.huk or next((d for d in (os.path.join(os.path.dirname(AQUI), "Huk"), os.path.expanduser("~/Desktop/Huk")) if os.path.exists(os.path.join(d, "whale.blend"))), "")
if not HUK: sys.exit("no encuentro whale.blend: pasa --huk <carpeta con whale.blend y ballena3.py>")
def buscar_blender():
    if a.blender: return a.blender
    s = platform.system(); cands = []
    if s == "Darwin": cands = ["/Applications/Blender.app/Contents/MacOS/Blender"]
    elif s == "Windows":
        base = r"C:\Program Files\Blender Foundation"
        if os.path.isdir(base): cands = [os.path.join(base, d, "blender.exe") for d in sorted(os.listdir(base), reverse=True)]
    cands += [shutil.which("blender") or ""]
    return next((c for c in cands if c and os.path.exists(c)), "")
py = sys.executable
venv = os.path.join(AQUI, "venv", "Scripts" if platform.system() == "Windows" else "bin", "python" + (".exe" if platform.system() == "Windows" else ""))
if os.path.exists(venv): py = venv
if not a.sin_blender:
    bl = buscar_blender()
    if not bl: print("   (no encuentro Blender: abrilo a mano con whale.blend; el add-on carga el receptor solo)")
    else:
        print(f">>> Blender: {bl}"); subprocess.Popen([bl, os.path.join(HUK, "whale.blend"), "--python", os.path.join(AQUI, "receptor_ballena.py")])
        time.sleep(3)
cmd = [py, os.path.join(AQUI, "grabar_ballena.py"), "--panel", str(a.panel), "--visitas", "1", "--script", os.path.join(HUK, "ballena3.py")]
if not a.con_emotibit: cmd += ["--emotibit", "0", "--emotibit-directo", "0"]
for e in a.espejo: cmd += ["--espejo", e]
print(">>> grabador en modo instalacion:", " ".join(cmd[1:]))
def abrir_panel():
    time.sleep(6)
    try: webbrowser.open(f"http://localhost:{a.panel}")
    except Exception: pass
import threading; threading.Thread(target=abrir_panel, daemon=True).start()
os.chdir(AQUI); sys.exit(subprocess.call(cmd))
