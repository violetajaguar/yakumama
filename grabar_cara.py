#!/usr/bin/env python3
"""grabar_cara.py - dataset de expresiones faciales de Yakumama con la webcam, grabado mientras actuas.

Como con la llama (llama_recorder.py), pero mejor:
  - la cara no son 7 numeros derivados a mano: son los 52 blendshapes de MediaPipe (boca, cejas, parpados,
    mejillas, nariz, lengua...) + la pose de la cabeza (yaw, pitch, roll), a 30 cuadros por segundo;
  - los 10 animos de la ballena (MOOD_KEYS de ballena3.py);
  - cada linea guarda ademas el paquete de cara que el receptor de whale.blend entiende (head_yaw, head_pitch,
    jaw_open, blink, brow_up, brow_down, mouth_sad), y se lo manda en vivo por UDP 9998: si Blender esta abierto
    con el receptor, ves a Yakumama sentir lo que actuas SIN la OAK-D (no correr ballena3.py al mismo tiempo);
  - auto-calibracion: los primeros 3 segundos mira de frente, neutra; eso es el cero.

USO
  Terminal 1 (opcional): Blender con whale.blend y su receptor corriendo
  Terminal 2:            cd ~/Desktop/Yakumama && venv/bin/python grabar_cara.py [--camara 0] [--sin_udp]

TECLAS (en la ventana)
  1-9, 0   elegir animo (el menu esta en pantalla)
  ESPACIO  pausa / sigue        c  recalibrar (mira de frente 3 s)
  ENTER    cierra el tramo y lo guarda (una emocion por archivo)
  ESC      guarda y sale

SALIDA  ~/Desktop/Yakumama/datasets/cara_webcam/<animo>_NNN.jsonl  (una linea por cuadro) y manifest.json con los nombres.
"""
import cv2, json, os, sys, time, socket, math, argparse
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "datasets", "cara_webcam"); os.makedirs(SALIDA, exist_ok=True)
MODELO = os.path.join(AQUI, "modelos", "face_landmarker.task")
EMOCIONES = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
TECLAS = "1234567890"
assert len(TECLAS) == len(EMOCIONES)

ap = argparse.ArgumentParser()
ap.add_argument("--camara", type=int, default=0)
ap.add_argument("--sin_udp", action="store_true")
ap.add_argument("--prueba", action="store_true", help="sin camara: carga el modelo, procesa un cuadro sintetico y sale")
a = ap.parse_args()

opts = vision.FaceLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path=MODELO),
    output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1,
    running_mode=vision.RunningMode.VIDEO)
lm = vision.FaceLandmarker.create_from_options(opts)

def pose_cabeza(M):
    """yaw, pitch, roll en grados de la matriz 4x4 de MediaPipe (camara mira a -Z)."""
    R = np.array(M)[:3, :3]
    pitch = math.degrees(math.atan2(-R[2, 1], R[2, 2])); yaw = math.degrees(math.asin(max(-1, min(1, R[2, 0]))))
    roll = math.degrees(math.atan2(-R[1, 0], R[0, 0]))
    return yaw, pitch, roll

def paquete_huk(bs, yaw, pitch, cero):
    """lo que entiende el receptor de whale.blend (los mismos campos que manda ballena3.py), derivado de los
    blendshapes. Rango [-1,1] para la cabeza, [0,1] para el resto."""
    g = lambda k: bs.get(k, 0.0)
    return {
        "head_yaw":  max(-1.0, min(1.0, (yaw - cero["yaw"]) / 30.0)),
        "head_pitch": max(-1.0, min(1.0, (pitch - cero["pitch"]) / 25.0)),
        "jaw_open":  max(0.0, min(1.0, g("jawOpen") * 1.4)),
        "blink":     max(0.0, min(1.0, (g("eyeBlinkLeft") + g("eyeBlinkRight")) / 2)),
        "brow_up":   max(0.0, min(1.0, (g("browInnerUp") + g("browOuterUpLeft") + g("browOuterUpRight")) / 3)),
        "brow_down": max(0.0, min(1.0, (g("browDownLeft") + g("browDownRight")) / 2)),
        "mouth_sad": max(0.0, min(1.0, (g("mouthFrownLeft") + g("mouthFrownRight")) / 2)),
        "t": time.time(),
    }

if a.prueba:
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((480, 640, 3), np.uint8))
    r = lm.detect_for_video(img, 0); print("modelo ok; caras en cuadro negro:", len(r.face_landmarks)); sys.exit(0)

