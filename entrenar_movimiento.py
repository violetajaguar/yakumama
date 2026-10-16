#!/usr/bin/env python3
"""entrenar_movimiento.py - la ballena aprende a ACTUAR cada animo con el estilo del actor (como train_llama_motion.py).

Entrada:  animo (one-hot) + fase en la toma + armonicos de tiempo (seno/coseno a varios periodos) + pulso previo
          + quien actua (one-hot de los actores grabados; todos a 1/n = el estilo promedio)
Salida:   los canales del actor en ese instante: cabeza, boca, parpadeo, cejas, sonrisa, mirada, manos, pulso, piel
Luego `generar_animo.py <animo>` corre la red y manda esos canales a Blender como si fuera el actor: la ballena
hace el animo sola, con la cara y las manos del actor aprendidas, sobre el cuerpo del comportamiento NOAA.

    venv/bin/python entrenar_movimiento.py --epochs 400
Guarda modelos/movimiento.pt (pesos + normalizacion + lista de canales).
"""
import json, os, math, argparse, numpy as np, torch, torch.nn as nn
AQUI = os.path.dirname(os.path.abspath(__file__))
MOODS = ["calm","singing","playful","curious","feeding","sad","angry","alert","diving","surfacing"]
SALIDAS = ["head_yaw","head_pitch","jaw_open","blink","brow_up","brow_down","mouth_sad","mouth_smile","eye_yaw","eye_pitch",
           "l_palm_y","r_palm_y","l_palm_x","r_palm_x","mano_l","mano_r","hr","eda"]
PERIODOS = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
def entrada(animo_idx, t, dur, hr_prev, actor=None, actores=()):
    """vector de entrada: one-hot(10) + progreso + 2*6 armonicos + pulso previo normalizado + one-hot del actor
    (actor None = 1/n en todos: el estilo promedio de los actores grabados)"""
    x = [0.0] * 10; x[animo_idx] = 1.0
    x.append(t / max(dur, 1.0))
    for P in PERIODOS: x += [math.sin(2 * math.pi * t / P), math.cos(2 * math.pi * t / P)]
    x.append((hr_prev - 85.0) / 30.0)
    if actores: x += [1.0 if a == actor else (0.0 if actor is not None else 1.0 / len(actores)) for a in actores]
    return x
def actor_de(nombre_archivo):
    """'calm_sanam_001.jsonl' -> 'sanam'; 'calm_001.jsonl' -> 'violeta' (las tomas sin nombre son de Violeta)."""
    partes = nombre_archivo[:-6].split("_"); return partes[1] if len(partes) == 3 else "violeta"
def parpadeo_offline(cara):
    """recalcula `blink` de una toma a partir de lo crudo (eyeBlink de MediaPipe y EAR de ballena3) con la regla
    actual del grabador: nivel de ojos abiertos de la persona (minimo lento), salto minimo absoluto, cierre de 0.15 s.
    Las tomas viejas se grabaron con reglas peores (dan: 31 % de cuadros 'cerrados'); asi todas quedan iguales."""
    base_e, base_b, alto, hold_hasta, out = 0.0, None, 0, -1.0, []
    for i, r in enumerate(cara):
        t = float(r.get("t", i / 15.0)); todo = r.get("todo") or {}
        e = float(todo.get("blink", r.get("blink", 0)) or 0); base_e = min(e, base_e + 0.002)
        n = min(1.0, (e - base_e) / 0.3) if e - base_e >= 0.2 else 0.0
        bl = r.get("face_eyeBlinkLeft"); br = r.get("face_eyeBlinkRight")
        if bl is not None or br is not None:
            b = max(float(bl or 0), float(br or 0)); base_b = b if base_b is None else min(b, base_b + 0.002)
            if b - base_b >= 0.3: n = max(n, min(1.0, (b - base_b) / max(0.3, 0.9 - base_b)))
        alto = alto + 1 if n > 0.5 else 0
        if alto == 1: hold_hasta = t + 0.15
        if alto > 12: base_e = e; base_b = b if (bl is not None or br is not None) else base_b; alto = 0; hold_hasta = -1.0; n = 0.0
        out.append(1.0 if t <= hold_hasta else 0.0)
    return out
