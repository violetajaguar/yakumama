#!/usr/bin/env python3
"""importar_imperial.py - ImperialDance (Zhong & Demiris, AAAI 2024; github.com/YunZhongNikki/ImperialDance-Dataset):
captura de movimiento OptiTrack, 21 puntos a 100 cuadros/s, cinco generos (ballet, k-pop, jazz, hip-hop, urban), cinco
coreografias por genero, tres niveles (experta, intermedia, principiante), 100 repeticiones de 10 s cada una.
Cada archivo dance_level_<nivel>_<genero>_ch<k>.npy es (100, 3, 1000, 21): muestras, xyz, cuadros, puntos.

Lo pasa al esqueleto de 26 puntos de Paqarina (datasets/cuerpo_video/<prefijo>_<nivel>_ch<k>_<muestra>.npz, a 25 cuadros/s)
para que jepa_datos lo tome con el animo de su prefijo: ballet -> sad. Los otros generos entran con su nombre (kpop,
jazz, hiphop, urban), sin animo, salvo que se mapeen en jepa_datos.VIDEO_ANIMO.

    venv_datos/bin/python importar_imperial.py ~/Desktop/imperialdance --generos b        (solo ballet)
    venv_datos/bin/python importar_imperial.py ~/Desktop/imperialdance --generos b,k,j,h,u --muestras 20
"""
import os, sys, glob, argparse, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
PUNTOS = ["RShin", "RToe", "RThigh", "LThigh", "LFoot", "RShoulder", "LHand", "RHand", "LFArm", "LShoulder", "RFoot", "Neck", "LShin", "Chest", "Head", "LToe", "Ab", "RUArm", "LUArm", "Hip", "RFArm"]
I = {n: i for i, n in enumerate(PUNTOS)}
NOMBRES = ["nose", "eye_l", "eye_r", "ear_l", "ear_r", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "wrist_l", "wrist_r", "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head", "neck", "pelvis", "bigtoe_l", "bigtoe_r", "smalltoe_l", "smalltoe_r", "heel_l", "heel_r"]
# OptiTrack da centros de segmento: el muslo hace de cadera, la espinilla de rodilla, el antebrazo de codo
MAPA = {"head": "Head", "nose": "Head", "neck": "Neck", "pelvis": "Hip", "shoulder_l": "LShoulder", "shoulder_r": "RShoulder", "elbow_l": "LFArm", "elbow_r": "RFArm", "wrist_l": "LHand", "wrist_r": "RHand",
        "hip_l": "LThigh", "hip_r": "RThigh", "knee_l": "LShin", "knee_r": "RShin", "ankle_l": "LFoot", "ankle_r": "RFoot", "bigtoe_l": "LToe", "bigtoe_r": "RToe", "heel_l": "LFoot", "heel_r": "RFoot"}
GENERO = {"b": "ballet", "k": "kpop", "j": "jazz", "h": "hiphop", "u": "urban"}; NIVEL = {"e": "experta", "i": "intermedia", "b": "principiante"}
def convertir(S):
    """S: (3, 1000, 21) -> (1000, 26, 3) con z arriba y metros (altura cabeza-cadera ~ 0.75 m)."""
    P = np.transpose(S, (1, 2, 0)).astype(np.float64)   # (cuadros, puntos, xyz)
    arriba = int(np.argmax(np.abs((P[:, I["Head"]] - P[:, I["Hip"]]).mean(0))))   # el eje donde la cabeza esta lejos de la cadera es el vertical
    orden = [a for a in range(3) if a != arriba] + [arriba]; P = P[:, :, orden]
    if (P[:, I["Head"], 2] - P[:, I["Hip"], 2]).mean() < 0: P[:, :, 2] *= -1
    alto = float(np.abs(P[:, I["Head"], 2] - P[:, I["Hip"], 2]).mean()); P = P / max(1e-6, alto) * 0.75
    B = np.full((len(P), len(NOMBRES), 3), np.nan)
    for k, nombre in enumerate(NOMBRES):
        if nombre in MAPA: B[:, k] = P[:, I[MAPA[nombre]]]
    return B
def importar(carpeta, generos, muestras, cada):
    sal = os.path.join(AQUI, "datasets", "cuerpo_video"); os.makedirs(sal, exist_ok=True); total = 0; n_arch = 0
    for f in sorted(glob.glob(os.path.join(carpeta, "**", "dance_level_*.npy"), recursive=True)):
        base = os.path.basename(f)[:-4].split("_"); nivel, gen, ch = base[2], base[3], base[4]
        if gen not in generos: continue
        A = np.load(f, mmap_mode="r"); n = min(muestras, A.shape[0]) if muestras else A.shape[0]
        for m in range(n):
            B = convertir(np.asarray(A[m]))[::cada]
            np.savez_compressed(os.path.join(sal, f"{GENERO[gen]}_{NIVEL[nivel]}_{ch}_{m:03d}.npz"), body=B.astype(np.float32), joint_names=np.array(NOMBRES), fps=100.0 / cada, origen="imperialdance", archivo=os.path.basename(f))
            total += len(B) / (100.0 / cada)
        n_arch += 1; print(f"  {os.path.basename(f)}: {n} muestras de 10 s -> {GENERO[gen]} {NIVEL[nivel]} {ch}", flush=True)
    print(f"importados {total / 60:.0f} min de {n_arch} archivos -> datasets/cuerpo_video/")
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("carpeta", nargs="?", default=os.path.expanduser("~/Desktop/imperialdance")); ap.add_argument("--generos", default="b"); ap.add_argument("--muestras", type=int, default=0, help="muestras por archivo (0 = las 100)"); ap.add_argument("--cada", type=int, default=4, help="1 de cada N cuadros (4 -> 25/s)")
    a = ap.parse_args(); importar(a.carpeta, set(a.generos.split(",")), a.muestras, a.cada)
