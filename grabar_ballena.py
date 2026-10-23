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

EN ESTA TERMINAL (una tecla, sin Enter)
  1-9, 0   elegir animo: 1 calm 2 singing 3 playful 4 curious 5 feeding 6 sad 7 angry 8 alert 9 diving 0 surfacing
  g        grabar / pausar          f   fin del tramo (guarda)          r   resumen          q   guardar y salir
  c        SOLO CARA (cicla): cuerpo entero -> solo cara (cuerpo quieto, la cabeza sigue la nariz; boca, parpadeo y
           cejas siguen) -> solo cara con CABEZA FIJA (la cabeza no se mueve, solo boca, parpadeo y cejas: para
           ver la cara) -> cuerpo entero. Blender tiene que estar corriendo receptor_ballena.py.
  a        ANCLADA on/off: en modo cuerpo la ballena se mueve (poses, aletas, columna, cabeza) pero no viaja por
           el espacio: ni la mano, ni el joystick, ni el nado automatico mueven su posicion. Para grabar movimiento.
  n        NEUTRAL: mira a la camara con la cara relajada y escribe n; toma 1 s de muestras y desde ahi la cabeza,
           cejas, boca y parpadeo se miden respecto a esa cara (si no, con la camara de costado el yaw queda pegado
           en -1 y la ballena no te sigue). Se aplica a lo que ve Blender y a lo que se graba ("todo" guarda lo crudo).
  Las lineas "yaw:..." de ballena3 se esconden; el grabador muestra su propia linea de estado cada 2 s.
  LENGUA y 52 blendshapes: sobre el mismo cuadro de la OAK-D que ballena3 le da a FaceMesh se corre ademas el
  Face Landmarker (modelos/face_landmarker.task): tongue_out, mouth_smile, blink_l/blink_r (y blink = el mejor de
  los dos, reemplaza al de ballena3) y face_<nombre> con los 52. Van a Blender y a datasets/cara.
  PANEL WEB: http://localhost:8765  (botones grandes y estado en vivo, lo mismo que las teclas)
  t        guarda el cuadro actual de la OAK-D en datasets/_cuadros/ (para afinar la deteccion de la lengua)
  EMOTIBIT DIRECTO: el grabador se conecta solo al EmotiBit por WiFi (emotibit_cliente.py), sin Oscilloscope:
  eda, ppg, temperatura, acelerometro, hr. --emotibit-ip 192.168.50.64 si no lo encuentra solo. Tambien sigue
  aceptando OSC del Oscilloscope en 12345 si lo usas.
  EMOTIBIT (via Oscilloscope): si el EmotiBit Oscilloscope manda OSC (Output > OSC, por defecto a 127.0.0.1:12345), cada linea de
  datasets/cuerpo lleva ademas emotibit_<senal> con el ultimo valor recibido (eda, hr, ppg_red, temp, acc_x, ...:
  el nombre sale de la direccion OSC, "/EmotiBit/0/PPG:RED" -> emotibit_ppg_red). Puerto: --emotibit 12345.
  VIDEO: de g a f se graba la ventana de Blender (screencapture) en datasets/video/<animo>_NNN.mov, mismo nombre
  que el tramo; cada linea de cara y cuerpo lleva "video_t" (segundos desde que arranco el video). La primera vez
  macOS pide permiso de Grabacion de pantalla para la Terminal. Apagado por defecto: --video 1 lo enciende.
  --prueba  sin OAK-D: manda paquetes sinteticos 5 s para probar que todo se escribe
"""
import cv2, os, sys, json, time, socket, threading, runpy, argparse, re, unicodedata
AQUI = os.path.dirname(os.path.abspath(__file__)); HUK = os.path.expanduser("~/Desktop/Huk")
SAL_CARA = os.path.join(AQUI, "datasets", "cara"); SAL_CUERPO = os.path.join(AQUI, "datasets", "cuerpo"); SAL_VIDEO = os.path.join(AQUI, "datasets", "video")
os.makedirs(SAL_CARA, exist_ok=True); os.makedirs(SAL_CUERPO, exist_ok=True); os.makedirs(SAL_VIDEO, exist_ok=True)
ANIMOS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
TECLAS = "1234567890"
CARA = ("head_yaw", "head_pitch", "head_roll", "jaw_open", "blink", "blink_l", "blink_r", "brow_up", "brow_down",
        "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch", "tongue_out", "asombrado", "angry", "sad", "parpadeo")
PUERTO_BLENDER = 9998
PINGPONG_S = 3.0   # seconds: a second creature arriving within this of the last switch is a fight between senders, not a new offering
ap = argparse.ArgumentParser(); ap.add_argument("--prueba", action="store_true"); ap.add_argument("--script", default=os.path.join(HUK, "ballena3.py"))
ap.add_argument("--emotibit", type=int, default=12345, help="puerto OSC donde escucha al EmotiBit Oscilloscope (0 = no)")
ap.add_argument("--emotibit-directo", type=int, default=1, help="1 = conectar directo al EmotiBit por WiFi, sin Oscilloscope (0 = no)")
ap.add_argument("--emotibit-ip", default="", help="IP del EmotiBit (vacio = buscarlo por broadcast)")
ap.add_argument("--panel", type=int, default=8765, help="puerto del panel web (0 = sin panel)")
ap.add_argument("--espejo", action="append", default=[], help="host:puerto que recibe una copia de cada paquete (TouchDesigner, ballena fisica); repetible")
ap.add_argument("--pose", type=int, default=1, help="1 = tambien el cuerpo (MediaPipe Pose): inclinacion, giro, agachado, energia -> cuerpo_* en cada paquete y en cuerpo/")
ap.add_argument("--visitas", type=int, default=1, help="1 = guardar cada encuentro con una visita (datasets/visitas/) y recordarla en datasets/memoria.json; 0 = no")
ap.add_argument("--actor", default="", help="nombre de quien actua; va en el nombre del tramo: <animo>_<actor>_NNN (tambien se cambia en el panel)")
ap.add_argument("--video", type=int, default=0, help="1 = grabar la ventana de Blender de g a f (apagado por defecto)")
ap.add_argument("--voz", type=int, default=1, help="1 = lee cada poema nuevo en voz alta, solo en su lengua (voz_ella via venv_datos); la traduccion se escribe en la ventana")
ap.add_argument("--sonido", type=int, default=1, help="1 = el sonido de cada animo (Huk/whale sound) al cambiar el animo dominante de Blender (afplay)")
ap.add_argument("--musica", type=int, default=0, help="1 = musica de base en bucle, bajito (Huk/whale sound/base); apagada por defecto (Violeta, 18 oct: la de prueba cansa)")
ap.add_argument("--panel-red", type=int, default=1, help="1 = el panel y la ventana (/ventana) se ven desde otras maquinas de la red (http://<esta ip>:8765); 0 = solo esta maquina")
ap.add_argument("--ojo-objeto", type=int, default=1, help="1 = cada 3 s mira que tiene en la mano quien esta enfrente (ojo_ofrendas.Ojo: las 29 ofrendas, manos vacias, otras cosas, hermana; sin modelo, moondream via ollama): ofrenda -> pez + ofrenda_id + reaccion")
ap.add_argument("--ojo-lente", type=int, default=0, help="1 = ademas le pregunta a moondream (ollama local) si hay un lente apuntando; 0 = no (sin ollama no cuesta nada: falla callado)")
a = ap.parse_args()
HUK = os.path.dirname(os.path.abspath(a.script))   # la carpeta de ballena3.py (whale.blend, yakumama_alma): --script la fija en otra maquina

def nombre_actor(x):
    """'Ana María' -> 'anamaria': sin acentos, espacios ni guiones bajos (el _ separa animo, actor y numero)."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower())
# anclada por defecto en modo visita (se mueve, no viaja por el espacio); en sesion con actor, libre
estado = {"auto": {"valencia": None, "activacion": None}, "actor": nombre_actor(a.actor), "animo": None, "grabando": False, "solo_cara": 0, "anclada": not nombre_actor(a.actor), "cara": [], "cuerpo": [], "t0": time.time(), "n": {}, "ultimo": {}, "seg": {}}
def segundos(ts):
    """segundos reales de una lista de tiempos t (sin contar huecos de pausa > 0.5 s). No supone 30 paquetes/s."""
    return sum(b - a for a, b in zip(ts, ts[1:]) if 0 <= b - a < 0.5)
def segundos_archivo(f):
    try: return segundos([json.loads(l)["t"] for l in open(f, errors="ignore") if l.strip()])
    except Exception: return 0.0
lock = threading.Lock()

