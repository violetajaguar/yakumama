#!/usr/bin/env python3
"""difusion_ballena.py - SHE INVENTS: Violeta's diffusion from Paqarina (codigo/difusion.py: a bidirectional-GRU denoiser that predicts
the clean window, cosine noise schedule, 200 steps, classifier-free guidance by dance, velocity loss x5, inpainting prefix for
long generation) brought to Yakumama's own body space. Here the diffusion works directly on her 32 channels (pitch, roll, yaw,
head, six spine, fluke, fins link by link, face, gaze, spin, depth, turbine, travel, pulse, skin) in windows of 4 s at 12/s,
conditioned on the mood. Every sample starts from a different noise, so every dance is a new one: this is the piece the
predictor and the phrase bank do not have.

    venv/bin/python difusion_ballena.py --minutos 25                 -> modelos/difusion_ballena.pt  (trains on modelos/ballena_datos.npz)
    venv/bin/python difusion_ballena.py --generar playful --n 2     -> prints what it invents (32 s), as a check
    from difusion_ballena import Inventora; inv = Inventora(); cuerpo = inv.inventar("playful", segundos=32, prefijo=ultimos_cuadros)
"""
import os, sys, time, math, argparse, numpy as np, torch, torch.nn as nn
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]; NCOND = len(MOODS) + 1   # + libre
PASOS = 200; W = 72; FPS = 12   # 6-s windows at 12/s, like m3f (144 at 24/s)
def betas_coseno(T):
    s = 0.008; t = torch.linspace(0, T, T + 1) / T; a = torch.cos((t + s) / (1 + s) * math.pi / 2) ** 2; a = a / a[0]
    return torch.clip(1 - a[1:] / a[:-1], 0, 0.999)
class Denoiser(nn.Module):
    """predicts the clean window x0 from the noisy one (B, W, nc), the step t and the mood c (Paqarina's Denoiser, same shape)."""
    def __init__(s, nc, W, oculto=256, ncond=NCOND):
        super().__init__(); s.W, s.nc = W, nc; s.ent = nn.Linear(nc + ncond + 2, oculto); s.gru = nn.GRU(oculto, oculto, num_layers=2, batch_first=True, bidirectional=True)
        s.sal = nn.Sequential(nn.Linear(oculto * 2, oculto), nn.GELU(), nn.Linear(oculto, nc))
    def forward(s, x, t, c):
        B, Wn, _ = x.shape; tt = (t.float() / PASOS).view(B, 1, 1).expand(B, Wn, 1); pos = torch.linspace(0, 1, Wn, device=x.device).view(1, Wn, 1).expand(B, Wn, 1)
        cc = c.unsqueeze(1).expand(B, Wn, c.shape[1]); o, _ = s.gru(s.ent(torch.cat([x, cc, tt, pos], 2))); return s.sal(o)
def ventanas(d, W=W, paso=12):
    X, M, SEQ, FU, AN = d["X"], d["M"], d["SEQ"], d["FUENTE"], d["ANIMO"]; xs, ms, cs = [], [], []
    for k, (s, e) in enumerate(SEQ):
        if str(FU[k]) == "ballena": continue
        for t0 in range(s, e - W + 1, paso):
            m = M[t0:t0 + W]
            if m.mean() < 0.3: continue
            xs.append(X[t0:t0 + W]); ms.append(m); cs.append(int(AN[k]) if AN[k] >= 0 else len(MOODS))
    return np.stack(xs).astype(np.float32), np.stack(ms), np.array(cs)