def salida_de(c, b):
    hr = b.get("emotibit_hr"); eda = b.get("emotibit_eda")
    return [float(c.get("head_yaw", 0)), float(c.get("head_pitch", 0)), float(c.get("jaw_open", 0)), float(c.get("blink", 0)), float(c.get("brow_up", 0)), float(c.get("brow_down", 0)),
            float(c.get("mouth_sad", 0)), float(c.get("mouth_smile", 0)), float(c.get("eye_yaw", 0)), float(c.get("eye_pitch", 0)),
            float(b.get("l_palm_y", 0.5)), float(b.get("r_palm_y", 0.5)), float(b.get("l_palm_x", 0.5)), float(b.get("r_palm_x", 0.5)), float("l_palm_y" in b), float("r_palm_y" in b),
            (float(hr) - 85.0) / 30.0 if hr and 35 < hr < 190 else 0.0, min(1.0, float(eda) / 10.0) if eda and 0.1 < eda < 1000 else 0.0]
class Red(nn.Module):
    def __init__(self, n_in, n_out, h=256):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(n_in, h), nn.ReLU(), nn.Dropout(0.05), nn.Linear(h, h), nn.ReLU(), nn.Dropout(0.05), nn.Linear(h, h), nn.ReLU(), nn.Linear(h, h // 2), nn.ReLU(), nn.Linear(h // 2, n_out))
    def forward(self, x): return self.net(x)
def cargar():
    archivos = sorted(f for f in os.listdir(os.path.join(AQUI, "datasets", "cara")) if f.endswith(".jsonl") and "_ravdess" not in f and "_beat" not in f)   # RAVDESS: caras sin manos ni pulso, no son estilos de la ballena
    actores = sorted(set(actor_de(f) for f in archivos)); X, Y, G, A = [], [], [], []
    hr_animo = {a: {m: [] for m in MOODS} for a in actores}   # pulso mediano de cada actor en cada animo (ancla para generar)
    for f in archivos:
        cara = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cara", f))]; cuerpo = [json.loads(l) for l in open(os.path.join(AQUI, "datasets", "cuerpo", f))]
        animo = f.split("_")[0]; ai = MOODS.index(animo); actor = actor_de(f); t0 = cara[0]["t"]; dur = cara[-1]["t"] - t0; hr_prev = 85.0
        parp = parpadeo_offline(cara)
        for i in range(min(len(cara), len(cuerpo))):
            c, b = cara[i], cuerpo[i]
            if i > 0 and c["todo"]["head_yaw"] == cara[i-1]["todo"]["head_yaw"]: continue   # cara perdida: no ensena nada
            c = {**c, "blink": parp[i]}
            X.append(entrada(ai, c["t"] - t0, dur, hr_prev, actor, actores)); y = salida_de(c, b); Y.append(y); G.append(f[:-6]); A.append(actor)
            hr = b.get("emotibit_hr")
            if hr and 35 < hr < 190: hr_prev = 0.9 * hr_prev + 0.1 * float(hr); hr_animo[actor][animo].append(float(hr))
    hr_animo = {a: {m: (float(np.median(v)) if v else None) for m, v in d.items()} for a, d in hr_animo.items()}
    return np.array(X, np.float32), np.array(Y, np.float32), np.array(G), actores, hr_animo
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--epochs", type=int, default=400); ap.add_argument("--lr", type=float, default=1e-3); a = ap.parse_args()
    X, Y, G, ACTORES, HR_ANIMO = cargar(); print(f"muestras {len(X)} | entrada {X.shape[1]} | salida {Y.shape[1]} | tomas {len(set(G))} | actores {ACTORES}")
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    # prueba: una toma de cada animo que tenga 2+ tomas, fuera
    tomas = sorted(set(G)); fuera = set()
    for m in MOODS:
        t = [g for g in tomas if g.startswith(m + "_")]
        if len(t) > 1: fuera.add(t[-1])
    mask = np.array([g not in fuera for g in G]); print("tomas de prueba:", sorted(fuera))
    Xt, Yt = torch.tensor(X[mask]).to(dev), torch.tensor(Y[mask]).to(dev); Xv, Yv = torch.tensor(X[~mask]).to(dev), torch.tensor(Y[~mask]).to(dev)
    red = Red(X.shape[1], Y.shape[1]).to(dev); opt = torch.optim.AdamW(red.parameters(), lr=a.lr, weight_decay=1e-5); sched = torch.optim.lr_scheduler.StepLR(opt, step_size=100, gamma=0.5); loss_fn = nn.SmoothL1Loss()
    n = len(Xt); mejor = 1e9
    for ep in range(a.epochs):
        red.train(); perm = torch.randperm(n, device=dev); tot = 0.0
        for i in range(0, n, 1024):
            idx = perm[i:i+1024]; opt.zero_grad(); loss = loss_fn(red(Xt[idx]), Yt[idx]); loss.backward(); opt.step(); tot += loss.item() * len(idx)
        sched.step()
        if ep % 50 == 0 or ep == a.epochs - 1:
            red.eval()
            with torch.no_grad(): lv = loss_fn(red(Xv), Yv).item() if len(Xv) else float("nan")
            print(f"  epoca {ep:4d}  entrenamiento {tot/n:.4f}  prueba {lv:.4f}")
    # baseline: predecir la media de cada canal
    with torch.no_grad():
        red.eval(); pv = red(Xv).cpu().numpy(); yv = Yv.cpu().numpy(); media = Y[mask].mean(0)
        err_red = np.abs(pv - yv).mean(0); err_media = np.abs(media - yv).mean(0)
    print("error por canal (red / media constante):"); [print(f"  {k:12s} {r:.3f} / {m:.3f}") for k, r, m in zip(SALIDAS, err_red, err_media)]
    # entrenar con todo para el modelo final
    Xa, Ya = torch.tensor(X).to(dev), torch.tensor(Y).to(dev); red = Red(X.shape[1], Y.shape[1]).to(dev); opt = torch.optim.AdamW(red.parameters(), lr=a.lr, weight_decay=1e-5); sched = torch.optim.lr_scheduler.StepLR(opt, step_size=100, gamma=0.5)
    for ep in range(a.epochs):
        red.train(); perm = torch.randperm(len(Xa), device=dev)
        for i in range(0, len(Xa), 1024):
            idx = perm[i:i+1024]; opt.zero_grad(); loss = loss_fn(red(Xa[idx]), Ya[idx]); loss.backward(); opt.step()
        sched.step()
    torch.save({"estado": red.state_dict(), "n_in": X.shape[1], "n_out": Y.shape[1], "salidas": SALIDAS, "moods": MOODS, "periodos": PERIODOS, "actores": ACTORES, "hr_animo": HR_ANIMO}, os.path.join(AQUI, "modelos", "movimiento.pt"))
    print("guardado modelos/movimiento.pt")
    # pesos en NumPy para TouchDesigner / yakumama_modelo.py (sin torch)
    capas = [m for m in red.net if isinstance(m, nn.Linear)]; z = {"n_capas": np.array(len(capas)), "actores": np.array(ACTORES), "hr_animo": np.array(json.dumps(HR_ANIMO))}
    for i, m in enumerate(capas): z[f"W{i}"] = m.weight.detach().cpu().numpy(); z[f"b{i}"] = m.bias.detach().cpu().numpy()
    np.savez(os.path.join(AQUI, "modelos", "movimiento_pesos.npz"), **z); print("guardado modelos/movimiento_pesos.npz")
