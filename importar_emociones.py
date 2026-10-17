#!/usr/bin/env python3
"""importar_emociones.py - Emotional Body Motion Data (Zenodo 10052504, CC BY 4.0): 29 personas sin formacion de actor,
20 ensayos de 5 s por emocion (feliz, triste, sorpresa, rabia, asco, miedo, neutro), 19 puntos 3D a 30 cuadros/s. Es la
primera fuente donde el CUERPO lleva la emocion que la persona quiso poner: de aqui ella aprende como se ve la tristeza
en un cuerpo humano, en vez de que se lo digamos nosotras con una danza.

Archivo {persona}_{bloque}_{ensayo}_{emocion}.csv con 1 feliz, 2 triste, 3 sorpresa, 4 rabia, 5 asco, 6 miedo, 7 neutro.
Puntos (Mixamo): Hips, Spine, Spine1, Neck, Head, L/RShoulder (clavicula), L/RArm (hombro), L/RForeArm (codo), L/RHand,
L/RUpLeg (cadera), L/RLeg (rodilla), L/RFoot (tobillo). Metros, y arriba.
Sale a datasets/cuerpo_video/feel<animo>_<persona>_<bloque>_<ensayo>.npz: el prefijo lleva el animo (jepa_datos.VIDEO_ANIMO:
feelsad -> sad, feelangry -> angry, feelhappy -> playful, feelsurprised -> curious, feelfearful -> alert, feelneutral -> calm;
el asco no se usa). jepa_datos encadena los 20 ensayos de cada persona y bloque en una pista de 100 s.

    venv_datos/bin/python importar_emociones.py ~/Desktop/emociones_cuerpo/ebm
"""
import os, sys, glob, csv, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
EMO = {1: "feelhappy", 2: "feelsad", 3: "feelsurprised", 4: "feelangry", 5: None, 6: "feelfearful", 7: "feelneutral"}
NOMBRES = ["nose", "eye_l", "eye_r", "ear_l", "ear_r", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "wrist_l", "wrist_r", "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head", "neck", "pelvis", "bigtoe_l", "bigtoe_r", "smalltoe_l", "smalltoe_r", "heel_l", "heel_r"]
MAPA = {"nose": "Head", "head": "Head", "neck": "Neck", "pelvis": "Hips", "shoulder_l": "LeftArm", "shoulder_r": "RightArm", "elbow_l": "LeftForeArm", "elbow_r": "RightForeArm", "wrist_l": "LeftHand", "wrist_r": "RightHand",
        "hip_l": "LeftUpLeg", "hip_r": "RightUpLeg", "knee_l": "LeftLeg", "knee_r": "RightLeg", "ankle_l": "LeftFoot", "ankle_r": "RightFoot", "heel_l": "LeftFoot", "heel_r": "RightFoot"}
def leer(ruta):
    with open(ruta) as fh:
        r = csv.reader(fh); cab = next(r); filas = [[float(x) for x in f] for f in r if f]
    A = np.array(filas); col = {c: i for i, c in enumerate(cab)}
    B = np.full((len(A), len(NOMBRES), 3), np.nan)
    for k, nombre in enumerate(NOMBRES):
        if nombre in MAPA and MAPA[nombre] + ".x" in col:
            p = MAPA[nombre]; xyz = A[:, [col[p + ".x"], col[p + ".y"], col[p + ".z"]]]
            B[:, k] = xyz[:, [0, 2, 1]] * np.array([1, -1, 1])   # y arriba -> z arriba
    return B
def importar(carpeta):
    sal = os.path.join(AQUI, "datasets", "cuerpo_video"); os.makedirs(sal, exist_ok=True); n = 0; por = {}
    for f in sorted(glob.glob(os.path.join(carpeta, "*.csv"))):
        per, blo, ens, emo = os.path.basename(f)[:-4].split("_"); pref = EMO.get(int(emo))
        if not pref: continue
        B = leer(f)
        np.savez_compressed(os.path.join(sal, f"{pref}_{int(per):02d}_{blo}_{int(ens):02d}.npz"), body=B.astype(np.float32), joint_names=np.array(NOMBRES), fps=30.0, origen="emotional_body_motion", archivo=os.path.basename(f))
        n += 1; por[pref] = por.get(pref, 0) + 1
    print(f"importados {n} ensayos de 5 s ({n * 5 / 60:.0f} min): " + ", ".join(f"{k} {v}" for k, v in sorted(por.items())))
if __name__ == "__main__": importar(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/emociones_cuerpo/ebm"))
