#!/usr/bin/env python3
"""retarget_ballena.py - a dancer's body translated onto HER body, Violeta's mapping (17 Oct 2026):
    hands -> her pectoral fins, each side its own: right hand -> right fin, left hand -> left fin (wrist height above the shoulder)
    head  -> her head, same as the face (head pitch/yaw from the skeleton; jaw, blink, brows from the face when the take has one)
    spine -> her spine: lean forward bends the front vertebrae down; a lifted leg / hip flexion bends the tail vertebrae up
    tail  -> the level of strength: the feet's speed sets the tail beat and the turbine speed; its amplitude is the body's energy
    body  -> pitch (lean forward = nose down), roll (side lean + shoulder twist), turn, depth (crouch sinks, jump rises)
Output: the whale's own channels per frame (pitch roll yaw head spine[6] fluke flap ladeo jaw cara[4] mirada[2] spin depth turbina).

    venv/bin/python retarget_ballena.py ~/Desktop/h26_limpio/BF-Lucia_kullawada_limpio.npz --tocar --animo playful     play it on the Blender whale
    venv/bin/python retarget_ballena.py playful_dan_001 --tocar                                                           a performer take (body + face)
    from retarget_ballena import esqueleto_a_ballena  ->  (n, 23) array + names, for the dataset in her body space
"""
import os, sys, json, math, time, socket, argparse, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from cuerpo_cualidades import cargar_npz, _norm, _clamp
CANALES_BALLENA = ["pitch", "roll", "yaw", "head", "spine0", "spine1", "spine2", "spine3", "spine4", "spine5", "fluke", "flap_l", "flap_r", "codo_l", "codo_r", "muneca_l", "muneca_r", "jaw", "cara_parpado", "cara_rabia", "cara_tristeza", "cara_asombro", "mirada_yaw", "mirada_pitch", "spin", "depth", "turbina", "avance", "deriva", "giro"]   # avance/deriva: the body's speed over the floor, forward and sideways (m/s); giro: turning speed (rad/s)
# CONSTRAINTS (Violeta, 17 Oct): her body has its own ranges; a dancer's extremes are folded into them. Radians unless noted.
LIMITES = {"pitch": (-0.6, 0.4), "roll": (-0.35, 0.35), "yaw": (-0.4, 0.4), "head": (-0.4, 0.35), "spine0": (-0.3, 0.3), "spine1": (-0.3, 0.3), "spine2": (-0.35, 0.25), "spine3": (-0.4, 0.25), "spine4": (-0.45, 0.25), "spine5": (-0.5, 0.25),
           "fluke": (-0.55, 0.3), "flap_l": (-0.25, 0.55), "flap_r": (-0.25, 0.55), "codo_l": (-0.4, 0.4), "codo_r": (-0.4, 0.4), "muneca_l": (-0.4, 0.4), "muneca_r": (-0.4, 0.4), "jaw": (0.0, 1.0), "cara_parpado": (0, 1), "cara_rabia": (0, 1), "cara_tristeza": (0, 1), "cara_asombro": (0, 1), "mirada_yaw": (-1, 1), "mirada_pitch": (-1, 1), "spin": (-6.3, 6.3), "depth": (-0.9, 0.9), "turbina": (0.3, 5.0), "avance": (-1.2, 1.5), "deriva": (-1.0, 1.0), "giro": (-2.0, 2.0)}
SUAVE = {"avance": 0.1, "deriva": 0.1, "giro": 0.1, "pitch": 0.12, "roll": 0.12, "yaw": 0.15, "head": 0.2, "flap_l": 0.25, "flap_r": 0.25, "codo_l": 0.3, "codo_r": 0.3, "muneca_l": 0.35, "muneca_r": 0.35, "depth": 0.1, "turbina": 0.08}   # low-pass per channel (fraction per frame at 24-30 fps); spine and fluke keep their own rhythm
REPOSO_MANO = -0.45   # metres: a hand hanging by the hip is this far below the shoulder = fin at rest (0); shoulder height = fin up ~0.3; above the head = 0.55
def limitar(X):
    """apply the constraints: clamp every channel to her range, then smooth the slow ones."""
    X = X.copy()
    for i, c in enumerate(CANALES_BALLENA):
        lo, hi = LIMITES[c]; v = X[:, i]; ok = np.isfinite(v); v[ok] = np.clip(v[ok], lo, hi)
        if c in SUAVE and ok.any():
            k = SUAVE[c]; e = v[ok][0]
            for f in range(len(v)):
                if ok[f]: e = (1 - k) * e + k * v[f]; v[f] = e
        X[:, i] = v
    return X
