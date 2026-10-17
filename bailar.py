#!/usr/bin/env python3
"""bailar.py - un cuerpo humano (esqueleto de 26 puntos de Paqarina) CONDUCE a la ballena.

No se copian las articulaciones: se traducen a lo que una ballena hace. Del esqueleto salen, por cuadro:
  cuerpo_pitch        torso inclinado adelante (+) / atras (-)         -> ella pica / levanta la nariz
  cuerpo_roll         torso o hombros torcidos a un lado               -> ella se ladea y gira
  cuerpo_yaw          cuanto gira el cuerpo (cambio de frente)          -> ella gira
  cuerpo_profundidad  pelvis mas baja (agachado, -) o mas alta (salto, +) que de pie -> ella baja / salta
  cuerpo_energia      velocidad media de todo el cuerpo (0 quieto .. 1 explosivo)  -> cola, latido, amplitud de todo
  l/r_palm_x,y        las manos (0 arriba .. 1 abajo), como con la camara        -> las aletas
  head_yaw, head_pitch la cabeza respecto del torso                             -> su cabeza
  emotibit_hr         60 + 70 * energia                                          -> latido y turbina

    venv/bin/python bailar.py ~/Desktop/h26_limpio/Galgo13-03_limpio.npz --animo playful
    venv/bin/python bailar.py toma.npz --animo auto --velocidad 1 --desde 20 --segundos 40 --espejo host:puerto
--animo auto: el animo sale de la energia (quieto calm, medio curious, fuerte playful). Blender tiene que estar abierto.
"""
import os, sys, json, time, socket, argparse, math, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("npz"); ap.add_argument("--animo", default="auto"); ap.add_argument("--velocidad", type=float, default=1.0)
ap.add_argument("--desde", type=float, default=0.0); ap.add_argument("--segundos", type=float, default=0.0); ap.add_argument("--puerto", type=int, default=9998)
ap.add_argument("--espejo", action="append", default=[]); ap.add_argument("--seco", action="store_true", help="no manda: imprime estadisticas"); ap.add_argument("--loop", action="store_true")
ap.add_argument("--solo-cuerpo", action="store_true", help="manda solo el torso (inclinacion, giro, agachado, energia): la cara, las manos y el animo los pone otro (reproducir.py o la camara)")
a = ap.parse_args()
z = np.load(a.npz, allow_pickle=True)
if "body" not in z.files and "X" in z.files:   # una ballena real o un surfista (importar_ballenas / importar_surf): ya viene en cuerpo_*, se manda tal cual
    X = np.nan_to_num(z["X"]).astype(float); can = [str(c) for c in z["canales"]]; fps = float(z["fps"]); nombre = os.path.basename(a.npz).replace(".npz", "")
    f0 = int(a.desde * fps); f1 = int(min(len(X), f0 + a.segundos * fps)) if a.segundos else len(X); s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"   {nombre}: {len(X)} cuadros de cuerpo_* a {fps:.0f} fps, cuadros {f0}-{f1}, animo {a.animo}")
    while True:
        t0 = time.time()
        for f in range(f0, f1):
            q = {c: round(float(X[f, i]), 3) for i, c in enumerate(can)}; en = q.get("cuerpo_energia", 0.3)
            pkt = {**q, "anclada": 1, "water": 0.8, "bailarin": nombre, "soltar_manual": 1 if f < f0 + 30 else 0, "emotibit_hr": round(60 + 70 * en, 1), "emotibit_eda": round(1 + 6 * en, 2)}
            if a.animo != "auto": pkt["actor_animo"] = a.animo
            if not a.seco:
                s.sendto(json.dumps(pkt).encode(), ("127.0.0.1", a.puerto))
                if f % int(fps) == 0: json.dump({"tramo": f"cuerpo:{nombre}", "modo": "anclada", "t": round((f - f0) / fps), "dur": round((f1 - f0) / fps), "loop": a.loop, "hora": time.time()}, open("/tmp/ballena_reproduciendo.json", "w"))
                objetivo = t0 + (f - f0) / fps / a.velocidad
                if (d_ := objetivo - time.time()) > 0: time.sleep(d_)
        if a.seco or not a.loop: break
    sys.exit(0)
