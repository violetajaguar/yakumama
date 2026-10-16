#!/usr/bin/env python3
"""cuerpo_cualidades.py - de un esqueleto de 26 puntos (Paqarina) a las CUALIDADES que conducen a la ballena.

    cualidades_toma(B, J, fps) -> dict de arrays (cuadros,):
        cuerpo_pitch, cuerpo_roll, cuerpo_yaw, cuerpo_profundidad, cuerpo_energia, cuerpo_suavidad,
        l_palm_x, l_palm_y, r_palm_x, r_palm_y, head_yaw, head_pitch   (NaN donde no se pudo medir)
Lo usan bailar.py (en vivo) y jepa_datos.py (para aprender). Ver bailar.py para el significado de cada una.
"""
import math, numpy as np
CUERPO = ["cuerpo_pitch", "cuerpo_roll", "cuerpo_yaw", "cuerpo_profundidad", "cuerpo_energia", "cuerpo_suavidad"]
def _norm(v):
    n = np.linalg.norm(v); return v / n if n > 1e-9 else v
def _clamp(v, lo=-1.0, hi=1.0): return float(max(lo, min(hi, v)))
def suavidad_toma(B, J, fps):
    """1 = suave (poca potencia del torso por encima de 3 Hz), 0 = a golpes."""
    torso = [J[k] for k in ("pelvis", "neck", "shoulder_l", "shoulder_r", "hip_l", "hip_r") if k in J]
    v = np.nan_to_num(np.diff(B[:, torso, :], axis=0) * fps)
    if len(v) < 8: return 0.5
    F = np.abs(np.fft.rfft(v - v.mean(0), axis=0)) ** 2; f = np.fft.rfftfreq(len(v), 1 / fps)
    hf = float(F[f > 3].sum() / max(1e-9, F[1:].sum())); return float(np.clip(1 - (hf - 0.08) / 0.3, 0, 1))
def energia_toma(B, fps):
    vel = np.nanmean(np.linalg.norm(np.diff(B, axis=0), axis=2), axis=1) * fps
    vel = np.concatenate([[vel[0] if len(vel) else 0.0], vel]); vel = np.where(np.isfinite(vel), vel, 0.0)
    ema = np.zeros_like(vel); e = 0.0
    for i, v in enumerate(vel): e = 0.9 * e + 0.1 * min(v, 3.0); ema[i] = e
    return np.clip((ema - 0.2) / 1.2, 0, 1)
def cualidades_toma(B, J, fps, largo_brazo=0.56):
    n = len(B); out = {k: np.full(n, np.nan) for k in CUERPO + ["l_palm_x", "l_palm_y", "r_palm_x", "r_palm_y", "head_yaw", "head_pitch"]}
    pelvis_z = B[:, J["pelvis"], 2]; z_pie = float(np.nanpercentile(pelvis_z, 80)) if np.isfinite(pelvis_z).any() else 0.9
    en = energia_toma(B, fps); su = suavidad_toma(B, J, fps); prev = None
    p = lambda k, f: B[f, J[k]]
    for f in range(n):
        pel, cue, cab = p("pelvis", f), p("neck", f), p("head", f); hl, hr = p("hip_l", f), p("hip_r", f); sl, sr = p("shoulder_l", f), p("shoulder_r", f)
        out["cuerpo_energia"][f] = en[f] * (1 - 0.4 * su); out["cuerpo_suavidad"][f] = su
        if not np.all(np.isfinite(np.concatenate([pel, cue, hl, hr, sl, sr]))): continue
        lado = _norm(hr - hl); lado[2] = 0; lado = _norm(lado); frente = np.array([-lado[1], lado[0], 0.0]); torso = _norm(cue - pel)
        out["cuerpo_pitch"][f] = _clamp(np.dot(torso, frente) / 0.7)
        hombros = _norm(sr - sl); hombros[2] = 0; hombros = _norm(hombros)
        twist = _clamp(math.atan2(np.cross(lado, hombros)[2], np.dot(lado, hombros)) / 0.8)
        out["cuerpo_roll"][f] = _clamp(0.6 * _clamp(np.dot(torso, lado) / 0.5) + 0.4 * twist)
        ang = math.atan2(frente[1], frente[0]); yaw = 0.0
        if prev is not None:
            d = ang - prev; d = (d + math.pi) % (2 * math.pi) - math.pi; yaw = _clamp(d * fps / 3.0)
        prev = ang; out["cuerpo_yaw"][f] = yaw; out["cuerpo_profundidad"][f] = _clamp((pel[2] - z_pie) / 0.35)
        for lado_n, w, s in (("l", "wrist_l", "shoulder_l"), ("r", "wrist_r", "shoulder_r")):
            wp, sp = p(w, f), p(s, f)
            if np.all(np.isfinite(np.concatenate([wp, sp]))):
                out[f"{lado_n}_palm_y"][f] = _clamp(0.5 - (wp[2] - sp[2]) / (2 * largo_brazo), 0, 1)
                out[f"{lado_n}_palm_x"][f] = _clamp(0.5 + np.dot(wp - sp, lado) / (2 * largo_brazo), 0, 1)
        if np.all(np.isfinite(cab)):
            v = _norm(cab - cue); out["head_yaw"][f] = _clamp(np.dot(v, lado) / 0.5); out["head_pitch"][f] = _clamp((v[2] - 0.9) / 0.4)
    return out
def cargar_npz(ruta):
    z = np.load(ruta, allow_pickle=True); B = z["body"].astype(np.float64); J = {str(k): i for i, k in enumerate(z["joint_names"])}
    return B, J, (float(z["fps"]) if "fps" in z.files else 30.0)