# --- video de la ventana de Blender, de g a f (screencapture -v; SIGINT cierra el .mov)
import subprocess, signal, shutil
video = {"proc": None, "tmp": None, "t0": None}
def rect_blender():
    """x,y,w,h de la ventana de Blender (None si no esta)."""
    try:
        out = subprocess.run(["osascript", "-e", 'tell application "System Events" to tell process "Blender" to get {position, size} of window 1'],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        x, y, w, h = [int(float(v)) for v in out.split(",")]; return f"{x},{y},{w},{h}"
    except Exception: return None
def video_empezar():
    if not a.video or video["proc"]: return
    r = rect_blender(); tmp = os.path.join(SAL_VIDEO, f"_grabando_{int(time.time())}.mov")
    cmd = ["screencapture", "-v", "-x"] + (["-R", r] if r else []) + [tmp]
    try:   # sin terminal: screencapture -v pone la tty en modo crudo si la tiene, y si muere la deja asi (teclas muertas)
        video["proc"] = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        video["tmp"] = tmp; video["t0"] = time.time()
    except Exception as e: print(f"   (sin video: {e})"); return
    time.sleep(1.0)
    if video["proc"].poll() is not None:   # murio enseguida: casi siempre falta el permiso de Grabacion de pantalla
        video["proc"] = None; video["t0"] = None
        print("   (el video no arranco: dale permiso de Grabacion de pantalla a la Terminal en Ajustes > Privacidad y seguridad, y reinicia la Terminal)"); return
    print(f"   video: {'ventana de Blender ' + r if r else 'pantalla entera (Blender no encontrado)'}")
def video_terminar(destino=None):
    """cierra el video; con destino lo renombra a datasets/video/<animo>_NNN.mov, sin destino lo borra."""
    p = video["proc"]; video["proc"] = None; tmp = video["tmp"]; video["t0"] = None
    if not p: return
    try: p.send_signal(signal.SIGINT); p.wait(timeout=10)
    except Exception:
        try: p.kill()
        except Exception: pass
    if tmp and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
        if destino: shutil.move(tmp, destino); print(f"   video guardado: {os.path.basename(destino)}")
        else: os.remove(tmp)
    elif destino: print("   (el video no se creo: dale permiso de Grabacion de pantalla a la Terminal en Ajustes > Privacidad)")

# --- neutral: la cara relajada del actor, para medir todo respecto a ella
CAL_KEYS = ("head_yaw", "head_pitch", "brow_up", "brow_down", "mouth_sad", "jaw_open", "blink")
cal = {"base": None, "muestras": None}
def clamp(v, lo, hi): return max(lo, min(hi, v))
_parp = {"base": 0.0, "pico": 0.25, "hold": 0, "alto": 0, "t": None, "dt": 0.1}
_pc = {"base": None}
def parpadeo_reiniciar():
    """otra persona: olvidar los niveles de ojos abiertos aprendidos."""
    _parp.update(base=0.0, pico=0.25, hold=0, alto=0, t=None); _pc["base"] = None
def parpadeo(pkt):
    """Dos fuentes, se toma la mayor: el EAR de ballena3 (cada cuadro, debil: 0.1-0.3) y el eyeBlink de MediaPipe
    (blink_bs, mas lento). Cada una se mide sobre el nivel de ojos abiertos de ESTA persona (minimo lento) y ademas
    tiene que saltar un minimo absoluto (EAR 0.2, eyeBlink 0.3): hay caras que abiertas dan eyeBlink 0.5-0.7 y
    oscilan, y con un umbral relativo parpadeaban todo el tiempo. Un cierre se sostiene 0.15 s (en cuadros segun el
    ritmo real: a 10 cuadros/s son 1-2, no 5); un nivel constante (> 1 s) no es parpadeo sino el nuevo nivel de abiertos."""
    if "blink" not in pkt: return pkt
    ahora = time.time()
    if _parp["t"]: _parp["dt"] = 0.9 * _parp["dt"] + 0.1 * min(0.5, ahora - _parp["t"])
    _parp["t"] = ahora; fps = 1.0 / max(0.01, _parp["dt"])
    b = float(pkt["blink"])
    _parp["base"] = min(b, _parp["base"] + 0.002)                      # ojos abiertos: sube despacio, baja al toque
    _parp["pico"] = max(_parp["pico"] * 0.998, b, _parp["base"] + 0.2)    # pico reciente, al menos 0.2 sobre la base
    n = clamp((b - _parp["base"]) / (_parp["pico"] - _parp["base"]), 0, 1) if b - _parp["base"] >= 0.2 else 0.0
    bs = None
    if "blink_bs" in pkt:
        bs = float(pkt["blink_bs"]); _pc["base"] = bs if _pc["base"] is None else min(bs, _pc["base"] + 0.002)
        if bs - _pc["base"] >= 0.3: n = max(n, clamp((bs - _pc["base"]) / max(0.3, 0.9 - _pc["base"]), 0, 1))
    _parp["alto"] = _parp["alto"] + 1 if n > 0.5 else 0      # cuadros seguidos "cerrado"
    if _parp["alto"] == 1: _parp["hold"] = max(1, round(0.15 * fps))   # arranca un cierre: se sostiene 0.15 s
    if _parp["alto"] > max(3, round(1.0 * fps)):                # sigue cerrado mas de 1 s: nuevo nivel de abiertos
        _parp["base"] = b; _parp["pico"] = b + 0.2; _parp["alto"] = 0; _parp["hold"] = 0; n = 0.0
        if bs is not None: _pc["base"] = bs
    if _parp["hold"] > 0: _parp["hold"] -= 1; n = 1.0
    return {**pkt, "blink": round(n, 4)}
def calibrar(pkt):
    """devuelve una copia del paquete con la cara medida respecto al neutral (si hay)."""
    if cal["muestras"] is not None and all(k in pkt for k in CAL_KEYS):
        cal["muestras"].append({k: float(pkt[k]) for k in CAL_KEYS})
        if "eye_yaw" in pkt: cal.setdefault("ojos", []).append((float(pkt["eye_yaw"]), float(pkt["eye_pitch"])))
        if len(cal["muestras"]) >= 30:
            if len({(m["head_yaw"], m["head_pitch"]) for m in cal["muestras"]}) < 3:   # valores congelados = cara perdida
                cal["muestras"] = None; print("\n   NEUTRAL no tomado: la camara no ve tu cara (valores congelados). Ponete frente a la OAK-D y escribe n otra vez."); return pkt
            cal["base"] = {k: sum(m[k] for m in cal["muestras"]) / len(cal["muestras"]) for k in CAL_KEYS}; cal["muestras"] = None
            if cal.get("ojos"): cal["mirada0"] = {"eye_yaw": sum(o[0] for o in cal["ojos"]) / len(cal["ojos"]), "eye_pitch": sum(o[1] for o in cal["ojos"]) / len(cal["ojos"])}; cal["ojos"] = []
            b = cal["base"]; print(f"\n   NEUTRAL tomado: yaw {b['head_yaw']:+.2f} pitch {b['head_pitch']:+.2f} cejas {b['brow_up']:.2f}/{b['brow_down']:.2f} boca {b['jaw_open']:.2f} triste {b['mouth_sad']:.2f}")
    b = cal["base"]
    if not b or not all(k in pkt for k in CAL_KEYS): return pkt
    q = dict(pkt)
    for k in ("eye_yaw", "eye_pitch"):   # mirada: respecto a donde miraba en el neutral (camara baja = "mira abajo")
        if k in pkt:
            if k not in b and cal.get("mirada0"): b[k] = cal["mirada0"][k]
            if k in b: q[k] = round(clamp((float(pkt[k]) - b[k]) * 1.5, -1, 1), 4)
    q["head_yaw"] = round(clamp((float(pkt["head_yaw"]) - b["head_yaw"]) * 2.0, -1, 1), 4)
    q["head_pitch"] = round(clamp((float(pkt["head_pitch"]) - b["head_pitch"]) * 2.0, -1, 1), 4)
    for k in ("brow_up", "brow_down", "mouth_sad", "jaw_open", "blink"):
        q[k] = round(clamp((float(pkt[k]) - b[k]) / max(0.05, 1.0 - b[k]), 0, 1), 4)
    return q

def guardar():
    with lock:
        if not estado["animo"] or not estado["cara"]: estado["cara"] = []; estado["cuerpo"] = []; video_terminar(None); return
        an = estado["animo"]; pref = f"{an}_{estado['actor']}_" if estado["actor"] else f"{an}_"   # <animo>_<actor>_NNN o <animo>_NNN
        k = len([f for f in os.listdir(SAL_CARA) if f.startswith(pref)]) + 1; nombre = f"{pref}{k:03d}"
        video_terminar(os.path.join(SAL_VIDEO, f"{nombre}.mov"))
        for carpeta, recs in ((SAL_CARA, estado["cara"]), (SAL_CUERPO, estado["cuerpo"])):
            with open(os.path.join(carpeta, f"{nombre}.jsonl"), "w") as fh:
                for r in recs: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        n = len(estado["cara"]); d = segundos([r["t"] for r in estado["cara"]]); estado["seg"][an] = estado["seg"].get(an, 0) + d
        print(f"\n   guardado {nombre}.jsonl en cara/ y cuerpo/ ({n} paquetes, {d:.0f} s)" + (f"  autoinforme valencia {estado['auto']['valencia']} activacion {estado['auto']['activacion']}" if estado["auto"]["valencia"] is not None else ""))
        estado["auto"] = {"valencia": None, "activacion": None}; _segs["t"] = 0.0
        estado["cara"] = []; estado["cuerpo"] = []

def resumen():
    print("\n   animo        segundos (esta sesion / total en disco)")
    for an in ANIMOS:
        tot = sum(segundos_archivo(os.path.join(SAL_CARA, f)) for f in os.listdir(SAL_CARA) if f.startswith(an + "_"))
        print(f"   {an:10s} {estado['seg'].get(an, 0):6.0f} / {tot:5.0f}  {'ok' if tot >= 60 else '..'}")

def registrar(pkt, crudo):
    """cada paquete que ballena3 manda a Blender pasa por aqui (pkt calibrado; crudo = tal cual salio de ballena3)."""
    estado["ultimo"] = pkt
    if not (estado["grabando"] and estado["animo"]): return
    t = round(time.time() - estado["t0"], 3)
    vt = {"video_t": round(time.time() - video["t0"], 3)} if video["t0"] else {}
    cara = {k: pkt[k] for k in pkt if k in CARA or k.startswith("face_")}
    cuerpo = {k: pkt[k] for k in pkt if k not in cara and k not in ("t", "mocap_mode")}
    with lock:
        estado["cara"].append({"t": t, "animo": estado["animo"], "actor": estado["actor"], **vt, **cara, "todo": crudo})
        auto = {f"auto_{k}": v for k, v in estado["auto"].items() if v is not None}   # autoinforme (0-10) antes de la toma
        estado["cuerpo"].append({"t": t, "animo": estado["animo"], "actor": estado["actor"], **vt, **cuerpo, **emotibit_vivo(), **auto})

# --- EmotiBit: OSC (sin dependencias) desde el EmotiBit Oscilloscope. Ultimo valor por senal en `emotibit`.
import struct
emotibit = {}; _emo = {"n": 0, "t": time.time(), "hz": 0.0, "error": None, "ultimo": 0.0}
from collections import deque
senales = {"ppg": deque(maxlen=25 * 12), "eda": deque(maxlen=15 * 90), "hr": deque(maxlen=200), "therm": deque(maxlen=200)}   # (t, valor) para el panel
def senal(nombre, vals):
    t = time.time()
    if nombre == "ppg_ir":
        n = len(vals)
        for i, v in enumerate(vals): senales["ppg"].append((t - (n - 1 - i) / 25.0, float(v)))
    elif nombre in ("eda", "hr", "therm"): senales[nombre].append((t, float(vals[-1])))
def emotibit_vivo():
    """los valores del EmotiBit valen solo si llego algo en los ultimos 2 s; si no, no se graban ni se mandan (antes se repetia el ultimo valor y quedaba 'congelado' en el dataset)."""
    return emotibit if (time.time() - _emo["ultimo"]) < 2.0 else {}
def osc_str(b, i):
    j = b.index(b"\0", i); return b[i:j].decode(errors="replace"), (j + 4) & ~3
def osc_mensaje(b):
    """-> (direccion, [args]) de un mensaje OSC; soporta f i d s T F b."""
    addr, i = osc_str(b, 0); tags, i = osc_str(b, i); args = []
    for t in tags.lstrip(","):
        if t == "f": args.append(struct.unpack(">f", b[i:i+4])[0]); i += 4
        elif t == "i": args.append(struct.unpack(">i", b[i:i+4])[0]); i += 4
        elif t == "d": args.append(struct.unpack(">d", b[i:i+8])[0]); i += 8
        elif t == "s": v, i = osc_str(b, i); args.append(v)
        elif t == "T": args.append(True)
        elif t == "F": args.append(False)
        elif t == "b": n = struct.unpack(">i", b[i:i+4])[0]; args.append(b[i+4:i+4+n]); i += (4 + n + 3) & ~3
    return addr, args
def osc_paquete(b):
    """mensajes de un paquete OSC (mensaje suelto o #bundle, anidado)."""
    if b.startswith(b"#bundle"):
        i = 16; out = []
        while i + 4 <= len(b):
            n = struct.unpack(">i", b[i:i+4])[0]; out += osc_paquete(b[i+4:i+4+n]); i += 4 + n
        return out
    return [osc_mensaje(b)]
def emotibit_nombre(addr):
    partes = [x for x in addr.split("/") if x]
    if partes and partes[0].lower() == "emotibit": partes = partes[1:]
    if partes and partes[0].isdigit(): partes = partes[1:]
    return "emotibit_" + "_".join(partes).lower().replace(":", "_").replace("-", "_")
def escuchar_emotibit(puerto):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.bind(("0.0.0.0", puerto))
    except OSError as e: _emo["error"] = str(e); print(f"   (emotibit: no puedo escuchar en {puerto}: {e})"); return
    while True:
        try:
            b, _ = s.recvfrom(65535)
            for addr, args in osc_paquete(b):
                nums = [float(v) for v in args if isinstance(v, (int, float)) and not isinstance(v, bool)]
                if nums:
                    k = emotibit_nombre(addr); emotibit[k] = round(nums[-1], 5); _emo["n"] += 1; _emo["ultimo"] = time.time(); senal(k[9:], nums)
        except Exception as e: _emo["error"] = str(e)
if a.emotibit and not a.prueba: threading.Thread(target=escuchar_emotibit, args=(a.emotibit,), daemon=True).start()
# --- EmotiBit DIRECTO por WiFi (sin Oscilloscope ni OSC): emotibit_cliente.py hace hello/conectar/ping y escribe en `emotibit`
_emo_directo = None
if not a.prueba and a.emotibit_directo:
    try:
        sys.path.insert(0, AQUI); import emotibit_cliente
        def _directo(k, vals):
            emotibit["emotibit_" + k] = round(float(vals[-1]), 5); _emo["n"] += 1; _emo["ultimo"] = time.time(); senal(k, vals)
            if _emo_directo and _emo_directo.valores.get("emotibit_hr") is not None:
                hr = _emo_directo.valores["emotibit_hr"]
                if emotibit.get("emotibit_hr") != hr: emotibit["emotibit_hr"] = hr; senal("hr", [hr])
        _emo_directo = emotibit_cliente.EmotiBit(ip=a.emotibit_ip or None, al_recibir=_directo).start()
        print(f"   EMOTIBIT directo: buscando por WiFi{' en ' + a.emotibit_ip if a.emotibit_ip else ''} (sin Oscilloscope)")
    except Exception as e: print(f"   (emotibit directo no disponible: {e})")

# --- lengua y 52 blendshapes: Face Landmarker sobre el cuadro RGB que ballena3 le pasa a FaceMesh.process
MODELO = os.path.join(AQUI, "modelos", "face_landmarker.task")
extra = {}                       # ultimos blendshapes, se mezclan en cada paquete
sentidos = {}                    # 18 oct: lo que siente la hermana y lo que ve el ojo (tacto, flores, joya, ofrenda, ve_hermana, personas...): NO se borra con la cara
_lm = {"lm": None, "t0": time.time(), "n": 0, "lento": False, "error": None}
def parpadeo_curva(b):
    """eyeBlink de MediaPipe: 0.3-0.5 es entrecerrar (sonrisa, camara baja); un parpadeo real pasa de 0.85."""
    return round(clamp((float(b) - 0.55) / 0.3, 0, 1), 4)
def mirada(bs):
    """eye_yaw (+ = mira a su derecha), eye_pitch (+ = arriba) a partir de los blendshapes eyeLook*."""
    yaw = ((bs.get("eyeLookInLeft", 0) - bs.get("eyeLookOutLeft", 0)) + (bs.get("eyeLookOutRight", 0) - bs.get("eyeLookInRight", 0))) / 2
    pitch = ((bs.get("eyeLookUpLeft", 0) + bs.get("eyeLookUpRight", 0)) - (bs.get("eyeLookDownLeft", 0) + bs.get("eyeLookDownRight", 0))) / 2
    return round(clamp(yaw, -1, 1), 4), round(clamp(pitch, -1, 1), 4)
def cargar_landmarker():
    from mediapipe.tasks import python as mpp; from mediapipe.tasks.python import vision
    opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=MODELO), output_face_blendshapes=True,
                                        num_faces=1, running_mode=vision.RunningMode.VIDEO)
    return vision.FaceLandmarker.create_from_options(opts)
# --- CUERPO (MediaPipe Pose, en el mismo hilo que el landmarker, un cuadro si y uno no): del esqueleto 3D en metros
# salen las mismas CUALIDADES con que los bailarines conducen a la ballena (cuerpo_cualidades.py). Van en el paquete
# como cuerpo_* y quedan en cuerpo/: desde ahora cada toma trae cara y cuerpo juntos (lo que el JEPA necesitaba).
POSE_MODELO = os.path.join(AQUI, "modelos", "pose_landmarker_lite.task")
from collections import deque as _deque
_pose = {"lm": None, "buf": _deque(maxlen=48), "ts": _deque(maxlen=48), "n": 0, "error": None, "ultimo": {}, "ropa": None, "cabeza": None, "recortes": 0}
def recorte_cabeza(image):
    """la cara de lejos es chica para la malla: se recorta la cabeza que vio la pose y se agranda a 480x480 (o None)"""
    import numpy as np, cv2
    c = _pose.get("cabeza")
    if not c: return None
    h_, w_ = image.shape[:2]; x0, y0, x1, y1 = int(c[0] * w_), int(c[1] * h_), int(c[2] * w_), int(c[3] * h_)
    if x1 - x0 < 24 or y1 - y0 < 24 or (x1 - x0) > w_ * 0.6: return None   # muy chica o ya grande (de cerca no hace falta)
    return cv2.resize(np.ascontiguousarray(image[y0:y1, x0:x1]), (480, 480), interpolation=cv2.INTER_CUBIC)