B = z["body"].astype(np.float64); J = {str(n): i for i, n in enumerate(z["joint_names"])}; fps = float(z["fps"]) if "fps" in z.files else 30.0
def p(nombre, f): return B[f, J[nombre]]
def norm(v): n = np.linalg.norm(v); return v / n if n > 1e-9 else v
def clamp(v, lo=-1.0, hi=1.0): return float(max(lo, min(hi, v)))
# altura de la pelvis de pie: percentil 80 (lo mas alto habitual) como referencia
pelvis_z = B[:, J["pelvis"], 2]; z_pie = float(np.nanpercentile(pelvis_z, 80))
largo_brazo = 0.56; alto_torso = 0.54
def cualidades(f, prev_frente):
    pel, cue, cab = p("pelvis", f), p("neck", f), p("head", f); hl, hr = p("hip_l", f), p("hip_r", f); sl, sr = p("shoulder_l", f), p("shoulder_r", f)
    if not np.all(np.isfinite([pel, cue, hl, hr, sl, sr])): return None, prev_frente
    lado = norm(hr - hl); lado[2] = 0; lado = norm(lado)            # eje izquierda->derecha de la cadera, en el piso
    frente = np.array([-lado[1], lado[0], 0.0])                     # perpendicular: hacia donde mira el cuerpo
    torso = norm(cue - pel)
    pitch = clamp(np.dot(torso, frente) / 0.7)                       # inclinado adelante: +1 a ~45 grados
    roll = clamp(np.dot(torso, lado) / 0.5)
    hombros = norm(sr - sl); hombros[2] = 0; hombros = norm(hombros)
    twist = clamp(math.atan2(np.cross(lado, hombros)[2], np.dot(lado, hombros)) / 0.8)   # hombros torcidos respecto de la cadera
    ang = math.atan2(frente[1], frente[0]); yaw = 0.0
    if prev_frente is not None:
        d = ang - prev_frente; d = (d + math.pi) % (2 * math.pi) - math.pi; yaw = clamp(d * fps / 3.0)   # 3 rad/s de giro = 1
    prof = clamp((pel[2] - z_pie) / 0.35)                            # agachado -1 (35 cm abajo) .. salto +1
    out = {"cuerpo_pitch": round(pitch, 3), "cuerpo_roll": round(0.6 * roll + 0.4 * twist, 3), "cuerpo_yaw": round(yaw, 3), "cuerpo_profundidad": round(prof, 3)}
    # manos: altura respecto del hombro (0 arriba, 1 abajo) y apertura lateral
    for lado_n, w, s in (("l", "wrist_l", "shoulder_l"), ("r", "wrist_r", "shoulder_r")):
        wp, sp = p(w, f), p(s, f)
        if np.all(np.isfinite([wp, sp])):
            out[f"{lado_n}_palm_y"] = round(clamp(0.5 - (wp[2] - sp[2]) / (2 * largo_brazo), 0, 1), 3)
            out[f"{lado_n}_palm_x"] = round(clamp(0.5 + np.dot(wp - sp, lado) / (2 * largo_brazo), 0, 1), 3)
    # cabeza respecto del torso
    if np.all(np.isfinite(cab)):
        v = norm(cab - cue); out["head_yaw"] = round(clamp(np.dot(v, lado) / 0.5), 3); out["head_pitch"] = round(clamp((v[2] - 0.9) / 0.4), 3)
    return out, ang
