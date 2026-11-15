#!/usr/bin/env python3
"""banco_caras.py - her blinks learn from the people who visit her (30 Oct 2026, Violeta: "build her blinks from what she did").

Her own blink (cerebro_ballena.parpadeo_propio) plays 6-second phrases of real eyelids from modelos/cara_banco.npz, one bank per
mood. Until today that bank held only the seven hours of faces recorded at home before Barcelona (modelos/cara_banco_casa.npz
keeps that copy as the base). This script cuts the saved visits (datasets/visitas/*.jsonl: every face that stood in front of her,
with the mood she read in it) into the same phrases and adds them to the bank, so her blinks carry the visitors' rhythm too.

    venv/bin/python -I banco_caras.py                              # datasets/visitas -> cara_banco_visitas.npz -> cara_banco.npz
    venv/bin/python -I banco_caras.py --visitas datasets/visitas /Volumes/USB/datasets/visitas   # several folders (home + Barcelona)
    venv/bin/python -I banco_caras.py --informe                    # only count what the bank holds, per mood

Her brain calls aprender() at night, right after decisiones.aprender(), and reloads the bank. The home bank is never touched: a day
with no visits or broken files leaves her blinking as before. Phrases: 6 s at 12/s (72 frames), hop 3 s, columns (eyelid, brow).
Eyelid: the home bank is the raw max(eyeBlinkLeft, eyeBlinkRight) blendshape (verified 30 Oct: it reproduces the bank exactly), but on
visitors that raw signal rests half-closed (median 0.30 against 0.09 at home: they stand farther from her eye), so for them we take the
eye's own neutral-corrected `blink` key (rest 0.02, blinks 0.9, the same range as the home bank) and fall back to the raw blendshape only
when it is missing. Brow from brow_up. A phrase needs a continuous face (no gap over 0.5 s) in a single mood."""
import os, sys, json, glob, shutil, time
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
VISITAS = os.path.join(AQUI, "datasets", "visitas")
BANCO = os.path.join(AQUI, "modelos", "cara_banco.npz")              # what her brain loads
CASA = os.path.join(AQUI, "modelos", "cara_banco_casa.npz")          # the home faces, kept as the base (copied once from BANCO)
DE_VISITAS = os.path.join(AQUI, "modelos", "cara_banco_visitas.npz") # the visitors' phrases alone
INFORME = os.path.join(AQUI, "modelos", "cara_banco_visitas.json")
FPS, LARGO_S, SALTO_S, HUECO_S = 12.0, 6.0, 3.0, 0.5
LARGO = int(LARGO_S * FPS)

def _parpado(r):
    b = r.get("blink")
    if b is not None: return min(1.0, max(0.0, float(b)))
    l, d = r.get("face_eyeBlinkLeft"), r.get("face_eyeBlinkRight")
    return min(1.0, max(0.0, max(float(l or 0.0), float(d or 0.0))))

def frases_de_visita(ruta):
    """-> {mood: [phrase (72, 2) float32, ...]} from one saved visit; the first line is the header, the rest are face packets."""
    out = {}
    try: regs = [json.loads(l) for l in open(ruta, encoding="utf-8") if l.strip()]
    except Exception: return out
    regs = [r for r in regs if isinstance(r.get("t"), (int, float)) and r.get("actor_animo")]
    if len(regs) < 2: return out
    # contiguous runs: same mood, no gap over HUECO_S
    tramos, actual = [], [regs[0]]
    for a, b in zip(regs, regs[1:]):
        if b["actor_animo"] != a["actor_animo"] or (b["t"] - a["t"]) > HUECO_S: tramos.append(actual); actual = [b]
        else: actual.append(b)
    tramos.append(actual)
    for tr in tramos:
        t = np.array([r["t"] for r in tr], dtype=np.float64)
        if t[-1] - t[0] < LARGO_S: continue
        y = np.array([[_parpado(r), min(1.0, max(0.0, float(r.get("brow_up") or 0.0)))] for r in tr], dtype=np.float32)
        tt = np.arange(t[0], t[-1], 1.0 / FPS)                                  # resample to 12/s
        z = np.stack([np.interp(tt, t, y[:, 0]), np.interp(tt, t, y[:, 1])], axis=1).astype(np.float32)
        m = tr[0]["actor_animo"]; salto = int(SALTO_S * FPS)
        for i in range(0, len(z) - LARGO + 1, salto): out.setdefault(m, []).append(z[i:i + LARGO])
    return out