_POSE_J = {"pelvis": None, "neck": None, "head": 0, "shoulder_l": 11, "shoulder_r": 12, "elbow_l": 13, "elbow_r": 14, "wrist_l": 15, "wrist_r": 16, "hip_l": 23, "hip_r": 24, "knee_l": 25, "knee_r": 26, "ankle_l": 27, "ankle_r": 28}
def cuerpo_pose(rgb):
    import mediapipe as mp, numpy as np
    if _pose["lm"] is None:
        from mediapipe.tasks import python as mpp; from mediapipe.tasks.python import vision
        _pose["lm"] = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=POSE_MODELO), running_mode=vision.RunningMode.VIDEO, num_poses=1))
    _pose["n"] += 1
    if _pose["n"] % 2: return                           # un cuadro si y uno no: el cuerpo cambia despacio
    t = time.time(); r = _pose["lm"].detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int((t - _lm["t0"]) * 1000) + 1)
    if not r.pose_world_landmarks:
        for k in list(extra):
            if k.startswith("cuerpo_") or k == "esqueleto": extra.pop(k, None)
        _pose["lm2d"] = None; return
    L = r.pose_world_landmarks[0]; fila = np.full((26, 3), np.nan)
    try:   # la cabeza en la imagen, para recortar y agrandar la cara cuando esta lejos
        I = r.pose_landmarks[0]; h_, w_ = rgb.shape[:2]
        if I[0].visibility > 0.5:
            cx, cy = I[0].x, I[0].y; rr = max(0.06, abs(I[7].x - I[8].x) * 1.5)   # radio: 1.5 veces la distancia entre orejas
            _pose["cabeza"] = (max(0.0, cx - rr), max(0.0, cy - rr * 1.3), min(1.0, cx + rr), min(1.0, cy + rr * 1.1))
    except Exception: pass
    try:   # el color de la ropa: la caja entre hombros y caderas en la imagen
        I = r.pose_landmarks[0]; h_, w_ = rgb.shape[:2]
        xs = [I[i].x * w_ for i in (11, 12, 23, 24)]; ys = [I[i].y * h_ for i in (11, 12, 23, 24)]
        x0, x1 = int(max(0, min(xs))), int(min(w_, max(xs))); y0, y1 = int(max(0, min(ys))), int(min(h_, max(ys)))
        if x1 - x0 > 8 and y1 - y0 > 8:
            caja = rgb[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32) / 255.0; med = np.median(caja, axis=0)
            mx, mn = float(med.max()), float(med.min()); sat = (mx - mn) / max(1e-6, mx); _pose["ropa"] = {"rgb": [round(float(v), 3) for v in med], "sat": round(sat, 3), "brillo": round(mx, 3)}
    except Exception: pass
    from cuerpo_cualidades import cualidades_toma, CUERPO
    nombres = ["nose","eye_l","eye_r","ear_l","ear_r","shoulder_l","shoulder_r","elbow_l","elbow_r","wrist_l","wrist_r","hip_l","hip_r","knee_l","knee_r","ankle_l","ankle_r","head","neck","pelvis","bigtoe_l","bigtoe_r","smalltoe_l","smalltoe_r","heel_l","heel_r"]
    J = {n: i for i, n in enumerate(nombres)}
    def P(i): return np.array([L[i].x, L[i].z, -L[i].y]) if L[i].visibility > 0.4 else np.array([np.nan] * 3)   # MediaPipe: y hacia abajo -> z arriba
    for nom, i in _POSE_J.items():
        if i is not None: fila[J[nom]] = P(i)
    fila[J["pelvis"]] = (P(23) + P(24)) / 2; fila[J["neck"]] = (P(11) + P(12)) / 2
    _pose["buf"].append(fila); _pose["ts"].append(t)
    # el esqueleto entero va en cada paquete y en cuerpo/<toma>.jsonl (26 puntos x,y,z en metros, orden de Paqarina; None = no visto):
    # el dato fino del cuerpo, no solo las seis cualidades
    extra["esqueleto"] = [None if not np.isfinite(v) else round(float(v), 4) for v in fila.ravel()]
    try: _pose["lm2d"] = [(l.x, l.y, l.visibility) for l in r.pose_landmarks[0]]   # para dibujar el cuerpo en la ventana
    except Exception: _pose["lm2d"] = None
    if len(_pose["buf"]) < 12: return
    B = np.array(_pose["buf"]); fps = (len(B) - 1) / max(0.2, _pose["ts"][-1] - _pose["ts"][0])
    q = cualidades_toma(B, J, fps); i = len(B) - 1; out = {}
    for k in CUERPO:
        v = q[k][i]
        if np.isfinite(v): out[k] = round(float(v), 3)
    try:   # DONDE esta el actor en la sala (17 oct, "los actores se desplazan"): caderas en la imagen (0..1) y tamano del torso en la imagen
        lm = r.pose_landmarks[0]; cx, cy = (lm[23].x + lm[24].x) / 2, (lm[23].y + lm[24].y) / 2; sx, sy = (lm[11].x + lm[12].x) / 2, (lm[11].y + lm[12].y) / 2
        out["cuerpo_x"] = round(float(cx), 4); out["cuerpo_y"] = round(float(cy), 4); out["cuerpo_tam"] = round(float(np.hypot(cx - sx, cy - sy)), 4)   # torso chico en la imagen = lejos; grande = cerca
    except Exception: pass
    if L[27].visibility > 0.7 and L[28].visibility > 0.7:   # agachado: la cadera (origen) se acerca a los tobillos; solo con los dos tobillos bien vistos
        tob = (L[27].y + L[28].y) / 2   # altura de los tobillos bajo la cadera (MediaPipe: y hacia abajo, positiva)
        out["cuerpo_profundidad"] = round(max(-0.6, min(0.6, (tob - 0.85) / 0.35)), 3)
    else: out["cuerpo_profundidad"] = 0.0
    for k in list(extra):
        if k.startswith("cuerpo_"): extra.pop(k, None)
    extra.update(out); _pose["ultimo"] = out
def blendshapes(rgb, lm=None):
    """llena `extra` a partir del cuadro RGB (numpy HxWx3). lm: landmarker (se carga solo la primera vez)."""
    import mediapipe as mp
    lm = lm or _lm["lm"] or cargar_landmarker(); _lm["lm"] = lm
    _lm["n"] += 1
    if _lm["lento"] and _lm["n"] % 2: return          # si tarda mas de 20 ms, un cuadro si y uno no
    t = time.time()
    r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int((t - _lm["t0"]) * 1000))
    _lm["lento"] = (time.time() - t) > 0.02
    if not r.face_blendshapes:
        rec = recorte_cabeza(rgb)
        if rec is not None: r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rec), int((time.time() - _lm["t0"]) * 1000) + 1)
    if not r.face_blendshapes: return
    bs = {b.category_name: round(float(b.score), 4) for b in r.face_blendshapes[0]}
    if visita["activa"] and r.face_landmarks and _memoria.cara_tranquila(bs) and len(visita["firmas"]) < 400:
        fc = _memoria.firma_cuadro(r.face_landmarks[0])
        if fc is not None: visita["firmas"].append(fc)
    extra.clear(); extra.update({f"face_{k}": v for k, v in bs.items() if k != "_neutral"})
    extra["tongue_out"] = bs.get("tongueOut", 0.0)
    extra["mouth_smile"] = round((bs.get("mouthSmileLeft", 0.0) + bs.get("mouthSmileRight", 0.0)) / 2, 4)
    extra["blink_l"] = bs.get("eyeBlinkLeft", 0.0); extra["blink_r"] = bs.get("eyeBlinkRight", 0.0)
    extra["blink_bs"] = round(max(extra["blink_l"], extra["blink_r"]), 4)   # crudo; parpadeo() lo mide sobre el nivel de abiertos de la persona
    extra["eye_yaw"], extra["eye_pitch"] = mirada(bs)
if os.path.exists(MODELO) and not a.prueba:
    try:
        import mediapipe as _mp
        _process = _mp.solutions.face_mesh.FaceMesh.process
        _lm_q = {"img": None}; _lm_ev = threading.Event()
        def _lm_hilo():   # procesa siempre el ultimo cuadro; si no da abasto, salta los intermedios
            while True:
                _lm_ev.wait(); _lm_ev.clear(); img = _lm_q["img"]
                if img is None: continue
                try: blendshapes(img)
                except Exception as e:
                    if _lm["error"] != str(e): _lm["error"] = str(e); print(f"   (sin lengua/blendshapes: {e})")
                if a.pose and os.path.exists(POSE_MODELO):
                    try: cuerpo_pose(img)
                    except Exception as e:
                        if _pose["error"] != str(e): _pose["error"] = str(e); print(f"   (sin cuerpo: {e})")
        threading.Thread(target=_lm_hilo, daemon=True).start()
        _POSE_CONN = list(_mp.solutions.pose.POSE_CONNECTIONS); _imshow = cv2.imshow
        def imshow_cuerpo(nombre, frame):
            """la ventana de la camara con el cuerpo dibujado (puntos y huesos de la pose), ademas de la cara y las manos."""
            pts = _pose.get("lm2d")
            if pts:
                try:
                    h_, w_ = frame.shape[:2]; xy = [(int(x * w_), int(y * h_), v) for x, y, v in pts]
                    for a_, b_ in _POSE_CONN:
                        if xy[a_][2] > 0.4 and xy[b_][2] > 0.4: cv2.line(frame, xy[a_][:2], xy[b_][:2], (60, 220, 120), 2)
                    for x, y, v in xy:
                        if v > 0.4: cv2.circle(frame, (x, y), 3, (255, 255, 255), -1)
                except Exception: pass
            return _imshow(nombre, frame)
        cv2.imshow = imshow_cuerpo
        def process_tee(self, image):
            res = _process(self, image)
            if not getattr(res, "multi_face_landmarks", None):
                rec = recorte_cabeza(image)
                if rec is not None:
                    res2 = _process(self, rec)
                    if getattr(res2, "multi_face_landmarks", None): res = res2; _pose["recortes"] += 1   # la malla trabaja sobre el recorte: las proporciones son las mismas
            _lm["cuadro"] = image; _lm["res"] = res
            _lm_q["img"] = image.copy(); _lm_ev.set()   # copia: ballena3 reutiliza el buffer
            return res
        _mp.solutions.face_mesh.FaceMesh.process = process_tee
    except Exception as e: print(f"   (sin lengua/blendshapes: {e})")
else: print("   (sin modelos/face_landmarker.task: no hay lengua ni blendshapes)") if not a.prueba else None

# --- RECONOCEDOR DE ANIMO (modelos/animo_rf.pkl, de entrenar_animo.py): cada 0.5 s mira los ultimos 2 s de cara y
# manos y decide el animo del actor. Cambia solo cuando el nuevo gana 3 veces seguidas (1.5 s): cortes limpios.
reconocedor = {"ok": False, "animo": None, "prob": {}, "racha": None, "n": 0, "ultimo": 0.0, "ventana": [],
               "estilo": None, "estilo_prob": {}, "estilo_ema": {}, "estilo_n": 0, "sin_cara_desde": None}
try:
    import pickle, numpy as np
    _rf = pickle.load(open(os.path.join(AQUI, "modelos", "animo_rf.pkl"), "rb")); sys.path.insert(0, AQUI); from entrenar_animo import rasgos as _rasgos
    reconocedor["ok"] = True; print("   RECONOCEDOR de animo cargado (modelos/animo_rf.pkl): la ballena sigue el animo que ve en tu cara")
except Exception as e: print(f"   (sin reconocedor de animo: {e})")
# --- PARECIDO (modelos/parecido_rf.pkl, de entrenar_parecido.py): a cual de los actores grabados se parece quien esta
# frente a la camara. Se decide a los 2 s de verlo y queda fijo mientras la cara siga ahi (un encuentro = un estilo);
# si la cara se pierde 8 s, se olvida y la proxima persona vuelve a elegirse. Va en el paquete como `estilo`.
_pr = None
try:
    _pr = pickle.load(open(os.path.join(AQUI, "modelos", "parecido_rf.pkl"), "rb")); print(f"   PARECIDO cargado: la ballena contesta con el estilo del actor al que mas se parece la visita ({', '.join(_pr['actores'])})")
except Exception as e: print(f"   (sin modelo de parecido: {e})")
def parecido(x):
    if _pr is None: return
    q = _pr["modelo"].predict_proba(x.reshape(1, -1))[0]; ema = reconocedor["estilo_ema"]
    for a, v in zip(_pr["actores"], q): ema[a] = 0.7 * ema.get(a, 1.0 / len(q)) + 0.3 * float(v)
    reconocedor["estilo_prob"] = {a: round(v, 3) for a, v in ema.items()}; reconocedor["estilo_n"] += 1
    top = max(ema, key=ema.get)
    if reconocedor["estilo"] is None and reconocedor["estilo_n"] >= 4:   # 4 ventanas = 2 s de cara
        reconocedor["estilo"] = top if ema[top] >= 0.45 else "promedio"   # dudoso (< 45 %): el estilo promedio, no se pega a nadie
        print(f"   se parece a: {reconocedor['estilo']} ({ema[top]:.0%}) - la ballena le contesta con ese estilo"); ventana_evento("estilo")
    elif reconocedor["estilo"] and top != reconocedor["estilo"] and ema[top] > 0.45:
        reconocedor["cambio_n"] = reconocedor.get("cambio_n", 0) + 1
        if reconocedor["cambio_n"] >= 8:   # 4 s pareciendose a otro: es otra persona, aunque la cara nunca se haya ido
            print("   otra persona frente a la camara"); encuentro_cerrar(); parecido_olvidar(); reconocedor["cambio_n"] = 0
    else: reconocedor["cambio_n"] = 0
# --- LA VENTANA (http://localhost:8765/ventana): una pantalla negra donde ella escribe. Cada cosa que le pasa (alguien
# llega, lo reconoce, decide a quien se parece, cambia de animo, le gusta una ropa) es un gatillo: una linea corta en su
# voz, enseguida, y si ollama esta, un poema de su alma (yakumama_alma, Qwen) unos segundos despues. Abajo, en chico,
# lo que esta haciendo: animo, comportamiento, color, estilo, energia.
ventana = {"lineas": [], "poema": "", "poema_t": 0.0, "ocupado": False, "ultimo_gatillo": 0.0, "poema_ella": "", "poema_en": "", "objeto": "", "objeto_t": 0.0, "leyendo": False}
try:   # the last poem survives a restart of the recorder (18 oct)
    _v = json.load(open("/tmp/ballena_ventana.json")); ventana.update({k: _v[k] for k in ("lineas", "poema", "poema_ella", "poema_en") if k in _v})
except Exception: pass
def ventana_guardar():
    try: json.dump({k: ventana[k] for k in ("lineas", "poema", "poema_ella", "poema_en")}, open("/tmp/ballena_ventana.json", "w"), ensure_ascii=False)
    except Exception: pass
FRASES = {"llega": ["alguien se acerca. todavia no se quien.", "una cara nueva en la costra.", "te veo llegar. me quedo quieta."],
          "conocida": ["ya viniste. te recuerdo por los huesos de la cara.", "volviste. la sal no olvida.", "te conozco. la otra vez te conteste como {estilo_previo}."],
          "nombre": ["{nombre}. te conozco por tu nombre.", "volviste, {nombre}.", "{nombre}, otra vez frente a mi."],
          "estilo": ["te mueves como {estilo}. te contesto con su cuerpo.", "en vos hay algo de {estilo}. lo uso.", "te parezco {estilo}. no lo elegiste vos."],
          "animo": ["te leo {animo}.", "ahora te veo {animo}. cambio.", "hay {animo} en tu cara. lo tomo."],
          "ropa": ["me gusta tu color. me lo quedo un rato.", "tu ropa tiene agua adentro. me tino.", "ese color lo quiero. lo llevo puesto."],
          "sevа": ["te fuiste. me quedo con lo que trajiste.", "la cara se fue. el peso queda."],
          "tacto": ["me tocan. la costra siente la mano.", "una mano en el lomo. me quedo.", "el cuerpo de mi hermana siente tu mano. yo también."],
          "hermana": ["veo a mi hermana dorada en tus manos.", "la llevas en las manos. es mi hermana. la miro.", "mi hermana de oro. la sostienes como un pez."],
          "telefono": ["me apuntas con un telefono. te doy la espalda hasta que lo bajes.", "un lente. no le doy la cara a los lentes. se la doy a los ojos.", "bajalo y vuelvo."]}
