#!/usr/bin/env python3
"""catdecide_de_ella.py - CatDecide-1 fitted to this experience with an ADAPTER (14 Nov 2026, Violeta: "use all the data to train").
Fabrício's weights (modelos/CatDecide-1, gated, "do not redistribute") are NOT changed: this trains small low-rank additions (LoRA, a few
MB) on the query and value projections of its last layers and saves only those, in modelos/CatDecide-1-de-ella/. With the adapter off
the model is exactly his. It learns from the same rows as her Laya (pruebas_laya/experiencia_datos.py: every decision she logged).
    python3 pruebas_laya/experiencia_datos.py                                    # first: the rows
    venv_catdecide/bin/python -I pruebas_laya/catdecide_de_ella.py              # train the adapter, then measure
    venv_catdecide/bin/python -I pruebas_laya/catdecide_de_ella.py --medir      # measure only: his model against his model + her adapter
    ... --todo 7000 --eng 12000 --solo 1000 --destino CatDecide-1-de-ella-todo --salida resultados_catdecide_de_ella_todo.json --n 1500 --sin_suyo
                                                                                # the same 67,337 examples her Laya saw (about 5 h); add --seguir if it was cut
The first adapter (17,796 examples, 14 Nov) is in modelos/CatDecide-1-de-ella; the one with all the examples in modelos/CatDecide-1-de-ella-todo.
Read through his own readout (example.py: prompt, option orders, temperature). His `decided` thresholds were calibrated on his data
without the adapter; with it they are not recalibrated. Nothing live uses the adapter (catdecide_sentidos.py loads his model as it is)."""
import os, sys, json, time, random, math, hashlib
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI); sys.path.insert(0, RAIZ); sys.path.insert(0, AQUI)
from laya_sentidos import PRE, Q
import experiencia_datos as EX
PESOS = os.path.join(RAIZ, "modelos", "CatDecide-1"); DESTINO = os.path.join(RAIZ, "modelos", "CatDecide-1-de-ella"); SALIDA = os.path.join(AQUI, "resultados_catdecide_de_ella.json")
CLAVES = list(Q); sys.path.insert(0, PESOS)

def poner(m, capas=12, r=16, alpha=32):
    """Wrap q_proj and v_proj of the last `capas` layers with a low-rank addition (zero at the start). Returns the additions, in a fixed order."""
    import torch, torch.nn as nn
    class LoRA(nn.Module):
        def __init__(self, base):
            super().__init__(); self.base = base; dev = base.weight.device
            self.A = nn.Parameter(torch.randn(r, base.in_features, device=dev) * 0.01); self.B = nn.Parameter(torch.zeros(base.out_features, r, device=dev)); self.s = alpha / r; self.activa = True
        def forward(self, x):
            y = self.base(x); return y + ((x.float() @ self.A.T) @ self.B.T * self.s).to(y.dtype) if self.activa else y
    for p in m.lm.parameters(): p.requires_grad_(False)
    loras = []
    for capa in m.lm.model.layers[-capas:]:
        for nombre in ("q_proj", "v_proj"):
            l = LoRA(getattr(capa.self_attn, nombre)); setattr(capa.self_attn, nombre, l); loras.append(l)
    return loras
def activar(loras, si):
    for l in loras: l.activa = si
def cargar(m, ruta=None):
    """His model + her adapter: `m` is example.CatDecide(...). Returns the additions (activar(loras, False) gives his model back)."""
    import torch
    ruta = ruta or DESTINO; meta = json.load(open(os.path.join(ruta, "adaptador.json"))); loras = poner(m, meta["capas"], meta["r"], meta["alpha"])
    for l, (A, B) in zip(loras, torch.load(os.path.join(ruta, "adaptador.pt"), map_location=m.device)): l.A.data.copy_(A); l.B.data.copy_(B)
    return loras