def construir(visitas=VISITAS, salida=DE_VISITAS, informe=INFORME):
    """all the visits of one folder, or of a list of folders (home + Barcelona) -> the visitors' bank. Returns the report dict."""
    carpetas = [visitas] if isinstance(visitas, str) else list(visitas)
    archivos = sorted(f for c in carpetas for f in glob.glob(os.path.join(c, "*.jsonl"))); banco, usadas = {}, 0
    for f in archivos:
        fr = frases_de_visita(f)
        if fr: usadas += 1
        for m, lst in fr.items(): banco.setdefault(m, []).extend(lst)
    arr = {m: np.stack(v) for m, v in banco.items() if v}
    rep = {"t": time.time(), "visitas_dir": visitas, "visitas": len(archivos), "visitas_con_frases": usadas,
           "frases": {m: int(len(a)) for m, a in arr.items()},
           "parpadeos_por_min": {m: round(float(_parpadeos_por_min(a)), 1) for m, a in arr.items()}}
    if arr:
        np.savez_compressed(salida, **arr); json.dump(rep, open(informe, "w"), indent=1)
    return rep

def _parpadeos_por_min(a):
    """blinks per minute in a stack of phrases (n, 72, 2): rising edges of the eyelid over 0.5."""
    e = a[:, :, 0] > 0.5; sub = (e[:, 1:] & ~e[:, :-1]).sum()
    return 60.0 * sub / (a.shape[0] * LARGO_S)

def fusionar(banco=BANCO, casa=CASA, de_visitas=DE_VISITAS):
    """home base + visitors -> the bank her brain loads. The home copy is made once and never rewritten."""
    if not os.path.exists(casa):
        if not os.path.exists(banco): raise FileNotFoundError(f"no bank to start from: {banco}")
        shutil.copy2(banco, casa)
    C = np.load(casa); out = {m: C[m] for m in C.files}
    if os.path.exists(de_visitas):
        V = np.load(de_visitas)
        for m in V.files: out[m] = np.concatenate([out[m], V[m]]) if m in out else V[m]
    tmp = banco + ".tmp.npz"; np.savez_compressed(tmp, **out); os.replace(tmp, banco)
    return {m: int(len(a)) for m, a in out.items()}

def informe():
    def cuenta(p):
        if not os.path.exists(p): return {}
        z = np.load(p); return {m: int(len(z[m])) for m in z.files}
    return {"casa": cuenta(CASA if os.path.exists(CASA) else BANCO), "visitas": cuenta(DE_VISITAS), "banco": cuenta(BANCO)}

def aprender(visitas=VISITAS):
    """the night step: cut the visits, merge over the home base, print one line. Never raises."""
    try:
        rep = construir(visitas); tot = fusionar()
        print(f"   face bank: {rep['visitas_con_frases']}/{rep['visitas']} visits -> {sum(rep['frases'].values())} visitor phrases; bank now {sum(tot.values())} phrases in {len(tot)} moods", flush=True)
        return rep
    except Exception as e: print(f"   (face bank: {e})", flush=True); return None

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--visitas", nargs="+", default=[VISITAS], help="one or more folders of saved visits"); ap.add_argument("--informe", action="store_true"); a = ap.parse_args()
    if a.informe: print(json.dumps(informe(), indent=1)); sys.exit()
    rep = construir(a.visitas); print(json.dumps(rep, indent=1, ensure_ascii=False))
    tot = fusionar(); print("bank per mood (home + visitors):", json.dumps(tot))
