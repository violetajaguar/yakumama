#!/usr/bin/env python3
"""importar_ravdess.py - 24 actores mas para el reconocedor de animo, desde los videos de RAVDESS.

RAVDESS (Livingstone & Russo 2018, CC BY-NC-SA 4.0, zenodo.org/records/1188976): 24 actores profesionales dicen dos
frases con ocho emociones. Esta ballena no copia los videos: les pasa el mismo Face Landmarker que usa con la camara
(52 blendshapes + pose de la cabeza) y guarda solo los numeros, como una toma mas del dataset, con el actor
`ravdessNN`. Emociones -> animos de la ballena:
    02 calm, 01 neutral -> calm | 03 happy -> playful | 04 sad -> sad | 05 angry -> angry | 06 fearful -> alert
    08 surprised -> curious | 07 disgust -> (no se usa)
Cada animo de cada actor queda en una toma: <animo>_ravdessNN_001.jsonl (cara) + cuerpo (vacio de manos y pulso).
El reconocedor de animo y el JEPA los usan; el parecido y la red de movimiento los saltan (son caras sin manos ni
pulso, y la ballena no tiene que parecerse a un actor de Toronto).

    venv/bin/python importar_ravdess.py ~/Desktop/ravdess            (busca Video_Speech_Actor_NN.zip o carpetas Actor_NN)
"""
import os, sys, json, glob, zipfile, subprocess, tempfile, math, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
MODELO = os.path.join(AQUI, "modelos", "face_landmarker.task")
EMO = {"01": "calm", "02": "calm", "03": "playful", "04": "sad", "05": "angry", "06": "alert", "08": "curious"}
FPS = 12.0
_reloj = {"ms": 0}
def landmarker():
    import mediapipe as mp; from mediapipe.tasks import python as mpp; from mediapipe.tasks.python import vision
    opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=MODELO), output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1, running_mode=vision.RunningMode.VIDEO)
    return vision.FaceLandmarker.create_from_options(opts), mp
def angulos(M):
    """matriz 4x4 de la cara -> yaw, pitch en grados"""
    R = np.array(M).reshape(4, 4)[:3, :3]; yaw = math.degrees(math.atan2(-R[2, 0], math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2))); pitch = math.degrees(math.atan2(R[2, 1], R[2, 2]))
    return yaw, pitch
def cuadros(video, lm, mp, t0):
    """lee el video a FPS con ffmpeg y devuelve registros (cara, cuerpo) en el formato del dataset"""
    import cv2
    w, h = 480, 270
    extra = ["-headers", "Referer: https://iframe.mediadelivery.net/\r\nUser-Agent: Mozilla/5.0\r\n"] if str(video).startswith("http") else []   # los CDN de video piden referer
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", *extra, "-i", video, "-vf", f"fps={FPS:.0f},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    cara, cuerpo, i = [], [], 0
    while True:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3: break
        rgb = np.frombuffer(buf, np.uint8).reshape(h, w, 3); t = t0 + i / FPS; i += 1
        _reloj["ms"] += int(1000 / FPS)   # el landmarker en modo VIDEO exige tiempos siempre crecientes, aunque cambie el video
        r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)), _reloj["ms"])
        if not r.face_blendshapes: continue
        bs = {b.category_name: round(float(b.score), 4) for b in r.face_blendshapes[0]}
        yaw, pitch = angulos(r.facial_transformation_matrixes[0]) if r.facial_transformation_matrixes else (0.0, 0.0)
        crudo = {"head_yaw": round(max(-1, min(1, yaw / 45.0)), 4), "head_pitch": round(max(-1, min(1, -pitch / 45.0)), 4), "jaw_open": bs.get("jawOpen", 0.0),
                 "blink": round(max(bs.get("eyeBlinkLeft", 0), bs.get("eyeBlinkRight", 0)), 4), "brow_up": round((bs.get("browInnerUp", 0) + bs.get("browOuterUpLeft", 0) + bs.get("browOuterUpRight", 0)) / 3, 4),
                 "brow_down": round((bs.get("browDownLeft", 0) + bs.get("browDownRight", 0)) / 2, 4), "mouth_sad": round((bs.get("mouthFrownLeft", 0) + bs.get("mouthFrownRight", 0)) / 2, 4)}
        c = {"t": round(t, 3), **crudo, "blink_l": bs.get("eyeBlinkLeft", 0.0), "blink_r": bs.get("eyeBlinkRight", 0.0),
             "mouth_smile": round((bs.get("mouthSmileLeft", 0) + bs.get("mouthSmileRight", 0)) / 2, 4), "tongue_out": bs.get("tongueOut", 0.0),
             **{f"face_{k}": v for k, v in bs.items() if k != "_neutral"}, "todo": crudo}
        cara.append(c); cuerpo.append({"t": round(t, 3)})
    p.wait(); return cara, cuerpo
def importar(carpeta):
    lm, mp = landmarker(); SAL_CARA = os.path.join(AQUI, "datasets", "cara"); SAL_CUERPO = os.path.join(AQUI, "datasets", "cuerpo")
    zips = sorted(glob.glob(os.path.join(carpeta, "Video_Speech_Actor_*.zip"))); dirs = sorted(glob.glob(os.path.join(carpeta, "Actor_*")))
    tmp = tempfile.mkdtemp()
    for z in zips:
        try: zipfile.ZipFile(z).extractall(tmp)
        except Exception as e: print("  (zip malo", os.path.basename(z), e, ")"); continue
    dirs += sorted(glob.glob(os.path.join(tmp, "Actor_*")))
    for d in dirs:
        actor = "ravdess" + os.path.basename(d).split("_")[-1]; tomas = {}
        for v in sorted(glob.glob(os.path.join(d, "*.mp4"))):
            partes = os.path.basename(v).split(".")[0].split("-")
            if len(partes) < 7 or partes[0] != "02" or partes[1] != "01": continue   # 02 = video+audio, 01 = habla
            animo = EMO.get(partes[2])
            if not animo: continue
            tomas.setdefault(animo, []).append(v)
        for animo, vids in tomas.items():
            cara, cuerpo, t0 = [], [], 0.0
            for v in vids:
                c, b = cuadros(v, lm, mp, t0)
                if c: cara += c; cuerpo += b; t0 = c[-1]["t"] + 1.0   # 1 s de hueco entre clips: las ventanas no los cruzan por tiempo
            if len(cara) < 24: continue
            for r in cara: r["animo"] = animo; r["actor"] = actor; r["origen"] = "ravdess"
            for r in cuerpo: r["animo"] = animo; r["actor"] = actor; r["origen"] = "ravdess"
            k = 1
            while os.path.exists(os.path.join(SAL_CARA, f"{animo}_{actor}_{k:03d}.jsonl")): k += 1
            for carp, recs in ((SAL_CARA, cara), (SAL_CUERPO, cuerpo)):
                with open(os.path.join(carp, f"{animo}_{actor}_{k:03d}.jsonl"), "w") as fh:
                    for r in recs: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  {actor} {animo:9s} {len(vids)} clips -> {len(cara)} cuadros ({len(cara) / FPS:.0f} s)", flush=True)
if __name__ == "__main__":
    importar(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/ravdess"))
