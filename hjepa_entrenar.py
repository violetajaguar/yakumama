#!/usr/bin/env python3
"""hjepa_entrenar.py - H-JEPA (LeCun 2022): una pila de dos JEPAs condicionados por ACCION, cada nivel prediciendo mas
lejos en su propio latente, y planificacion de arriba hacia abajo con submetas. Sobre los SEIS canales del cuerpo
(cuerpo_cualidades.CUERPO) que comparten Yakumama, los bailarines de Paqarina, los hablantes de BEAT y, desde hoy, las
ballenas reales con etiqueta (importar_ballenas.py).

    NIVEL 1 (rapido, 12 cuadros/s): 4 s de contexto -> z1; predictor P1(z1, accion) -> z1 de los 2 s siguientes.
    NIVEL 2 (lento, 1 paso = 2 s):  16 pasos (32 s) de z1 -> z2; predictor P2(z2, accion) -> z2 de los 32 s siguientes;
                                    decodificador D2: z2 -> 16 submetas z1.
    ACCION: el animo que ella elige (10) | "libre" (bailarines, sin animo) | "ballena" (las etiquetas, sin animo).
    PLAN (planear): meta = un animo g. Prototipo z2 de g = media de z2 en ventanas de ese animo. Desde la historia,
         probar cada accion en P2, quedarse con la que acerca mas al prototipo; D2 -> 16 submetas z1; D1 -> 32 s de cuerpo.
Receta LeJEPA en cada nivel: un codificador compartido, prediccion latente + SIGReg (Epps-Pulley), sin EMA.
Mide con honestidad, con pistas enteras fuera (una yubarta entera, 1 de 8 bailarines, la ultima toma de cada animo):
error a 2 s (nivel 1) y a 4/16/32 s (nivel 2) contra "repetir el ultimo cuadro" y contra la media; y si la accion cambia
lo predicho (misma historia, distinta accion).

    venv/bin/python hjepa_entrenar.py --epochs1 6 --epochs2 20     -> modelos/hjepa.pt
"""
import os, sys, glob, math, argparse, time, numpy as np, torch, torch.nn as nn, torch.nn.functional as F
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from cuerpo_cualidades import CUERPO
MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
ACCIONES = MOODS + ["libre", "ballena"]; NA = len(ACCIONES); NC = 6; FPS = 12
C1, T1, Z1 = 48, 24, 32          # nivel 1: 4 s -> 2 s
PASO = 24; C2, T2, Z2 = 16, 16, 32   # nivel 2: un paso = 2 s; 32 s -> 32 s
ap = argparse.ArgumentParser(); ap.add_argument("--epochs1", type=int, default=6); ap.add_argument("--epochs2", type=int, default=20); ap.add_argument("--lr", type=float, default=1e-3); ap.add_argument("--sigreg", type=float, default=1.0); a = ap.parse_args()
torch.manual_seed(0); np.random.seed(0)
# ---------------- datos: pistas (X (n,6), M (n,6), accion, fuente, nombre) ----------------
d = np.load(os.path.join(AQUI, "modelos", "jepa_datos.npz"), allow_pickle=True)
CAN = [str(c) for c in d["CANALES"]]; ci = [CAN.index(c) for c in CUERPO]; media, desvio = d["media"][ci].astype(np.float32), d["desvio"][ci].astype(np.float32)
pistas = []
for k, (s, e) in enumerate(d["SEQ"]):
    X, M = d["X"][s:e][:, ci].astype(np.float32), d["M"][s:e][:, ci]
    if M.mean() < 0.5: continue
    fu = str(d["FUENTE"][k]); an = int(d["ANIMO"][k]); acc = an if an >= 0 else ACCIONES.index("libre")
    pistas.append(dict(X=X, M=M, accion=acc, fuente=fu, nombre=str(d["NOMBRE"][k]), actor=str(d["ACTOR"][k])))