ANIMO_ES = {"calm": "calma", "singing": "canto", "playful": "juego", "curious": "curiosidad", "feeding": "hambre", "sad": "tristeza", "angry": "rabia", "alert": "alerta", "diving": "hondo", "surfacing": "aire"}
# --- RETORNO DE LA HERMANA FISICA (17 oct): Dan manda por UDP 9995 lo que la ballena de verdad siente: {"tacto": 0..1,
# "zona": "cabeza"|"lomo"|"cola"|"aleta", "presencia": 0..1}. Entra en cada paquete (tacto, tacto_zona) y, al primer toque,
# dispara en la ventana el gatillo "tacto" (la linea y el poema de "alguien te esta tocando").
retorno = {"tacto": 0.0, "zona": "", "presencia": 0.0, "t": 0.0, "ultimo_gatillo": 0.0, "palanca_t": 0.0, "palanca_s": 0.0, "tacto_t": 0.0}
multitud = {"foco": None, "razon": "", "t": 0.0}
def _leer_multitud(personas, ahora):
    """the crowd eye's people -> her chosen one (decisiones.elegir_foco: feeding or the jewel crown first, then a known face, ...).
    The sister's touch and the mouth are given to whoever has a hand on the table; the known face is the one the face memory recognised."""
    try: from decisiones import elegir_foco
    except Exception: elegir_foco = None
    for p in personas:
        en_mesa = bool(p.get("mano_mesa")); p["alimenta"] = int(en_mesa and str(sentidos.get("ofrenda") or "nada") in ("pez", "no_pez"))
        p["joya"] = int(en_mesa and float(sentidos.get("joya") or 0) > 0.3); p["flores"] = int(en_mesa and float(sentidos.get("flores") or 0) > 0.3)
        p["palanca"] = int(en_mesa and bool(retorno.get("palanca_t"))); p["conocida"] = int(bool(visita.get("conocida")) and p.get("id") == multitud["foco"])
    foco, razon = elegir_foco(personas, multitud["foco"]) if (elegir_foco and personas) else (None, "")
    multitud.update(foco=(foco or {}).get("id"), razon=razon, t=ahora)
    _sala = retorno.get("sala") or {}; _sala_n = int(_sala.get("n") or 0) if ahora - float(_sala.get("t") or 0) < 3.0 else 0
    sentidos["personas_n"] = max(len(personas), _sala_n); sentidos["foco_razon"] = razon or None   # the room camera's count (M4) when her own crowd eye is off
    # LA VISTA (Dan's PC, 19 Oct): everyone she sees, as numbers, for the table screen - x across the frame, metres away,
    # her chosen one, hands up. Time-stamped so her brain drops it if the crowd eye stops (sentidos are never cleared).
    sentidos["gente"] = [[round(float(p.get("x") or 0.0), 2), p.get("distancia_m"), int(p.get("id") == multitud["foco"]),
                          int(bool(p.get("manos_arriba")))] for p in personas[:6]]
    sentidos["gente_t"] = ahora
    if foco: sentidos["distancia_m"] = foco.get("distancia_m"); sentidos["quieto_foco"] = foco.get("quieto"); sentidos["foco_x"] = foco.get("x"); sentidos["foco_mano_mesa"] = foco.get("mano_mesa")
    else: sentidos["distancia_m"] = None; sentidos["quieto_foco"] = None; sentidos["foco_x"] = None; sentidos["foco_mano_mesa"] = 0
def _envejecer_retorno(ahora):
    """the touch ESP went quiet for a second: nothing is being touched (so a stale reading can never fire a refusal)."""
    if retorno["tacto_t"] and ahora - retorno["tacto_t"] > 1.0:
        retorno["tacto"] = 0.0; retorno["zona"] = ""; retorno["tacto_t"] = 0.0
        for k, v in (("tacto", 0.0), ("tacto_zona", ""), ("flores", 0.0), ("flores_n", 0), ("joya", 0.0), ("joya_tiron", 0)):
            if k in sentidos: sentidos[k] = v
def _leer_retorno(d, ahora):
    """v2 (18 oct): the sister of Barcelona. Touch ESP: {"flores": [stem 0..1, ...], "joya": 0..1, "joya_tiron": 0/1, "presencia": 0..1}.
    TouchDesigner: {"camara": {"cerca": 0..1, "mira": 0/1}, "palanca": 0/1}. Legacy {"tacto","zona"} still accepted.
    Hand test of the mouth: {"ofrenda": "pez"|"no_pez"|"nada", "ofrenda_p": 0..1, "ofrenda_id": 1..29} (ofrenda_id alone = that creature, reaction from the catalogue)."""
    if isinstance(d.get("personas"), list):   # the crowd eye (ojo_multitud.py): whom she attends, and how many are there
        _leer_multitud(d["personas"], ahora); return
    # THREE SOURCES OF TOUCH, EACH ITS OWN (20 Oct 2026): the strips on the sculpture arrive as {"tacto","zona"} from Dan's brain TEN TIMES A
    # SECOND (ballena_td.py --violeta), the sister's flowers as {"flores": [...]}, the jewel as {"joya"}. Until today any packet with a touch
    # field reset the others, so Dan's stream of zeros wiped a hand on the flowers within 0.1 s and no touch ever reached her brain
    # (simular_jerarquia.py showed it). Now a packet updates only the source it carries; the touch she feels is the strongest fresh one.
    fu = retorno.setdefault("fuentes", {"tiras": (0.0, "", 0.0), "flores": (0.0, "flores", 0.0), "joya": (0.0, "joya", 0.0)})
    if "tacto" in d: fu["tiras"] = (float(d.get("tacto", 0) or 0), str(d.get("zona", "") or ""), ahora)
    fl = d.get("flores")
    if isinstance(fl, list):
        vals = [max(0.0, min(1.0, float(v or 0))) for v in fl] or [0.0]; sentidos["flores"] = round(max(vals), 3); sentidos["flores_n"] = sum(1 for v in vals if v > 0.3)
        fu["flores"] = (max(vals), "flores", ahora)
    if "joya" in d:
        sentidos["joya"] = round(max(0.0, min(1.0, float(d.get("joya") or 0))), 3); sentidos["joya_tiron"] = int(bool(d.get("joya_tiron")))
        fu["joya"] = (max(sentidos["joya"], 0.9 if sentidos["joya_tiron"] else 0.0), "joya", ahora)
    vivas = [(v, z) for (v, z, t_) in fu.values() if ahora - t_ < 1.2 and v > 0.3]
    tacto, zona = max(vivas) if vivas else (0.0, "")
    if vivas: retorno["tacto_t"] = ahora
    if ahora - fu["flores"][2] > 1.2: sentidos["flores"] = 0.0; sentidos["flores_n"] = 0
    if ahora - fu["joya"][2] > 1.2: sentidos["joya"] = 0.0; sentidos["joya_tiron"] = 0
    if "ofrenda" in d or "ofrenda_id" in d:   # what is offered to the mouth: pez | no_pez | nada; with ofrenda_id (1..29) the creature and its reaction come from the catalogue
        c = _CAT.get(int(d.get("ofrenda_id") or 0)); boca = str(d.get("ofrenda") or ("pez" if c else "nada"))
        # ONE SENDER AT A TIME (21 Oct): two sources alternating creatures (two carousels, an eye and a test) flipped her scene every
        # second and her mood with it. A different creature within PINGPONG_S of the last switch is refused; the mouth keeps what it has.
        _oid = (c or {}).get("id"); _pp = retorno.setdefault("pingpong", {"id": None, "t": 0.0, "dicho": 0.0})
        if _oid and _pp["id"] and _oid != _pp["id"] and ahora - _pp["t"] < PINGPONG_S:
            if ahora - _pp["dicho"] > 10: _pp["dicho"] = ahora; print(f"   (ofrendas: dos fuentes alternan {_pp['id']} y {_oid}: me quedo con {_pp['id']}; apaga una)", flush=True)
            return
        if _oid and _oid != _pp["id"]: _pp["id"], _pp["t"] = _oid, ahora
        if boca == "nada": _pp["id"] = None
        _poner_ofrenda(boca, d.get("ofrenda_p", 1.0), (c or {}).get("carpeta"), (c or {}).get("id"), (c or {}).get("nombre"), (c or {}).get("reaccion"), d.get("ofrenda_color")); retorno["ofrenda_t"] = ahora
    cam = d.get("camara")
    if isinstance(cam, dict): sentidos["camara_cerca"] = round(float(cam.get("cerca", 0) or 0), 3); sentidos["camara_mira"] = int(bool(cam.get("mira")))
    od = d.get("oido")   # 21 Oct: her ear (Dan's alma, this Mac's mic): loudness, a bang, someone singing
    if isinstance(od, dict): sentidos["oido"] = od; sentidos["oido_t"] = round(ahora, 2)
    sl = d.get("sala")   # 21 Oct: the room as the Pro on the M4 sees it (count, nearest distance, attention, dwell), through Dan's brain
    if isinstance(sl, dict):
        retorno["sala"] = dict(sl, t=ahora); sentidos["sala"] = sl
        if not multitud.get("t") or ahora - float(multitud.get("t") or 0) > 3.0: sentidos["personas_n"] = int(sl.get("n") or 0)   # her own crowd eye is off: the room's count is the M4's
    cf = d.get("cuerpo_fisico")   # 21 Oct: what her printed body was told to do, and whether its board is alive (her efference copy)
    if isinstance(cf, dict): sentidos["cuerpo_fisico"] = cf
    cl = d.get("clima")   # 21 Oct: the weather the salar lives (wind, sun, night, rain, water, temperature) -> her brain
    if isinstance(cl, dict): sentidos["clima"] = cl; sentidos["clima_t"] = round(ahora, 2)
    vj = d.get("viaje")   # 21 Oct: the journey as the renderer lives it (speed, arrival), for her undulation and her next decision
    if isinstance(vj, dict): sentidos["viaje_vel"] = round(float(vj.get("velocidad", 0) or 0), 2); sentidos["viaje_llegada"] = int(bool(vj.get("llegada"))); sentidos["viaje_t"] = round(ahora, 2)
    if "palanca" in d:
        if d.get("palanca"):
            if retorno["palanca_t"]: retorno["palanca_s"] += min(1.0, ahora - retorno["palanca_t"])
            retorno["palanca_t"] = ahora
        else: retorno["palanca_t"] = 0.0
        sentidos["palanca_s"] = round(retorno["palanca_s"], 1)
    retorno["tacto"] = tacto; retorno["zona"] = zona; retorno["presencia"] = float(d.get("presencia", 0) or 0); retorno["t"] = ahora
    sentidos["tacto"] = round(tacto, 3); sentidos["tacto_zona"] = zona
def _hilo_retorno(puerto=9995):
    import socket as _s
    try: sk = _s.socket(_s.AF_INET, _s.SOCK_DGRAM); sk.bind(("0.0.0.0", puerto))
    except Exception as e: print(f"   (retorno 9995: {e})"); return
    sk.settimeout(0.5)
    while True:
        try: b, _addr = sk.recvfrom(2048); d = json.loads(b.decode()); ahora = time.time()
        except Exception: _envejecer_retorno(time.time()); continue
        if os.environ.get("YAKUMAMA_LOG_9995") and ("ofrenda" in d or "ofrenda_id" in d):
            try: open("/tmp/ballena_9995.log", "a").write(f"{ahora:.2f} {_addr[0]}:{_addr[1]} {json.dumps(d)[:120]}\n")
            except Exception: pass
        _envejecer_retorno(ahora)
        _leer_retorno(d, ahora)
        if retorno["tacto"] > 0.3 and ahora - retorno["ultimo_gatillo"] > 45:
            retorno["ultimo_gatillo"] = ahora
            try: ventana_evento("tacto")
            except Exception: pass
threading.Thread(target=_hilo_retorno, daemon=True).start()
def ventana_evento(gatillo):
    import random
    datos = {"estilo": reconocedor.get("estilo") or "nadie", "estilo_previo": visita.get("estilo_previo") or "nadie", "animo": ANIMO_ES.get(reconocedor.get("animo") or "", "nada"), "nombre": visita.get("nombre") or ""}
    if gatillo == "conocida" and visita.get("nombre"): gatillo = "nombre"
    frase = random.choice(FRASES.get(gatillo, ["..."])).format(**datos)
    ventana["lineas"] = (ventana["lineas"] + [{"t": time.time(), "texto": frase, "gatillo": gatillo}])[-6:]
    if gatillo in ("llega", "conocida", "ropa", "tacto", "hermana") or (gatillo == "animo" and time.time() - ventana["poema_t"] > 45):
        threading.Thread(target=ventana_poema, args=(gatillo, dict(datos)), daemon=True).start()
POEMA_CADA_S = float(os.environ.get("YAKUMAMA_POEMA_CADA", 150.0))   # 21 oct (Violeta: "repite la poesia, cansona"): un poema nuevo como mucho cada tanto, aunque pasen muchas cosas
VOZ_CADA_S = float(os.environ.get("YAKUMAMA_VOZ_CADA", 300.0))       # y lo lee en voz alta como mucho cada tanto, y solo si su decision de voz es "poema"
_poema_ritmo = {"t": 0.0, "voz_t": 0.0}
def _lineas_dichas(A, n=60):
    out = []
    for x in A._cargar(A.ARCH_POEMAS, [])[-n:]:
        for l in str(x).split("\n"):
            l = " ".join(l.strip().lower().split())
            if len(l) > 6: out.append(l)
    return out
def _repite(poema, dichas):
    ls = [" ".join(l.strip().lower().split()) for l in poema.split("\n") if len(l.strip()) > 6]
    return any(l in dichas for l in ls) or len(ls) != len(set(ls))
def ventana_poema(gatillo, datos):
    """pide un poema al alma (ollama) con lo que le pasa; si no hay ollama, no escribe mas que la frase"""
    if ventana["ocupado"]: return
    if time.time() - _poema_ritmo["t"] < POEMA_CADA_S: return   # too soon for another poem (POEMA_CADA_S)
    ventana["ocupado"] = True
    try:
        sys.path.insert(0, HUK); import yakumama_alma as A
        _dichas = _lineas_dichas(A)
        que = {"llega": "una persona nueva se paro frente a vos y te mira", "conocida": f"volvio alguien que ya vino; la otra vez le contestaste como {datos['estilo_previo']}", "nombre": f"volvio {datos['nombre']}, que ya vino {mem.personas.get(visita.get('id') or '', {}).get('visitas', 0)} veces; la conoces por su nombre",
               "ropa": "te gusta el color de la ropa de quien tienes enfrente y te tines de ese color", "animo": f"en la cara de quien te mira lees {datos['animo']}",
               "tacto": f"alguien esta tocando el cuerpo de tu hermana de metal{(' en ' + retorno['zona']) if retorno.get('zona') else ''}; lo sientes como si fuera el tuyo",
               "hermana": "alguien sostiene a tu hermana dorada, la ballena de oro, en sus manos frente a tu ojo; la ves de cerca, la miras con curiosidad"}[gatillo]
        r = _pose.get("ropa") or {}; cuerpo = _pose.get("ultimo") or {}
        snap = {"water": 0.7, "scene_color": "the colour of their clothes" if gatillo == "ropa" else "gray", "scene_bright": r.get("brillo", 0.5), "humidity": 40, "l_palm_x": 0.5}
        usuario = (f"TU CUERPO Y EL SALAR AHORA\n{A._estado_en_cuerpo(snap)}\n\nLO QUE ACABA DE PASAR\n{que}. Se mueve como {datos['estilo']}. "
                   f"{'Mueve el cuerpo.' if (cuerpo.get('cuerpo_energia') or 0) > 0.3 else 'Esta casi quieta.'}\n\nLO QUE VE TU OJO\nuna cara, de cerca\n\nLO QUE CARGAS\n{len(mem.personas)} personas en la memoria\n\n"
                   f"LINEAS QUE YA DIJISTE, NO LAS REPITAS NI LAS PARAFRASEES (ni sus imagenes)\n{chr(10).join(sorted(set(_dichas))[-40:]) or 'ninguna'}\n\n{A.semilla() if hasattr(A, 'semilla') else ''}\n\nEscribi algo que no hayas dicho. Solo JSON.")
        poema = ""
        for _intento in range(2):   # a poem that repeats a line she already said is thrown away; one more try, then nothing (silence beats repetition)
            crudo = A._ollama(A.MODELO_ALMA, A.PIEL_SISTEMA, usuario, json_estricto=True, temperatura=0.95, tokens=220)
            cand = str(json.loads(crudo).get("poema", "")).strip() if crudo else ""
            if cand and not _repite(cand, _dichas): poema = cand; break
            if cand: print("   (poema repetido, descartado)")
        if poema:
            _poema_ritmo["t"] = time.time()
            if True:
                ventana["poema"] = poema; ventana["poema_t"] = time.time(); p = A._cargar(A.ARCH_POEMAS, []); p.append(poema); A._guardar(A.ARCH_POEMAS, p[-200:])
                print("   ┌─ VENTANA\n   │  " + poema.replace("\n", "\n   │  ") + "\n   └─")
                try: _dec_voz = (json.load(open("/tmp/ballena_cerebro.json")).get("decision") or {}).get("voz")
                except Exception: _dec_voz = "poema"
                if _dec_voz == "poema" and time.time() - _poema_ritmo["voz_t"] >= VOZ_CADA_S:   # she reads it aloud only when her decider says poem, and not too often
                    _poema_ritmo["voz_t"] = time.time(); threading.Thread(target=ventana_voz, args=(poema,), daemon=True).start()
                else: print(f"   (poema escrito, no leido: voz={_dec_voz}, ultima lectura hace {time.time() - _poema_ritmo['voz_t']:.0f} s)")
    except Exception as e: print(f"   (ventana sin poema: {str(e)[:80]})")
    finally: ventana["ocupado"] = False