# energia: velocidad media de las articulaciones, suavizada
vel = np.nanmean(np.linalg.norm(np.diff(B, axis=0), axis=2), axis=1) * fps   # m/s por cuadro
vel = np.concatenate([[vel[0]], vel]); vel = np.where(np.isfinite(vel), vel, 0.0)
ema = np.zeros_like(vel); e = 0.0
for i, v in enumerate(vel): e = 0.9 * e + 0.1 * min(v, 3.0); ema[i] = e
energia = np.clip((ema - 0.2) / 1.2, 0, 1)   # 0.2 m/s = quieto, 1.4 m/s = explosivo
# SUAVIDAD de la toma: cuanta potencia del movimiento del torso esta por encima de 3 Hz (golpes, acentos). Poca = suave.
_torso = [J[k] for k in ("pelvis", "neck", "shoulder_l", "shoulder_r", "hip_l", "hip_r") if k in J]
_v = np.nan_to_num(np.diff(B[:, _torso, :], axis=0) * fps); _F = np.abs(np.fft.rfft(_v - _v.mean(0), axis=0)) ** 2; _f = np.fft.rfftfreq(len(_v), 1 / fps)
hf = float(_F[_f > 3].sum() / max(1e-9, _F[1:].sum())); suavidad = float(np.clip(1 - (hf - 0.08) / 0.3, 0, 1))
alpha = 0.3 - 0.2 * suavidad   # cuanto mas suave la bailarina, mas redondas las transiciones de la ballena
def animo_de(en): return "calm" if en < 0.15 else ("curious" if en < 0.45 else "playful")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); espejos = []
for esp in a.espejo:
    h, pt = esp.rsplit(":", 1); espejos.append((h, int(pt)))
f0 = int(a.desde * fps); f1 = int(min(len(B), f0 + a.segundos * fps)) if a.segundos else len(B)
nombre = os.path.basename(a.npz).replace(".npz", ""); print(f"   {nombre}: {len(B)} cuadros a {fps:.0f} fps, cuadros {f0}-{f1}, animo {a.animo}, velocidad x{a.velocidad} | suavidad {suavidad:.2f} (potencia del torso >3 Hz {hf:.0%})")
suave = {}; prev = None; stats = {}
while True:
    t0 = time.time()
    for f in range(f0, f1):
        q, prev = cualidades(f, prev)
        if q is None: continue
        q["cuerpo_energia"] = round(float(energia[f]) * (1 - 0.4 * suavidad), 3)   # una bailarina suave mueve a la ballena con menos fuerza
        for k, v in q.items(): suave[k] = v if k not in suave else (1 - alpha) * suave[k] + alpha * v   # sin temblor; mas lento si es suave
        suave["cuerpo_suavidad"] = suavidad
        animo = a.animo if a.animo != "auto" else animo_de(suave["cuerpo_energia"])
        pkt = {**{k: round(v, 3) for k, v in suave.items()}, "actor_animo": animo, "emotibit_hr": round(60 + 70 * suave["cuerpo_energia"], 1), "emotibit_eda": round(1 + 6 * suave["cuerpo_energia"], 2),
               "anclada": 1, "water": 0.8, "bailarin": nombre, "soltar_manual": 1 if f < f0 + 30 else 0}
        if a.solo_cuerpo: pkt = {k: v for k, v in pkt.items() if k.startswith("cuerpo_") or k in ("bailarin", "anclada")}   # el torso nada mas (y anclada)
        for k, v in pkt.items():
            if isinstance(v, float): stats.setdefault(k, []).append(v)
        if not a.seco:
            d = json.dumps(pkt).encode(); s.sendto(d, ("127.0.0.1", a.puerto))
            for h, pt in espejos: s.sendto(d, (h, pt))
            if f % int(fps) == 0: json.dump({"tramo": f"cuerpo:{nombre}", "modo": "anclada", "t": round((f - f0) / fps), "dur": round((f1 - f0) / fps), "loop": a.loop, "hora": time.time()}, open("/tmp/ballena_reproduciendo.json", "w"))
            objetivo = t0 + (f - f0) / fps / a.velocidad
            if (d_ := objetivo - time.time()) > 0: time.sleep(d_)
    if a.seco or not a.loop: break
if a.seco:
    for k, v in stats.items(): print(f"   {k:20s} media {np.mean(v):6.2f}  min {np.min(v):6.2f}  max {np.max(v):6.2f}")
print("   fin")
