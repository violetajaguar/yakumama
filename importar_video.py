#!/usr/bin/env python3
"""importar_video.py - la cara de cualquier video (archivo o URL) entra a la ballena, sin guardar el video.

Le pasa el Face Landmarker (el mismo de la camara) y guarda solo los numeros: blendshapes, pose de la cabeza, boca,
parpadeo, cejas. Dos destinos:
  --animo <animo>   una toma del dataset: datasets/cara/<animo>_<actor>_NNN.jsonl (+ cuerpo vacio). Para el reconocedor.
  (sin --animo)     una cara LIBRE, sin animo: datasets/caras_libres/<actor>_<nombre>.jsonl. Para el JEPA (dinamica de
                    la cara) y la memoria (como se ve esa persona en muchos dias). No la usan los entrenadores por animo.

    venv/bin/python importar_video.py video.mp4 --actor violeta --animo playful
    venv/bin/python importar_video.py "https://.../play_720p.mp4" --actor violeta --nombre quien-es-futura
    venv/bin/python importar_video.py --sala lista.tsv --actor violeta        (todos los videos de sala.red, en segundo plano)
"""
import os, sys, json, argparse, subprocess, time
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from importar_ravdess import landmarker, cuadros, FPS
MOODS = ["calm","singing","playful","curious","feeding","sad","angry","alert","diving","surfacing"]
ap = argparse.ArgumentParser(); ap.add_argument("video", nargs="?"); ap.add_argument("--actor", required=True); ap.add_argument("--animo", default=None, choices=MOODS)
ap.add_argument("--nombre", default=None); ap.add_argument("--sala", default=None, help="tsv de sala.red: ruta, biblioteca, guid, titulo"); ap.add_argument("--cdn", default="https://vz-1e216fa4-d0e.b-cdn.net")
a = ap.parse_args()
lm, mp = landmarker()
def importar(fuente, nombre):
    t0 = time.time(); cara, cuerpo = cuadros(fuente, lm, mp, 0.0)
    if len(cara) < 24: print(f"  {nombre}: sin cara ({len(cara)} cuadros)"); return 0
    for r in cara: r["actor"] = a.actor; r["origen"] = nombre; r["animo"] = a.animo or "libre"
    for r in cuerpo: r["actor"] = a.actor; r["origen"] = nombre; r["animo"] = a.animo or "libre"
    if a.animo:
        SAL_CARA = os.path.join(AQUI, "datasets", "cara"); SAL_CUERPO = os.path.join(AQUI, "datasets", "cuerpo"); k = 1
        while os.path.exists(os.path.join(SAL_CARA, f"{a.animo}_{a.actor}_{k:03d}.jsonl")): k += 1
        for carp, recs in ((SAL_CARA, cara), (SAL_CUERPO, cuerpo)):
            with open(os.path.join(carp, f"{a.animo}_{a.actor}_{k:03d}.jsonl"), "w") as fh:
                for r in recs: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        destino = f"{a.animo}_{a.actor}_{k:03d}"
    else:
        d = os.path.join(AQUI, "datasets", "caras_libres"); os.makedirs(d, exist_ok=True); destino = f"{a.actor}_{nombre}"
        with open(os.path.join(d, destino + ".jsonl"), "w") as fh:
            for r in cara: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    dur = cara[-1]["t"] - cara[0]["t"]; print(f"  {nombre}: {len(cara)} cuadros con cara, {dur:.0f} s -> {destino}  ({time.time() - t0:.0f} s de proceso)", flush=True); return dur
if a.sala:
    total = 0
    for l in open(a.sala):
        p = l.rstrip("\n").split("\t")
        if len(p) < 3 or len(p[2]) != 36: continue
        slug = p[0].strip("/").split("/")[-1]
        if os.path.exists(os.path.join(AQUI, "datasets", "caras_libres", f"{a.actor}_{slug}.jsonl")): print(f"  {slug}: ya estaba"); continue
        total += importar(f"{a.cdn}/{p[2]}/play_720p.mp4", slug)
    print(f"caras libres de {a.actor}: {total / 60:.0f} min nuevos")
else:
    importar(a.video, a.nombre or os.path.basename(a.video).split(".")[0].replace(" ", "_"))
