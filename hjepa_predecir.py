#!/usr/bin/env python3
"""hjepa_predecir.py - her H-JEPA, standalone (numpy + torch only). Reads a body (the six body qualities at 12 frames/s:
cuerpo_pitch, cuerpo_roll, cuerpo_yaw, cuerpo_profundidad, cuerpo_energia, cuerpo_suavidad) and gives:
  - animo_cuerpo: the mood read from the last 4 s of body alone (level-1 probe; ~55 % right on strangers, chance 10 %)
  - prevision: the body 4 s and 16 s ahead (level 2 rolled out under the current mood as action), and the mood it will
    look like at 16 s (probe on the predicted sub-goal)
  - plan(meta): which mood-action brings her closest to the goal mood's prototype (LeCun-style planning with sub-goals)

    python3 hjepa_predecir.py modelos/hjepa.pt                      self-test on random bodies
    python3 hjepa_predecir.py modelos/hjepa.pt toma.npz             on a 26-point skeleton (needs cuerpo_cualidades.py next to it)
    from hjepa_predecir import HJepa; h = HJepa("hjepa.pt"); h.empujar(cualidades_de_un_cuadro); h.leer()
"""
import sys, os, math, numpy as np, torch, torch.nn as nn, torch.nn.functional as F
class Enc(nn.Module):
    def __init__(s, nin, z, pool=6):
        super().__init__(); s.c1 = nn.Conv1d(nin, 64, 5, padding=2); s.c2 = nn.Conv1d(64, 96, 5, stride=2, padding=2); s.c3 = nn.Conv1d(96, 64, 3, stride=2, padding=1); s.pool = nn.AdaptiveAvgPool1d(pool); s.fc = nn.Linear(64 * pool, z)
    def forward(s, x):
        h = x.transpose(1, 2); h = F.gelu(s.c1(h)); h = F.gelu(s.c2(h)); h = F.gelu(s.c3(h)); return s.fc(s.pool(h).flatten(1))
class Pred(nn.Module):
    def __init__(s, z, na):
        super().__init__(); s.na = na; s.net = nn.Sequential(nn.Linear(z + na, 128), nn.GELU(), nn.Linear(128, 128), nn.GELU(), nn.Linear(128, z))
    def forward(s, z, acc): return s.net(torch.cat([z, F.one_hot(acc, s.na).float()], -1))
class Dec(nn.Module):
    def __init__(s, z, L, nout):
        super().__init__(); s.L, s.nout = L, nout; s.net = nn.Sequential(nn.Linear(z, 256), nn.GELU(), nn.Linear(256, L * nout))
    def forward(s, z): return s.net(z).view(-1, s.L, s.nout)
