#!/usr/bin/env python3
"""importar_video_cuerpo.py - el CUERPO de cualquier video (apneistas, clavadistas, ballet, lo que sea) al mismo esqueleto
de 26 puntos de Paqarina, para que la ballena lo copie en vivo (bailar.py) y para aprender (jepa_datos / hjepa).

Corre el Pose Landmarker de MediaPipe (modelos/pose_landmarker_lite.task) a 12 cuadros/s sobre el video, toma los
puntos 3D del mundo (metros, centrados en la cadera) y los pasa al orden de Paqarina exactamente como lo hace el
grabador (cuerpo_pose en grabar_ballena.py: x, z, -y). Guarda datasets/cuerpo_video/<nombre>.npz con body, joint_names,
fps (lo que lee cuerpo_cualidades.cargar_npz, asi bailar.py lo conduce igual que a Galgo) e imprime cuantos cuadros
tuvieron cuerpo y como se mueve (cuerpo_*).

    venv/bin/python importar_video_cuerpo.py ~/Desktop/freediving/*.mp4
    venv/bin/python bailar.py datasets/cuerpo_video/freediver_01.npz --solo-cuerpo --loop     -> ella lo copia
"""
import os, sys, time, argparse, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from cuerpo_cualidades import cualidades_toma, CUERPO
FPS = 12.0
NOMBRES = ["nose", "eye_l", "eye_r", "ear_l", "ear_r", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "wrist_l", "wrist_r", "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head", "neck", "pelvis", "bigtoe_l", "bigtoe_r", "smalltoe_l", "smalltoe_r", "heel_l", "heel_r"]
POSE_J = {"head": 0, "shoulder_l": 11, "shoulder_r": 12, "elbow_l": 13, "elbow_r": 14, "wrist_l": 15, "wrist_r": 16, "hip_l": 23, "hip_r": 24, "knee_l": 25, "knee_r": 26, "ankle_l": 27, "ankle_r": 28,
          "nose": 0, "eye_l": 2, "eye_r": 5, "ear_l": 7, "ear_r": 8, "bigtoe_l": 31, "bigtoe_r": 32, "heel_l": 29, "heel_r": 30}
J = {n: i for i, n in enumerate(NOMBRES)}
def landmarker():
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    return vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=os.path.join(AQUI, "modelos", "pose_landmarker_lite.task")), running_mode=vision.RunningMode.VIDEO, min_pose_detection_confidence=0.4, min_tracking_confidence=0.4))
def fila_de(L):
    f = np.full((len(NOMBRES), 3), np.nan)
    def P(i): return np.array([L[i].x, L[i].z, -L[i].y]) if L[i].visibility > 0.4 else np.array([np.nan] * 3)
    for nom, i in POSE_J.items(): f[J[nom]] = P(i)
    f[J["pelvis"]] = (P(23) + P(24)) / 2; f[J["neck"]] = (P(11) + P(12)) / 2; return f
def importar(ruta, lm, prefijo=""):
    import cv2, mediapipe as mp
    cap = cv2.VideoCapture(ruta); fps_v = cap.get(cv2.CAP_PROP_FPS) or 24.0; n_v = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); paso = max(1, int(round(fps_v / FPS)))
    B = []; vistos = 0; k = 0; t0 = time.time()
    while True:
        ok, bgr = cap.read()
        if not ok: break
        if k % paso: k += 1; continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB); r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(k / fps_v * 1000))
        if r.pose_world_landmarks: B.append(fila_de(r.pose_world_landmarks[0])); vistos += 1
        else: B.append(np.full((len(NOMBRES), 3), np.nan))
        k += 1
    cap.release(); B = np.array(B); nombre = (prefijo + "_" if prefijo else "") + os.path.splitext(os.path.basename(ruta))[0]
    sal = os.path.join(AQUI, "datasets", "cuerpo_video"); os.makedirs(sal, exist_ok=True)
    np.savez_compressed(os.path.join(sal, nombre + ".npz"), body=B.astype(np.float32), joint_names=np.array(NOMBRES), fps=fps_v / paso, origen="video", archivo=os.path.basename(ruta))
    q = cualidades_toma(B, J, fps_v / paso) if vistos >= 12 else {}
    res = " ".join(f"{c[7:]} {np.nanmean(q[c]):+.2f}±{np.nanstd(q[c]):.2f}" for c in CUERPO if c in q and np.isfinite(q[c]).any())
    print(f"  {nombre}: {len(B)} cuadros, cuerpo en {100 * vistos / max(1, len(B)):.0f}% | {res} ({time.time() - t0:.0f} s)", flush=True)
    return vistos, len(B)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("videos", nargs="+"); ap.add_argument("--prefijo", default="", help="nombre de salida <prefijo>_<video>.npz: el prefijo dice el animo en jepa_datos (freediver/diving48 -> diving, tinku -> angry, ballet -> sad)")
    ap.add_argument("--max", type=int, default=0, help="procesar como mucho N videos"); a = ap.parse_args(); tv = tn = 0
    for ruta in (a.videos[:a.max] if a.max else a.videos):
        v, n = importar(ruta, landmarker(), a.prefijo); tv += v; tn += n   # un landmarker por video (los tiempos deben crecer)
    print(f"total: cuerpo en {100 * tv / max(1, tn):.0f}% de {tn} cuadros ({tn / FPS:.0f} s) -> datasets/cuerpo_video/")
