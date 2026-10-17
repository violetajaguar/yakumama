#!/usr/bin/env python3
"""ballena_datos.py - everything she can learn, translated into HER OWN BODY SPACE (retarget_ballena.CANALES_BALLENA + heart and skin),
one track per take at 12 frames/s with a mask of what each source brings. This is what hjepa_ballena.py trains on, so that
what she generates is whale movement, not six summary numbers (Dan, 17 Oct).

Sources (and the mood each one carries as the action):
  - Paqarina dancers (~/Desktop/h26_limpio, 26-point skeletons): tinku -> angry, kullawada -> playful, suri -> curious, breaking -> alert; others free
  - bodies from video (datasets/cuerpo_video): freedivers/diving48 -> diving, ballet -> sad, jazz -> singing, swimmers -> surfacing/feeding,
    people expressing emotions (feel*) -> their mood; capped per prefix so the set stays balanced
  - the performers head to toe (datasets/cuerpo + datasets/cara: Violeta, Dan, Suri...): body + face + heart + skin, mood of the take
  - real tagged humpbacks (datasets/ballenas): pitch, roll, turning, depth only; action "ballena"
  - her ten designed behaviours (comportamientos_animos.comp_<mood>): 120 s each, the anchors of each mood

    venv/bin/python ballena_datos.py                      -> modelos/ballena_datos.npz
    venv/bin/python ballena_datos.py --max-video 150      (per video prefix)
"""
import os, sys, json, glob, math, argparse, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from retarget_ballena import esqueleto_a_ballena, CANALES_BALLENA, cargar_toma, limitar
from cuerpo_cualidades import cargar_npz
MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
CANALES = CANALES_BALLENA + ["pulso", "piel"]   # heart (bpm/100) and skin (uS/10) ride with the body
NC = len(CANALES); FPS = 12.0; CI = {c: i for i, c in enumerate(CANALES)}
DANZA_ANIMO = {"tinku": "angry", "kullawada": "playful", "breaking": "alert", "toprock": "alert", "gbr": "alert", "suri": "curious"}
VIDEO_ANIMO = {"freediver": "diving", "diving48": "diving", "tinku": "angry", "ballet": "sad", "jazz": "singing", "feelsad": "sad", "feelangry": "angry", "feelhappy": "playful", "feelsurprised": "curious", "feelfearful": "alert", "feelneutral": "calm"}
def a_rejilla(t, X, fps_out=FPS):
    """resample a (n, k) track with its times to 12/s; NaN -> masked."""
    tg = np.arange(t[0], t[-1], 1 / fps_out); out = np.full((len(tg), X.shape[1]), np.nan, np.float32)
    for j in range(X.shape[1]):
        v = X[:, j]; ok = np.isfinite(v)
        if ok.sum() >= 2: out[:, j] = np.interp(tg, t[ok], v[ok]); pres = np.interp(tg, t, ok.astype(float)) > 0.5; out[~pres, j] = np.nan
    return out
def pista_esqueleto(B, J, fps, animo, actor, fuente, nombre, cara=None, vit=None):
    X = esqueleto_a_ballena(B, J, fps); n = len(X); t = np.arange(n) / fps
    full = np.full((n, NC), np.nan, np.float32); full[:, :len(CANALES_BALLENA)] = X
    if cara is not None:   # a performer's face: jaw, brows -> cara, eyes -> mirada
        full[:, CI["jaw"]] = cara["jaw_open"]; full[:, CI["cara_parpado"]] = cara["blink"]; full[:, CI["cara_rabia"]] = np.clip(cara["brow_down"], 0, 1); full[:, CI["cara_tristeza"]] = np.clip(cara["mouth_sad"], 0, 1); full[:, CI["cara_asombro"]] = np.clip(cara["brow_up"], 0, 1)
        full[:, CI["mirada_yaw"]] = cara["eye_yaw"]; full[:, CI["mirada_pitch"]] = cara["eye_pitch"]
        if "emotibit_hr" in cara: full[:, CI["pulso"]] = np.where(cara["emotibit_hr"] > 30, cara["emotibit_hr"] / 100.0, np.nan)
        if "emotibit_eda" in cara: full[:, CI["piel"]] = np.where(cara["emotibit_eda"] > 0.05, cara["emotibit_eda"] / 10.0, np.nan)
    else:
        for c in ("jaw", "cara_parpado", "cara_rabia", "cara_tristeza", "cara_asombro"): full[:, CI[c]] = np.nan   # no face: masked, not zero
    Xg = a_rejilla(t, full)
    if len(Xg) < 48: return None
    return dict(X=Xg, animo=MOODS.index(animo) if animo in MOODS else -1, actor=actor, fuente=fuente, nombre=nombre)
