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
import os, sys, json, time, socket, threading, runpy, argparse, re, unicodedata
AQUI = os.path.dirname(os.path.abspath(__file__)); HUK = os.path.expanduser("~/Desktop/Huk")
SAL_CARA = os.path.join(AQUI, "datasets", "cara"); SAL_CUERPO = os.path.join(AQUI, "datasets", "cuerpo"); SAL_VIDEO = os.path.join(AQUI, "datasets", "video")
os.makedirs(SAL_CARA, exist_ok=True); os.makedirs(SAL_CUERPO, exist_ok=True); os.makedirs(SAL_VIDEO, exist_ok=True)
ANIMOS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
TECLAS = "1234567890"
CARA = ("head_yaw", "head_pitch", "head_roll", "jaw_open", "blink", "blink_l", "blink_r", "brow_up", "brow_down",
        "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch", "tongue_out", "asombrado", "angry", "sad", "parpadeo")
PUERTO_BLENDER = 9998
ap = argparse.ArgumentParser(); ap.add_argument("--prueba", action="store_true"); ap.add_argument("--script", default=os.path.join(HUK, "ballena3.py"))
ap.add_argument("--emotibit", type=int, default=12345, help="puerto OSC donde escucha al EmotiBit Oscilloscope (0 = no)")
ap.add_argument("--emotibit-directo", type=int, default=1, help="1 = conectar directo al EmotiBit por WiFi, sin Oscilloscope (0 = no)")
ap.add_argument("--emotibit-ip", default="", help="IP del EmotiBit (vacio = buscarlo por broadcast)")
ap.add_argument("--panel", type=int, default=8765, help="puerto del panel web (0 = sin panel)")
ap.add_argument("--espejo", action="append", default=[], help="host:puerto que recibe una copia de cada paquete (TouchDesigner, ballena fisica); repetible")
ap.add_argument("--visitas", type=int, default=1, help="1 = guardar cada encuentro con una visita (datasets/visitas/) y recordarla en datasets/memoria.json; 0 = no")
ap.add_argument("--actor", default="", help="nombre de quien actua; va en el nombre del tramo: <animo>_<actor>_NNN (tambien se cambia en el panel)")
ap.add_argument("--video", type=int, default=0, help="1 = grabar la ventana de Blender de g a f (apagado por defecto)")
a = ap.parse_args()
HUK = os.path.dirname(os.path.abspath(a.script))   # la carpeta de ballena3.py (whale.blend, yakumama_alma): --script la fija en otra maquina

