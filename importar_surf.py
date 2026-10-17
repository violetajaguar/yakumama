#!/usr/bin/env python3
"""importar_surf.py - surfistas reales (Zenodo 14535620, CC BY 4.0: siete surfistas en la ola del rio de Nuremberg, diez
IMUs y angulos por estimacion de pose, un ciclo promedio de surf por persona: medio de la ola, giro de frente, giro de
espalda, vuelta al medio; ~20 s a 15 cuadros/s los angulos y 400 Hz los IMU) a los seis canales de cuerpo de la ballena.

Los .mat guardan tablas de MATLAB (objetos opacos): los lee leer_mat_opaco.py. Orden de las columnas de angulos:
pelvis_tilt, pelvis_rotation, pelvis_obliquity, hip_flexion_r, knee_angle_r, arm_add_r, elbow_flex_r, hip_flexion_l,
knee_angle_l, arm_add_l, elbow_flex_l (rad), luego el tiempo y pelvis_tz (m). IMU: 10 segmentos x 3 ejes de acc y luego
de gyro, el torso primero.
    cuerpo_pitch        sin(pelvis_tilt - mediana) / 0.7      (respecto a la postura propia; misma escala que un bailarin)
    cuerpo_roll         sin(pelvis_obliquity - mediana) / 0.5
    cuerpo_yaw          d(pelvis_rotation)/dt / 3 rad/s  (como en jepa_datos)
    cuerpo_profundidad  (pelvis_tz - percentil 80) / 0.35 (agachado negativo, como un bailarin)
    cuerpo_energia      giro del torso (norma del gyro), suavizado, 0..1 por el percentil 90
    cuerpo_suavidad     1 - potencia del torso por encima de 3 Hz
Guarda datasets/surf/surf_NN.npz (X, M, fps, canales, angulos crudos) e imprime las medidas de cada surfista.

    venv_datos/bin/python importar_surf.py ~/Desktop/surf/BiomechSurfData_24_12_20
"""
import os, sys, glob, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from cuerpo_cualidades import CUERPO; from leer_mat_opaco import leer
FPS = 12.0; FPS_PE = 15.0; FS_IMU = 400.0
ANG = ["pelvis_tilt", "pelvis_rotation", "pelvis_obliquity", "hip_flexion_r", "knee_angle_r", "arm_add_r", "elbow_flex_r", "hip_flexion_l", "knee_angle_l", "arm_add_l", "elbow_flex_l"]
def a12(x, fs, n):
    t = np.arange(n) / FPS; return np.interp(t, np.arange(len(x)) / fs, x)
def importar(carpeta):
    sal = os.path.join(AQUI, "datasets", "surf"); os.makedirs(sal, exist_ok=True); total = 0
    for fa in sorted(glob.glob(os.path.join(carpeta, "AvgData_Angle", "Subject_*_C1_Surf_PE_avgTurns.mat"))):
        sub = os.path.basename(fa).split("_")[1]; fi = os.path.join(carpeta, "AvgData_IMU", f"Subject_{sub}_Surf_IMU_avgTurns.mat")
        arrs = [a.ravel() for c, a in leer(fa) if not isinstance(a, str)]; ang = {k: arrs[1 + i] for i, k in enumerate(ANG)}; tz = arrs[13]
        imu = [a.ravel() for c, a in leer(fi) if not isinstance(a, str)]; acc = np.stack(imu[0:3]); gyr = np.stack(imu[30:33])   # torso
        n = int(len(tz) / FPS_PE * FPS); dur = len(tz) / FPS_PE
        X = np.zeros((n, 6), np.float32)
        tilt, rot, obl = (a12(ang[k], FPS_PE, n) for k in ("pelvis_tilt", "pelvis_rotation", "pelvis_obliquity")); z = a12(tz, FPS_PE, n)
        tilt, obl = tilt - np.median(tilt), obl - np.median(obl)   # respecto a la postura propia (de lado en la tabla): la ballena rola respecto a su nivel
        X[:, 0] = np.clip(np.sin(tilt) / 0.7, -1, 1); X[:, 1] = np.clip(np.sin(obl) / 0.5, -1, 1)
        X[:, 2] = np.clip(np.gradient(np.unwrap(rot)) * FPS / 3.0, -1, 1); X[:, 3] = np.clip((z - np.percentile(z, 80)) / 0.35, -1, 1)
        g = a12(np.linalg.norm(gyr, axis=0), FS_IMU, n); ema = np.zeros(n); e = 0.0
        for i in range(n): e = 0.9 * e + 0.1 * g[i]; ema[i] = e
        en = np.clip(ema / max(1e-6, np.percentile(ema, 90)), 0, 1)
        k = int(FS_IMU * 1); grav = np.stack([np.convolve(acc[i], np.ones(k) / k, "same") for i in range(3)]); din = (acc - grav).T
        F = np.abs(np.fft.rfft(din - din.mean(0), axis=0)) ** 2; f = np.fft.rfftfreq(len(din), 1 / FS_IMU); hf = float(F[f > 3].sum() / max(1e-9, F[(f > 0.2)].sum()))
        su = float(np.clip(1 - (hf - 0.08) / 0.3, 0, 1)); X[:, 4] = en * (1 - 0.4 * su); X[:, 5] = su
        np.savez_compressed(os.path.join(sal, f"surf_{sub}.npz"), X=X, M=np.ones_like(X, bool), fps=FPS, canales=np.array(CUERPO), depid=f"surf_{sub}", especie="surfista",
                            **{k: v.astype(np.float32) for k, v in ang.items()}, pelvis_tz=tz.astype(np.float32), torso_gyro=gyr.astype(np.float32))
        yaw = np.degrees(np.abs(np.gradient(np.unwrap(ang["pelvis_rotation"])) * FPS_PE))
        print(f"  surfista {sub}: ciclo {dur:.1f} s | giro de la pelvis {np.degrees(np.ptp(np.unwrap(ang['pelvis_rotation']))):.0f} grados de rango, hasta {yaw.max():.0f} grados/s | "
              f"ladeo (obliquity) hasta {np.degrees(np.abs(ang['pelvis_obliquity'])).max():.0f} grados | inclinacion (tilt) rango {np.degrees(np.ptp(ang['pelvis_tilt'])):.0f} grados | "
              f"agachado {100 * np.ptp(tz):.0f} cm | rodilla {np.degrees(np.abs(ang['knee_angle_r'])).mean():.0f} grados media | suavidad {su:.2f}")
        print("    canales:", " ".join(f"{c[7:]} {X[:, i].mean():+.2f}±{X[:, i].std():.2f}" for i, c in enumerate(CUERPO))); total += dur
    print(f"importados {total:.0f} s de surf -> datasets/surf/")
if __name__ == "__main__": importar(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/surf/BiomechSurfData_24_12_20"))
