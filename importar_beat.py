#!/usr/bin/env python3
"""importar_beat.py - BEAT: 30 personas con CARA Y CUERPO a la vez, con emocion. Lo que a la ballena le faltaba.

BEAT (Liu et al. 2022, Apache-2.0, huggingface.co/datasets/H-Liu1997/BEAT): 30 hablantes, captura de movimiento del
cuerpo (BVH, 75 huesos, 120 Hz) y 51 blendshapes ARKit de la cara (los mismos nombres que da MediaPipe), un minuto por
clip, con la emocion actuada en el csv. Emociones -> animos de la ballena:
    00_netural -> calm | 01_happiness -> playful | 02_anger -> angry | 03_sadness -> sad | 05_surprise -> curious
    06_fear -> alert | 04_contempt, 07_disgust -> no se usan
Cada clip es una toma: datasets/cara/<animo>_beatNN_<k>.jsonl (cara, 12 cuadros/s) y cuerpo/ con las manos y las
cualidades del cuerpo (cuerpo_*). Los usan el reconocedor de animo y el JEPA (por fin cara y cuerpo juntos); no el
parecido ni la red de estilos (hablan, no actuan una ballena).

    venv/bin/python importar_beat.py ~/Desktop/beat        (carpetas <hablante>/ con .json .bvh .csv)
"""
import os, sys, json, glob, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from bvh26 import cargar_bvh; from cuerpo_cualidades import cualidades_toma, CUERPO
EMO = {"00_netural": "calm", "01_happiness": "playful", "02_anger": "angry", "03_sadness": "sad", "05_surprise": "curious", "06_fear": "alert"}
FPS = 12.0
def clamp(v, lo=-1.0, hi=1.0): return float(max(lo, min(hi, v)))
def importar(carpeta):
    SAL_CARA = os.path.join(AQUI, "datasets", "cara"); SAL_CUERPO = os.path.join(AQUI, "datasets", "cuerpo"); total = 0
    for h in sorted(glob.glob(os.path.join(carpeta, "[0-9]*"))):
        if not os.path.isdir(h): continue
        actor = f"beat{int(os.path.basename(h)):02d}"
        for bvh in sorted(glob.glob(os.path.join(h, "*.bvh"))):
            base = bvh[:-4]
            if not (os.path.exists(base + ".json") and os.path.exists(base + ".csv")): continue
            etiqueta = open(base + ".csv").readline().split(",")[0].strip(); animo = EMO.get(etiqueta)
            if not animo: continue
            try: B, J, fps = cargar_bvh(bvh, cada=10)
            except Exception as e: print("  (bvh malo", os.path.basename(bvh), e, ")"); continue
            q = cualidades_toma(B, J, fps); n = len(B)
            fj = json.load(open(base + ".json")); nombres = fj["names"]; cuadros = fj["frames"]
            tiempos = np.array([c["time"] for c in cuadros]); W = np.array([c["weights"] for c in cuadros], np.float32)
            cara, cuerpo = [], []
            for i in range(n):
                t = i / FPS; k = int(np.clip(np.searchsorted(tiempos, t), 0, len(tiempos) - 1))
                if abs(tiempos[k] - t) > 0.1: continue
                bs = {nm: float(W[k, j]) for j, nm in enumerate(nombres)}
                hy = q["head_yaw"][i]; hp = q["head_pitch"][i]
                crudo = {"head_yaw": round(float(hy) if np.isfinite(hy) else 0.0, 4), "head_pitch": round(float(hp) if np.isfinite(hp) else 0.0, 4), "jaw_open": round(bs.get("jawOpen", 0), 4),
                         "blink": round(max(bs.get("eyeBlinkLeft", 0), bs.get("eyeBlinkRight", 0)), 4), "brow_up": round((bs.get("browInnerUp", 0) + bs.get("browOuterUpLeft", 0) + bs.get("browOuterUpRight", 0)) / 3, 4),
                         "brow_down": round((bs.get("browDownLeft", 0) + bs.get("browDownRight", 0)) / 2, 4), "mouth_sad": round((bs.get("mouthFrownLeft", 0) + bs.get("mouthFrownRight", 0)) / 2, 4)}
                eye_yaw = ((bs.get("eyeLookInLeft", 0) - bs.get("eyeLookOutLeft", 0)) + (bs.get("eyeLookOutRight", 0) - bs.get("eyeLookInRight", 0))) / 2
                eye_pitch = ((bs.get("eyeLookUpLeft", 0) + bs.get("eyeLookUpRight", 0)) - (bs.get("eyeLookDownLeft", 0) + bs.get("eyeLookDownRight", 0))) / 2
                c = {"t": round(t, 3), "animo": animo, "actor": actor, "origen": "beat", **crudo, "blink_l": bs.get("eyeBlinkLeft", 0), "blink_r": bs.get("eyeBlinkRight", 0),
                     "mouth_smile": round((bs.get("mouthSmileLeft", 0) + bs.get("mouthSmileRight", 0)) / 2, 4), "eye_yaw": round(clamp(eye_yaw), 4), "eye_pitch": round(clamp(eye_pitch), 4), "tongue_out": 0.0,
                     **{f"face_{nm}": round(float(W[k, j]), 4) for j, nm in enumerate(nombres)}, "face_tongueOut": 0.0, "todo": crudo}
                b = {"t": round(t, 3), "animo": animo, "actor": actor, "origen": "beat"}
                for kk in ("l_palm_x", "l_palm_y", "r_palm_x", "r_palm_y"):
                    v = q[kk][i]
                    if np.isfinite(v): b[kk] = round(float(v), 4)
                for kk in CUERPO:
                    v = q[kk][i]
                    if np.isfinite(v): b[kk] = round(float(v), 4)
                cara.append(c); cuerpo.append(b)
            if len(cara) < 24: continue
            k = 1
            while os.path.exists(os.path.join(SAL_CARA, f"{animo}_{actor}_{k:03d}.jsonl")): k += 1
            for carp, recs in ((SAL_CARA, cara), (SAL_CUERPO, cuerpo)):
                with open(os.path.join(carp, f"{animo}_{actor}_{k:03d}.jsonl"), "w") as fh:
                    for r in recs: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            total += len(cara) / FPS; print(f"  {actor} {animo:8s} {os.path.basename(base)} -> {len(cara)} cuadros ({len(cara) / FPS:.0f} s)", flush=True)
    print(f"importados {total / 60:.0f} min de BEAT con cara y cuerpo")
if __name__ == "__main__":
    importar(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/beat"))