def pista_ballena(ruta):
    z = np.load(ruta, allow_pickle=True); fps = float(z["fps"]); n = len(z["pitch"]); t = np.arange(n) / fps
    full = np.full((n, NC), np.nan, np.float32)
    full[:, CI["pitch"]] = np.clip(z["pitch"], -0.6, 0.4); full[:, CI["roll"]] = np.clip(z["roll"], -0.35, 0.35)
    rumbo = np.unwrap(z["rumbo"].astype(np.float64)); giro = np.gradient(rumbo) * fps; full[:, CI["giro"]] = np.clip(giro, -2, 2); full[:, CI["yaw"]] = np.clip(giro * 0.2, -0.4, 0.4)
    prof = z["prof"].astype(np.float64); full[:, CI["depth"]] = np.clip(-prof / 30.0, -0.9, 0.9)   # 30 m down = -0.9 (her deepest)
    full[:, CI["avance"]] = 1.0   # a swimming whale moves forward at about 1 m/s
    Xg = a_rejilla(t, full)
    return dict(X=Xg, animo=-2, actor="ballena", fuente="ballena", nombre=os.path.basename(ruta)[:-4])
def pistas_comportamientos(dur=120.0):
    import comportamientos_animos as CA
    out = []
    for m in MOODS:
        f = CA.COMPORTAMIENTOS[m]; n = int(dur * FPS); X = np.full((n, NC), np.nan, np.float32)
        for i in range(n):
            c = f(i / FPS)
            X[i, CI["pitch"]], X[i, CI["roll"]], X[i, CI["yaw"]], X[i, CI["head"]] = c["pitch"], c["roll"], c["yaw"], c["head"]
            for k in range(6): X[i, CI[f"spine{k}"]] = c["spine"][k]
            X[i, CI["fluke"]] = c["fluke"]; X[i, CI["flap_l"]] = c["flap"] + c["ladeo"]; X[i, CI["flap_r"]] = c["flap"] - c["ladeo"]; X[i, CI["codo_l"]] = X[i, CI["codo_r"]] = 0.35 * c["flap"]; X[i, CI["muneca_l"]] = X[i, CI["muneca_r"]] = 0.15 * c["flap"]
            X[i, CI["jaw"]] = c["jaw"]; X[i, CI["cara_parpado"]], X[i, CI["cara_rabia"]], X[i, CI["cara_tristeza"]], X[i, CI["cara_asombro"]] = c["cara"]; X[i, CI["mirada_yaw"]], X[i, CI["mirada_pitch"]] = c["mirada"]
            X[i, CI["spin"]] = c["spin"]; X[i, CI["depth"]] = c["depth"]; tb = CA.TURBINA_ANIMO.get(m, 1.0); X[i, CI["turbina"]] = 1.2 if tb == "pulso" else float(tb)
            X[i, CI["avance"]] = X[i, CI["deriva"]] = X[i, CI["giro"]] = 0.0
        out.append(dict(X=X, animo=MOODS.index(m), actor="ballena_disenada", fuente="comportamiento", nombre="comp_" + m))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--bailarines", default=os.path.expanduser("~/Desktop/h26_limpio")); ap.add_argument("--max-video", type=int, default=150); a = ap.parse_args()
    pistas = []
    for ruta in sorted(glob.glob(os.path.join(a.bailarines, "*.npz"))):
        try:
            B, J, fps = cargar_npz(ruta); n = os.path.basename(ruta)[:-4]; an = next((v for k, v in DANZA_ANIMO.items() if k in n.lower()), None)
            actor = n.split("_")[0].split("-")[-1].lower(); r = pista_esqueleto(B, J, fps, an, actor, "bailarin", n)
            if r: pistas.append(r)
        except Exception as e: print("  (dancer skipped", os.path.basename(ruta), e, ")")
    print(f"dancers: {len(pistas)} tracks")
    por_pref = {}; nv = 0
    for ruta in sorted(glob.glob(os.path.join(AQUI, "datasets", "cuerpo_video", "*.npz"))):
        n = os.path.basename(ruta)[:-4].lower(); pref = n.split("_")[0]
        if por_pref.get(pref, 0) >= a.max_video: continue
        an = VIDEO_ANIMO.get(pref)
        if pref == "swim": an = "surfacing" if ("butterfly" in n or "freestyle" in n) else "feeding"
        try:
            B, J, fps = cargar_npz(ruta); r = pista_esqueleto(B, J, fps, an, pref, "video", n)
            if r: pistas.append(r); por_pref[pref] = por_pref.get(pref, 0) + 1; nv += 1
        except Exception as e: pass
    print(f"video bodies: {nv} tracks " + ", ".join(f"{k} {v}" for k, v in sorted(por_pref.items())))
    npf = 0
    for ruta in sorted(glob.glob(os.path.join(AQUI, "datasets", "cuerpo", "*.jsonl"))):
        nombre = os.path.basename(ruta)[:-6]
        try: B, J, fps, cara, animo = cargar_toma(nombre)
        except SystemExit: continue
        except Exception as e: continue
        r = pista_esqueleto(B, J, fps, animo, nombre.split("_")[1] if "_" in nombre else "?", "performer", nombre, cara=cara)
        if r: pistas.append(r); npf += 1
    print(f"performers head to toe: {npf} tracks")
    for ruta in sorted(glob.glob(os.path.join(AQUI, "datasets", "ballenas", "*.npz"))):
        try: pistas.append(pista_ballena(ruta))
        except Exception as e: print("  (whale skipped", ruta, e, ")")
    pistas += pistas_comportamientos()
    X = np.concatenate([p["X"] for p in pistas]); M = np.isfinite(X); Xz = np.where(M, X, 0.0).astype(np.float32)
    media = np.array([np.nanmean(X[:, j]) if M[:, j].any() else 0.0 for j in range(NC)], np.float32); desvio = np.array([np.nanstd(X[:, j]) + 1e-3 if M[:, j].any() else 1.0 for j in range(NC)], np.float32)
    SEQ = []; pos = 0
    for p in pistas: SEQ.append((pos, pos + len(p["X"]))); pos += len(p["X"])
    np.savez_compressed(os.path.join(AQUI, "modelos", "ballena_datos.npz"), X=Xz, M=M, SEQ=np.array(SEQ), ANIMO=np.array([p["animo"] for p in pistas]), ACTOR=np.array([p["actor"] for p in pistas]), FUENTE=np.array([p["fuente"] for p in pistas]), NOMBRE=np.array([p["nombre"] for p in pistas]), CANALES=np.array(CANALES), media=media, desvio=desvio, fps=FPS)
    horas = pos / FPS / 3600; print(f"\nmodelos/ballena_datos.npz: {len(pistas)} tracks, {horas:.1f} h at {FPS:.0f}/s, {NC} channels: {' '.join(CANALES)}")
    for fu in ("bailarin", "video", "performer", "ballena", "comportamiento"): print(f"  {fu:14s} {sum(len(p['X']) for p in pistas if p['fuente'] == fu) / FPS / 60:7.1f} min")
    print("  per mood: " + ", ".join(f"{m} {sum(len(p['X']) for p in pistas if p['animo'] == i) / FPS / 60:.0f} min" for i, m in enumerate(MOODS)))
    print("  channel coverage: " + ", ".join(f"{c} {100 * M[:, j].mean():.0f}%" for j, c in enumerate(CANALES)))
if __name__ == "__main__": main()