class HJepa:
    def __init__(self, ruta):
        ck = torch.load(ruta, map_location="cpu", weights_only=False); self.ck = ck
        self.CUERPO = list(ck["canales"]); self.ACCIONES = list(ck["acciones"]); self.NA = len(self.ACCIONES); self.NC = len(self.CUERPO)
        self.C1, self.T1, self.Z1, self.C2, self.T2, self.Z2, self.PASO, self.fps = ck["C1"], ck["T1"], ck["Z1"], ck["C2"], ck["T2"], ck["Z2"], ck["PASO"], ck["fps"]
        self.media, self.desvio = np.asarray(ck["media"], np.float32), np.asarray(ck["desvio"], np.float32)
        self.enc1 = Enc(2 * self.NC, self.Z1); self.pred1 = Pred(self.Z1, self.NA); self.dec1 = Dec(self.Z1, self.T1, self.NC)
        self.enc2 = Enc(self.Z1, self.Z2, pool=4); self.pred2 = Pred(self.Z2, self.NA); self.dec2 = Dec(self.Z2, self.T2, self.Z1)
        for n in ("enc1", "pred1", "dec1", "enc2", "pred2", "dec2"): getattr(self, n).load_state_dict(ck[n]); getattr(self, n).eval()
        self.sonda1 = self.sonda2 = None
        if ck.get("sonda1"): self.sonda1 = nn.Linear(self.Z1, self.NA); self.sonda1.load_state_dict(ck["sonda1"]); self.sonda1.eval()
        if ck.get("sonda2"): self.sonda2 = nn.Linear(self.Z2, self.NA); self.sonda2.load_state_dict(ck["sonda2"]); self.sonda2.eval()
        self.protos = ck["protos"]; self.largo = self.C2 * self.PASO   # 32 s of body at 12/s
        self.X = np.zeros((self.largo, self.NC), np.float32); self.M = np.zeros((self.largo, self.NC), np.float32); self.n = 0
    def empujar(self, cualidades):
        """one frame (dict cuerpo_* -> value, NaN/None = not measured), at 12 frames/s."""
        x = np.array([float(cualidades.get(c, np.nan) if cualidades.get(c) is not None else np.nan) for c in self.CUERPO], np.float32)
        m = np.isfinite(x).astype(np.float32); x = np.where(m > 0, (x - self.media) / self.desvio, 0.0)
        self.X = np.roll(self.X, -1, 0); self.M = np.roll(self.M, -1, 0); self.X[-1] = x; self.M[-1] = m; self.n += 1
    def _z1(self, x, m): return self.enc1(torch.tensor(np.concatenate([x, m], -1))[None])
    def desn(self, x): return x * self.desvio + self.media
    @torch.no_grad()
    def leer(self, accion=None):
        """what she reads and foresees from the body in the buffer. accion: the mood she is acting (default: the one read)."""
        out = {"cuadros": min(self.n, self.largo)}
        if self.n < self.C1: return out
        z1 = self._z1(self.X[-self.C1:], self.M[-self.C1:])
        if self.sonda1 is not None:
            p = F.softmax(self.sonda1(z1), -1)[0]; k = int(p.argmax()); out["animo_cuerpo"] = self.ACCIONES[k]; out["p_cuerpo"] = round(float(p[k]), 2)
        acc = self.ACCIONES.index(accion) if accion in self.ACCIONES else (self.ACCIONES.index(out.get("animo_cuerpo", "libre")))
        if self.n < self.largo: return out
        zs = torch.cat([self._z1(self.X[k * self.PASO:(k + 1) * self.PASO], self.M[k * self.PASO:(k + 1) * self.PASO]) for k in range(self.C2)])   # (C2, Z1)
        z2 = self.enc2(zs[None]); self._z2 = z2
        sub = self.dec2(self.pred2(z2, torch.tensor([acc])))                # (1, T2, Z1): sub-goals, one per 2 s
        cuerpo = self.desn(self.dec1(sub.reshape(-1, self.Z1)).view(self.T2 * self.PASO, self.NC).numpy())   # 32 s of body ahead
        fps = int(self.fps); out["prevision"] = {"cuerpo_4s": [round(float(v), 3) for v in cuerpo[3 * fps:4 * fps].mean(0)], "cuerpo_16s": [round(float(v), 3) for v in cuerpo[15 * fps:16 * fps].mean(0)], "canales": self.CUERPO, "accion": self.ACCIONES[acc]}
        if self.sonda1 is not None:
            p16 = F.softmax(self.sonda1(sub[0, 7:8]), -1)[0]; out["prevision"]["animo_16s"] = self.ACCIONES[int(p16.argmax())]
        if self.sonda2 is not None:
            p2 = F.softmax(self.sonda2(z2), -1)[0]; out["animo_32s_cuerpo"] = self.ACCIONES[int(p2.argmax())]
        return out
    @torch.no_grad()
    def plan(self, meta):
        """goal mood -> the action (mood) that brings her closest to the goal's prototype after 32 s, and that body."""
        if not hasattr(self, "_z2"): return None
        k = self.ACCIONES.index(meta); cand = torch.stack([self.pred2(self._z2, torch.tensor([a])) for a in range(self.NA)], 1)[0]   # (NA, Z2)
        dist = ((cand - self.protos[k][None]) ** 2).sum(-1); mejor = int(dist.argmin())
        return {"meta": meta, "accion": self.ACCIONES[mejor], "distancias": {self.ACCIONES[a]: round(float(dist[a]), 2) for a in range(self.NA)}}
    @torch.no_grad()
    def generar(self, animo, accion=None):
        """no camera, no body: 32 s of body from a mood alone. Context = the mood's prototype in level-2 latent (the average
        of everything she saw of that mood); action = the same mood unless given. Returns (T2*PASO, 6) at 12 frames/s
        in body-quality units, plus the mood each 2-s sub-goal reads as."""
        k = self.ACCIONES.index(animo); acc = self.ACCIONES.index(accion or animo); z2 = self.protos[k][None]
        sub = self.dec2(self.pred2(z2, torch.tensor([acc]))); cuerpo = self.desn(self.dec1(sub.reshape(-1, self.Z1)).view(self.T2 * self.PASO, self.NC).numpy())
        animos = [self.ACCIONES[int(self.sonda1(sub[0, i:i + 1]).argmax())] for i in range(self.T2)] if self.sonda1 is not None else None
        return cuerpo, animos
