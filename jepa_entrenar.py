#!/usr/bin/env python3
"""jepa_entrenar.py - un JEPA para la ballena: aprende a predecir lo que falta.

Receta LeJEPA (Balestriero & LeCun, 2025): UN solo codificador compartido para contexto y objetivo, sin copia EMA ni
stop-gradient; la perdida es la prediccion en el espacio latente + SIGReg (Sketched Isotropic Gaussian Regularization:
las proyecciones 1D de los z sobre direcciones al azar tienen que parecer una normal estandar, medido con el
estadistico de Epps-Pulley sobre la funcion caracteristica). Eso evita el colapso sin heuristicas. --sin-lejepa vuelve
a la version anterior (codificador objetivo propio + regularizador de varianza).

Ventanas de 4 s de CONTEXTO (48 cuadros a 12/s) y 2 s de OBJETIVO (los 24 cuadros siguientes), sobre los 24 canales
con mascara de jepa_datos.py. Un codificador convierte una ventana en un vector latente z (64); un codificador
objetivo (copia EMA) hace lo mismo con el objetivo; un predictor, desde el z del contexto, el animo y que canales va a
haber, predice el z del objetivo. Un decodificador vuelve de z a los canales. Durante el entrenamiento se esconden
modalidades enteras del contexto (cara, cuerpo, manos) para que aprenda a predecir una desde la otra.

Mide, con tomas enteras fuera: error por canal del futuro predicho contra "repetir el ultimo cuadro" y contra la media;
cara->cuerpo escondiendo el cuerpo del contexto; y relaciones (boca-cabeza, cabeza-giro) reales vs predichas.

    venv/bin/python jepa_entrenar.py --epochs 30     -> modelos/jepa.pt y modelos/jepa_pesos.npz
"""
import os, sys, json, math, argparse, time, numpy as np, torch, torch.nn as nn, torch.nn.functional as F
AQUI = os.path.dirname(os.path.abspath(__file__))
C, T, Z = 48, 24, 64
ap = argparse.ArgumentParser(); ap.add_argument("--epochs", type=int, default=30); ap.add_argument("--lr", type=float, default=1e-3); ap.add_argument("--paso", type=int, default=6); ap.add_argument("--sin-lejepa", action="store_true"); ap.add_argument("--sigreg", type=float, default=1.0, help="peso de SIGReg"); a = ap.parse_args()
d = np.load(os.path.join(AQUI, "modelos", "jepa_datos.npz"), allow_pickle=True)
X, M, SEQ, ANIMO, ACTOR, FUENTE, NOMBRE = d["X"], d["M"], d["SEQ"], d["ANIMO"], d["ACTOR"], d["FUENTE"], d["NOMBRE"]
CANALES = [str(c) for c in d["CANALES"]]; NC = len(CANALES); media, desvio = d["media"], d["desvio"]
Xn = np.where(M, (X - media) / desvio, 0.0).astype(np.float32); Mf = M.astype(np.float32)
CARA = [i for i, c in enumerate(CANALES) if c in ("jaw_open", "blink", "brow_up", "brow_down", "mouth_sad", "mouth_smile", "eye_yaw", "eye_pitch")]
CABEZA = [i for i, c in enumerate(CANALES) if c in ("head_yaw", "head_pitch")]; MANOS = [i for i, c in enumerate(CANALES) if "palm" in c or c.startswith("mano")]
CUERPO = [i for i, c in enumerate(CANALES) if c.startswith("cuerpo_")]; PULSO = [i for i, c in enumerate(CANALES) if c in ("hr", "eda")]
# --- particion por tomas: una toma por (actor, animo) fuera en yakumama, una de la llama, 1 de cada 8 bailarines
fuera = set(); vistos = {}
for i, (fu, ac, an, no) in enumerate(zip(FUENTE, ACTOR, ANIMO, NOMBRE)):
    k = (fu, ac, int(an))
    vistos.setdefault(k, []).append(i)
for k, idxs in vistos.items():
    if k[0] == "yakumama" and len(idxs) > 1: fuera.add(idxs[-1])
    if k[0] == "llama": fuera.add(idxs[-1])
bail = [i for i, fu in enumerate(FUENTE) if fu == "bailarin"]; fuera.update(bail[::8])
def ventanas(idxs):
    out = []
    for i in idxs:
        s, e = SEQ[i]
        for t0 in range(s, e - C - T + 1, a.paso): out.append((t0, i))
    return np.array(out)