def animos_ballena(b, fps=12):
    """la ballena real se etiqueta con lo que hace su propio cuerpo, por segundo: feeding = rola mas de 60 grados (la embestida
    lateral), diving = baja con la nariz a mas de 30 grados, surfacing = sube a mas de 30 grados y llega cerca de la superficie,
    calm = en superficie casi sin moverse; lo demas queda "ballena" (sin animo)."""
    n = len(b["X"]); pitch = np.degrees(np.nan_to_num(b["pitch"])); roll = np.degrees(np.abs(np.nan_to_num(b["roll"]))); prof = np.nan_to_num(b["prof"]); en = np.nan_to_num(b["X"][:, 4])
    acc = np.full(n, ACCIONES.index("ballena"))
    dprof = np.gradient(np.convolve(prof, np.ones(fps * 3) / (fps * 3), "same")) * fps   # m/s, + baja
    acc[(roll > 60)] = MOODS.index("feeding")
    acc[(pitch < -30) & (dprof > 0.15) & (roll <= 60)] = MOODS.index("diving")
    acc[(pitch > 30) & (dprof < -0.15) & (prof < 25) & (roll <= 60)] = MOODS.index("surfacing")
    acc[(prof < 3) & (np.abs(pitch) < 12) & (en < 0.15) & (roll <= 20)] = MOODS.index("calm")
    return acc
for f in sorted(glob.glob(os.path.join(AQUI, "datasets", "ballenas", "*.npz"))):   # (surf y apneistas entran por jepa_datos, con animo)
    b = np.load(f, allow_pickle=True); X = np.nan_to_num(b["X"]).astype(np.float32); M = b["M"]; acc = animos_ballena(b)
    # tramos de accion constante (minimo 8 s), como pistas con animo; lo largo se parte en trozos de 1 h
    cortes = np.flatnonzero(np.diff(acc)) + 1; ini = np.concatenate([[0], cortes]); fin = np.concatenate([cortes, [len(acc)]])
    for s, e in zip(ini, fin):
        if e - s < 8 * 12: continue
        for s2 in range(s, e, 12 * 3600):
            e2 = min(e, s2 + 12 * 3600); pistas.append(dict(X=X[s2:e2], M=M[s2:e2], accion=int(acc[s]), fuente="ballena", nombre=str(b["depid"]), actor=str(b["depid"])))
# fuera: la yubarta mn18_175d entera, 1 de cada 8 bailarines, la ultima toma de cada (actor, animo) de yakumama/beat
fuera = set(); vistos = {}
for i, p in enumerate(pistas):
    if p["nombre"] == "mn18_175d": fuera.add(i)
    vistos.setdefault((p["fuente"], p["actor"], p["accion"]), []).append(i)
for k, idxs in vistos.items():
    if k[0] in ("yakumama", "beat", "llama") and len(idxs) > 1: fuera.add(idxs[-1])
bail = [i for i, p in enumerate(pistas) if p["fuente"] == "bailarin"]; fuera.update(bail[::8])
Xn = [np.where(p["M"], (p["X"] - media) / desvio, 0.0).astype(np.float32) for p in pistas]; Mf = [p["M"].astype(np.float32) for p in pistas]
ACC = np.array([p["accion"] for p in pistas]); horas = sum(len(x) for x in Xn) / FPS / 3600
print("horas con animo: " + ", ".join(f"{ACCIONES[k]} {sum(len(p['X']) for p in pistas if p['accion'] == k) / FPS / 3600:.2f}" for k in range(NA) if any(p['accion'] == k for p in pistas)))
print(f"pistas {len(pistas)} ({len(fuera)} fuera) | {horas:.1f} h | por fuente: " + ", ".join(f"{f} {sum(1 for p in pistas if p['fuente'] == f)}" for f in sorted(set(p["fuente"] for p in pistas))))
dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
Xcat = torch.tensor(np.concatenate(Xn), device=dev); Mcat = torch.tensor(np.concatenate(Mf), device=dev)
OFF = np.cumsum([0] + [len(x) for x in Xn]); ACCt = torch.tensor(ACC, device=dev)
def ventanas1(idxs, paso=12):
    out = []
    for i in idxs:
        n = len(Xn[i]); m = Mf[i]
        for t0 in range(0, n - C1 - T1 + 1, paso):
            if m[t0:t0 + C1 + T1].mean() >= 0.6: out.append((OFF[i] + t0, i))
    return np.array(out)
# ---------------- modelos ----------------
class Enc(nn.Module):
    def __init__(s, nin, z, pool=6):
        super().__init__(); s.c1 = nn.Conv1d(nin, 64, 5, padding=2); s.c2 = nn.Conv1d(64, 96, 5, stride=2, padding=2); s.c3 = nn.Conv1d(96, 64, 3, stride=2, padding=1); s.pool = nn.AdaptiveAvgPool1d(pool); s.fc = nn.Linear(64 * pool, z)
    def forward(s, x):   # x: (B, L, nin)
        h = x.transpose(1, 2); h = F.gelu(s.c1(h)); h = F.gelu(s.c2(h)); h = F.gelu(s.c3(h)); return s.fc(s.pool(h).flatten(1))