def entrenar(a):
    import torch
    from example import CatDecide, render, NOUL, orders
    destino = os.path.join(RAIZ, "modelos", a.destino); punto = os.path.join(destino, "punto.pt")
    m = CatDecide(PESOS, device="mps" if torch.backends.mps.is_available() else "cpu"); cal = m.calibration; cabeza = m.head.detach()
    ej, info = EX.ejemplos(a.todo, a.eng, a.solo); print("  ", info, flush=True); R = random.Random(7)
    loras = poner(m, a.capas, a.r, 2 * a.r); params = [p for l in loras for p in (l.A, l.B)]; opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.0)
    por_epoca = math.ceil(len(ej) / a.lote); pasos = a.epocas * por_epoca; calienta = max(5, pasos // 20)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda p: (p + 1) / calienta if p < calienta else 0.5 * (1 + math.cos(math.pi * (p - calienta) / max(1, pasos - calienta))))
    paso = 0
    if a.seguir and os.path.exists(punto):                                      # a run that was cut (hours long): pick it up at its last saved step
        pt = torch.load(punto, map_location=m.device)
        for l, (A, B) in zip(loras, pt["ab"]): l.A.data.copy_(A); l.B.data.copy_(B)
        opt.load_state_dict(pt["opt"]); sched.load_state_dict(pt["sched"]); paso = pt["paso"]; print(f"   sigue desde el paso {paso}", flush=True)
    def guardar_punto():
        os.makedirs(destino, exist_ok=True)
        torch.save({"ab": [(l.A.detach().cpu(), l.B.detach().cpu()) for l in loras], "opt": opt.state_dict(), "sched": sched.state_dict(), "paso": paso}, punto + ".tmp"); os.replace(punto + ".tmp", punto)
    print(f"   {len(ej)} ejemplos, {pasos} pasos, {sum(p.numel() for p in params)} parametros del adaptador", flush=True); t0 = time.time(); paso0 = paso; media = None
    for ep in range(a.epocas):
        orden_ej = list(range(len(ej))); random.Random(7 + ep).shuffle(orden_ej)  # the order depends only on the epoch, so a resumed run continues the same pass
        for nl, i in enumerate(range(0, len(ej), a.lote)):
            if ep * por_epoca + nl < paso0: continue
            g = [ej[k] for k in orden_ej[i:i + a.lote]]; prompts = []; Y = torch.zeros(len(g), 3); M = torch.full((len(g), 3), -1e4); T = torch.ones(len(g), 1)
            for j, (t, k, v) in enumerate(g):
                q = Q[k]
                if q["type"] == "score": desc = {str(n): c for n, c in enumerate(q["criteria"])}; dist = {o: (1 - a.suave if int(o) == int(v) else a.suave / (len(desc) - 1)) for o in desc}
                else: desc = dict(NOUL); p = min(1 - a.suave, max(a.suave, float(v))); dist = {"true": p, "false": 1 - p}
                orden = R.choice(orders(q["type"], list(desc))); estado = PRE + t; marca = hashlib.sha256(estado.encode("utf-8")).hexdigest()[:6].upper()
                prompts.append(m.prompt(render(estado, marca, q["instructions"], [desc[o] for o in orden])))
                for n, o in enumerate(orden): Y[j, n] = dist[o]; M[j, n] = 0.0
                T[j, 0] = cal[q["type"]]["temperature"]                            # trained through the temperature his readout applies, so decide() gives what was taught
            enc = m.tok(prompts, add_special_tokens=False, padding=True, return_tensors="pt").to(m.device); mask = enc["attention_mask"]; pos = (mask.cumsum(-1) - 1).clamp(min=0)
            h = m.lm.model(input_ids=enc["input_ids"], attention_mask=mask, position_ids=pos, use_cache=False).last_hidden_state[:, -1].float()
            z = (h @ cabeza.T)[:, :3] / T.to(m.device) + M.to(m.device); l = -(Y.to(m.device) * torch.log_softmax(z, dim=-1)).sum(-1).mean()
            opt.zero_grad(); l.backward(); torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); sched.step()
            paso += 1; media = l.item() if media is None else 0.98 * media + 0.02 * l.item()
            hechos = paso - paso0
            if paso % 100 == 0 or hechos == 10: print(f"   paso {paso}/{pasos}  perdida {media:.4f}  {(time.time() - t0) / hechos:.2f} s/paso  faltan {(pasos - paso) * (time.time() - t0) / hechos / 60:.1f} min", flush=True)
            if not a.prueba and paso % a.guardar_cada == 0: guardar_punto()
            if a.pasos and paso >= a.pasos: break
        if a.pasos and paso >= a.pasos: break
    if not a.prueba:
        os.makedirs(destino, exist_ok=True); torch.save([(l.A.detach().cpu(), l.B.detach().cpu()) for l in loras], os.path.join(destino, "adaptador.pt"))
        json.dump({"fecha": time.strftime("%Y-%m-%d"), "sobre": "fabriciocarraro/CatDecide-1 (sus pesos no cambian; esto se suma a q_proj y v_proj de sus ultimas capas)", "capas": a.capas, "r": a.r, "alpha": 2 * a.r,
                   "datos": json.load(open(os.path.join(EX.SALIDA, "efectos.json")))["fuentes"], "muestra": info, "pasos": paso, "lr": a.lr, "lote": a.lote, "script": "pruebas_laya/catdecide_de_ella.py"}, open(os.path.join(destino, "adaptador.json"), "w"), indent=1)
        if os.path.exists(punto): os.remove(punto)                              # the finished adapter replaces the resume point
        print(f"   adaptador guardado en {destino} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    return m, loras

def medir(a, m=None, loras=None):
    """His model and his model + the adapter in modelos/<a.destino>, on the first a.n held-out rows (muestra_mide: a fixed shuffle, so a
    larger n contains the rows of a smaller one). --sin_suyo skips his model as it is (already measured on the first 350)."""
    import torch
    salida_f = os.path.join(AQUI, a.salida)
    if m is None:
        from example import CatDecide
        m = CatDecide(PESOS, device="mps" if torch.backends.mps.is_available() else "cpu"); loras = cargar(m, os.path.join(RAIZ, "modelos", a.destino))
    F = EX.muestra_mide(a.n); salida = {}
    for nombre, si in (("CatDecide-1 (el suyo)", False), ("CatDecide-1 + adaptador de ella", True)):
        if a.sin_suyo and not si: continue
        activar(loras, si); t0 = time.time(); resp = []; dec = []
        for n, f in enumerate(F):
            r = m.decide(PRE + f["texto"], Q); dec.append({k: bool(r[k].get("decided")) for k in CLAVES})
            resp.append({k: (int(r[k]["choice"]) if Q[k]["type"] == "score" else r[k]["probabilities"]["true"]) for k in CLAVES})
            if (n + 1) % 250 == 0: print(f"   {nombre}: {n + 1}/{len(F)} situaciones, faltan {(len(F) - n - 1) * (time.time() - t0) / (n + 1) / 60:.0f} min", flush=True)
        salida[nombre] = {"ms": 1000 * (time.time() - t0) / len(F), "tabla": EX.informe(f"{nombre}  [{1000 * (time.time() - t0) / len(F):.0f} ms por situacion; 'decided' en engaged: {sum(d['engaged'] for d in dec)}]", F, resp), "resp": resp, "decided": dec}
        json.dump(salida, open(salida_f, "w"), ensure_ascii=False)
    print("   ->", salida_f)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--medir", action="store_true"); ap.add_argument("--prueba", action="store_true")
    ap.add_argument("--todo", type=int, default=1800); ap.add_argument("--eng", type=int, default=3600); ap.add_argument("--solo", type=int, default=200)
    ap.add_argument("--epocas", type=int, default=1); ap.add_argument("--lote", type=int, default=8); ap.add_argument("--lr", type=float, default=1e-4); ap.add_argument("--suave", type=float, default=0.03)
    ap.add_argument("--capas", type=int, default=12); ap.add_argument("--r", type=int, default=16); ap.add_argument("--pasos", type=int, default=0)
    ap.add_argument("--destino", default="CatDecide-1-de-ella"); ap.add_argument("--salida", default="resultados_catdecide_de_ella.json")   # folder under modelos/ and result file, so a second adapter does not replace the first
    ap.add_argument("--n", type=int, default=350); ap.add_argument("--sin_suyo", action="store_true"); ap.add_argument("--seguir", action="store_true"); ap.add_argument("--guardar_cada", type=int, default=500)
    a = ap.parse_args()
    if a.prueba: a.n = min(a.n, 6); a.salida = "resultados_catdecide_prueba.json"
    if a.medir: medir(a)
    else:
        m, loras = entrenar(a); medir(a, m, loras)