sock = None if a.sin_udp else socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cap = cv2.VideoCapture(a.camara)
if not cap.isOpened(): print("no abre la camara", a.camara); sys.exit(1)
nombres_bs = None; cero = {"yaw": 0.0, "pitch": 0.0}; cal_hasta = time.time() + 3.0; cal_acum = []
emocion = None; grabando = False; tramo = []; t0 = time.time(); contador = {}

def guardar():
    global tramo
    if emocion and tramo:
        n = len([f for f in os.listdir(SALIDA) if f.startswith(emocion + "_")]) + 1
        ruta = os.path.join(SALIDA, f"{emocion}_{n:03d}.jsonl")
        with open(ruta, "w") as fh:
            for rec in tramo: fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        contador[emocion] = contador.get(emocion, 0) + len(tramo)
        print(f"   guardado {ruta} ({len(tramo)} cuadros, {len(tramo)/30:.0f} s)")
    tramo = []

print("Yakumama - grabador de cara (webcam). Mira de frente, neutra, 3 segundos (calibra)...")
while True:
    ok, fr = cap.read()
    if not ok: break
    fr = cv2.flip(fr, 1)
    rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
    r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int((time.time() - t0) * 1000))
    ahora = time.time(); rec = None
    if r.face_blendshapes:
        bsl = r.face_blendshapes[0]
        if nombres_bs is None:
            nombres_bs = [c.category_name for c in bsl]
            json.dump({"blendshapes": nombres_bs, "emociones": EMOCIONES, "fps": 30}, open(os.path.join(SALIDA, "manifest.json"), "w"), ensure_ascii=False, indent=1)
        bs = {c.category_name: float(c.score) for c in bsl}
        yaw, pitch, roll = pose_cabeza(r.facial_transformation_matrixes[0]) if r.facial_transformation_matrixes else (0, 0, 0)
        if ahora < cal_hasta: cal_acum.append((yaw, pitch))
        elif cal_acum: cero = {"yaw": float(np.median([c[0] for c in cal_acum])), "pitch": float(np.median([c[1] for c in cal_acum]))}; cal_acum = []; print(f"   calibrado: yaw {cero['yaw']:.1f} pitch {cero['pitch']:.1f}")
        huk = paquete_huk(bs, yaw, pitch, cero)
        if sock:
            try: sock.sendto(json.dumps(huk).encode(), ("127.0.0.1", 9998))
            except Exception: pass
        if grabando and emocion and ahora >= cal_hasta:
            rec = {"t": round(ahora - t0, 3), "emocion": emocion, "bs": [round(bs[k], 4) for k in nombres_bs],
                   "cabeza": [round(yaw - cero["yaw"], 2), round(pitch - cero["pitch"], 2), round(roll, 2)],
                   "ballena": {k: round(v, 3) for k, v in huk.items() if k != "t"}}
            tramo.append(rec)
    # pantalla
    y = 22
    for i, (k, e) in enumerate(zip(TECLAS, EMOCIONES)):
        col = (0, 255, 0) if e == emocion else (200, 200, 200)
        cv2.putText(fr, f"{k}:{e}", (10, y + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1)
    estado = "CALIBRANDO: mira de frente" if ahora < cal_hasta else (f"GRABANDO {emocion} {len(tramo)/30:.0f}s" if grabando else f"pausa ({emocion or 'elige emocion'})")
    cv2.putText(fr, estado, (10, fr.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255) if grabando else (255, 255, 0), 2)
    cv2.putText(fr, "ESPACIO graba/pausa  ENTER cierra tramo  c calibra  ESC sale", (10, fr.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imshow("Yakumama - cara", fr)
    k = cv2.waitKey(1) & 0xFF
    if k == 27: break
    elif k == 32: grabando = not grabando
    elif k in (10, 13): guardar(); grabando = False
    elif k == ord("c"): cal_hasta = time.time() + 3.0; cal_acum = []
    elif chr(k) in TECLAS and (emocion is None or not tramo):
        emocion = EMOCIONES[TECLAS.index(chr(k))]; print("   emocion:", emocion)
    elif chr(k) in TECLAS and tramo:
        guardar(); emocion = EMOCIONES[TECLAS.index(chr(k))]; print("   emocion:", emocion)
guardar(); cap.release(); cv2.destroyAllWindows()
print("\nResumen de esta sesion:"); [print(f"   {e:14s} {n/30:6.0f} s") for e, n in sorted(contador.items())]
