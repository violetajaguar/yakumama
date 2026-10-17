#!/usr/bin/env python3
"""importar_swimxyz.py - SwimXYZ (Fiche et al. 2023, Zenodo 8399376, CC BY 4.0): 240 secuencias de nado de 12 s a 30
cuadros/s (60 por estilo: crol, espalda, pecho, mariposa) en parametros SMPL-H (eje-angulo por articulacion). Sin el
modelo SMPL (que pide registro) se reconstruye el esqueleto con cinematica directa sobre un esqueleto medio: los largos
de los huesos son aproximados, las ROTACIONES son exactas, y la ballena solo lee orientaciones (inclinacion, ladeo,
giro, energia): lo que necesita.

Sale al esqueleto de 26 puntos de Paqarina: datasets/cuerpo_video/swim_<estilo>_<n>.npz. El prefijo swim lleva el animo
que diga jepa_datos.VIDEO_ANIMO (hoy: feeding, "comer es nadar").

    venv_datos/bin/python importar_swimxyz.py ~/Desktop/swimxyz/motions
"""
import os, sys, glob, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
# SMPL: 22 articulaciones del cuerpo, padre de cada una, y desplazamiento en reposo (metros, y arriba) de un cuerpo medio
PADRE = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]
OFF = np.array([[0, 0, 0], [0.06, -0.09, -0.01], [-0.06, -0.09, -0.01], [0, 0.10, 0], [0.04, -0.38, 0], [-0.04, -0.38, 0], [0, 0.14, 0], [-0.01, -0.42, -0.03], [0.01, -0.42, -0.03], [0, 0.05, 0],
                [0.02, -0.06, 0.12], [-0.02, -0.06, 0.12], [0, 0.22, -0.01], [0.07, 0.10, 0], [-0.07, 0.10, 0], [0, 0.07, 0.03], [0.10, 0.03, -0.01], [-0.10, 0.03, -0.01], [0.26, 0, 0], [-0.26, 0, 0], [0.25, 0, 0], [-0.25, 0, 0]])
SMPL = ["pelvis", "L_hip", "R_hip", "spine1", "L_knee", "R_knee", "spine2", "L_ankle", "R_ankle", "spine3", "L_foot", "R_foot", "neck", "L_collar", "R_collar", "head", "L_shoulder", "R_shoulder", "L_elbow", "R_elbow", "L_wrist", "R_wrist"]
NOMBRES = ["nose", "eye_l", "eye_r", "ear_l", "ear_r", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "wrist_l", "wrist_r", "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head", "neck", "pelvis", "bigtoe_l", "bigtoe_r", "smalltoe_l", "smalltoe_r", "heel_l", "heel_r"]
MAPA = {"nose": "head", "head": "head", "neck": "neck", "pelvis": "pelvis", "shoulder_l": "L_shoulder", "shoulder_r": "R_shoulder", "elbow_l": "L_elbow", "elbow_r": "R_elbow", "wrist_l": "L_wrist", "wrist_r": "R_wrist",
        "hip_l": "L_hip", "hip_r": "R_hip", "knee_l": "L_knee", "knee_r": "R_knee", "ankle_l": "L_ankle", "ankle_r": "R_ankle", "bigtoe_l": "L_foot", "bigtoe_r": "R_foot", "heel_l": "L_ankle", "heel_r": "R_ankle"}
def rodrigues(v):
    th = np.linalg.norm(v)
    if th < 1e-8: return np.eye(3)
    k = v / th; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]); return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K
def fk(poses, trans):
    """poses (n, >=66), trans (n, 3) -> (n, 22, 3) posiciones, y arriba (SMPL)."""
    n = len(poses); P = np.zeros((n, 22, 3)); R = [None] * 22
    for f in range(n):
        for j in range(22):
            Rl = rodrigues(poses[f, 3 * j: 3 * j + 3])
            if PADRE[j] < 0: R[j] = Rl; P[f, j] = trans[f]
            else: R[j] = R[PADRE[j]] @ Rl; P[f, j] = P[f, PADRE[j]] + R[PADRE[j]] @ OFF[j]
    return P
def importar(carpeta):
    sal = os.path.join(AQUI, "datasets", "cuerpo_video"); os.makedirs(sal, exist_ok=True); total = 0; n = 0
    for f in sorted(glob.glob(os.path.join(carpeta, "*", "*_poses.npz"))):
        z = np.load(f); fps = float(z["mocap_framerate"]); P = fk(z["poses"], z["trans"])
        P = P[:, :, [0, 2, 1]] * np.array([1, -1, 1])   # SMPL y arriba -> z arriba (x, -z, y)
        B = np.full((len(P), len(NOMBRES), 3), np.nan)
        for k, nombre in enumerate(NOMBRES):
            if nombre in MAPA: B[:, k] = P[:, SMPL.index(MAPA[nombre])]
        estilo = os.path.basename(os.path.dirname(f)); num = os.path.basename(f).split("_")[1]
        np.savez_compressed(os.path.join(sal, f"swim_{estilo}_{int(num):03d}.npz"), body=B.astype(np.float32), joint_names=np.array(NOMBRES), fps=fps, origen="swimxyz", archivo=os.path.basename(f))
        total += len(P) / fps; n += 1
    print(f"importados {n} nados, {total / 60:.0f} min -> datasets/cuerpo_video/swim_*")
if __name__ == "__main__": importar(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/swimxyz/motions"))