def _suave(x, k=0.2):
    y = np.zeros_like(x); e = x[0] if len(x) else 0.0
    for i, v in enumerate(x): e = (1 - k) * e + k * v; y[i] = e
    return y
def esqueleto_a_ballena(B, J, fps, largo_brazo=0.56):
    """B (n, 26, 3) metres, z up; J name -> index. Returns (n, 23) float32 with NaN where it could not be measured."""
    n = len(B); out = np.full((n, len(CANALES_BALLENA)), np.nan, np.float32); C = {c: i for i, c in enumerate(CANALES_BALLENA)}
    p = lambda k, f: B[f, J[k]]
    pel_z = B[:, J["pelvis"], 2]; z_pie = float(np.nanpercentile(pel_z, 80)) if np.isfinite(pel_z).any() else 0.9
    # MediaPipe world landmarks keep the pelvis at the origin: then crouch/jump is read from the legs (ankles rising towards the pelvis = crouch)
    pelvis_fija = np.nanstd(pel_z) < 0.02; tob = -np.nanmean(B[:, [J["ankle_l"], J["ankle_r"]], 2], axis=1) if pelvis_fija else None
    z_pierna = float(np.nanpercentile(tob, 80)) if pelvis_fija and np.isfinite(tob).any() else None
    # feet speed (m/s) -> tail: phase advances with the feet, amplitude with the body's energy
    pies = np.nanmean(np.linalg.norm(np.diff(B[:, [J["ankle_l"], J["ankle_r"]], :], axis=0), axis=2), axis=1) * fps; pies = np.concatenate([[0.0], np.where(np.isfinite(pies), pies, 0.0)]); pies = _suave(np.minimum(pies, 3.0), 0.15)
    todo = np.nanmean(np.linalg.norm(np.diff(B, axis=0), axis=2), axis=1) * fps; todo = np.concatenate([[0.0], np.where(np.isfinite(todo), todo, 0.0)]); energia = np.clip((_suave(np.minimum(todo, 3.0), 0.1) - 0.2) / 1.2, 0, 1)
    fase = 0.0; prev_ang = None
    # the body's path over the floor (pelvis x, y): its speed in its own frame -> avance (forward) and deriva (sideways); camera takes keep the pelvis fixed -> no travel
    pel_xy = B[:, J["pelvis"], :2]; vel_xy = np.vstack([[0, 0], np.diff(pel_xy, axis=0) * fps]); vel_xy = np.where(np.isfinite(vel_xy), vel_xy, 0.0)
    hay_camino = bool(np.nanstd(pel_xy[:, 0]) > 0.05 or np.nanstd(pel_xy[:, 1]) > 0.05)
    for f in range(n):
        pel, cue, cab = p("pelvis", f), p("neck", f), p("head", f); hl, hr = p("hip_l", f), p("hip_r", f); sl, sr = p("shoulder_l", f), p("shoulder_r", f)
        hz = 0.4 * min(1.0, pies[f] / 1.5) * 2.5   # 0..2.5 beats per second with the feet
        fase += 2 * math.pi * hz / fps; A = 0.12 + 0.4 * energia[f]
        out[f, C["fluke"]] = -A * math.sin(fase)                      # negative = flukes raised
        out[f, C["turbina"]] = 0.4 + 6.0 * min(1.0, pies[f] / 2.0)    # rad/s: still feet 0.4, running feet 6.4
        out[f, C["spin"]] = 0.0; out[f, C["jaw"]] = np.nan
        if not np.all(np.isfinite(np.concatenate([pel, cue, hl, hr, sl, sr]))): continue
        lado = _norm(hr - hl); lado[2] = 0; lado = _norm(lado); frente = np.array([-lado[1], lado[0], 0.0]); torso = _norm(cue - pel)
        lean = _clamp(np.dot(torso, frente) / 0.7)                   # forward +
        hombros = _norm(sr - sl); hombros[2] = 0; hombros = _norm(hombros)
        twist = _clamp(math.atan2(np.cross(lado, hombros)[2], np.dot(lado, hombros)) / 0.8); roll_h = _clamp(0.6 * _clamp(np.dot(torso, lado) / 0.5) + 0.4 * twist)
        ang = math.atan2(frente[1], frente[0]); giro = 0.0
        if prev_ang is not None: dd = (ang - prev_ang + math.pi) % (2 * math.pi) - math.pi; giro = _clamp(dd * fps / 3.0)
        prev_ang = ang
        out[f, C["pitch"]] = -0.5 * lean; out[f, C["roll"]] = 0.35 * roll_h; out[f, C["yaw"]] = 0.4 * giro
        if hay_camino:
            v = vel_xy[f]; out[f, C["avance"]] = float(np.dot(v, frente[:2])); out[f, C["deriva"]] = float(np.dot(v, lado[:2])); out[f, C["giro"]] = giro * 3.0
        else: out[f, C["avance"]] = 0.0; out[f, C["deriva"]] = 0.0; out[f, C["giro"]] = 0.0
        out[f, C["depth"]] = 0.7 * _clamp(((tob[f] - z_pierna) / 0.35) if (pelvis_fija and z_pierna is not None and np.isfinite(tob[f])) else (pel[2] - z_pie) / 0.35)
        # spine: front vertebrae follow the lean (down when leaning forward), tail vertebrae follow the legs (a lifted leg raises the tail)
        pierna = 0.0; cnt = 0
        for hip, knee in (("hip_l", "knee_l"), ("hip_r", "knee_r")):
            h_, k_ = p(hip, f), p(knee, f)
            if np.all(np.isfinite(np.concatenate([h_, k_]))): pierna += _clamp((k_[2] - h_[2] + 0.45) / 0.45, 0, 1); cnt += 1   # 0 = leg hanging, 1 = knee at hip height
        pierna = pierna / cnt if cnt else 0.0
        out[f, C["spine0"]] = 0.30 * lean; out[f, C["spine1"]] = 0.22 * lean
        for k, g in zip(("spine2", "spine3", "spine4", "spine5"), (0.12, 0.2, 0.28, 0.36)): out[f, C[k]] = -g * pierna - 0.08 * energia[f] * math.sin(fase)
        # hands -> fins
        fl = fr_ = np.nan
        for lado_n, w, s_ in (("l", "wrist_l", "shoulder_l"), ("r", "wrist_r", "shoulder_r")):
            wp, sp = p(w, f), p(s_, f)
            if np.all(np.isfinite(np.concatenate([wp, sp]))):
                v = 0.55 * _clamp((wp[2] - sp[2] - REPOSO_MANO) / (largo_brazo - REPOSO_MANO), -0.45, 1.0)   # hanging hand = 0, shoulder = ~0.25, above the head = 0.55
                if lado_n == "l": fl = v
                else: fr_ = v
        out[f, C["flap_l"]] = fl; out[f, C["flap_r"]] = fr_   # each hand its own fin
        # the arm's joints -> the fin's three links: shoulder (upper arm elevation) = side_fine, elbow = .001, wrist = .002
        for lado_n, sh, el, wr in (("l", "shoulder_l", "elbow_l", "wrist_l"), ("r", "shoulder_r", "elbow_r", "wrist_r")):
            S_, E_, W_ = p(sh, f), p(el, f), p(wr, f)
            if np.all(np.isfinite(np.concatenate([S_, E_, W_]))):
                out[f, C["flap_" + lado_n]] = 0.55 * _clamp((E_[2] - S_[2] - REPOSO_MANO * 0.55) / (0.3 - REPOSO_MANO * 0.55), -0.45, 1.0)   # upper arm: hanging = rest, horizontal = up
                out[f, C["codo_" + lado_n]] = 0.4 * _clamp((W_[2] - E_[2]) / 0.28)                                                            # forearm rises above the elbow -> link 2 up
                u = _norm(E_ - S_); v = _norm(W_ - E_); out[f, C["muneca_" + lado_n]] = 0.4 * _clamp((1.0 - float(np.dot(u, v))) / 0.8) * (1 if W_[2] >= E_[2] else -1)   # bent arm -> link 3 curls, up or down
        # head -> head (and gaze)
        if np.all(np.isfinite(cab)):
            v = _norm(cab - cue); hy = _clamp(np.dot(v, lado) / 0.5); hp = _clamp((v[2] - 0.9) / 0.4)
            out[f, C["head"]] = 0.35 * hp; out[f, C["mirada_yaw"]] = hy; out[f, C["mirada_pitch"]] = hp
        out[f, C["cara_parpado"]] = 0.0; out[f, C["cara_rabia"]] = 0.0; out[f, C["cara_tristeza"]] = 0.0; out[f, C["cara_asombro"]] = 0.0
    return limitar(out)
