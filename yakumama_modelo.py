#!/usr/bin/env python3
"""yakumama_modelo.py - the Yakumama motion net with NumPy only (no PyTorch), for TouchDesigner or any Python.

Weights: modelos/movimiento_pesos.npz (exported from modelos/movimiento.pt). Same maths as entrenar_movimiento.py.

    from yakumama_modelo import Modelo
    m = Modelo("modelos/movimiento_pesos.npz")
    canales = m.paso("playful", t=3.2)        # dict of the 18 performer channels at second 3.2 of a playful performance
    paquete = m.paquete("playful", t=3.2)     # the same, shaped as the UDP packet the Blender receiver understands

Inputs (24): one-hot mood (10), progress in the take (t/dur), sin/cos at periods 0.5,1,2,4,8,16 s (12), previous pulse (hr-85)/30.
Outputs (18): head_yaw, head_pitch, jaw_open, blink, brow_up, brow_down, mouth_sad, mouth_smile, eye_yaw, eye_pitch,
              l_palm_y, r_palm_y, l_palm_x, r_palm_x, mano_l, mano_r, hr (hr-85)/30, eda (eda/10).
"""
import math, json, numpy as np
MOODS = ["calm","singing","playful","curious","feeding","sad","angry","alert","diving","surfacing"]
SALIDAS = ["head_yaw","head_pitch","jaw_open","blink","brow_up","brow_down","mouth_sad","mouth_smile","eye_yaw","eye_pitch","l_palm_y","r_palm_y","l_palm_x","r_palm_x","mano_l","mano_r","hr","eda"]
PERIODOS = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
HR_ANIMO = {"calm": 84, "singing": 88, "playful": 86, "curious": 89, "feeding": 118, "sad": 101, "angry": 87, "alert": 102, "diving": 57, "surfacing": 78}
def entrada(animo, t, dur=120.0, hr_prev=85.0):
    x = [0.0] * 10; x[MOODS.index(animo)] = 1.0; x.append(t / max(dur, 1.0))
    for P in PERIODOS: x += [math.sin(2 * math.pi * t / P), math.cos(2 * math.pi * t / P)]
    x.append((hr_prev - 85.0) / 30.0); return np.array(x, np.float32)
class Modelo:
    def __init__(self, ruta="modelos/movimiento_pesos.npz"):
        z = np.load(ruta); self.capas = [(z[f"W{i}"], z[f"b{i}"]) for i in range(int(z["n_capas"]))]
        self.hr_prev = {m: float(HR_ANIMO[m]) for m in MOODS}; self.ult_parpadeo = {m: -9.0 for m in MOODS}
    def forward(self, x):
        h = x
        for i, (W, b) in enumerate(self.capas):
            h = h @ W.T + b
            if i < len(self.capas) - 1: h = np.maximum(h, 0.0)
        return h
    def paso(self, animo, t, dur=120.0):
        y = self.forward(entrada(animo, t % dur, dur, self.hr_prev[animo])); v = dict(zip(SALIDAS, [float(a) for a in y]))
        hr = max(HR_ANIMO[animo] - 15, min(HR_ANIMO[animo] + 20, 85.0 + 30.0 * v["hr"])); self.hr_prev[animo] = 0.9 * self.hr_prev[animo] + 0.1 * hr
        v["hr_bpm"] = hr; v["eda_uS"] = max(0.2, v["eda"] * 10); return v
    def paquete(self, animo, t, dur=120.0, modo="anclada"):
        v = self.paso(animo, t, dur); c = lambda a, lo=0.0, hi=1.0: max(lo, min(hi, a))
        p = {"head_yaw": c(v["head_yaw"], -1, 1), "head_pitch": c(v["head_pitch"], -1, 1), "jaw_open": c(v["jaw_open"]), "blink": 1.0 if v["blink"] > 0.6 else 0.0,
             "brow_up": c(v["brow_up"]), "brow_down": c(v["brow_down"]), "mouth_sad": c(v["mouth_sad"]), "mouth_smile": c(v["mouth_smile"]), "eye_yaw": c(v["eye_yaw"], -1, 1), "eye_pitch": c(v["eye_pitch"], -1, 1),
             "emotibit_hr": round(v["hr_bpm"], 1), "emotibit_eda": round(v["eda_uS"], 2), "actor_animo": animo, "water": 0.8}
        if modo == "anclada": p["anclada"] = 1
        elif modo == "cara": p["solo_cara"] = 1
        if v["mano_l"] > 0.5: p["l_palm_y"] = c(v["l_palm_y"]); p["l_palm_x"] = c(v["l_palm_x"])
        if v["mano_r"] > 0.5: p["r_palm_y"] = c(v["r_palm_y"]); p["r_palm_x"] = c(v["r_palm_x"])
        return p
if __name__ == "__main__":
    import sys
    m = Modelo(); animo = sys.argv[1] if len(sys.argv) > 1 else "playful"
    for t in (0.0, 1.0, 2.5, 5.0): print(t, json.dumps(m.paquete(animo, t)))