class Pred(nn.Module):
    def __init__(s, z):
        super().__init__(); s.net = nn.Sequential(nn.Linear(z + NA, 128), nn.GELU(), nn.Linear(128, 128), nn.GELU(), nn.Linear(128, z))
    def forward(s, z, acc): return s.net(torch.cat([z, F.one_hot(acc, NA).float()], -1))
class Dec(nn.Module):
    def __init__(s, z, L, nout):
        super().__init__(); s.L, s.nout = L, nout; s.net = nn.Sequential(nn.Linear(z, 256), nn.GELU(), nn.Linear(256, L * nout))
    def forward(s, z): return s.net(z).view(-1, s.L, s.nout)
def sigreg(z, n_dir=256, n_t=17):
    """SIGReg (LeJEPA): proyecciones 1D de z sobre direcciones al azar comparadas con una normal estandar (Epps-Pulley)."""
    z = (z - z.mean(0)) / (z.std(0) + 1e-6) * z.std(0) + z.mean(0) * 0   # centrado (la media la fija el predictor)
    dirs = F.normalize(torch.randn(z.shape[1], n_dir, device=z.device), dim=0); p = z @ dirs   # (B, n_dir)
    t = torch.linspace(-5, 5, n_t, device=z.device); w = torch.exp(-t ** 2 / 2)
    phi_re = torch.cos(p[..., None] * t).mean(0); phi_im = torch.sin(p[..., None] * t).mean(0); phi0 = torch.exp(-t ** 2 / 2)
    return (((phi_re - phi0) ** 2 + phi_im ** 2) * w).sum(-1).mean()
def entrenar(nombre, enc, pred, dec, lote_fn, wins, epochs, mask_recon=True):
    opt = torch.optim.AdamW(list(enc.parameters()) + list(pred.parameters()) + list(dec.parameters()), lr=a.lr, weight_decay=1e-4)
    B = 512
    for ep in range(epochs):
        perm = np.random.permutation(len(wins)); tot = n = 0; t0 = time.time()
        for b in range(0, len(perm), B):
            xc, xo, mo, acc = lote_fn(wins[perm[b:b + B]])
            zc, zo = enc(xc), enc(xo); zp = pred(zc, acc)
            l_lat = F.mse_loss(zp, zo); l_reg = a.sigreg * 0.5 * (sigreg(zc) + sigreg(zo))
            rec = dec(zo); l_rec = (((rec - xo[..., :rec.shape[-1]]) ** 2) * (mo if mask_recon else 1.0)).mean()
            loss = l_lat + l_reg + l_rec; opt.zero_grad(); loss.backward(); opt.step(); tot += float(loss); n += 1
        print(f"  {nombre} epoca {ep + 1}/{epochs} perdida {tot / max(1, n):.4f} ({time.time() - t0:.0f} s)", flush=True)
# ---------------- nivel 1 ----------------
tr1 = ventanas1([i for i in range(len(pistas)) if i not in fuera]); va1 = ventanas1(sorted(fuera), paso=24)
print(f"nivel 1: ventanas entrenamiento {len(tr1)} | prueba {len(va1)}")
enc1, pred1, dec1 = Enc(2 * NC, Z1).to(dev), Pred(Z1).to(dev), Dec(Z1, T1, NC).to(dev)
def lote1(w):
    t0 = torch.tensor(w[:, 0], device=dev); idx = t0[:, None] + torch.arange(C1 + T1, device=dev)
    x, m = Xcat[idx], Mcat[idx]; xm = torch.cat([x, m], -1); acc = ACCt[torch.tensor(w[:, 1], device=dev)]
    return xm[:, :C1], xm[:, C1:], m[:, C1:], acc
entrenar("nivel 1", enc1, pred1, dec1, lote1, tr1, a.epochs1)
# ---------------- nivel 2: z1 por paso de 2 s en todas las pistas ----------------
enc1.eval(); Zs = []; Zok = []
with torch.no_grad():
    for i in range(len(pistas)):
        n = len(Xn[i]); npas = n // PASO; zs = torch.zeros(npas, Z1, device=dev); ok = np.zeros(npas, bool)
        for b in range(0, npas, 2048):
            t0 = torch.tensor(OFF[i] + np.arange(b, min(npas, b + 2048)) * PASO, device=dev); idx = t0[:, None] + torch.arange(PASO, device=dev)
            zs[b:b + len(t0)] = enc1(torch.cat([Xcat[idx], Mcat[idx]], -1))
        for k in range(npas): ok[k] = Mf[i][k * PASO:(k + 1) * PASO].mean() >= 0.6
        Zs.append(zs); Zok.append(ok)
