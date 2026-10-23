#!/usr/bin/env python3
"""Fotos de las ofrendas con la camara de la ballena, para ensenarle a reconocer cada criatura.

Una ventana con la camara. Eliges una criatura (n/p o escribes su numero y Enter), la sostienes en la mano frente a la
camara, aprietas espacio y durante --segundos guarda un cuadro cada --cada segundos en la carpeta de esa criatura.
Arriba a la derecha se ve la foto de catalogo de la criatura elegida, para no confundir las que se parecen.

    venv/bin/python fotos_ofrendas.py [--fuente oak|webcam|auto] [--camara 0] [--salida ofrendas_fotos] [--quien sanam]

La camara de la ballena es la OAK-D (depthai): con --fuente auto (por defecto) la usa si esta conectada, y si no, la webcam.

Teclas:  n / p  siguiente / anterior      1..29 + Enter  ir a esa criatura      m  manos vacias   o  otras cosas   h  hermana dorada
         espacio  empezar / parar la rafaga      s  guardar un solo cuadro      q  salir

Carpetas (una por clase, los cuadros enteros tal cual los ve la camara, sin recortar ni espejar):
    ofrendas_fotos/01_ciempies/sanam_20261021_153012_417.jpg
"""
import argparse, json, os, sys, time
import cv2

AQUI = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--fuente", default="auto", choices=("auto", "oak", "webcam"), help="oak = la OAK-D de la ballena (depthai); webcam = cv2.VideoCapture; auto = OAK-D si hay, si no webcam")
ap.add_argument("--camara", type=int, default=0, help="indice de la webcam si --fuente webcam (0 = la primera)")
ap.add_argument("--salida", default=os.path.join(AQUI, "ofrendas_fotos"), help="carpeta donde van las fotos")
ap.add_argument("--quien", default="", help="quien sostiene (va en el nombre del archivo)")
ap.add_argument("--catalogo", default="", help="ofrendas.json (por defecto: docs/ofrendas/ofrendas.json o ./ofrendas.json)")
ap.add_argument("--cada", type=float, default=0.5, help="segundos entre cuadros en la rafaga")
ap.add_argument("--segundos", type=float, default=20.0, help="cuanto dura una rafaga")
ap.add_argument("--meta", type=int, default=40, help="cuadros que se quieren por clase (solo para la cuenta en pantalla)")
ap.add_argument("--ancho", type=int, default=1280); ap.add_argument("--alto", type=int, default=720)
ap.add_argument("--prueba", action="store_true", help="sin camara: cuadros sinteticos, guarda 3 y sale (para probar que todo corre)")
a = ap.parse_args()

# ---- clases: las 29 criaturas del catalogo + las tres de 'no es una ofrenda' ----
cat = a.catalogo or next((p for p in (os.path.join(AQUI, "docs", "ofrendas", "ofrendas.json"), os.path.join(AQUI, "catalogo", "ofrendas.json"), os.path.join(AQUI, "ofrendas.json")) if os.path.exists(p)), "")
if not cat: sys.exit("no encuentro ofrendas.json (pasa --catalogo)")
CARPETA_CAT = os.path.dirname(os.path.abspath(cat))
d = json.load(open(cat))
clases = [{"carpeta": os.path.splitext(c["archivo"])[0], "nombre": f"{c['id']:02d} {c['nombre']}", "foto": os.path.join(CARPETA_CAT, c["archivo"]), "id": c["id"]} for c in d["criaturas"]]
EXTRA = {"m": ("manos_vacias", "manos vacias (sin nada)"), "o": ("otras_cosas", "otras cosas en la mano (celular, llaves, taza, lapiz...)"), "h": ("hermana_dorada", "la hermana dorada")}
for k, (carp, nom) in EXTRA.items(): clases.append({"carpeta": carp, "nombre": nom, "foto": "", "id": None, "tecla": k})
os.makedirs(a.salida, exist_ok=True)
for c in clases: os.makedirs(os.path.join(a.salida, c["carpeta"]), exist_ok=True)
def cuantas(c): return len([f for f in os.listdir(os.path.join(a.salida, c["carpeta"])) if f.lower().endswith(".jpg")])

# ---- camara ----
if a.prueba:
    import numpy as np
    class Cam:
        def read(self): fr = np.full((a.alto, a.ancho, 3), 90, np.uint8); cv2.putText(fr, "PRUEBA sin camara", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 2); return True, fr
        def release(self): pass
    cap = Cam()