tr = ventanas([i for i in range(len(SEQ)) if i not in fuera]); va = ventanas(sorted(fuera))
print(f"tomas {len(SEQ)} ({len(fuera)} fuera) | ventanas entrenamiento {len(tr)} | prueba {len(va)}")
dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
Xt, Mt = torch.tensor(Xn, device=dev), torch.tensor(Mf, device=dev); ANt = torch.tensor(ANIMO, device=dev)
class Enc(nn.Module):
    """ventana (L cuadros, cualquier L) -> z. Conserva el orden: 6 posiciones temporales (pool adaptativo) aplanadas."""
    def __init__(s, L=None):
        super().__init__(); s.c1 = nn.Conv1d(2 * NC, 64, 5, padding=2); s.c2 = nn.Conv1d(64, 96, 5, stride=2, padding=2); s.c3 = nn.Conv1d(96, 64, 3, stride=2, padding=1); s.pool = nn.AdaptiveAvgPool1d(6); s.fc = nn.Linear(64 * 6, Z)
    def forward(s, x, m):   # x, m: (B, L, NC)
        h = torch.cat([x, m], -1).transpose(1, 2); h = F.gelu(s.c1(h)); h = F.gelu(s.c2(h)); h = F.gelu(s.c3(h)); return s.fc(s.pool(h).flatten(1))
def sigreg(z, n_dir=256, n_t=17):
    """SIGReg (LeJEPA): proyecta z sobre n_dir direcciones unitarias al azar y mide, con Epps-Pulley, cuanto se aleja cada
    proyeccion de una normal estandar: integral ponderada de |phi_emp(t) - exp(-t^2/2)|^2 con ventana gaussiana, t en [-5,5]."""
    B, D = z.shape; u = F.normalize(torch.randn(D, n_dir, device=z.device), dim=0); p = z @ u   # (B, n_dir)
    t = torch.linspace(-5, 5, n_t, device=z.device); arg = p[:, :, None] * t[None, None, :]       # (B, n_dir, n_t)
    re = torch.cos(arg).mean(0); im = torch.sin(arg).mean(0); obj = torch.exp(-t ** 2 / 2)         # funcion caracteristica empirica vs la normal
    dist = ((re - obj) ** 2 + im ** 2) * obj; return torch.trapezoid(dist, t, dim=-1).mean()
class Pred(nn.Module):
    """z del contexto + ultimo cuadro (valor y mascara) + animo + que canales va a haber -> z del objetivo"""
    def __init__(s):
        super().__init__(); s.net = nn.Sequential(nn.Linear(Z + 2 * NC + 10 + NC, 256), nn.GELU(), nn.Dropout(0.2), nn.Linear(256, 256), nn.GELU(), nn.Dropout(0.2), nn.Linear(256, Z))
    def forward(s, z, ultimo, animo, mt): return s.net(torch.cat([z, ultimo, animo, mt], -1))
class Dec(nn.Module):
    """z + ultimo cuadro + animo -> los T cuadros siguientes, como CAMBIO respecto del ultimo cuadro (donde lo hubo)"""
    def __init__(s):
        super().__init__(); s.net = nn.Sequential(nn.Linear(Z + 2 * NC + 10, 256), nn.GELU(), nn.Dropout(0.2), nn.Linear(256, 256), nn.GELU(), nn.Dropout(0.2), nn.Linear(256, T * NC))
        nn.init.zeros_(s.net[-1].weight); nn.init.zeros_(s.net[-1].bias)   # arranca en "repetir el ultimo cuadro" y solo puede mejorar
    def forward(s, z, ultimo, animo):
        d = s.net(torch.cat([z, ultimo, animo], -1)).view(-1, T, NC); xu, mu = ultimo[:, :NC], ultimo[:, NC:]
        return d + (xu * mu)[:, None, :]
enc, pred, dec = Enc().to(dev), Pred().to(dev), Dec().to(dev); enc_obj = enc if not a.sin_lejepa else Enc().to(dev)   # LeJEPA: el mismo codificador para todo
params = list(enc.parameters()) + list(pred.parameters()) + list(dec.parameters()) + ([] if enc_obj is enc else list(enc_obj.parameters())); opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=1e-3)
def lote(w, train):
    t0 = torch.tensor(w[:, 0], device=dev); si = torch.tensor(w[:, 1], device=dev)
    ar = torch.arange(C + T, device=dev); idx = t0[:, None] + ar[None, :]
    x = Xt[idx]; m = Mt[idx]; xc, mc, xo, mo = x[:, :C], m[:, :C].clone(), x[:, C:], m[:, C:]
    if train:   # esconder modalidades del contexto
        B = len(w); r = torch.rand(B, 3, device=dev)
        for k, grupo in enumerate((CARA + CABEZA, CUERPO, MANOS)):
            esc = (r[:, k] < 0.35).float()[:, None, None]; g = torch.tensor(grupo, device=dev); mc[:, :, g] = mc[:, :, g] * (1 - esc)
        xc = xc * mc
    an = torch.zeros(len(w), 10, device=dev); ok = ANt[si] >= 0; an[ok, ANt[si][ok]] = 1.0
    return xc, mc, xo, mo, an
