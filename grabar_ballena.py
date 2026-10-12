#!/usr/bin/env python3
"""grabar_ballena.py - datasets de cara y de cuerpo de Yakumama, grabados mientras actuas, como con la llama.

Se corre EN LUGAR de `python ballena3.py`: lo arranca el mismo (sin modificarlo), deja pasar todos los paquetes a
Blender (UDP 9998) tal cual, y guarda una copia de cada paquete etiquetada con el estado de animo que escribas en
esta terminal. Dos archivos por tramo, con el mismo nombre:
    datasets/cara/<animo>_NNN.jsonl     head_yaw, head_pitch, jaw_open, blink, brow_up, brow_down, mouth_sad, ...
    datasets/cuerpo/<animo>_NNN.jsonl   water, joy_x/y/btn, temp, humidity, pressure, l_palm_x/y, l_depth, cyber_*, ...
    (lo que no es cara va al cuerpo; nada se pierde: cada linea trae ademas el paquete entero en "todo")

Mejor que el de la llama: no pelea por el puerto con Blender (la llama se enganchaba al 9998), guarda TODO el
paquete y no 23 numeros elegidos a mano, y los animos son los 10 de la ballena (MOOD_KEYS de ballena3.py).

USO
  Terminal 1: Blender con whale.blend y su receptor corriendo (puerto 9998)
  Terminal 2: ollama serve
  Terminal 3: cd ~/Desktop/Yakumama && venv/bin/python grabar_ballena.py      (con la OAK-D enchufada)

EN ESTA TERMINAL (escribir y Enter)
  1-9, 0   elegir animo: 1 calm 2 singing 3 playful 4 curious 5 feeding 6 sad 7 angry 8 alert 9 diving 0 surfacing
  g        grabar / pausar          f   fin del tramo (guarda)          r   resumen          q   guardar y salir
  --prueba  sin OAK-D: manda paquetes sinteticos 5 s para probar que todo se escribe
"""
import os, sys, json, time, socket, threading, runpy, argparse
AQUI = os.path.dirname(os.path.abspath(__file__)); HUK = os.path.expanduser("~/Desktop/Huk")
SAL_CARA = os.path.join(AQUI, "datasets", "cara"); SAL_CUERPO = os.path.join(AQUI, "datasets", "cuerpo")
os.makedirs(SAL_CARA, exist_ok=True); os.makedirs(SAL_CUERPO, exist_ok=True)
ANIMOS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
TECLAS = "1234567890"
CARA = ("head_yaw", "head_pitch", "head_roll", "jaw_open", "blink", "blink_l", "blink_r", "brow_up", "brow_down",
        "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch", "tongue_out", "asombrado", "angry", "sad", "parpadeo")
PUERTO_BLENDER = 9998
ap = argparse.ArgumentParser(); ap.add_argument("--prueba", action="store_true"); ap.add_argument("--script", default=os.path.join(HUK, "ballena3.py"))
a = ap.parse_args()

estado = {"animo": None, "grabando": False, "cara": [], "cuerpo": [], "t0": time.time(), "n": {}}
lock = threading.Lock()

def guardar():
    with lock:
        if not estado["animo"] or not estado["cara"]: estado["cara"] = []; estado["cuerpo"] = []; return
        an = estado["animo"]; k = len([f for f in os.listdir(SAL_CARA) if f.startswith(an + "_")]) + 1
        for carpeta, recs in ((SAL_CARA, estado["cara"]), (SAL_CUERPO, estado["cuerpo"])):
            with open(os.path.join(carpeta, f"{an}_{k:03d}.jsonl"), "w") as fh:
                for r in recs: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        n = len(estado["cara"]); estado["n"][an] = estado["n"].get(an, 0) + n
        print(f"\n   guardado {an}_{k:03d}.jsonl en cara/ y cuerpo/ ({n} paquetes, {n/30:.0f} s)")
        estado["cara"] = []; estado["cuerpo"] = []

def resumen():
    print("\n   animo        segundos (esta sesion / total en disco)")
    for an in ANIMOS:
        tot = sum(sum(1 for _ in open(os.path.join(SAL_CARA, f), errors="ignore")) for f in os.listdir(SAL_CARA) if f.startswith(an + "_")) / 30
        print(f"   {an:10s} {estado['n'].get(an, 0)/30:6.0f} / {tot:5.0f}  {'ok' if tot >= 60 else '..'}")

def registrar(pkt):
    """cada paquete que ballena3 manda a Blender pasa por aqui (copia)."""
    if not (estado["grabando"] and estado["animo"]): return
    t = round(time.time() - estado["t0"], 3)
    cara = {k: pkt[k] for k in pkt if k in CARA or k.startswith("face_")}
    cuerpo = {k: pkt[k] for k in pkt if k not in cara and k not in ("t", "mocap_mode")}
    with lock:
        estado["cara"].append({"t": t, "animo": estado["animo"], **cara, "todo": pkt})
        estado["cuerpo"].append({"t": t, "animo": estado["animo"], **cuerpo})

# --- el tee: socket.sendto hacia 9998 sigue llegando a Blender y ademas se copia aqui
_sendto = socket.socket.sendto
def sendto_tee(self, data, *args):
    try:
        dest = args[-1]
        if isinstance(dest, tuple) and dest[1] == PUERTO_BLENDER:
            try: registrar(json.loads(data.decode()))
            except Exception: pass
    except Exception: pass
    return _sendto(self, data, *args)
socket.socket.sendto = sendto_tee

def teclado():
    print(__doc__.split("EN ESTA TERMINAL")[1])
    for linea in sys.stdin:
        c = linea.strip().lower()
        if not c: continue
        if c in TECLAS:
            if estado["cara"]: guardar()
            estado["animo"] = ANIMOS[TECLAS.index(c)]; print(f"   animo: {estado['animo']}  ({'grabando' if estado['grabando'] else 'pausa: g para grabar'})")
        elif c == "g": estado["grabando"] = not estado["grabando"]; print("   GRABANDO" if estado["grabando"] else "   pausa")
        elif c == "f": guardar(); estado["grabando"] = False
        elif c == "r": resumen()
        elif c == "q": guardar(); resumen(); os._exit(0)
threading.Thread(target=teclado, daemon=True).start()

if a.prueba:
    import math, random
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    estado["animo"] = "calm"; estado["grabando"] = True; print("   prueba: 5 s de paquetes sinteticos como 'calm'")
    t0 = time.time()
    while time.time() - t0 < 5:
        t = time.time() - t0
        s.sendto(json.dumps({"head_yaw": math.sin(t), "head_pitch": 0.1, "jaw_open": abs(math.sin(3 * t)), "blink": 0.0, "brow_up": 0.2, "brow_down": 0.0, "mouth_sad": 0.1,
                             "water": 0.5 + 0.5 * math.sin(t / 2), "joy_x": random.uniform(-1, 1), "joy_y": 0.0, "joy_btn": 0, "temp": 21.5, "humidity": 40, "pressure": 1013, "t": time.time()}).encode(), ("127.0.0.1", PUERTO_BLENDER))
        time.sleep(1 / 30)
    guardar(); resumen(); sys.exit(0)

print(f">>> arrancando {a.script} con el grabador enganchado (Blender sigue recibiendo en {PUERTO_BLENDER})")
sys.argv = [a.script]; os.chdir(HUK)
runpy.run_path(a.script, run_name="__main__")