def entrenar(a):
    dev = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")); d = np.load(a.datos or os.path.join(AQUI, "modelos", "ballena_datos.npz"), allow_pickle=True)
    CAN = [str(c) for c in d["CANALES"]]; X, M, C = ventanas(d, W=a.W); nc = X.shape[2]; Wl = a.W
    mu = np.array([X[:, :, j][M[:, :, j]].mean() if M[:, :, j].any() else 0.0 for j in range(nc)], np.float32); sd = np.array([X[:, :, j][M[:, :, j]].std() + 1e-3 if M[:, :, j].any() else 1.0 for j in range(nc)], np.float32)
    Xn = torch.tensor(np.where(M, (X - mu) / sd, 0.0), device=dev); Mt = torch.tensor(M.astype(np.float32), device=dev); Ct = torch.eye(NCOND, device=dev)[torch.tensor(C, device=dev)]
    print(f"{len(Xn)} windows of {W / FPS:.0f} s, {nc} channels · device {dev} · " + ", ".join(f"{m} {int((C == i).sum())}" for i, m in enumerate(MOODS + ['libre'])), flush=True)
    b = betas_coseno(PASOS).to(dev); al = torch.cumprod(1 - b, 0); m = Denoiser(nc, Wl).to(dev); opt = torch.optim.AdamW(m.parameters(), lr=a.lr); n = len(Xn); t0 = time.time(); ep = 0
    salida = a.out or os.path.join(AQUI, "modelos", "difusion_ballena.pt")
    if a.desde and os.path.exists(a.desde):   # resume (cloud sessions can drop)
        ck0 = torch.load(a.desde, map_location="cpu", weights_only=False); m.load_state_dict(ck0["dif"]); ep = int(ck0.get("epochs", 0)); print(f"resuming from {a.desde} at epoch {ep}", flush=True)
    def guardar(ep_):
        torch.save({"dif": m.state_dict(), "W": Wl, "nc": nc, "mu": mu, "sd": sd, "canales": CAN, "moods": MOODS, "pasos": PASOS, "fps": FPS, "epochs": ep_}, salida)
    while ep < a.epochs and (time.time() - t0) / 60 < a.minutos:
        perm = torch.randperm(n, device=dev); tot = nb = 0
        for i in range(0, n, a.batch):
            sel = perm[i:i + a.batch]; x0, mk, c = Xn[sel], Mt[sel], Ct[sel]; t = torch.randint(0, PASOS, (len(x0),), device=dev)
            if a.p_uncond > 0: c = c * (torch.rand(len(x0), 1, device=dev) >= a.p_uncond).float()
            at = al[t].view(-1, 1, 1); xt = at.sqrt() * x0 + (1 - at).sqrt() * torch.randn_like(x0); pred = m(xt, t, c)
            loss = (((pred - x0) ** 2) * mk).sum() / mk.sum().clamp(min=1)
            v_p, v_0, mv = pred[:, 1:] - pred[:, :-1], x0[:, 1:] - x0[:, :-1], mk[:, 1:] * mk[:, :-1]; loss = loss + a.peso_vel * (((v_p - v_0) ** 2) * mv).sum() / mv.sum().clamp(min=1)
            if a.peso_suave > 0:   # m3f: smoothness (acceleration) too
                ac_p, ac_0, ma = pred[:, 2:] - 2 * pred[:, 1:-1] + pred[:, :-2], x0[:, 2:] - 2 * x0[:, 1:-1] + x0[:, :-2], mk[:, 2:] * mk[:, 1:-1] * mk[:, :-2]; loss = loss + a.peso_suave * (((ac_p - ac_0) ** 2) * ma).sum() / ma.sum().clamp(min=1)
            opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step(); tot += float(loss.detach()); nb += 1
        ep += 1
        if ep % 5 == 0 or ep == 1: print(f"epoch {ep}  loss {tot / nb:.4f}  ({(time.time() - t0) / 60:.1f} min)", flush=True)
        if ep % a.cada == 0: guardar(ep)   # checkpoint: a dropped session keeps what was learned
    guardar(ep); print(f"guardado {salida} ({ep} epochs)", flush=True)