def cargar_toma(nombre):
    """a performer take: datasets/cuerpo/<take>.jsonl (esqueleto per frame) + datasets/cara/<take>.jsonl (face)."""
    cu = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cuerpo", nombre + ".jsonl"))]; ca = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cara", nombre + ".jsonl"))]
    filas = [(r["t"], r["esqueleto"]) for r in cu if r.get("esqueleto")]
    if len(filas) < 24: raise SystemExit("take without body")
    t = np.array([f[0] for f in filas]); B = np.array([[np.nan if v is None else v for v in f[1]] for f in filas], np.float32).reshape(-1, 26, 3); fps = float(len(t) / max(1e-6, t[-1] - t[0]))
    # the performer's travel in the room (takes from 17 Oct evening on): hips in the image + torso size -> a floor path, added to the whole skeleton
    pos = [(r.get("cuerpo_x"), r.get("cuerpo_tam")) for r in cu if r.get("esqueleto")]
    if sum(1 for x, tm in pos if x is not None and tm) > len(pos) * 0.5:
        xi = np.array([np.nan if x is None else x for x, tm in pos], np.float32); tam = np.array([np.nan if not tm else tm for x, tm in pos], np.float32)
        dist = np.clip(0.5 / np.maximum(tam, 0.05), 0.5, 6.0)                       # metres from the camera, approx (torso ~0.5 m)
        xm = (xi - 0.5) * 2.0 * dist * math.tan(math.radians(34.5))                  # OAK-D colour camera ~69 deg horizontal
        for a_ in (xm, dist):
            ok = np.isfinite(a_)
            if ok.any(): a_[:] = np.interp(np.arange(len(a_)), np.flatnonzero(ok), a_[ok])
        xm, dist = _suave(np.nan_to_num(xm), 0.1), _suave(np.nan_to_num(dist), 0.1)
        B[:, :, 0] += xm[:, None]; B[:, :, 1] += (-dist)[:, None]   # the viewer/camera is at -Y: closer to the camera = more negative Y
    from cuerpo_cualidades import cargar_npz as _c; J = {k: i for i, k in enumerate(["nose", "eye_l", "eye_r", "ear_l", "ear_r", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "wrist_l", "wrist_r", "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head", "neck", "pelvis", "bigtoe_l", "bigtoe_r", "smalltoe_l", "smalltoe_r", "heel_l", "heel_r"])}
    vit = {k: np.array([float(r.get(k) or 0) for r in cu if r.get("esqueleto")]) for k in ("emotibit_hr", "emotibit_eda", "emotibit_therm")}
    tc = np.array([r["t"] for r in ca]); cara = {k: np.array([float(r.get(k, 0) or 0) for r in ca]) for k in ("jaw_open", "blink", "brow_up", "brow_down", "mouth_sad", "mouth_smile", "head_yaw", "head_pitch")}
    caraf = {k: np.interp(t, tc, v) for k, v in cara.items()} if len(tc) else None
    if caraf is not None: caraf.update({k: v for k, v in vit.items() if (v > 0).any()})
    return B, J, fps, caraf, nombre.split("_")[0]