def nombre_actor(x):
    """'Ana María' -> 'anamaria': sin acentos, espacios ni guiones bajos (el _ separa animo, actor y numero)."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower())
estado = {"auto": {"valencia": None, "activacion": None}, "actor": nombre_actor(a.actor), "animo": None, "grabando": False, "solo_cara": 0, "anclada": False, "cara": [], "cuerpo": [], "t0": time.time(), "n": {}, "ultimo": {}, "seg": {}}
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
        estado["auto"] = {"valencia": None, "activacion": None}
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
def blendshapes(rgb, lm=None):
    """llena `extra` a partir del cuadro RGB (numpy HxWx3). lm: landmarker (se carga solo la primera vez)."""
    import mediapipe as mp
    lm = lm or _lm["lm"] or cargar_landmarker(); _lm["lm"] = lm
    _lm["n"] += 1
    if _lm["lento"] and _lm["n"] % 2: return          # si tarda mas de 20 ms, un cuadro si y uno no
    t = time.time()
    r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int((t - _lm["t0"]) * 1000))
    _lm["lento"] = (time.time() - t) > 0.02
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
        threading.Thread(target=_lm_hilo, daemon=True).start()
        def process_tee(self, image):
            res = _process(self, image)
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
    if reconocedor["estilo"] is None and reconocedor["estilo_n"] >= 4:   # 4 ventanas = 2 s de cara
        top = max(ema, key=ema.get); reconocedor["estilo"] = top; print(f"   se parece a: {top} ({ema[top]:.0%}) - la ballena le contesta con su estilo")
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
            visita.update(activa=True, t0=ahora, regs=[], firmas=[], id=None, conocida=None, dist=None, estilo_previo=None); print("   visita: alguien llego")
        visita["ultima_cara"] = ahora
        r = {"t": round(ahora - visita["t0"], 3), **{k: pkt[k] for k in CAMPOS_VISITA if k in pkt}, **{k: v for k, v in pkt.items() if k.startswith("face_") or k.startswith("actor_") or k.startswith("parecido_")}}
        if emotibit_vivo(): r.update(emotibit_vivo())
        visita["regs"].append(r)
        if visita["id"] is None and len(visita["firmas"]) >= _memoria.MIN_CUADROS: memoria_reconocer()
    elif visita["activa"] and ahora - visita["ultima_cara"] > 8.0: encuentro_cerrar()
def memoria_reconocer():
    f = _memoria.firma_encuentro(visita["firmas"])
    if f is None: return
    pid, d = mem.buscar(f); visita["dist"] = round(d, 4)
    if pid:
        p = mem.personas[pid]; visita.update(id=pid, conocida=True, estilo_previo=p.get("estilo"))
        print(f"   TE CONOZCO: {pid}, visita numero {p['visitas'] + 1}, la otra vez le conteste como {p.get('estilo') or 'nadie'} (distancia {d:.3f})")
        if p.get("estilo") and reconocedor["estilo"] is None: reconocedor["estilo"] = p["estilo"]; reconocedor["estilo_n"] = 99   # la saluda con su estilo de la otra vez
    else: visita.update(id="nueva", conocida=False); print(f"   cara nueva (la mas parecida esta a {d:.3f}; umbral {_memoria.UMBRAL})")
def encuentro_cerrar():
    if not visita["activa"]: return
    regs = visita["regs"]; dur = (visita["ultima_cara"] - visita["t0"]) if visita["t0"] else 0; visita["activa"] = False
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
    if reconocedor["n"] >= 3 and reconocedor["animo"] != top:
        reconocedor["animo"] = top; print(f"   la ballena ve: {top}")

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
                crudo = json.loads(data.decode()); pkt = parpadeo(calibrar({**crudo, **extra})); reconocer(pkt, crudo)
                if reconocedor["animo"] and reconocedor["prob"]: pkt = {**pkt, "actor_animo": reconocedor["animo"], **{"actor_" + m: q for m, q in reconocedor["prob"].items()}}
                if reconocedor["estilo"]: pkt = {**pkt, "estilo": reconocedor["estilo"], **{"parecido_" + a: q for a, q in reconocedor["estilo_prob"].items()}}
                if visita["activa"] and visita["id"]: pkt = {**pkt, "visita": visita["id"], "conocida": 1 if visita["conocida"] else 0}
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
def estado_json():
    u = estado["ultimo"]; segs = {an: 0.0 for an in ANIMOS}
    try:
        for f in os.listdir(SAL_CARA):
            an = f.rsplit("_", 1)[0]
            if an in segs: segs[an] += segundos_archivo(os.path.join(SAL_CARA, f))
    except Exception: pass
    try: rx = json.load(open("/tmp/ballena_receptor.json")); blender = (time.time() - rx.get("t", 0)) < 6
    except Exception: blender = False
    cara = bool(u) and u.get("head_yaw") is not None and estado.get("_yaw_prev") != u.get("head_yaw")
    estado["_yaw_prev"] = u.get("head_yaw") if u else None
    return {"modo": ("cuerpo", "solo cara", "solo cara, cabeza fija")[estado["solo_cara"]] + (" + anclada" if estado["anclada"] else ""),
            "auto": estado["auto"], "actor": estado["actor"], "animo": estado["animo"], "grabando": estado["grabando"], "tramo_s": segundos([r["t"] for r in estado["cara"]]) if estado["cara"] else 0.0,
            "neutral": bool(cal["base"]), "cara": cara, "blender": blender, "segundos": segs, "detectado": reconocedor["animo"], "prob": reconocedor["prob"],
            "estilo": reconocedor["estilo"], "estilo_prob": reconocedor["estilo_prob"], "sin_emotibit": not (a.emotibit or a.emotibit_directo),
            "memoria": {"aprender": bool(a.visitas) and not estado["actor"], "activa": visita["activa"], "id": visita["id"], "conocida": visita["conocida"], "dist": visita["dist"],
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
<div class=row><input id=actor placeholder="quien actua (nombre)" style="border:0;border-radius:12px;padding:14px 16px;font-size:17px;background:var(--card);color:var(--fg);min-width:200px"><button class=b onclick="setActor()">Cambiar actor</button><button class="b off" onclick="if(confirm('Olvidar a la persona que esta ahora?'))fetch('/olvidar',{method:'POST'})">Olvidar a esta persona</button></div>
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
  `<div class=k><b>Memoria</b><span class="${s.memoria&&s.memoria.conocida?'ok':''}">${!s.memoria||!s.memoria.aprender?'apagada':(!s.memoria.activa?'nadie':(s.memoria.conocida?'te conozco · visita '+s.memoria.visitas+(s.memoria.estilo_previo?' · estilo '+s.memoria.estilo_previo:''):(s.memoria.id=='nueva'?'cara nueva':'mirando…')))}</span><small class=small>${s.memoria?s.memoria.personas+' personas · '+s.memoria.guardadas+' visitas guardadas hoy':''}</small></div>`+
  `<div class=k><b>Se parece a</b><span class="${s.estilo?'ok':''}">${s.estilo||'—'}</span>${s.estilo_prob&&s.estilo?'<small class=small>'+Math.round((s.estilo_prob[s.estilo]||0)*100)+' %</small>':''}</div>`+
  `<div class=k><b>Neutral</b><span class="${s.neutral?'ok':'bad'}">${s.neutral?'tomado':'falta: Neutral'}</span></div>`+
  `<div class=k><b>Blender</b><span class="${s.blender?'ok':'bad'}">${s.blender?'recibiendo':'sin receptor'}</span></div>`+
  `<div class=k><b>EmotiBit</b><span class="${e?'ok':(s.sin_emotibit?'':'bad')}">${e?e.hz+'/s · hr '+f(e.hr,0)+' · eda '+f(e.eda,1):(s.sin_emotibit?'apagado: pulso y piel los pone la red':'SIN DATOS')}</span></div>`+
  `<div class=k><b>Cabeza</b><span>${f(v.head_yaw)} / ${f(v.head_pitch)}</span></div><div class=k><b>Boca · sonrisa · lengua</b><span>${f(v.jaw_open)} · ${f(v.mouth_smile)} · ${f(v.tongue_out)}</span></div>`+
  `<div class=k><b>Parpadeo · cejas</b><span>${f(v.blink)} · ${f(v.brow_up)}</span></div>`;
 let h='';for(const k in A){const a=A[k],x=s.segundos[a]||0;h+=`<div class="m ${x>=60?'ok':''}"><span>${a}</span><span>${Math.round(x)} s ${x>=60?'✓':''}</span></div>`}document.getElementById('tot').innerHTML=h;
}catch(err){}}
est();setInterval(est,1000);
</script></body></html>"""
def panel_web(puerto):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import urlparse, parse_qs
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="application/json"):
            b = body.encode(); self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/estado": self._send(200, json.dumps(estado_json()))
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
            elif u.path == "/actor":   # cambiar de actor: cierra el tramo en curso y pide neutral nuevo
                nombre = nombre_actor(parse_qs(u.query).get("nombre", [""])[0])
                if estado["grabando"]: guardar(); estado["grabando"] = False
                estado["actor"] = nombre; cal["base"] = None; cal["muestras"] = None; parpadeo_reiniciar()
                print(f"   ACTOR: {nombre or '(sin nombre)'} - tomar NEUTRAL con esta persona antes de grabar"); self._send(200, "{}")
            else: self._send(400, "{}")
    try:
        srv = HTTPServer(("127.0.0.1", puerto), H); print(f"   PANEL: http://localhost:{puerto}"); srv.serve_forever()
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