class Inventora:
    def __init__(self, ruta=None):
        ck = torch.load(ruta or os.path.join(AQUI, "modelos", "difusion_ballena.pt"), map_location="cpu", weights_only=False)
        self.W, self.nc, self.mu, self.sd, self.CAN, self.fps = ck["W"], ck["nc"], ck["mu"], ck["sd"], list(ck["canales"]), ck["fps"]; self.m = Denoiser(self.nc, self.W); self.m.load_state_dict(ck["dif"]); self.m.eval()
        # GPU when there is one (Dan's PC, RTX 4080 SUPER, 17 Oct night): 32 s took 7.5 s on its CPU, inside the brain's loop.
        # CPU when torch has no CUDA, exactly as before. Apple Silicon (20 Oct, the brain moved to a Mac): MPS, as entrenar() does.
        # Measured on Violeta's Mac (M5 Max, 20 Oct): this small batch-1 GRU runs 32 s in 2.1 s on the CPU and 12.6 s on MPS, so MPS
        # is NOT taken by default; YAKUMAMA_DIFUSION_DEV=mps|cpu|cuda forces a device.
        _dev = os.environ.get("YAKUMAMA_DIFUSION_DEV", "").strip() or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dev = torch.device(_dev); self.m.to(self.dev)
        self.b = betas_coseno(PASOS).to(self.dev); self.al = torch.cumprod(1 - self.b, 0)
    @torch.no_grad()
    def _ventana(self, c, temp=1.0, prefijo=None, guia=1.0, pasos=None):
        dv = self.dev
        x = torch.randn(1, self.W, self.nc, device=dv) * temp; n = 0 if prefijo is None else len(prefijo); al, b = self.al, self.b; salto = max(1, PASOS // (pasos or PASOS))
        for t in range(PASOS - 1, -1, -salto):
            tt = torch.tensor([t], device=dv)
            if n: x[:, :n] = al[t].sqrt() * prefijo + (1 - al[t]).sqrt() * torch.randn(1, n, self.nc, device=dv) * temp
            x0p = self.m(x, tt, c)
            if guia > 1.0: x0u = self.m(x, tt, torch.zeros_like(c)); x0p = x0u + guia * (x0p - x0u)
            tp = max(0, t - salto); at, atm = al[t], (al[tp] if t > 0 else torch.tensor(1.0, device=dv)); bt = 1 - at / atm
            media = (atm.sqrt() * bt / (1 - at)) * x0p + (((1 - bt).sqrt() * (1 - atm)) / (1 - at)) * x
            x = media + ((1 - atm) / (1 - at) * bt).sqrt() * torch.randn_like(x) if t > 0 else media
        if n: x[:, :n] = prefijo
        return x[0]
    @torch.no_grad()
    def inventar(self, animo, segundos=32.0, prefijo=None, temp=1.0, guia=1.0, pasos=100, solape=None):
        solape = solape or self.W // 6   # m3f: inpaint one sixth of the window
        """a new dance of `segundos` for the mood, window after window, each continuing the last `solape` frames of the previous one
        (inpainting, as in Paqarina). prefijo: (k, nc) real frames in body units to start from (None = from nothing). Returns (n, nc)."""
        c = torch.zeros(1, NCOND, device=self.dev); c[0, MOODS.index(animo) if animo in MOODS else len(MOODS)] = 1.0
        if prefijo is not None:   # a prefix with fewer channels (e.g. the 30 of retarget_ballena, without pulse and skin) is completed with the means
            pf = np.asarray(prefijo, np.float32)[-solape:]; pad = np.tile(self.mu, (len(pf), 1)); pad[:, :min(self.nc, pf.shape[1])] = pf[:, :self.nc]; pf = np.where(np.isfinite(pad), pad, self.mu)
        pre = None if prefijo is None else torch.tensor(((pf - self.mu) / self.sd).astype(np.float32), device=self.dev)
        out = []; total = int(segundos * self.fps)
        while sum(len(o) for o in out) < total:
            w = self._ventana(c, temp, pre, guia, pasos); out.append(w if pre is None else w[len(pre):]); pre = w[-solape:]
        X = torch.cat(out)[:total].cpu().numpy() * self.sd + self.mu; return X.astype(np.float32)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--minutos", type=float, default=25.0); ap.add_argument("--epochs", type=int, default=400); ap.add_argument("--batch", type=int, default=64); ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--p_uncond", type=float, default=0.0); ap.add_argument("--peso_vel", type=float, default=5.0); ap.add_argument("--peso_suave", type=float, default=1.0); ap.add_argument("--W", type=int, default=W); ap.add_argument("--generar", default=None); ap.add_argument("--n", type=int, default=2); ap.add_argument("--datos", default=None); ap.add_argument("--out", default=None); ap.add_argument("--desde", default=None); ap.add_argument("--cada", type=int, default=25, help="checkpoint every N epochs"); a = ap.parse_args()
    if a.generar:
        inv = Inventora(); C = {c: i for i, c in enumerate(inv.CAN)}
        for k in range(a.n):
            t0 = time.time(); X = inv.inventar(a.generar); print(f"  {a.generar} #{k + 1}: 32 s in {time.time() - t0:.1f} s | pitch {X[:, C['pitch']].mean():+.2f} fluke std {X[:, C['fluke']].std():.2f} fin L std {X[:, C['flap_l']].std():.2f} travel {np.abs(X[:, C['avance']]).mean():.2f} | jaw max {X[:, C['jaw']].max():.2f}")
    else: entrenar(a)
