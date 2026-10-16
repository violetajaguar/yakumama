#!/usr/bin/env python3
"""importar_llama.py - las caras (y cuerpos) que Violeta grabo para la LLAMA (abril 2026) entran al dataset de la ballena.

Las grabaciones de la llama (llama_recordings_blender/<animo>_001.jsonl, ~5-8 min cada una) traen la cara y el cuerpo
de Violeta actuando nueve animos de llama. Seis coinciden con animos de la ballena y se importan como tomas de
Violeta (otra sesion, de otro dia: sirven para medir entre sesiones):
    serena -> calm   curiosa -> curious   juguetona -> playful   enojada -> angry   triste -> sad   asustada -> alert
(contenta, cansada y orgullosa no tienen equivalente claro y se dejan afuera.)

Canales: head_yaw/pitch/roll, jaw_open (mouth_open), blink (el mayor de los dos ojos), brow_down (brow_anger),
mouth_sad, manos (hand_up -> palm_y), y en cuerpo/ el torso de la llama (spine, neck_lean, body_depth, body_yaw) como
`llama_*`. No hay blendshapes (face_*) ni EmotiBit: el reconocedor de animo las salta solas; la red de movimiento las usa.

    venv/bin/python importar_llama.py "/Volumes/Crucial X10/llama_recordings_blender"
"""
import os, sys, json, glob
AQUI = os.path.dirname(os.path.abspath(__file__))
MAPA = {"serena": "calm", "curiosa": "curious", "juguetona": "playful", "enojada": "angry", "triste": "sad", "asustada": "alert"}
carpeta = sys.argv[1] if len(sys.argv) > 1 else "/Volumes/Crucial X10/llama_recordings_blender"
SAL_CARA = os.path.join(AQUI, "datasets", "cara"); SAL_CUERPO = os.path.join(AQUI, "datasets", "cuerpo")
def g(r, k, d=0.0):
    v = r.get(k); return float(v) if isinstance(v, (int, float)) else d
total = 0
for f in sorted(glob.glob(os.path.join(carpeta, "*_001.jsonl"))):
    llama = os.path.basename(f).split("_")[0]
    if llama not in MAPA: print(f"  {llama}: sin equivalente, se deja"); continue
    animo = MAPA[llama]; k = 10
    while os.path.exists(os.path.join(SAL_CARA, f"{animo}_{k:03d}.jsonl")): k += 1   # tomas 010+ : Violeta, sesion llama
    cara, cuerpo = [], []
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l); t = round(g(r, "t"), 3); blink = max(g(r, "in_blink_l"), g(r, "in_blink_r"))
        crudo = {"head_yaw": g(r, "in_head_yaw"), "head_pitch": g(r, "in_head_pitch"), "head_roll": g(r, "in_head_roll"), "jaw_open": g(r, "in_mouth_open"), "blink": blink,
                 "brow_up": 0.0, "brow_down": g(r, "in_brow_anger"), "mouth_sad": g(r, "in_mouth_sad")}
        c = {"t": t, "animo": animo, "actor": "violeta", "origen": "llama_2026-04-30_" + llama, **crudo, "blink_l": g(r, "in_blink_l"), "blink_r": g(r, "in_blink_r"), "todo": crudo}
        b = {"t": t, "animo": animo, "actor": "violeta", "origen": "llama_2026-04-30_" + llama,
             "l_palm_y": round(1.0 - g(r, "in_l_hand_up"), 4), "r_palm_y": round(1.0 - g(r, "in_r_hand_up"), 4), "l_palm_x": round((g(r, "in_l_hand_x") + 1) / 2, 4), "r_palm_x": round((g(r, "in_r_hand_x") + 1) / 2, 4),
             **{"llama_" + key[3:]: g(r, key) for key in ("in_spine_x", "in_spine_y", "in_neck_lean_x", "in_neck_lean_y", "in_body_depth", "in_body_yaw", "in_ear_alert", "in_nose_flare", "in_walk_mode") if key in r}}
        cara.append(c); cuerpo.append(b)
    for carp, recs in ((SAL_CARA, cara), (SAL_CUERPO, cuerpo)):
        with open(os.path.join(carp, f"{animo}_{k:03d}.jsonl"), "w") as fh:
            for r in recs: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    dur = cara[-1]["t"] - cara[0]["t"] if cara else 0; total += dur
    print(f"  {llama:10s} -> {animo}_{k:03d}  {len(cara)} cuadros, {dur:.0f} s")
print(f"importados {total/60:.0f} min de Violeta (abril, la llama)")