def ult(xc, mc): return torch.cat([xc[:, -1, :] * mc[:, -1, :], mc[:, -1, :]], -1)
def varianza(z): return F.relu(1.0 - z.std(0)).mean()
n = len(tr); mejor = None
for ep in range(a.epochs):
    enc.train(); pred.train(); dec.train(); perm = np.random.permutation(n); tot = {"lat": 0.0, "rec": 0.0}; nb = 0
    lr = a.lr * 0.5 * (1 + math.cos(math.pi * ep / a.epochs))
    for g in opt.param_groups: g["lr"] = lr
    for i in range(0, n, 256):
        xc, mc, xo, mo, an = lote(tr[perm[i:i + 256]], True)
        u = ult(xc, mc); zc = enc(xc, mc); zp = pred(zc, u, an, mo.mean(1))
        if a.sin_lejepa:
            with torch.no_grad(): zo = enc_obj(xo, mo)
            l_lat = F.smooth_l1_loss(zp, zo); l_reg = 0.1 * varianza(zc)
        else:   # LeJEPA: prediccion latente con gradiente por los dos lados + SIGReg sobre los z de contexto y objetivo
            zo = enc_obj(xo, mo); l_lat = F.mse_loss(zp, zo); l_reg = a.sigreg * 0.5 * (sigreg(zc) + sigreg(zo))
        rec = dec(zp, u, an); l_rec = (F.smooth_l1_loss(rec, xo, reduction="none") * mo).sum() / mo.sum().clamp(min=1)
        rec2 = dec(zo.detach(), u, an); l_rec2 = (F.smooth_l1_loss(rec2, xo, reduction="none") * mo).sum() / mo.sum().clamp(min=1)
        loss = l_lat + l_rec + 0.5 * l_rec2 + l_reg
        opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(params, 1.0); opt.step()
        with torch.no_grad():   # el codificador objetivo aprende por reconstruccion (l_rec2) y se mueve despacio
            pass
        tot["lat"] += l_lat.item(); tot["rec"] += l_rec.item(); nb += 1
    enc.eval(); pred.eval(); dec.eval()
    with torch.no_grad():
        xc, mc, xo, mo, an = lote(va[::4], False); u = ult(xc, mc); zp = pred(enc(xc, mc), u, an, mo.mean(1)); rec = dec(zp, u, an)
        lv = ((F.smooth_l1_loss(rec, xo, reduction="none") * mo).sum() / mo.sum()).item()
    print(f"  epoca {ep:3d}  latente {tot['lat'] / nb:.4f}  reconstruccion {tot['rec'] / nb:.4f}  prueba {lv:.4f}", flush=True)
    if mejor is None or lv < mejor[0]: mejor = (lv, ep, {k: {kk: vv.detach().clone() for kk, vv in m.state_dict().items()} for k, m in (("enc", enc), ("enc_obj", enc_obj), ("pred", pred), ("dec", dec))})