Zcat = torch.cat(Zs); ZOFF = np.cumsum([0] + [len(z) for z in Zs])
def ventanas2(idxs, paso=2):
    out = []
    for i in idxs:
        for k0 in range(0, len(Zs[i]) - C2 - T2 + 1, paso):
            if Zok[i][k0:k0 + C2 + T2].mean() >= 0.8: out.append((ZOFF[i] + k0, i))
    return np.array(out)
tr2 = ventanas2([i for i in range(len(pistas)) if i not in fuera]); va2 = ventanas2(sorted(fuera), paso=4)
print(f"nivel 2: ventanas entrenamiento {len(tr2)} | prueba {len(va2)} | pistas con 64 s: {sum(1 for i in range(len(pistas)) if len(Zs[i]) >= C2 + T2)}")
enc2, pred2, dec2 = Enc(Z1, Z2, pool=4).to(dev), Pred(Z2).to(dev), Dec(Z2, T2, Z1).to(dev)
def lote2(w):
    k0 = torch.tensor(w[:, 0], device=dev); idx = k0[:, None] + torch.arange(C2 + T2, device=dev); z = Zcat[idx]; acc = ACCt[torch.tensor(w[:, 1], device=dev)]
    return z[:, :C2], z[:, C2:], None, acc
entrenar("nivel 2", enc2, pred2, dec2, lote2, tr2, a.epochs2, mask_recon=False)
# ---------------- evaluacion honesta ----------------
enc2.eval(); pred1.eval(); pred2.eval(); dec1.eval(); dec2.eval()
def desn(x): return x * torch.tensor(desvio, device=dev) + torch.tensor(media, device=dev)
print("\nNIVEL 1 - error medio por canal a 2 s (unidades de la ballena, pistas fuera): H-JEPA / repetir ultimo / media")
with torch.no_grad():
    err = {k: torch.zeros(NC, device=dev) for k in ("jepa", "ult", "media")}; nn_ = 0
    for b in range(0, len(va1), 1024):
        xc, xo, mo, acc = lote1(va1[b:b + 1024]); zp = pred1(enc1(xc), acc); rec = desn(dec1(zp)); real = desn(xo[..., :NC])
        ult = desn(xc[:, -1:, :NC]).expand_as(real); med = torch.tensor(media, device=dev).expand_as(real)
        for k, pr in (("jepa", rec), ("ult", ult), ("media", med)): err[k] += ((pr - real).abs() * mo).sum((0, 1))
        nn_ += mo.sum((0, 1))
    gana1 = 0
    for j, c in enumerate(CUERPO):
        e = {k: float(err[k][j] / nn_[j]) for k in err}; gana1 += e["jepa"] < min(e["ult"], e["media"]); print(f"  {c:18s} {e['jepa']:.3f} / {e['ult']:.3f} / {e['media']:.3f}")
    print(f"  canales donde gana el H-JEPA a 2 s: {gana1}/6")
print("\nNIVEL 2 - error medio a 4 / 16 / 32 s (submetas decodificadas, pistas fuera): H-JEPA / repetir ultimo / media")
def desplegar(z2, acc):
    """z2 de contexto + accion -> 32 s de cuerpo (T2 pasos x PASO cuadros), via submetas z1 y el decodificador del nivel 1."""
    sub = dec2(pred2(z2, acc)); return desn(dec1(sub.reshape(-1, Z1)).view(z2.shape[0], T2 * PASO, NC)[..., :NC]), sub