def a_ballena(cuerpo6, canales=("cuerpo_pitch", "cuerpo_roll", "cuerpo_yaw", "cuerpo_profundidad", "cuerpo_energia", "cuerpo_suavidad")):
    """the six body qualities -> what they do to the whale, exactly as cerebro_ballena.py / receptor_ballena.py apply them on top of
    the mood's behaviour: pitch -= 0.45*cuerpo_pitch (leaning forward = nose down), roll += 0.35*cuerpo_roll, turn += 0.5*cuerpo_yaw,
    depth += 0.6*cuerpo_profundidad (crouch = sink, jump = rise), and fins/spine amplitude x (0.4 + 1.3*cuerpo_energia)."""
    c = dict(zip(canales, [float(v) for v in cuerpo6])); cl = lambda v, lo=-1.0, hi=1.0: max(lo, min(hi, v))
    return {"d_pitch": -0.45 * cl(c["cuerpo_pitch"]), "d_roll": 0.35 * cl(c["cuerpo_roll"]), "d_giro": 0.5 * cl(c["cuerpo_yaw"]), "d_depth": 0.6 * cl(c["cuerpo_profundidad"]), "escala_aletas_columna": 0.4 + 1.3 * cl(c["cuerpo_energia"], 0.0, 1.0), "suavidad": cl(c["cuerpo_suavidad"], 0.0, 1.0)}
if __name__ == "__main__":
    h = HJepa(sys.argv[1] if len(sys.argv) > 1 else "modelos/hjepa.pt"); print("H-JEPA:", h.CUERPO, "| actions:", h.ACCIONES)
    if len(sys.argv) > 2:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from cuerpo_cualidades import cualidades_toma, cargar_npz
        B, J, fps = cargar_npz(sys.argv[2]); q = cualidades_toma(B, J, fps); paso = max(1, int(round(fps / h.fps)))
        for i in range(0, len(B), paso):
            h.empujar({c: q[c][i] for c in h.CUERPO})
            if h.n % (4 * int(h.fps)) == 0 and h.n >= h.largo:
                r = h.leer(); print(f"  t={i / fps:5.1f}s  body reads {r.get('animo_cuerpo')} ({r.get('p_cuerpo')}) | at 16 s it will look {r['prevision'].get('animo_16s')} | plan to surfacing: {h.plan('surfacing')['accion']}")
    elif len(sys.argv) > 1 and sys.argv[1].endswith("--generar"):
        pass
    else:
        for an in ("diving", "singing", "playful"):
            cu, ams = h.generar(an); print(f"  generated from mood alone '{an}': 32 s, mean body {np.round(cu.mean(0), 2).tolist()} | sub-goals read as {ams[:8]}... | on the whale: {a_ballena(cu.mean(0))}")
        rng = np.random.default_rng(0)
        for i in range(h.largo): h.empujar({c: float(v) for c, v in zip(h.CUERPO, rng.normal(0, 0.3, h.NC))})
        print(h.leer()); print(h.plan("diving"))