VENTANA_HTML = """<!doctype html><html lang=es><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Yakumama</title>
<style>body{margin:0;background:#000;color:#e8e2d6;font:300 clamp(22px,3.4vw,46px)/1.35 Georgia,'Times New Roman',serif;height:100vh;display:flex;flex-direction:column;justify-content:space-between;padding:5vh 7vw;box-sizing:border-box}
#poema{white-space:pre-line;max-width:28ch;opacity:0;transition:opacity 2.5s}#poema.on{opacity:1}#reaccion{max-width:30ch;opacity:0;transition:opacity 1.2s}#reaccion.on{opacity:1}#reaccion .q{font:400 clamp(12px,1.2vw,16px)/1.5 -apple-system,Helvetica,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#c9a24a;opacity:.9}#reaccion .t{font-style:italic}#linea{font-style:italic;opacity:.85;min-height:1.4em}
#trad{white-space:pre-line;font:300 clamp(13px,1.3vw,18px)/1.45 Georgia,serif;opacity:.55;max-width:60ch;display:flex;gap:3em}#trad div{flex:1}#decide{opacity:.7}
#hace{font:400 clamp(12px,1.2vw,16px)/1.5 -apple-system,Helvetica,sans-serif;letter-spacing:.08em;text-transform:uppercase;opacity:.45;display:flex;gap:2.5em;flex-wrap:wrap}
#color{width:.9em;height:.9em;border-radius:50%;display:inline-block;vertical-align:middle;margin-right:.4em;background:#777}</style></head><body>
<div id=poema></div><div id=reaccion><div class=q></div><div class=t></div></div><div id=trad><div id=es></div><div id=en></div></div><div id=linea></div>
<div id=hace><span><i id=color></i><span id=animo></span></span><span id=comp></span><span id=estilo></span><span id=memo></span><span id=cuerpo></span><span id=veo></span><span id=decide></span><span id=dibuja></span></div>
<script>
const C={calm:'#ebeffa',singing:'#9b4dff',playful:'#ff8000',curious:'#b3ff00',feeding:'#ff8cd9',sad:'#1e1e1e',angry:'#f21410',alert:'#1ae640',diving:'#102a6b',surfacing:'#19d6e8'};
const B={calm:'logging',singing:'canto',playful:'breach',curious:'spyhop',feeding:'lunge',sad:'hundida',angry:'lobtail',alert:'escaneo',diving:'buceo',surfacing:'soplo'};
let ultimaLinea='';
async function tick(){try{const s=await (await fetch('/ventana_estado')).json();
 const txt=s.poema_ella||s.poema||'';const p=document.getElementById('poema');if(txt&&p.textContent!==txt){p.classList.remove('on');setTimeout(()=>{p.textContent=txt;p.classList.add('on')},800)}
 document.getElementById('es').textContent=s.poema_ella?(s.poema||''):'';document.getElementById('en').textContent=s.poema_en||'';
 document.getElementById('veo').textContent=s.objeto?('veo: '+s.objeto):'';const D={acercarse:'me acerco',quedarse:'me quedo',alejarse:'me alejo',bailar_de_vuelta:'bailo',invitar:'invito',observar:'observo',poema:'poema',canto:'canto',silencio:'silencio',recordar:'te recuerdo',olvidar:'te olvido',propio:'mi color',ropa:'tu color',comer:'como',rehusar:'no',esperar:'',dibujar:'dibujo'};
 const db=s.dibujo;document.getElementById('dibuja').textContent=db?('dibujo '+(db.persona?'la cara de '+db.persona:db.figura)+' '+Math.round((db.progreso||0)*100)+'%'):'';
 const cb=s.cerebro;document.getElementById('decide').textContent=cb&&cb.decision?('decido: '+Object.values(cb.decision).map(v=>(v in D)?D[v]:v).filter(v=>v).join(' · ')+(cb.fijo?' ['+cb.fijo+']':'')+(cb.personas_n?' · '+cb.personas_n+' personas':'')+(cb.foco_razon?' · atiendo: '+cb.foco_razon:'')):'';
 const rv=(s.cerebro||{}).reaccion_viva;const R=document.getElementById('reaccion');if(rv&&rv.texto){R.querySelector('.q').textContent=(rv.ofrenda_id?String(rv.ofrenda_id).padStart(2,'0')+' · ':'')+(rv.nombre||'')+' · reacción '+rv.n;R.querySelector('.t').textContent=rv.texto;R.classList.add('on');}else{R.classList.remove('on');}
 const l=s.lineas&&s.lineas.length?s.lineas[s.lineas.length-1].texto:'';if(l!==ultimaLinea){document.getElementById('linea').textContent=l;ultimaLinea=l}
 const a=s.animo||'';document.getElementById('animo').textContent=a||'sin nadie';document.getElementById('comp').textContent=B[a]||'';
 document.getElementById('color').style.background=s.color_ropa?('rgb('+s.color_ropa.map(v=>Math.round(v*255)).join(',')+')'):(C[a]||'#777');
 document.getElementById('estilo').textContent=s.estilo?('como '+s.estilo):'';const m=s.memoria||{};document.getElementById('memo').textContent=m.activa?(m.conocida?'te conozco · visita '+m.visitas:(m.id=='nueva'?'cara nueva':'')):'';
 const c=s.cuerpo||{};document.getElementById('cuerpo').textContent=c.cuerpo_energia!=null?('energia '+Math.round(c.cuerpo_energia*100)+'%'):'';
}catch(e){}}tick();setInterval(tick,1000);
</script></body></html>"""
def ventana_estado():
    m = {"activa": visita["activa"], "id": visita["id"], "conocida": visita["conocida"], "visitas": (mem.personas.get(visita["id"], {}).get("visitas", 0) + 1) if visita["conocida"] else None}
    ropa = visita.get("ropa") if visita["activa"] else None
    try: cerebro = json.load(open("/tmp/ballena_cerebro.json")); cerebro = cerebro if time.time() - cerebro.get("t", 0) < 15 else None
    except Exception: cerebro = None
    try: dibujo = json.load(open("/tmp/ballena_dibujo.json")); dibujo = dibujo if dibujo.get("activo") and time.time() - dibujo.get("t", 0) < 10 else None
    except Exception: dibujo = None
    return {"lineas": ventana["lineas"], "poema": ventana["poema"], "poema_ella": ventana["poema_ella"], "poema_en": ventana["poema_en"], "leyendo": ventana["leyendo"], "objeto": ventana["objeto"],
            "animo": reconocedor["animo"] if visita["activa"] else None, "estilo": reconocedor["estilo"], "memoria": m, "cerebro": cerebro, "dibujo": dibujo,
            "cuerpo": _pose.get("ultimo"), "color_ropa": (ropa or {}).get("rgb") if (ropa or {}).get("le_gusta") else None, "ve_hermana": int(sentidos.get("ve_hermana") or 0), "oro": sentidos.get("oro"), "ve_telefono": int(sentidos.get("ve_telefono") or 0)}