else:
    cap = None
    if a.fuente in ("auto", "oak"):
        try:
            import depthai as dai
            if not dai.Device.getAllAvailableDevices(): raise RuntimeError("no hay OAK-D conectada por USB")
            class CamOak:
                """la OAK-D por depthai: el sensor de color, cuadro BGR de --ancho x --alto (el mismo ojo que tiene la ballena)."""
                def __init__(self):
                    pl = dai.Pipeline(); cam = pl.create(dai.node.ColorCamera); cam.setCamera("color"); cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
                    cam.setPreviewSize(a.ancho, a.alto); cam.setPreviewKeepAspectRatio(True); cam.setInterleaved(False); cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR); cam.setFps(15)
                    xo = pl.create(dai.node.XLinkOut); xo.setStreamName("rgb"); cam.preview.link(xo.input)
                    self.dev = dai.Device(pl); self.q = self.dev.getOutputQueue(name="rgb", maxSize=2, blocking=False)
                def read(self):
                    m = self.q.tryGet()
                    return (True, m.getCvFrame()) if m is not None else (False, None)
                def release(self): self.dev.close()
            cap = CamOak(); fr = None
            for _ in range(100):
                ok, fr = cap.read()
                if ok: break
                time.sleep(0.05)
            if fr is None: raise RuntimeError("la OAK-D no entrega cuadros")
            print(f"   OAK-D: {fr.shape[1]}x{fr.shape[0]}")
        except Exception as e:
            if a.fuente == "oak": sys.exit(f"OAK-D: {e}")
            print(f"   (sin OAK-D: {e}; uso la webcam {a.camara})"); cap = None
    if cap is None:
        cap = cv2.VideoCapture(a.camara)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.ancho); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.alto)
        ok, fr = cap.read()
        if not ok: sys.exit(f"no abre la webcam {a.camara} (prueba --camara 1, y en Ajustes > Privacidad > Camara permite Terminal)")
        print(f"   webcam {a.camara}: {fr.shape[1]}x{fr.shape[0]}")
print(f"   {len(clases)} clases -> {a.salida}")

# ---- estado ----
i = 0; rafaga_fin = 0.0; ultimo = 0.0; escribiendo = ""; aviso = ""; aviso_t = 0.0; guardados_sesion = 0
mini = {}
def miniatura(c):
    if c["carpeta"] not in mini:
        im = cv2.imread(c["foto"]) if c["foto"] else None
        if im is not None:
            h = 220; w = int(im.shape[1] * h / im.shape[0]); im = cv2.resize(im, (w, h))
        mini[c["carpeta"]] = im
    return mini[c["carpeta"]]
def guardar(fr, c):
    global guardados_sesion
    nombre = f"{(a.quien + '_') if a.quien else ''}{time.strftime('%Y%m%d_%H%M%S')}_{int((time.time() % 1) * 1000):03d}.jpg"
    cv2.imwrite(os.path.join(a.salida, c["carpeta"], nombre), fr, [cv2.IMWRITE_JPEG_QUALITY, 92]); guardados_sesion += 1
def ir_a(n):
    global i, aviso, aviso_t
    for k, c in enumerate(clases):
        if c["id"] == n: i = k; return
    aviso = f"no hay criatura {n}"; aviso_t = time.time()

cv2.namedWindow("ofrendas", cv2.WINDOW_NORMAL)
if a.prueba: pruebas = 0
while True:
    ok, fr = cap.read()
    if not ok: time.sleep(0.05); continue
    t = time.time(); c = clases[i]; grabando = t < rafaga_fin
    if grabando and t - ultimo >= a.cada: ultimo = t; guardar(fr, c)
    # ---- pantalla (espejada para que sea comodo; lo guardado no se espeja) ----
    v = cv2.flip(fr, 1); H, W = v.shape[:2]
    cv2.rectangle(v, (0, 0), (W, 96), (0, 0, 0), -1)
    n = cuantas(c); color = (80, 220, 80) if n >= a.meta else (255, 255, 255)
    cv2.putText(v, c["nombre"][:70], (16, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(v, f"{n}/{a.meta} fotos en esta carpeta   |   sesion: {guardados_sesion}", (16, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    if grabando:
        cv2.circle(v, (W - 40, 48), 16, (0, 0, 255), -1); cv2.putText(v, f"GRABANDO {rafaga_fin - t:4.1f}s", (W - 330, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    m = miniatura(c)
    if m is not None:
        mh, mw = m.shape[:2]; v[110:110 + mh, W - mw - 12:W - 12] = m; cv2.rectangle(v, (W - mw - 12, 110), (W - 12, 110 + mh), (255, 255, 255), 2)
    pie = f"numero: {escribiendo}_" if escribiendo else "n/p siguiente/anterior   numero+Enter   m manos   o otras cosas   h hermana   espacio rafaga   s una foto   q salir"
    cv2.rectangle(v, (0, H - 40), (W, H), (0, 0, 0), -1); cv2.putText(v, pie, (16, H - 13), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    if t - aviso_t < 2: cv2.putText(v, aviso, (16, H - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
    cv2.imshow("ofrendas", v)
    k = cv2.waitKey(1) & 0xFF
    if a.prueba:
        pruebas += 1
        if pruebas == 2: rafaga_fin = t + 2.0
        if pruebas > 60: break
        time.sleep(0.05); continue
    if k == 255: continue
    ch = chr(k) if k < 128 else ""
    if ch.isdigit(): escribiendo += ch
    elif k in (13, 10) and escribiendo: ir_a(int(escribiendo)); escribiendo = ""
    elif k == 27: escribiendo = ""
    elif ch == "q": break
    elif ch == "n": i = (i + 1) % len(clases); rafaga_fin = 0
    elif ch == "p": i = (i - 1) % len(clases); rafaga_fin = 0
    elif ch in EXTRA: i = next(k_ for k_, c_ in enumerate(clases) if c_["carpeta"] == EXTRA[ch][0]); rafaga_fin = 0
    elif ch == " ": rafaga_fin = 0 if grabando else t + a.segundos; ultimo = 0
    elif ch == "s": guardar(fr, c); aviso = "guardada"; aviso_t = t
cap.release(); cv2.destroyAllWindows()
print(f"   {guardados_sesion} fotos guardadas en esta sesion. Por clase:")
for c in clases: print(f"   {cuantas(c):4d}  {c['carpeta']}")