with torch.no_grad():
    H = {4: slice(0, 4 * FPS), 16: slice(12 * FPS, 16 * FPS), 32: slice(28 * FPS, 32 * FPS)}
    err = {h: {k: torch.zeros(NC, device=dev) for k in ("jepa", "ult", "media")} for h in H}; cnt = {h: torch.zeros(NC, device=dev) for h in H}
    cambia = []; prof_real = []; prof_pred = []
    for b in range(0, len(va2), 512):
        w = va2[b:b + 512]; zc, zo, _, acc = lote2(w); z2 = enc2(zc); pr, sub = desplegar(z2, acc)
        k0 = torch.tensor(w[:, 0], device=dev); pista = w[:, 1]
        # cuadros reales de los 32 s siguientes: desde el cuadro (k0 - ZOFF[pista] + C2) * PASO de cada pista
        t0 = torch.tensor([OFF[i] + (k - ZOFF[i] + C2) * PASO for k, i in zip(w[:, 0], pista)], device=dev); idx = t0[:, None] + torch.arange(T2 * PASO, device=dev)
        real, mo = desn(Xcat[idx]), Mcat[idx]; ult = desn(Xcat[t0 - 1])[:, None, :].expand_as(real); med = torch.tensor(media, device=dev).expand_as(real)
        for h, sl in H.items():
            for k, p_ in (("jepa", pr), ("ult", ult), ("media", med)): err[h][k] += ((p_[:, sl] - real[:, sl]).abs() * mo[:, sl]).sum((0, 1))
            cnt[h] += mo[:, sl].sum((0, 1))
        otra = (acc + 3) % NA; pr2, _ = desplegar(z2, otra); cambia.append(float((pr - pr2).abs().mean()))
        es_ballena = torch.tensor([pistas[i]["fuente"] == "ballena" for i in pista], device=dev)
        if es_ballena.any(): prof_real.append(real[es_ballena][:, :, 3].mean(1)); prof_pred.append(pr[es_ballena][:, :, 3].mean(1))
    for h in H:
        e = {k: (err[h][k] / cnt[h]).mean().item() for k in err[h]}; print(f"  a {h:2d} s: {e['jepa']:.3f} / {e['ult']:.3f} / {e['media']:.3f}   (media de los 6 canales)")
    print(f"  cambiar la accion con la misma historia cambia el plan en {np.mean(cambia):.3f} (unidades medias; 0 = la accion no importa)")
    if prof_real:
        r, p_ = torch.cat(prof_real).cpu().numpy(), torch.cat(prof_pred).cpu().numpy()
        print(f"  yubarta fuera: correlacion profundidad media real vs predicha en los 32 s siguientes: {np.corrcoef(r, p_)[0, 1]:.2f} ({len(r)} ventanas)")
# ---------------- prototipos por animo y planificacion ----------------
with torch.no_grad():
    protos = torch.zeros(NA, Z2, device=dev); nprot = torch.zeros(NA, device=dev)
    for b in range(0, len(tr2), 1024):
        zc, zo, _, acc = lote2(tr2[b:b + 1024]); z2 = enc2(zo); protos.index_add_(0, acc, z2); nprot.index_add_(0, acc, torch.ones_like(acc, dtype=torch.float))
    protos = protos / nprot.clamp(min=1)[:, None]
    def planear(z2_hist, meta):
        """meta: indice de animo. Prueba las NA acciones, elige la que acerca mas al prototipo de la meta, devuelve (accion, 32 s de cuerpo)."""
        cand = torch.stack([pred2(z2_hist, torch.full((z2_hist.shape[0],), k, device=dev, dtype=torch.long)) for k in range(NA)], 1)   # (B, NA, Z2)
        dist = ((cand - protos[meta][None, None]) ** 2).sum(-1); mejor = dist.argmin(1)
        cuerpo, _ = desplegar(z2_hist, mejor); return mejor, cuerpo
    print("\nPLAN - desde 32 s de la yubarta fuera, meta 'diving' y meta 'surfacing' (profundidad media por tramos de 8 s, -1 hondo .. 0 superficie):")
    wb = [w for w in va2 if pistas[w[1]]["fuente"] == "ballena"][:64]
    if wb:
        zc, _, _, _ = lote2(np.array(wb)); z2 = enc2(zc)
        for meta in ("diving", "surfacing", "playful"):
            acc, cuerpo = planear(z2, MOODS.index(meta)); prof = cuerpo[:, :, 3].view(len(wb), 4, -1).mean(2).mean(0).cpu().numpy()
            print(f"  meta {meta:9s}: elige accion " + ", ".join(f"{ACCIONES[k]} x{int((acc == k).sum())}" for k in acc.unique().tolist()) + f" | profundidad {np.round(prof, 2).tolist()} | energia {cuerpo[:, :, 4].mean().item():.2f}")
torch.save({"enc1": enc1.state_dict(), "pred1": pred1.state_dict(), "dec1": dec1.state_dict(), "enc2": enc2.state_dict(), "pred2": pred2.state_dict(), "dec2": dec2.state_dict(),
            "protos": protos.cpu(), "media": media, "desvio": desvio, "canales": CUERPO, "acciones": ACCIONES, "C1": C1, "T1": T1, "Z1": Z1, "C2": C2, "T2": T2, "Z2": Z2, "PASO": PASO, "fps": FPS}, os.path.join(AQUI, "modelos", "hjepa.pt"))
print("guardado modelos/hjepa.pt")
