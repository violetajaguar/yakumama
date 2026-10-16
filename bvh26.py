#!/usr/bin/env python3
"""bvh26.py - un BVH (captura de movimiento, p. ej. BEAT) -> esqueleto de 26 puntos de Paqarina (posiciones 3D, z arriba).

Lee la jerarquia y el bloque MOTION, hace la cinematica directa y devuelve las posiciones de las articulaciones que
usa cuerpo_cualidades.cualidades_toma: pelvis, neck, head, hip_l/r, shoulder_l/r, elbow_l/r, wrist_l/r, knee_l/r,
ankle_l/r (las demas quedan NaN). Convierte de y-arriba (BVH) a z-arriba y de centimetros a metros si hace falta.

    B, J, fps = cargar_bvh("1_wayne_0_100_100.bvh", cada=10)    # cada=10: de 120 a 12 cuadros/s
"""
import numpy as np, math
NOMBRES26 = ["nose","eye_l","eye_r","ear_l","ear_r","shoulder_l","shoulder_r","elbow_l","elbow_r","wrist_l","wrist_r","hip_l","hip_r","knee_l","knee_r","ankle_l","ankle_r","head","neck","pelvis","bigtoe_l","bigtoe_r","smalltoe_l","smalltoe_r","heel_l","heel_r"]
# nombres de BVH (BEAT / Mixamo-like) -> nombre de los 26
MAPA = {"Hips": "pelvis", "Neck": "neck", "Head": "head", "LeftShoulder": None, "LeftArm": "shoulder_l", "RightArm": "shoulder_r", "LeftForeArm": "elbow_l", "RightForeArm": "elbow_r",
        "LeftHand": "wrist_l", "RightHand": "wrist_r", "LeftUpLeg": "hip_l", "RightUpLeg": "hip_r", "LeftLeg": "knee_l", "RightLeg": "knee_r", "LeftFoot": "ankle_l", "RightFoot": "ankle_r", "HeadEnd": "nose"}
def _rot(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    if axis == "X": return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "Y": return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
def cargar_bvh(ruta, cada=10):
    lineas = open(ruta).read().split("\n"); i = 0; nodos = []; pila = []
    while not lineas[i].strip().startswith("MOTION"):
        t = lineas[i].strip().split(); i += 1
        if not t: continue
        if t[0] in ("ROOT", "JOINT"): nodos.append({"nombre": t[1], "padre": pila[-1] if pila else None, "offset": np.zeros(3), "canales": []}); pila.append(len(nodos) - 1)
        elif t[0] == "End": nodos.append({"nombre": nodos[pila[-1]]["nombre"] + "End", "padre": pila[-1], "offset": np.zeros(3), "canales": []}); pila.append(len(nodos) - 1)
        elif t[0] == "OFFSET": nodos[pila[-1]]["offset"] = np.array([float(x) for x in t[1:4]])
        elif t[0] == "CHANNELS": nodos[pila[-1]]["canales"] = t[2:]
        elif t[0] == "}": pila.pop()
    n_frames = int(lineas[i + 1].split(":")[1]); dt = float(lineas[i + 2].split(":")[1]); datos = lineas[i + 3:i + 3 + n_frames]
    fps = 1.0 / dt; sel = range(0, n_frames, cada); B = np.full((len(sel), 26, 3), np.nan); idx = {n: k for k, n in enumerate(NOMBRES26)}
    escala = None
    for fi, f in enumerate(sel):
        vals = [float(x) for x in datos[f].split()]; k = 0; pos = {}; rot = {}
        for j, nd in enumerate(nodos):
            R = np.eye(3); T = nd["offset"].copy()
            for c in nd["canales"]:
                v = vals[k]; k += 1
                if c == "Xposition": T[0] = v
                elif c == "Yposition": T[1] = v
                elif c == "Zposition": T[2] = v
                else: R = R @ _rot(c[0], v)
            if nd["padre"] is None: pos[j] = T; rot[j] = R
            else: pos[j] = pos[nd["padre"]] + rot[nd["padre"]] @ T; rot[j] = rot[nd["padre"]] @ R
        if escala is None:   # cm o m: se mira el largo cadera-cuello (~0.5 m); la raiz puede estar en el origen
            jn = next((j for j, nd in enumerate(nodos) if nd["nombre"] == "Neck"), None); largo = float(np.linalg.norm(pos[jn] - pos[0])) if jn is not None else 1.0
            escala = 0.01 if largo > 3 else 1.0
        for j, nd in enumerate(nodos):
            nom = MAPA.get(nd["nombre"])
            if nom: p = pos[j] * escala; B[fi, idx[nom]] = [p[0], -p[2], p[1]]   # y-arriba -> z-arriba
    return B, idx, fps / cada
if __name__ == "__main__":
    import sys; B, J, fps = cargar_bvh(sys.argv[1]); print(B.shape, fps, "pelvis z media", np.nanmean(B[:, J["pelvis"], 2]).round(2), "cabeza z", np.nanmean(B[:, J["head"], 2]).round(2))