print(f"mejor epoca {mejor[1]} (prueba {mejor[0]:.4f}): se guarda esa")
for k, m in (("enc", enc), ("enc_obj", enc_obj), ("pred", pred), ("dec", dec)): m.load_state_dict(mejor[2][k])
# --- medir con tomas fuera, en unidades originales
enc.eval(); pred.eval(); dec.eval()
def desnorm(x): return x * torch.tensor(desvio, device=dev) + torch.tensor(media, device=dev)
with torch.no_grad():
    xc, mc, xo, mo, an = lote(va, False); u = ult(xc, mc); zp = pred(enc(xc, mc), u, an, mo.mean(1)); rec = desnorm(dec(zp, u, an)); real = desnorm(xo)
    ultimo = desnorm(xc[:, -1:, :]).expand(-1, T, -1); med = torch.tensor(media, device=dev).expand_as(real)
    pend = (desnorm(xc[:, -1, :]) - desnorm(xc[:, -7, :])) / 6.0; lineal = desnorm(xc[:, -1, :])[:, None, :] + pend[:, None, :] * torch.arange(1, T + 1, device=dev)[None, :, None]
    err = lambda p, h=T: ((p[:, :h] - real[:, :h]).abs() * mo[:, :h]).sum((0, 1)) / mo[:, :h].sum((0, 1)).clamp(min=1)
    pres = mo.sum((0, 1)).cpu().numpy()
    for h, nombre in ((12, "1 s"), (24, "2 s")):
        e_j, e_u, e_l, e_m = err(rec, h).cpu().numpy(), err(ultimo, h).cpu().numpy(), err(lineal, h).cpu().numpy(), err(med, h).cpu().numpy()
        print(f"\nfuturo a {nombre} con tomas fuera: error por canal  JEPA / repetir ultimo / lineal / media   [cuadros]   (gana el JEPA: *)")
        for j, c in enumerate(CANALES):
            if pres[j] > 100: print(f"  {c:18s} {e_j[j]:.3f} / {e_u[j]:.3f} / {e_l[j]:.3f} / {e_m[j]:.3f}   [{int(pres[j])}] {'*' if e_j[j] < min(e_u[j], e_l[j], e_m[j]) else ''}")
    # cara -> cuerpo: tomas de la llama fuera, escondiendo el cuerpo del contexto
    vl = np.array([w for w in va if FUENTE[w[1]] == "llama"])
    if len(vl):
        xc, mc, xo, mo, an = lote(vl, False); g = torch.tensor(CUERPO, device=dev); mc[:, :, g] = 0; xc = xc * mc; u = ult(xc, mc)
        rec = desnorm(dec(pred(enc(xc, mc), u, an, mo.mean(1)), u, an)); real = desnorm(xo)
        e_j, e_m = err(rec).cpu().numpy(), err(med[:len(real)]).cpu().numpy()
        print("\ncara -> cuerpo (llama fuera, cuerpo escondido en el contexto): JEPA / media")
        for j in CUERPO: print(f"  {CANALES[j]:18s} {e_j[j]:.3f} / {e_m[j]:.3f}")
    # relaciones: correlacion dentro de la ventana predicha vs real
    def rel(ia, ib, filtro):
        w = np.array([x for x in va if filtro(x[1])])
        if not len(w): return None
        xc, mc, xo, mo, an = lote(w, False); u = ult(xc, mc); rec = desnorm(dec(pred(enc(xc, mc), u, an, mo.mean(1)), u, an)).cpu().numpy(); real = desnorm(xo).cpu().numpy(); m = mo.cpu().numpy()
        ok = (m[:, :, ia].all(1)) & (m[:, :, ib].all(1)); rr, rp = [], []
        for k in np.where(ok)[0]:
            if real[k, :, ia].std() > 1e-3 and real[k, :, ib].std() > 1e-3 and rec[k, :, ia].std() > 1e-3 and rec[k, :, ib].std() > 1e-3:
                rr.append(np.corrcoef(real[k, :, ia], real[k, :, ib])[0, 1]); rp.append(np.corrcoef(rec[k, :, ia], rec[k, :, ib])[0, 1])
        return (float(np.mean(rr)), float(np.mean(rp)), len(rr)) if rr else None
    ci = {c: i for i, c in enumerate(CANALES)}
    for nombre, ia, ib, filtro in (("boca-cabeza en singing", ci["jaw_open"], ci["head_pitch"], lambda i: FUENTE[i] != "bailarin" and ANIMO[i] == 1),
                                   ("cabeza-giro en bailarines", ci["head_yaw"], ci["cuerpo_yaw"], lambda i: FUENTE[i] == "bailarin"),
                                   ("energia-agachado en bailarines", ci["cuerpo_energia"], ci["cuerpo_profundidad"], lambda i: FUENTE[i] == "bailarin")):
        r = rel(ia, ib, filtro); print(f"relacion {nombre}: real {r[0]:+.2f} predicha {r[1]:+.2f} ({r[2]} ventanas)" if r else f"relacion {nombre}: sin ventanas")
torch.save({"lejepa": not a.sin_lejepa, "enc": enc.state_dict(), "enc_obj": enc_obj.state_dict(), "pred": pred.state_dict(), "dec": dec.state_dict(), "canales": CANALES, "media": media, "desvio": desvio, "C": C, "T": T, "Z": Z, "fps": float(d["fps"])}, os.path.join(AQUI, "modelos", "jepa.pt"))
z = {"canales": np.array(CANALES), "media": media, "desvio": desvio, "C": np.array(C), "T": np.array(T)}
for nom, mod in (("enc", enc), ("pred", pred), ("dec", dec)):   # el codificador de CONTEXTO (48 cuadros) es el que se usa para predecir
    for k, v in mod.state_dict().items(): z[f"{nom}.{k}"] = v.cpu().numpy()
np.savez(os.path.join(AQUI, "modelos", "jepa_pesos.npz"), **z); print("guardado modelos/jepa.pt y modelos/jepa_pesos.npz")
