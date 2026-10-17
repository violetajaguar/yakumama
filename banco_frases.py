#!/usr/bin/env python3
"""banco_frases.py - her PHRASE BANK: every 2-second window of real movement in her body space (ballena_datos.npz: dancers,
swimmers, divers, performers, faces, her behaviours; not the tagged whales, which only bring 6 channels), encoded with the
level-1 encoder of hjepa_ballena.pt. The sampling head (hjepa_predecir.HJepa.muestrear) plans sub-goals in latent space and,
for each one, retrieves a real phrase whose latent is close, choosing at random among the closest and keeping continuity.
So what she generates is made of real phrases, never an average.

    venv/bin/python banco_frases.py        -> modelos/banco_frases.npz
"""
import os, sys, numpy as np, torch
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from hjepa_predecir import HJepa
h = HJepa(os.path.join(AQUI, "modelos", "hjepa_ballena.pt")); d = np.load(os.path.join(AQUI, "modelos", "ballena_datos.npz"), allow_pickle=True)
CAN = [str(c) for c in d["CANALES"]]; assert CAN == h.CUERPO, "channels differ"
X, M, SEQ, FU, AN = d["X"], d["M"], d["SEQ"], d["FUENTE"], d["ANIMO"]
L = h.PASO; paso = L // 2; zs = []; ini = []; pista = []; animo = []; ventanas = []; mascaras = []
with torch.no_grad():
    for k, (s, e) in enumerate(SEQ):
        if str(FU[k]) == "ballena": continue
        for t0 in range(s, e - L + 1, paso):
            m = M[t0:t0 + L]
            if m.mean() < 0.3: continue
            x = np.where(m, (X[t0:t0 + L] - h.media) / h.desvio, 0.0).astype(np.float32)
            zs.append(h.enc1(torch.tensor(np.concatenate([x, m.astype(np.float32)], -1))[None])[0].numpy()); ini.append(t0); pista.append(k); animo.append(int(AN[k]))
            ventanas.append(np.where(m, X[t0:t0 + L], np.nan).astype(np.float16)); mascaras.append(m)
Z = np.stack(zs).astype(np.float32); V = np.stack(ventanas); MM = np.stack(mascaras)
np.savez_compressed(os.path.join(AQUI, "modelos", "banco_frases.npz"), Z=Z, V=V, M=MM, pista=np.array(pista), animo=np.array(animo), canales=np.array(CAN), fps=h.fps, L=L)
print(f"phrase bank: {len(Z)} phrases of {L / h.fps:.0f} s from {len(set(pista))} tracks | {V.nbytes / 1e6:.0f} MB | per mood: " + ", ".join(f"{m} {int((np.array(animo) == i).sum())}" for i, m in enumerate(h.ACCIONES[:10])) + f", libre {int((np.array(animo) < 0).sum())}")