def cara_de_animo(animo, preferir=("dan", "violeta", "suri", "sanam")):
    """a body without a face borrows the face of a performer recorded in that mood (datasets/cara/<animo>_<actor>_NNN.jsonl):
    jaw, blink, brows, mouth, eyes, head, and their heart. Returns dict of arrays on the take's own time, or None."""
    import glob as _g
    cands = sorted(_g.glob(os.path.join(AQUI, "datasets", "cara", f"{animo}_*.jsonl")))
    cands.sort(key=lambda f: (next((i for i, a in enumerate(preferir) if "_" + a + "_" in os.path.basename(f)), 9), -os.path.getsize(f)))
    for f in cands:
        ca = [json.loads(l) for l in open(f)]; ca = [r for r in ca if "jaw_open" in r]
        if len(ca) < 60: continue
        t = np.array([r["t"] for r in ca]); t = t - t[0]
        out = {k: np.array([float(r.get(k, 0) or 0) for r in ca]) for k in ("jaw_open", "blink", "brow_up", "brow_down", "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch", "head_yaw", "head_pitch")}
        fc = f.replace("/cara/", "/cuerpo/")
        if os.path.exists(fc):
            cu = [json.loads(l) for l in open(fc)]; hr = np.array([float(r.get("emotibit_hr") or 0) for r in cu]); tcu = np.array([r["t"] for r in cu]); tcu = tcu - tcu[0] if len(tcu) else tcu
            if len(hr) and (hr > 0).any(): out["emotibit_hr"] = np.interp(t, tcu, hr); out["emotibit_eda"] = np.interp(t, tcu, np.array([float(r.get("emotibit_eda") or 0) for r in cu]))
        out["_t"] = t; out["_nombre"] = os.path.basename(f)[:-6]; return out
    return None
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("fuente"); ap.add_argument("--tocar", action="store_true"); ap.add_argument("--animo", default=None); ap.add_argument("--loop", action="store_true"); ap.add_argument("--puerto", type=int, default=9998); ap.add_argument("--quieta", action="store_true", help="do not travel: only the body moves (default: she travels with the body's own displacement)"); a = ap.parse_args()
    caraf = None
    if a.fuente.endswith(".npz"): B, J, fps = cargar_npz(a.fuente); nombre = os.path.basename(a.fuente)[:-4]; animo = a.animo or "calm"
    else: B, J, fps, caraf, animo = cargar_toma(a.fuente); nombre = a.fuente; animo = a.animo or animo
    prestada = cara_de_animo(animo) if caraf is None else None
    if prestada is not None: print(f"   face borrowed from {prestada['_nombre']} ({animo})")
    X = esqueleto_a_ballena(B, J, fps); ok = np.isfinite(X[:, 0]).mean(); C_ = {c: i for i, c in enumerate(CANALES_BALLENA)}; m_ = lambda c: float(np.nanmean(X[:, C_[c]]))
    print(f"   {nombre}: {len(B) / fps:.0f} s at {fps:.0f} fps -> whale channels | measured {100 * ok:.0f}% of frames | pitch {m_('pitch'):+.2f} fin L {m_('flap_l'):+.2f} R {m_('flap_r'):+.2f} elbow {m_('codo_l'):+.2f} wrist {m_('muneca_l'):+.2f} | fluke amp {float(np.nanstd(X[:, C_['fluke']])):.2f} turbine {m_('turbina'):.1f} rad/s | travel {float(np.nanmean(np.abs(X[:, C_['avance']]))):.2f} m/s | depth {m_('depth'):+.2f} (min {float(np.nanmin(X[:, C_['depth']])):+.2f})")
    if not a.tocar: sys.exit(0)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); FPS = 30.0; C = {c: i for i, c in enumerate(CANALES_BALLENA)}; ult = {}
    ESCALA_PISO = 0.8; RADIO_MAX = 2.0; px = py_ = 0.0; rumbo = math.pi   # she starts at home facing the viewer (yaw pi); the dancer's forward is her forward
    import random; proximo_parpadeo = 2.0 + random.random() * 3.0; parpadeo_hasta = -1.0   # a body without a face still blinks: every 2-5 s, 0.15 s closed (a double blink now and then)
    while True:
        t0 = time.time(); n30 = int(len(B) / fps * FPS)
        for i in range(n30):
            f = min(len(B) - 1, int(i / FPS * fps)); x = X[f]
            for k, v in zip(CANALES_BALLENA, x):
                if np.isfinite(v): ult[k] = float(v)
            can = {"pitch": ult.get("pitch", 0), "roll": ult.get("roll", 0), "yaw": ult.get("yaw", 0), "head": ult.get("head", 0), "spine": [ult.get(f"spine{j}", 0) for j in range(6)], "fluke": ult.get("fluke", 0), "flap": 0.0, "ladeo": 0.0, "aleta_l": [ult.get("flap_l", 0), ult.get("codo_l", 0), ult.get("muneca_l", 0)], "aleta_r": [ult.get("flap_r", 0), ult.get("codo_r", 0), ult.get("muneca_r", 0)],   # shoulder, elbow, wrist -> the three links of each fin
                   "jaw": 0.0, "cara": [ult.get("cara_parpado", 0), ult.get("cara_rabia", 0), ult.get("cara_tristeza", 0), ult.get("cara_asombro", 0)], "mirada": [ult.get("mirada_yaw", 0), ult.get("mirada_pitch", 0)], "spin": 0.0, "depth": ult.get("depth", 0), "turbina": ult.get("turbina", 1.0)}
            if not a.quieta:   # travel: integrate the body's speeds in her own heading (yaw 0 = looking +Y; she moves forward along where she looks)
                dt = 1.0 / FPS; rumbo += ult.get("giro", 0.0) * dt; av, de = ult.get("avance", 0.0) * ESCALA_PISO, ult.get("deriva", 0.0) * ESCALA_PISO
                px += (av * math.sin(rumbo) + de * math.cos(rumbo)) * dt; py_ += (av * math.cos(rumbo) - de * math.sin(rumbo)) * dt
                r_ = math.hypot(px, py_)
                if r_ > RADIO_MAX: px, py_ = px * RADIO_MAX / r_, py_ * RADIO_MAX / r_   # her space has an edge: she slides along it
                can["x"], can["y"], can["z"], can["rumbo"] = round(px, 3), round(py_, 3), 0.0, round((rumbo + math.pi) % (2 * math.pi) - math.pi, 3)
            pk = {"actor_animo": animo, "bailarin": "retarget:" + nombre, "water": 0.8, "red": 1, "soltar_manual": 1 if i < 30 else 0, "espacio": 0 if a.quieta else 1, "canales": can, "head_yaw": round(0.5 * ult.get("mirada_yaw", 0), 3), "head_pitch": round(0.5 * ult.get("mirada_pitch", 0), 3),
                  "l_palm_y": round(float(np.clip(0.5 - ult.get("flap_l", 0.0) / 1.2, 0, 1)), 3), "r_palm_y": round(float(np.clip(0.5 - ult.get("flap_r", 0.0) / 1.2, 0, 1)), 3)}   # receiver: hand height -> that side's fin (0 = hand up)
            if caraf is None and prestada is not None:   # the borrowed face, looping on its own clock
                tt = (i / FPS) % float(prestada["_t"][-1]); j = int(np.searchsorted(prestada["_t"], tt))
                j = min(len(prestada["_t"]) - 1, j)
                for k in ("jaw_open", "blink", "brow_up", "brow_down", "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch", "emotibit_hr", "emotibit_eda"):
                    if k in prestada: pk[k] = round(float(prestada[k][j]), 3)
                pk["head_yaw"] = round(0.5 * ult.get("mirada_yaw", 0) + 0.5 * float(prestada["head_yaw"][j]), 3); pk["head_pitch"] = round(0.5 * ult.get("mirada_pitch", 0) + 0.5 * float(prestada["head_pitch"][j]), 3)   # head: half the dancer, half the face
            elif caraf is None:
                tt = i / FPS
                if tt >= proximo_parpadeo: parpadeo_hasta = tt + 0.15; proximo_parpadeo = tt + (0.4 if random.random() < 0.2 else 2.0 + random.random() * 3.0)
                pk["blink"] = 1.0 if tt < parpadeo_hasta else 0.0; pk["eye_yaw"] = round(0.6 * ult.get("mirada_yaw", 0), 3); pk["eye_pitch"] = round(0.6 * ult.get("mirada_pitch", 0), 3)   # the eyes look where the dancer's head looks
            if caraf is not None:
                tt = f / fps + (caraf and 0); ti = min(len(caraf["jaw_open"]) - 1, f)
                for k in ("jaw_open", "blink", "brow_up", "brow_down", "mouth_sad", "mouth_smile", "head_yaw", "head_pitch", "emotibit_hr", "emotibit_eda", "emotibit_therm"):
                    if k in caraf: pk[k] = round(float(caraf[k][min(len(caraf[k]) - 1, ti)]), 3)   # heart, skin and warmth of the performer travel with the body
            s.sendto(json.dumps(pk).encode(), ("127.0.0.1", a.puerto))
            if i % 30 == 0: json.dump({"tramo": "retarget:" + nombre, "modo": "cuerpo", "t": int(i / FPS), "dur": int(len(B) / fps), "loop": a.loop, "hora": time.time()}, open("/tmp/ballena_reproduciendo.json", "w"))
            esp = t0 + (i + 1) / FPS - time.time()
            if esp > 0: time.sleep(esp)
        if not a.loop: break