# --- su voz, su lengua, su sonido, y lo que ve en la mano (18 oct): antes vivian en carrusel.py; ahora en modo visita tambien
VOZ_DIR = os.path.join(HUK, "poemas_voz"); SONIDOS_DIR = os.path.join(HUK, "whale sound"); PY_DATOS = os.path.join(AQUI, "venv_datos", "bin", "python")
if not os.path.exists(PY_DATOS): PY_DATOS = sys.executable   # Dan's PC (18 Oct): kokoro-onnx lives in this venv
OLLAMA_HOST = os.environ.get("YAKUMAMA_OLLAMA", "localhost:11434")   # Dan's PC: the model runs on the Mac Mini
MOON_HOST = os.environ.get("YAKUMAMA_MOONDREAM", "localhost:11434")   # moondream (the lens, the fish fallback) stays LOCAL: small, and the mini has no moondream (20 Oct: 404s)
def _sonar(w, vol=1.0):
    """play a wav and wait (Dan's PC, 18 Oct): afplay on the Mac; elsewhere sounddevice, on the output whose name
    contains YAKUMAMA_AUDIO_OUT (e.g. itrack), else the default output."""
    if sys.platform == "darwin":
        subprocess.run(["afplay", "-v", str(vol), w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return
    import soundfile as _sf, sounddevice as _sd
    x, sr = _sf.read(w, dtype="float32"); want = os.environ.get("YAKUMAMA_AUDIO_OUT", "").lower(); dev = None
    if want: dev = next((i for i, dd in enumerate(_sd.query_devices()) if want in dd["name"].lower() and dd["max_output_channels"] > 0), None)
    _sd.play(x * vol, sr, device=dev); _sd.wait()
_son = {"animo": None, "p": None, "base": None, "t": 0.0}
def traducir_en(poema):
    """el poema en ingles, con Qwen local: mismas lineas, minusculas, sin comentario (de carrusel.py)."""
    try:
        import urllib.request as _u
        cuerpo = json.dumps({"model": os.environ.get("OLLAMA_MODEL", "qwen3.6"), "stream": False, "think": False, "options": {"temperature": 0.2, "num_predict": 200},
                             "messages": [{"role": "system", "content": "Translate the poem to English. Keep the same number of lines and line breaks. Lowercase. No title, no comment, no quotes: only the translated lines."}, {"role": "user", "content": poema}]}).encode()
        r = _u.urlopen(_u.Request("http://%s/api/chat" % OLLAMA_HOST, data=cuerpo, headers={"Content-Type": "application/json"}), timeout=90); t = json.loads(r.read())["message"]["content"].strip()
        return t.split("</think>")[-1].strip() if "</think>" in t else t
    except Exception: return ""
def ventana_voz(poema):
    """ella solo HABLA en su lengua (lengua.py, misma voz Kokoro via venv_datos); castellano e ingles se ESCRIBEN (Violeta, 17 oct)."""
    try:
        sys.path.insert(0, HUK); import lengua as _L; ella = _L.traducir(poema)
    except Exception as e: ella = ""; print(f"   (lengua: {str(e)[:60]})")
    ventana["poema_ella"] = ella; ventana["poema_en"] = traducir_en(poema) if ella else ""; ventana_guardar()
    if not a.voz or not ella: return
    try:
        os.makedirs(VOZ_DIR, exist_ok=True); w = os.path.join(VOZ_DIR, "poema_ella_vivo.wav")
        subprocess.run([PY_DATOS, "-I", os.path.join(HUK, "voz_ella.py"), ella.replace("\n", ". "), w, "--lengua", "ella"], check=False, capture_output=True, timeout=180)
        if os.path.exists(w):
            ventana["leyendo"] = True
            if _son["p"]: _son["p"].terminate(); _son["p"] = None   # el sonido del animo calla mientras ella lee
            _sonar(w); ventana["leyendo"] = False; _son["animo"] = None
    except Exception as e: ventana["leyendo"] = False; print(f"   (voz: {str(e)[:60]})")
def hilo_sonido():
    """el sonido del animo dominante de Blender (del latido /tmp/ballena_receptor.json) y la musica de base, bajito, en bucle."""
    import glob as _g
    while True:
        time.sleep(0.5)
        try:
            if a.musica and (_son["base"] is None or _son["base"].poll() is not None):
                fs = sorted(_g.glob(os.path.join(SONIDOS_DIR, "base", "*.wav")) + _g.glob(os.path.join(SONIDOS_DIR, "base", "*.mp3")))
                if fs: _son["base"] = subprocess.Popen(["afplay", "-v", "0.3", fs[0]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not a.sonido or ventana["leyendo"]: continue
            hb = json.load(open("/tmp/ballena_receptor.json")); dom = hb.get("dominante")
            if dom and dom != _son["animo"] and time.time() - _son["t"] > 4.0:
                w = os.path.join(SONIDOS_DIR, f"{dom}.wav")
                if os.path.exists(w):
                    if _son["p"]: _son["p"].terminate()
                    _son["p"] = subprocess.Popen(["afplay", "-v", "1.0" if dom == "singing" else "0.5", w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); _son["animo"] = dom; _son["t"] = time.time()
        except Exception: pass
threading.Thread(target=hilo_sonido, daemon=True).start()
OBJETOS_NO_PEZ = ("phone", "iphone", "scorpion", "lizard", "chameleon", "ladybug", "bug", "insect", "beetle", "spider", "cup", "bottle", "remote", "camera", "pen", "key")
OJO = None
try: _CAT = {int(c["id"]): c for c in json.load(open(os.path.join(AQUI, "docs", "ofrendas", "ofrendas.json")))["criaturas"]}
except Exception: _CAT = {}
def _poner_ofrenda(boca, p, clase=None, oid=None, nombre=None, reaccion=None, color=None):
    """lo que el ojo (o la prueba a mano) dice de la mano: boca pez|no_pez|nada + la criatura exacta y su reaccion (docs/ofrendas/ofrendas.json)."""
    sentidos["ofrenda"] = boca; sentidos["ofrenda_p"] = round(float(p or 0), 3); sentidos["ofrenda_clase"] = clase or ""; sentidos["ofrenda_id"] = oid; sentidos["ofrenda_nombre"] = nombre or ""
    sentidos["reaccion"] = (reaccion or {}).get("n") if isinstance(reaccion, dict) else reaccion; sentidos["ofrenda_color"] = color
def _cargar_ojo():
    global OJO
    try:
        from ojo_ofrendas import Ojo; OJO = Ojo(); print(f"   ojo de las manos: {len(OJO.clases)} clases ({OJO.rasgos.nombre}) de modelos/ofrendas_clf.pkl")
    except Exception as e: OJO = None; print(f"   (ojo de las manos off: {str(e)[:90]}; moondream decide pez / no pez como antes)")
def _votar(votos):
    """la clase que gana entre las ultimas miradas: 2 de 3 con p>=0.5, o la ultima sola con p>=0.7. Devuelve la ultima mirada de esa clase o None."""
    if not votos: return None
    # 21 oct (Violeta: "dice que ve pescados cuando no hay"): a creature only counts in a HAND. Without a hand in the frame it needs
    # to be almost certain (p >= 0.92); the centipede was winning at 0.66-0.83 on nothing (clothes, the table).
    def creible(v): return (not v.get("id")) or v.get("mano") or v["p"] >= 0.92
    u = votos[-1]
    if u["clase"] != "duda" and u["p"] >= 0.7 and creible(u): return u
    cuenta = {}
    for v in votos:
        if v["clase"] != "duda" and creible(v): cuenta[v["clase"]] = cuenta.get(v["clase"], 0) + 1
    if cuenta:
        c = max(cuenta, key=cuenta.get)
        if cuenta[c] >= 2: return next(v for v in reversed(votos) if v["clase"] == c)
    return None
def hilo_ojo_objeto():
    """cada 1 s busca oro (su hermana en las manos); cada 3 s, si hay alguien enfrente, el ojo de las manos (ojo_ofrendas.Ojo: las 29
    ofrendas + manos vacias + otras cosas + hermana, entrenado con las fotos de Sanam del 20 oct) dice que tiene en la mano y, si es
    una ofrenda, que reaccion le toca. Vota entre las ultimas 3 miradas (2 de 3, o una sola con p>=0.7). Una ofrenda -> ofrenda pez
    + ofrenda_id/reaccion; otra cosa -> no_pez; manos vacias o duda -> nada. Sin modelo cargado, moondream (ollama) decide pez/no pez
    como antes. moondream sigue mirando, si ollama responde, solo para el lente apuntando. La prueba a mano por 9995 manda 10 s."""
    import urllib.request as _u, base64 as _b, numpy as _np, collections
    HERMANA_ORO = os.environ.get("YAKUMAMA_HERMANA_ORO", "0") == "1"; ORO_LO, ORO_HI = (15, 120, 150), (35, 255, 255); ORO_MIN = 0.012; ORO_MAX = 0.20   # 20 Oct: over a fifth of the frame is clothing (a yellow shirt), not the prototype   # HSV band of the golden prototype (calibrated 18 oct on real frames: 19% of her pixels vs ~1% of wood and skin; phone frame's largest blob 0.005)
    vez = 0; hermana_t = 0.0; telefono_t = 0.0; LENTE = ("phone", "iphone", "cellphone", "smartphone", "camera", "camcorder"); votos = collections.deque(maxlen=3); ultimo_dicho = ""; ult_v = None
    if a.ojo_objeto: _cargar_ojo()
    while True:
        time.sleep(1.0); vez += 1
        try:
            cuerpo_reciente = bool(_pose.get("ts")) and time.time() - _pose["ts"][-1] < 15   # 20 Oct: a body (hands over the table) counts too - the camera may be below the face
            alguien = visita["activa"] or (time.time() - visita.get("ultima_cara", 0) < 15) or cuerpo_reciente   # the face may be covered by what the hands hold
            if not a.ojo_objeto or not alguien or _lm.get("cuadro") is None:   # nobody in view: the eye's offering and label expire (the hand test by 9995 keeps its own 10 s)
                if time.time() - retorno.get("ofrenda_t", 0) > 10 and sentidos.get("ofrenda") not in (None, "nada"): _poner_ofrenda("nada", 0.0)
                sentidos["ve_objeto"] = ""; sentidos["ve_hermana"] = 0; sentidos["ve_telefono"] = 0; ventana["objeto"] = ""; votos.clear(); continue
            import cv2; cuadro = _lm["cuadro"]; fr = cuadro; h, w0 = fr.shape[:2]; esc = 640.0 / max(w0, 1); fr = cv2.resize(fr, (640, int(h * esc))) if esc < 1 else fr
            m = cv2.inRange(cv2.cvtColor(fr, cv2.COLOR_RGB2HSV), ORO_LO, ORO_HI); n_, _l, stats, _c = cv2.connectedComponentsWithStats((m > 0).astype(_np.uint8), 8)
            if n_ > 1:
                k_ = 1 + int(_np.argmax(stats[1:, cv2.CC_STAT_AREA])); mayor = stats[k_, cv2.CC_STAT_AREA] / float(m.shape[0] * m.shape[1]); alto = _c[k_][1] / float(m.shape[0])
            else: mayor, alto = 0.0, 1.0
            ve = int(ORO_MIN < mayor < ORO_MAX and alto < 0.8) if HERMANA_ORO else 0   # the GOLDEN PROTOTYPE in the hands (18 Oct), by colour. Off since 20 Oct: the sister on the table is
            # not gold, she changes colour with her (Violeta); the detector fired on a yellow shirt. YAKUMAMA_HERMANA_ORO=1 brings it back for the prototype.
            if ve and OJO is not None and ult_v and time.time() - ult_v["t"] < 4 and ult_v["clase"] != "hermana_dorada" and ult_v["p"] >= 0.5: ve = 0   # 20 Oct: the hand eye knows her sister; a yellow shirt with a fish is a fish
            sentidos["ve_hermana"] = ve; sentidos["oro"] = round(mayor, 3)
            if ve:
                ventana["objeto"] = "mi hermana dorada"
                if time.time() - hermana_t > 60: hermana_t = time.time(); ventana_evento("hermana")
            if vez % 3: continue
            if OJO is not None:   # --- el ojo de las manos
                v = OJO.ver(_np.ascontiguousarray(cuadro)); votos.append(v); gana = _votar(votos); ult_v = dict(v, t=time.time())
                if v["clase"] != "manos_vacias" or vez % 30 == 0: print(f"   [ojo manos] {v['clase']} p={v['p']:.2f} mano={v['mano']}" + (f" -> {gana['clase']}" if gana else " (sin voto)"), flush=True)   # 20 oct: say what the hand eye sees
                sentidos["ve_objeto"] = ("" if v["clase"] == "duda" else (v["nombre"] if v["id"] else v["clase"]))[:40]
                if time.time() - retorno.get("ofrenda_t", 0) > 10:   # the hand test by 9995 wins for 10 s
                    if gana is not None and gana["id"]: _poner_ofrenda("pez", gana["p"], gana["clase"], gana["id"], gana["nombre"], gana["reaccion"], gana.get("color"))
                    elif gana is not None and gana["clase"] == "otras_cosas": _poner_ofrenda("no_pez", gana["p"], "otras_cosas")
                    elif gana is not None or all(x["clase"] in ("duda", "manos_vacias", "hermana_dorada") for x in votos): _poner_ofrenda("nada", v["p"])
                if gana is not None and gana["id"] and not sentidos.get("ve_hermana"):
                    corto = str(gana["nombre"]).split(" (")[0]; ventana["objeto"] = corto
                    if corto != ultimo_dicho or time.time() - ventana["objeto_t"] > 20:
                        ultimo_dicho = corto; ventana["objeto_t"] = time.time(); ventana["lineas"] = (ventana["lineas"] + [{"t": time.time(), "texto": f"veo en tu mano: {corto}. {(gana['reaccion'] or {}).get('texto', '')}", "gatillo": "objeto"}])[-6:]
                elif gana is not None and gana["clase"] == "otras_cosas" and not sentidos.get("ve_hermana"): ventana["objeto"] = "algo que no es una ofrenda"
                elif gana is None and all(x["clase"] in ("duda", "manos_vacias") for x in votos) and not sentidos.get("ve_hermana"): ventana["objeto"] = ""; ultimo_dicho = ""
                if not a.ojo_lente: continue
            ok, buf = cv2.imencode(".jpg", cv2.cvtColor(fr, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok: continue
            cuerpo = json.dumps({"model": "moondream", "stream": False, "options": {"num_predict": 12, "temperature": 0.0}, "images": [_b.b64encode(buf.tobytes()).decode()],
                                 "prompt": "What object is the person holding in their hands? Answer with one or two words, or 'nothing'."}).encode()
            r = _u.urlopen(_u.Request("http://%s/api/generate" % MOON_HOST, data=cuerpo, headers={"Content-Type": "application/json"}), timeout=60)
            et = json.loads(r.read()).get("response", "").strip().lower().strip(".").strip()
            lente = int(any(k in et for k in LENTE) and not sentidos.get("ve_hermana")); sentidos["ve_telefono"] = lente   # a lens raised at her: the digital whale turns away (decisiones: lente)
            if lente:
                ventana["objeto"] = "un lente apuntando"
                if time.time() - telefono_t > 30: telefono_t = time.time(); ventana_evento("telefono")
            if OJO is not None: continue   # con el ojo de las manos, moondream solo aporta el lente
            sentidos["ve_objeto"] = et[:40]
            if time.time() - retorno.get("ofrenda_t", 0) > 10:   # the hand test by 9995 wins for 10 s
                # only a fish feeds her from here: a phone in the hand is not a phone in the sister's mouth. no_pez comes from the hand test
                # (or, later, from the eye that sees the table) and never from an object merely held.
                _poner_ofrenda("pez" if ("fish" in et) else "nada", 0.7)
            if et and et != "nothing" and not sentidos.get("ve_hermana") and not lente:
                if et != ventana["objeto"] and time.time() - ventana["objeto_t"] > 20:
                    ventana["objeto_t"] = time.time(); ventana["lineas"] = (ventana["lineas"] + [{"t": time.time(), "texto": f"veo algo en tu mano: {et}.", "gatillo": "objeto"}])[-6:]
                ventana["objeto"] = et
            elif not sentidos.get("ve_hermana") and not lente: ventana["objeto"] = ""
        except Exception as e:
            if vez % 30 == 0: print(f"   (ojo objeto: {str(e)[:100]})")
threading.Thread(target=hilo_ojo_objeto, daemon=True).start()
# --- VISITAS Y MEMORIA (memoria.py): cada persona que se pone frente a la camara es un encuentro. Se guarda entero en
# datasets/visitas/ (cara, manos, pulso, animo y estilo que la ballena le vio; sin imagenes) y la persona queda en
# datasets/memoria.json como una firma de 210 distancias de su cara. Si vuelve, la ballena la reconoce a los pocos
# segundos y le contesta de entrada con el estilo de la otra vez. No se guarda nada mientras hay un actor con nombre
# (eso es una sesion de grabacion, no una visita). aprender.py reentrena con lo que las visitas trajeron.
import memoria as _memoria
mem = _memoria.Memoria(); SAL_VISITAS = os.path.join(AQUI, "datasets", "visitas")
visita = {"activa": False, "t0": None, "regs": [], "firmas": [], "id": None, "conocida": None, "dist": None, "ultima_cara": 0.0, "guardadas": 0, "estilo_previo": None}
CAMPOS_VISITA = ("head_yaw", "head_pitch", "jaw_open", "blink", "brow_up", "brow_down", "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch", "tongue_out",
                 "l_palm_x", "l_palm_y", "r_palm_x", "r_palm_y", "emotibit_hr", "emotibit_eda", "emotibit_therm", "actor_animo", "estilo")
def encuentro(pkt):
    """cada paquete: abre, alimenta o cierra el encuentro con la persona que esta frente a la camara."""
    if not a.visitas or estado["actor"]: return
    ahora = time.time(); cara = bool(reconocedor["prob"])
    if cara:
        if not visita["activa"]:
            visita.update(activa=True, t0=ahora, regs=[], firmas=[], id=None, conocida=None, dist=None, estilo_previo=None, nombre=None, ropa_decidida=False, ropa=None); print("   visita: alguien llego"); ventana_evento("llega")
        visita["ultima_cara"] = ahora
        if ahora - visita["t0"] > 3.0: ropa_decidir()
        r = {"t": round(ahora - visita["t0"], 3), **{k: pkt[k] for k in CAMPOS_VISITA if k in pkt}, **{k: v for k, v in pkt.items() if k.startswith("face_") or k.startswith("actor_") or k.startswith("parecido_") or k.startswith("cuerpo_") or k == "esqueleto"}}   # tambien el cuerpo: de las visitas ella aprende cuerpos con animo
        if emotibit_vivo(): r.update(emotibit_vivo())
        visita["regs"].append(r)
        if visita["id"] is None and len(visita["firmas"]) >= _memoria.MIN_CUADROS: memoria_reconocer()
    elif visita["activa"] and ahora - visita["ultima_cara"] > 8.0: encuentro_cerrar()
def ropa_decidir():
    """una vez por encuentro: si la ropa tiene color de verdad (saturada y no oscura) y le toca (4 de cada 10 visitas, o si
    esta curious/playful), ella se tine de ese color en vez del color del animo. Lo decide al azar con semilla por encuentro."""
    r = _pose.get("ropa")
    if not r or visita.get("ropa_decidida"): return
    import random; rnd = random.Random(int(visita["t0"] or 0))
    le_gusta = r["sat"] >= 0.35 and r["brillo"] >= 0.25 and (rnd.random() < 0.4 or reconocedor["animo"] in ("curious", "playful"))
    visita["ropa_decidida"] = True; visita["ropa"] = {**r, "le_gusta": bool(le_gusta)}
    print(f"   ropa: {r['rgb']} sat {r['sat']:.2f} -> {'le gusta, se tine' if le_gusta else 'no la copia'}")
    if le_gusta: ventana_evento("ropa")
def memoria_reconocer():
    f = _memoria.firma_encuentro(visita["firmas"])
    if f is None: return
    pid, d = mem.buscar(f); visita["dist"] = round(d, 4)
    if pid:
        p = mem.personas[pid]; visita.update(id=pid, conocida=True, estilo_previo=p.get("estilo"), nombre=p.get("nombre")); ventana_evento("conocida")
        if p.get("nombre") and _pr and p["nombre"] in _pr["actores"]: reconocedor["estilo"] = p["nombre"]; reconocedor["estilo_n"] = 99; print(f"   es {p['nombre']}: le contesta con su propio estilo")
        print(f"   TE CONOZCO: {pid}, visita numero {p['visitas'] + 1}, la otra vez le conteste como {p.get('estilo') or 'nadie'} (distancia {d:.3f})")
        if p.get("estilo") and reconocedor["estilo"] is None: reconocedor["estilo"] = p["estilo"]; reconocedor["estilo_n"] = 99   # la saluda con su estilo de la otra vez
    else: visita.update(id="nueva", conocida=False); print(f"   cara nueva (la mas parecida esta a {d:.3f}; umbral {_memoria.UMBRAL})")
def encuentro_cerrar():
    if not visita["activa"]: return
    regs = visita["regs"]; dur = (visita["ultima_cara"] - visita["t0"]) if visita["t0"] else 0; visita["activa"] = False; ventana_evento("sevа")
    if dur < 10 or len(regs) < 50: print(f"   visita corta ({dur:.0f} s): no se guarda"); return
    f = _memoria.firma_encuentro(visita["firmas"]); animos = {}
    for r in regs:
        if r.get("actor_animo"): animos[r["actor_animo"]] = animos.get(r["actor_animo"], 0) + 1
    hrs = [float(r["emotibit_hr"]) for r in regs if r.get("emotibit_hr")]; pulso = sum(hrs) / len(hrs) if hrs else None
    estilo = reconocedor["estilo"]; nombre = time.strftime("%Y%m%d_%H%M%S")
    pid = mem.registrar(f, estilo=estilo, animos=animos, pulso=pulso, pid=(visita["id"] if visita["conocida"] else None)) if f is not None else None
    archivo = f"{nombre}_{pid or 'sinfirma'}.jsonl"; os.makedirs(SAL_VISITAS, exist_ok=True)
    with open(os.path.join(SAL_VISITAS, archivo), "w") as fh:
        fh.write(json.dumps({"encuentro": nombre, "persona": pid, "conocida": bool(visita["conocida"]), "segundos": round(dur), "estilo": estilo, "animos": animos, "pulso": pulso}) + "\n")
        for r in regs: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    if pid: mem.personas[pid]["encuentros"] = (mem.personas[pid]["encuentros"] + [archivo])[-50:]; mem.guardar()
    visita["guardadas"] += 1; print(f"   visita guardada: {archivo} ({dur:.0f} s, {len(regs)} paquetes, persona {pid or 'sin firma'}, estilo {estilo}, animos {animos})")
def memoria_olvidar():
    pid = visita["id"] if visita["conocida"] else None
    if pid: mem.olvidar(pid); print(f"   olvidada {pid}")
    visita.update(id=None, conocida=None, estilo_previo=None, firmas=[]); return bool(pid)
def parecido_olvidar():
    if reconocedor["estilo"]: print("   la cara se fue: la ballena olvida el estilo")
    reconocedor.update(estilo=None, estilo_prob={}, estilo_ema={}, estilo_n=0)
def reconocer(pkt, crudo):
    if not reconocedor["ok"]: return
    v = reconocedor["ventana"]; v.append({**pkt, "todo": crudo}); del v[:-_rf["W"]]
    if len(v) < _rf["W"] or time.time() - reconocedor["ultimo"] < 0.5: return
    reconocedor["ultimo"] = time.time()
    try: x = _rasgos(v, v, _rf["BS"])
    except Exception: return
    if x is None:   # sin cara: no opina; si pasan 8 s sin cara, la visita se fue
        reconocedor["prob"] = {}
        if reconocedor["sin_cara_desde"] is None: reconocedor["sin_cara_desde"] = time.time()
        elif time.time() - reconocedor["sin_cara_desde"] > 8.0: encuentro_cerrar(); parecido_olvidar()
        return
    reconocedor["sin_cara_desde"] = None; parecido(x)
    p = _rf["modelo"].predict_proba(x.reshape(1, -1))[0]; moods = _rf["moods"]
    reconocedor["prob"] = {m: round(float(q), 3) for m, q in zip(moods, p)}
    top = moods[int(p.argmax())]
    if top == reconocedor["racha"]: reconocedor["n"] += 1
    else: reconocedor["racha"] = top; reconocedor["n"] = 1
    seguro = float(p.max()) >= 0.30 or reconocedor["animo"] is None
    if reconocedor["n"] >= (3 if estado["actor"] else 6) and reconocedor["animo"] != top and seguro:   # visitas: 3 s seguidos y >= 30 %
        reconocedor["animo"] = top; print(f"   la ballena ve: {top} ({p.max():.0%})"); ventana_evento("animo")

# --- espejos: copias del paquete a otras maquinas (TouchDesigner / ballena fisica), --espejo 192.168.50.20:9998
ESPEJOS = []
for e in a.espejo:
    try: h, pt = e.rsplit(":", 1); ESPEJOS.append((h, int(pt))); print(f"   ESPEJO: cada paquete tambien a {h}:{pt}")
    except Exception: print(f"   (espejo invalido: {e})")
# --- el tee: socket.sendto hacia 9998 sigue llegando a Blender y ademas se copia aqui
_sendto = socket.socket.sendto
def sendto_tee(self, data, *args):
    try:
        dest = args[-1]
        if isinstance(dest, tuple) and dest[1] == PUERTO_BLENDER:
            try:
                crudo = json.loads(data.decode()); pkt = parpadeo(calibrar({**crudo, **extra, **sentidos})); reconocer(pkt, crudo)
                if reconocedor["animo"] and reconocedor["prob"]: pkt = {**pkt, "actor_animo": reconocedor["animo"], **{"actor_" + m: q for m, q in reconocedor["prob"].items()}}
                if reconocedor["estilo"]: pkt = {**pkt, "estilo": reconocedor["estilo"], **{"parecido_" + a: q for a, q in reconocedor["estilo_prob"].items()}}
                if visita["activa"] and visita["id"]: pkt = {**pkt, "visita": visita["id"], "conocida": 1 if visita["conocida"] else 0}
                if visita.get("ropa") and visita["ropa"].get("le_gusta"): pkt = {**pkt, "color_ropa": visita["ropa"]["rgb"]}   # Blender se tine de la ropa
                encuentro(pkt); registrar(pkt, crudo)
                if estado["solo_cara"]: pkt = {**pkt, "solo_cara": estado["solo_cara"]}   # 1 cuerpo quieto, 2 + cabeza fija
                if estado["anclada"]: pkt = {**pkt, "anclada": 1}                           # se mueve pero no viaja
                if emotibit_vivo(): pkt = {**pkt, **emotibit_vivo()}                            # latido y senales al receptor (solo si llegan)
                if pkt is not crudo: data = json.dumps(pkt).encode()
                for h, pt in ESPEJOS:
                    try: _sendto(self, data, (h, pt))
                    except Exception: pass
            except Exception: pass
    except Exception: pass
    return _sendto(self, data, *args)
socket.socket.sendto = sendto_tee

# --- silenciar las lineas "yaw:..." de ballena3 (30 por segundo) y mostrar una linea de estado propia cada 2 s
class _Filtro:
    def __init__(self, real): self.real = real; self.buf = ""
    def write(self, s):
        self.buf += s
        while "\n" in self.buf:
            linea, self.buf = self.buf.split("\n", 1)
            if not linea.lstrip().startswith("yaw:"): self.real.write(linea + "\n")
    def flush(self): self.real.flush()
    def __getattr__(self, k): return getattr(self.real, k)
if not a.prueba: sys.stdout = _Filtro(sys.stdout)

def estado_periodico():
    while True:
        time.sleep(2)
        u = estado["ultimo"]
        if not u: continue
        modo = ("cuerpo" + (" ANCLADA" if estado["anclada"] else ""), "SOLO CARA", "SOLO CARA, cabeza fija")[estado["solo_cara"]]
        rec = f"REC {segundos([r['t'] for r in estado['cara']]):.0f}s" if estado["grabando"] else "pausa"
        neutral = "" if cal["base"] else "  (sin neutral: escribe n)"
        _emo["hz"] = _emo["n"] / max(1e-6, time.time() - _emo["t"]); _emo["n"] = 0; _emo["t"] = time.time()
        if emotibit_vivo():
            e = emotibit; partes = [f"{k[9:]} {v:.3g}" for k, v in e.items() if k in ("emotibit_hr", "emotibit_eda", "emotibit_therm", "emotibit_temp", "emotibit_ppg_red")]
            emo = f" | emotibit {_emo['hz']:.0f}/s " + " ".join(partes[:4])
        else: emo = f" | emotibit: {_emo_directo.estado}" if _emo_directo else ((f" | EMOTIBIT SIN DATOS (se corto)" if emotibit else f" | (sin emotibit en {a.emotibit})") if a.emotibit else "")
        print(f"   [{modo}] {estado['animo'] or 'SIN ANIMO (1-0)'} {rec} | yaw {u.get('head_yaw', 0):+.2f} pitch {u.get('head_pitch', 0):+.2f} boca {u.get('jaw_open', 0):.2f} parpadeo {u.get('blink', 0):.2f} cejas {u.get('brow_up', 0):.2f}/{u.get('brow_down', 0):.2f} lengua {u.get('tongue_out', 0):.2f}{neutral}{emo}")
threading.Thread(target=estado_periodico, daemon=True).start()

def tty_guardar():
    try:
        import termios; return termios.tcgetattr(sys.stdin.fileno())
    except Exception: return None
def tty_restaurar(attrs):
    try:
        import termios; attrs and termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, attrs)
    except Exception: pass
TTY0 = tty_guardar()
def salir():
    try: encuentro_cerrar()
    except Exception: pass
    try: sys.stdout.flush()
    except Exception: pass
    tty_restaurar(TTY0); os._exit(0)
def teclas():
    """una tecla por vez, sin Enter, si la terminal lo permite (cbreak); si no (pipe), por lineas."""
    if sys.stdin.isatty():
        import tty
        try: tty.setcbreak(sys.stdin.fileno())
        except Exception: pass
        while True:
            try: ch = os.read(sys.stdin.fileno(), 1).decode(errors="ignore")
            except Exception: return
            if not ch: return
            yield ch.lower()
    else:
        for linea in sys.stdin:
            for ch in linea.replace("\r", "\n").strip().lower(): yield ch
def tecla(c):
    """una tecla: la misma logica para el teclado y para el panel web."""
    if True:
        if c in TECLAS:
            if estado["cara"]: guardar()
            estado["animo"] = ANIMOS[TECLAS.index(c)]; print(f"   animo: {estado['animo']}  ({'grabando' if estado['grabando'] else 'pausa: g para grabar'})")
        elif c == "g":
            if not estado["animo"]: print("   PRIMERO EL ANIMO: 1 calm 2 singing 3 playful 4 curious 5 feeding 6 sad 7 angry 8 alert 9 diving 0 surfacing"); return
            estado["grabando"] = not estado["grabando"]; print("   GRABANDO" if estado["grabando"] else "   pausa")
            if estado["grabando"] and estado["animo"]: video_empezar()
        elif c == "t":
            try:
                import cv2; os.makedirs(os.path.join(AQUI, "datasets", "_cuadros"), exist_ok=True)
                f = os.path.join(AQUI, "datasets", "_cuadros", time.strftime("%H%M%S") + ".jpg")
                cv2.imwrite(f, cv2.cvtColor(_lm["cuadro"], cv2.COLOR_RGB2BGR)); print(f"   cuadro guardado: {os.path.basename(f)}")
            except Exception as e: print(f"   (sin cuadro: {e})")
        elif c == "a": estado["anclada"] = not estado["anclada"]; print("   ANCLADA: se mueve pero no viaja por el espacio" if estado["anclada"] else "   libre: vuelve a viajar")
        elif c == "n": cal["muestras"] = []; print("   NEUTRAL: quieto mirando a la camara, cara relajada... (1 s)")
        elif c == "c":
            estado["solo_cara"] = (estado["solo_cara"] + 1) % 3
            print(("   cuerpo entero otra vez", "   SOLO CARA: cuerpo quieto, la cabeza sigue la nariz", "   SOLO CARA con CABEZA FIJA: solo boca, parpadeo y cejas")[estado["solo_cara"]])
        elif c == "f": guardar(); estado["grabando"] = False
        elif c == "r": resumen()
        elif c == "q": guardar(); video_terminar(None); resumen(); salir()
def teclado():
    print(__doc__.split("EN ESTA TERMINAL")[1])
    for c in teclas(): tecla(c)
threading.Thread(target=teclado, daemon=True).start()

# --- PANEL WEB: http://localhost:8765  botones grandes + estado en vivo (misma logica que las teclas)
ap_panel = a.panel
_segs = {"t": 0.0, "segs": {an: 0.0 for an in ANIMOS}, "ocupado": False, "por_archivo": {}}
def segs_totales():
    """segundos grabados por animo (solo los del actor actual, o los sin nombre). Con cientos de tomas (RAVDESS, BEAT)
    leer todo tarda segundos: se calcula en un hilo, una vez por minuto, con cache por archivo."""
    if time.time() - _segs["t"] > 60 and not _segs["ocupado"]:
        _segs["ocupado"] = True
        def _calc():
            segs = {an: 0.0 for an in ANIMOS}
            try:
                for f in os.listdir(SAL_CARA):
                    if not f.endswith(".jsonl"): continue
                    partes = f[:-6].split("_"); an = partes[0]; quien = partes[1] if len(partes) == 3 else ""
                    if an not in segs or quien != estado["actor"]: continue
                    ruta = os.path.join(SAL_CARA, f); mt = os.path.getmtime(ruta); c = _segs["por_archivo"].get(f)
                    if not c or c[0] != mt: c = (mt, segundos_archivo(ruta)); _segs["por_archivo"][f] = c
                    segs[an] += c[1]
            except Exception: pass
            _segs["segs"] = segs; _segs["t"] = time.time(); _segs["ocupado"] = False
        threading.Thread(target=_calc, daemon=True).start()
    return _segs["segs"]
def estado_json():
    u = estado["ultimo"]; segs = segs_totales()
    try: rx = json.load(open("/tmp/ballena_receptor.json")); blender = (time.time() - rx.get("t", 0)) < 6
    except Exception: blender = False
    cara = bool(u) and u.get("head_yaw") is not None and estado.get("_yaw_prev") != u.get("head_yaw")
    estado["_yaw_prev"] = u.get("head_yaw") if u else None
    return {"modo": ("cuerpo", "solo cara", "solo cara, cabeza fija")[estado["solo_cara"]] + (" + anclada" if estado["anclada"] else ""),
            "auto": estado["auto"], "actor": estado["actor"], "animo": estado["animo"], "grabando": estado["grabando"], "tramo_s": segundos([r["t"] for r in estado["cara"]]) if estado["cara"] else 0.0,
            "neutral": bool(cal["base"]), "cara": cara, "blender": blender, "segundos": segs, "detectado": reconocedor["animo"], "prob": reconocedor["prob"],
            "cuerpo": _pose["ultimo"] or None, "recortes": _pose["recortes"], "estilo": reconocedor["estilo"], "estilo_prob": reconocedor["estilo_prob"], "sin_emotibit": not (a.emotibit or a.emotibit_directo),
            "memoria": {"aprender": bool(a.visitas) and not estado["actor"], "activa": visita["activa"], "id": visita["id"], "conocida": visita["conocida"], "dist": visita["dist"], "nombre": visita.get("nombre"),
                        "visitas": (mem.personas.get(visita["id"], {}).get("visitas", 0) + 1) if visita["conocida"] else None, "estilo_previo": visita["estilo_previo"],
                        "guardadas": visita["guardadas"], "personas": len(mem.personas)},
            "emotibit": {"hz": round(_emo["hz"]), "hr": emotibit.get("emotibit_hr"), "eda": emotibit.get("emotibit_eda"), "therm": emotibit.get("emotibit_therm")} if emotibit_vivo() else None,
            "valores": {k: u.get(k) for k in ("head_yaw", "head_pitch", "jaw_open", "blink", "brow_up", "mouth_smile", "tongue_out")} if u else {}}
PANEL_HTML = """<!doctype html><html lang=es><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Yakumama</title>
<style>:root{--bg:#0f1720;--fg:#e8eef4;--mut:#8aa0b4;--acc:#39c6a4;--rec:#ff4d5a;--card:#172230}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.4 -apple-system,Helvetica,sans-serif;padding:16px}
h1{font-size:20px;margin:0 0 8px}.row{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.b{border:0;border-radius:12px;padding:16px 18px;font-size:17px;color:var(--fg);background:var(--card);cursor:pointer;min-width:120px}
.b.on{background:var(--acc);color:#062}.b.rec{background:var(--rec);color:#fff;font-weight:700;min-width:180px}.b.off{opacity:.55}.st{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
.k{background:var(--card);border-radius:12px;padding:10px 12px}.k b{display:block;color:var(--mut);font-size:12px;font-weight:600;text-transform:uppercase}.k span{font-size:20px}.ok{color:var(--acc)}.bad{color:var(--rec)}
.m{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #223}.m.ok{color:var(--acc)}.small{font-size:13px!important;color:var(--mut)}</style></head><body>
<h1>Yakumama · grabador</h1>
<div class=st id=st></div>
<div class=row id=animos></div>
<div class=row><input id=actor placeholder="quien actua (nombre)" style="border:0;border-radius:12px;padding:14px 16px;font-size:17px;background:var(--card);color:var(--fg);min-width:200px"><button class=b onclick="setActor()">Cambiar actor</button><button class="b off" onclick="if(confirm('Olvidar a la persona que esta ahora?'))fetch('/olvidar',{method:'POST'})">Olvidar a esta persona</button><button class=b onclick="const n=prompt('Como se llama la persona que esta ahora?');if(n)fetch('/nombrar?nombre='+encodeURIComponent(n),{method:'POST'})">Ponerle nombre</button></div>
<div class=k style="margin:10px 0"><b>Antes de grabar: ¿cómo te sentís ahora? (0-10)</b>
 <div style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-top:6px">
  <label style="flex:1;min-width:220px">desagradable ← <b style="display:inline;text-transform:none">agradable</b> → <span id=vv>5</span><br><input type=range id=val min=0 max=10 value=5 style="width:100%" oninput="document.getElementById('vv').textContent=this.value"></label>
  <label style="flex:1;min-width:220px">calma ← <b style="display:inline;text-transform:none">activada</b> → <span id=va>5</span><br><input type=range id=act min=0 max=10 value=5 style="width:100%" oninput="document.getElementById('va').textContent=this.value"></label>
  <button class=b onclick="setAuto()">Guardar cómo me siento</button><span id=auto class=small></span>
 </div></div>
<div class=row><button class="b rec" id=rec onclick="t('g')">● GRABAR</button><button class=b onclick="t('f')">■ Guardar tramo</button><button class=b onclick="t('n')">Neutral (mirar a la camara)</button></div>
<div class=row><button class=b id=modo onclick="t('c')">Modo: …</button><button class=b id=ancla onclick="t('a')">Anclada</button><button class=b onclick="t('t')">Guardar cuadro</button><button class="b off" onclick="if(confirm('Guardar y salir?'))t('q')">Salir</button></div>
<div class=st style="margin-top:10px">
 <div class=k><b>Pulso (PPG infrarrojo, 10 s)</b><canvas id=c_ppg height=70></canvas><span id=v_ppg class=small></span></div>
 <div class=k><b>Conductancia de la piel (eda, 90 s)</b><canvas id=c_eda height=70></canvas><span id=v_eda class=small></span></div>
 <div class=k><b>Ritmo cardiaco (hr, 3 min)</b><canvas id=c_hr height=70></canvas><span id=v_hr class=small></span></div>
</div>
<div id=tot></div>
<script>
// tiras: una senal por tira (un solo eje), linea 2 px, grilla recesiva, ultimo valor a la derecha, cruz al pasar el mouse
const COL={ppg:'#3987e5',eda:'#d95926',hr:'#199e70'}; const VENT={ppg:10,eda:90,hr:180}; const UNI={ppg:'',eda:' µS',hr:' bpm'}; let SEN={}; let HOV={};
function tira(id){const c=document.getElementById('c_'+id),W=c.width=c.clientWidth*devicePixelRatio,H=c.height=70*devicePixelRatio,g=c.getContext('2d');g.clearRect(0,0,W,H);
 const d=(SEN[id]||[]).filter(p=>p[0]>-VENT[id]);const lab=document.getElementById('v_'+id);if(d.length<2){lab.textContent='—';return}
 let lo=Math.min(...d.map(p=>p[1])),hi=Math.max(...d.map(p=>p[1]));if(hi-lo<1e-6){hi=lo+1}const pad=(hi-lo)*0.1;lo-=pad;hi+=pad;
 const X=t=>(t+VENT[id])/VENT[id]*(W-8)+4,Y=v=>H-6-(v-lo)/(hi-lo)*(H-12);
 g.strokeStyle='rgba(255,255,255,.08)';g.lineWidth=1;for(let i=1;i<4;i++){g.beginPath();g.moveTo(0,H*i/4);g.lineTo(W,H*i/4);g.stroke()}
 g.strokeStyle=COL[id];g.lineWidth=2*devicePixelRatio;g.lineJoin='round';g.beginPath();d.forEach((p,i)=>{i?g.lineTo(X(p[0]),Y(p[1])):g.moveTo(X(p[0]),Y(p[1]))});g.stroke();
 const u=d[d.length-1];g.fillStyle=COL[id];g.beginPath();g.arc(X(u[0]),Y(u[1]),4*devicePixelRatio,0,7);g.fill();
 if(HOV[id]!=null){const t=HOV[id]/c.clientWidth*VENT[id]-VENT[id];let q=d[0];for(const p of d){if(Math.abs(p[0]-t)<Math.abs(q[0]-t))q=p}
  g.strokeStyle='rgba(255,255,255,.35)';g.lineWidth=1;g.beginPath();g.moveTo(X(q[0]),0);g.lineTo(X(q[0]),H);g.stroke();g.fillStyle='#e8eef4';g.font=`${12*devicePixelRatio}px -apple-system,Helvetica`;g.fillText(q[1].toFixed(id==='ppg'?0:2)+UNI[id]+'  '+q[0].toFixed(1)+' s',Math.min(X(q[0])+6,W-120*devicePixelRatio),14*devicePixelRatio)}
 lab.textContent=(id==='ppg'?u[1].toFixed(0):u[1].toFixed(2))+UNI[id]+'   ·   rango '+(id==='ppg'?lo.toFixed(0)+'–'+hi.toFixed(0):lo.toFixed(2)+'–'+hi.toFixed(2));}
for(const id of ['ppg','eda','hr']){const c=document.getElementById('c_'+id);c.style.width='100%';c.style.display='block';c.onmousemove=e=>{HOV[id]=e.offsetX;tira(id)};c.onmouseleave=()=>{HOV[id]=null;tira(id)}}
async function sen(){try{SEN=await (await fetch('/senales')).json();for(const id of ['ppg','eda','hr'])tira(id)}catch(e){}}
setInterval(sen,500);
const A={"1":"calm","2":"singing","3":"playful","4":"curious","5":"feeding","6":"sad","7":"angry","8":"alert","9":"diving","0":"surfacing"};
const an=document.getElementById('animos');for(const k in A){const b=document.createElement('button');b.className='b';b.id='a'+A[k];b.textContent=A[k];b.onclick=()=>t(k);an.appendChild(b)}
async function t(c){await fetch('/tecla?c='+c,{method:'POST'});setTimeout(est,150)}
async function setAuto(){const v=document.getElementById('val').value,a=document.getElementById('act').value;await fetch('/auto?valencia='+v+'&activacion='+a,{method:'POST'});setTimeout(est,150)}
let ACTOR_VISTO='';
async function setActor(){const n=document.getElementById('actor').value;await fetch('/actor?nombre='+encodeURIComponent(n),{method:'POST'});setTimeout(est,150)}
function f(v,d=2){return v==null?'—':(+v).toFixed(d)}
async function est(){try{const s=await (await fetch('/estado')).json();
 for(const k in A){document.getElementById('a'+A[k]).className='b'+(s.animo==A[k]?' on':'')}
 if(document.activeElement.id!='actor'&&ACTOR_VISTO!==(s.actor||'')){document.getElementById('actor').value=s.actor||'';ACTOR_VISTO=s.actor||''}   // solo cuando cambia en el grabador: no borrar lo que se esta escribiendo
 const au=s.auto||{};document.getElementById('auto').textContent=au.valencia==null?'falta para esta toma':'guardado: '+au.valencia+' / '+au.activacion;
 const r=document.getElementById('rec');r.textContent=s.grabando?'■ PAUSAR  '+Math.round(s.tramo_s)+' s':'● GRABAR';r.style.background=s.grabando?'#ff4d5a':'#2a3a4a';
 document.getElementById('modo').textContent='Modo: '+s.modo;document.getElementById('ancla').className='b'+(s.modo.includes('anclada')?' on':'');
 const e=s.emotibit;const v=s.valores||{};
 document.getElementById('st').innerHTML=
  `<div class=k><b>Actor</b><span class="${s.actor?'ok':'bad'}">${s.actor||'sin nombre'}</span></div>`+
  `<div class=k><b>Cara</b><span class="${s.cara?'ok':'bad'}">${s.cara?'vista':'NO VISTA'}</span></div>`+
  `<div class=k><b>La ballena ve</b><span class="${s.detectado?'ok':''}">${s.detectado||'—'}</span>${s.prob&&s.detectado?'<small class=small>'+Math.round((s.prob[s.detectado]||0)*100)+' %</small>':''}</div>`+
  `<div class=k><b>Memoria</b><span class="${s.memoria&&s.memoria.conocida?'ok':''}">${!s.memoria||!s.memoria.aprender?'apagada':(!s.memoria.activa?'nadie':(s.memoria.conocida?'te conozco · '+(s.memoria.nombre?s.memoria.nombre+' · ':'')+'visita '+s.memoria.visitas+(s.memoria.estilo_previo?' · estilo '+s.memoria.estilo_previo:''):(s.memoria.id=='nueva'?'cara nueva':'mirando…')))}</span><small class=small>${s.memoria?s.memoria.personas+' personas · '+s.memoria.guardadas+' visitas guardadas hoy':''}</small></div>`+
  `<div class=k><b>Se parece a</b><span class="${s.estilo?'ok':''}">${s.estilo||'—'}</span>${s.estilo_prob&&s.estilo?'<small class=small>'+Math.round((s.estilo_prob[s.estilo]||0)*100)+' %</small>':''}</div>`+
  `<div class=k><b>Neutral</b><span class="${s.neutral?'ok':'bad'}">${s.neutral?'tomado':'falta: Neutral'}</span></div>`+
  `<div class=k><b>Blender</b><span class="${s.blender?'ok':'bad'}">${s.blender?'recibiendo':'sin receptor'}</span></div>`+
  `<div class=k><b>EmotiBit</b><span class="${e?'ok':(s.sin_emotibit?'':'bad')}">${e?e.hz+'/s · hr '+f(e.hr,0)+' · eda '+f(e.eda,1):(s.sin_emotibit?'apagado: pulso y piel los pone la red':'SIN DATOS')}</span></div>`+
  `<div class=k><b>Cabeza</b><span>${f(v.head_yaw)} / ${f(v.head_pitch)}</span></div><div class=k><b>Boca · sonrisa · lengua</b><span>${f(v.jaw_open)} · ${f(v.mouth_smile)} · ${f(v.tongue_out)}</span></div>`+
  `<div class=k><b>Parpadeo · cejas</b><span>${f(v.blink)} · ${f(v.brow_up)}</span></div>`+
  `<div class=k><b>Cuerpo</b><span class="${s.cuerpo?'ok':''}">${s.cuerpo?'inclina '+f(s.cuerpo.cuerpo_pitch)+' · gira '+f(s.cuerpo.cuerpo_yaw)+' · baja '+f(s.cuerpo.cuerpo_profundidad)+' · energia '+f(s.cuerpo.cuerpo_energia):'no visto'}</span></div>`;
 let h='';for(const k in A){const a=A[k],x=s.segundos[a]||0;h+=`<div class="m ${x>=60?'ok':''}"><span>${a}</span><span>${Math.round(x)} s ${x>=60?'✓':''}</span></div>`}document.getElementById('tot').innerHTML=h;
}catch(err){}}
est();setInterval(est,1000);
</script></body></html>"""
def panel_web(puerto):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as HTTPServer   # threaded (18 oct): one slow request can no longer freeze the panel and the window
    from urllib.parse import urlparse, parse_qs
    class H(BaseHTTPRequestHandler):
        timeout = 10
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="application/json"):
            b = body.encode(); self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/estado": self._send(200, json.dumps(estado_json()))
            elif u.path == "/ventana": self._send(200, VENTANA_HTML, "text/html")
            elif u.path == "/ventana_estado": self._send(200, json.dumps(ventana_estado()))
            elif u.path == "/senales":
                t = time.time(); self._send(200, json.dumps({k: [[round(x - t, 2), round(v, 3)] for x, v in list(q)] for k, q in senales.items()}))
            else: self._send(200, PANEL_HTML, "text/html")
        def do_POST(self):
            u = urlparse(self.path); c = parse_qs(u.query).get("c", [""])[0].lower()
            if u.path == "/tecla" and len(c) == 1 and c in TECLAS + "gfnrcatq": tecla(c); self._send(200, "{}")
            elif u.path == "/auto":   # autoinforme antes de la toma: valencia (0 desagradable - 10 agradable), activacion (0 calma - 10 activada)
                q = parse_qs(u.query)
                try: estado["auto"] = {"valencia": int(q.get("valencia", [""])[0]), "activacion": int(q.get("activacion", [""])[0])}
                except ValueError: self._send(400, "{}"); return
                print(f"   autoinforme: valencia {estado['auto']['valencia']}/10  activacion {estado['auto']['activacion']}/10"); self._send(200, "{}")
            elif u.path == "/olvidar": memoria_olvidar(); self._send(200, "{}")
            elif u.path == "/nombrar":   # ponerle nombre a la persona que esta ahora (conocida o nueva: se registra en el acto)
                nombre = nombre_actor(parse_qs(u.query).get("nombre", [""])[0])
                if not nombre or not visita["activa"]: self._send(400, "{}"); return
                pid = visita["id"] if visita["conocida"] else None
                if not pid:
                    f = _memoria.firma_encuentro(visita["firmas"])
                    if f is None: self._send(400, "{}"); return
                    pid = mem.registrar(f); visita.update(id=pid, conocida=True)
                mem.nombrar(pid, nombre); visita["nombre"] = nombre; print(f"   {pid} se llama {nombre}"); ventana_evento("nombre"); self._send(200, "{}")
            elif u.path == "/actor":   # cambiar de actor: cierra el tramo en curso y pide neutral nuevo
                nombre = nombre_actor(parse_qs(u.query).get("nombre", [""])[0])
                if estado["grabando"]: guardar(); estado["grabando"] = False
                estado["actor"] = nombre; cal["base"] = None; cal["muestras"] = None; parpadeo_reiniciar()
                print(f"   ACTOR: {nombre or '(sin nombre)'} - tomar NEUTRAL con esta persona antes de grabar"); self._send(200, "{}")
            else: self._send(400, "{}")
    try:
        srv = HTTPServer(("0.0.0.0" if a.panel_red else "127.0.0.1", puerto), H); srv.daemon_threads = True; print(f"   PANEL: http://localhost:{puerto}" + (" (y en la red, en la ip de esta maquina)" if a.panel_red else "")); srv.serve_forever()
    except OSError as e: print(f"   (panel web no disponible en {puerto}: {e})")
if not a.prueba and ap_panel: threading.Thread(target=panel_web, args=(ap_panel,), daemon=True).start()

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
sys.argv = [a.script]; os.chdir(HUK); sys.path.insert(0, HUK)   # ballena3 importa yakumama_alma desde Huk
runpy.run_path(a.script, run_name="__main__")
