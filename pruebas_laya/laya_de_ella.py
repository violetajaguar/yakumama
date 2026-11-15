#!/usr/bin/env python3
"""laya_de_ella.py - Laya's weights rewritten from this experience (14 Nov 2026, Violeta: "use all the data to train"). The open Laya
(Apache-2.0, ModernBERT-large + a decision head, 807 MB) answered her eight production questions with a near-constant. This fine-tunes
a COPY of it on every decision she logged, at home and in Barcelona (pruebas_laya/experiencia_datos.py builds the rows and says what
each question learns: engaged = what the visitor did, maltrato and regalo = what her senses read, the five "should she" = what worked).
    python3 pruebas_laya/experiencia_datos.py                             # first: the rows, from every decisiones.jsonl
    venv_datos/bin/python -I pruebas_laya/laya_de_ella.py                 # train -> modelos/laya-de-ella-mlx, then measure
    venv_datos/bin/python -I pruebas_laya/laya_de_ella.py --medir         # measure only: the original against hers, on visits neither saw
The original stays in modelos/laya-typed-decisions-mlx. Production (laya_sentidos.MODELO, the mini) is NOT changed by this file.
To use hers, production must also write the sentences she learned to read (experiencia_datos.escribir: back touch, stillness, dancing)."""
import os, sys, json, time, random, math, shutil
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI); sys.path.insert(0, RAIZ); sys.path.insert(0, AQUI)
from laya_sentidos import PRE, Q
import experiencia_datos as EX
ORIGEN = os.path.join(RAIZ, "modelos", "laya-typed-decisions-mlx"); DESTINO = os.path.join(RAIZ, "modelos", "laya-de-ella-mlx"); SALIDA = os.path.join(AQUI, "resultados_laya_de_ella.json")
CLAVES = list(Q)

def entrenar(a):
    import numpy as np, mlx.core as mx, mlx.nn as nn, mlx.optimizers as optim, laya_mlx as laya
    from mlx.utils import tree_flatten
    from laya_mlx.agent import collate_items
    ag = laya.load(ORIGEN, dtype="float32"); modelo = ag.model; pad = ag.tok.pad_token_id; largo = ag.cfg.get("max_len", 512)
    ej, info = EX.ejemplos(a.todo, a.eng, a.solo); print("  ", info, flush=True)
    preparado = {}                                                              # (text, question) -> its tokens, prepared once
    por_texto = {}
    for t, q, _ in ej: por_texto.setdefault(t, set()).add(q)
    for t, qs in por_texto.items():
        qs = sorted(qs); items, _ = ag.prepare(PRE + t, {q: Q[q] for q in qs})
        for q, it in zip(qs, items): preparado[(t, q)] = it
    filas = []                                                                  # (item, target distribution over its options): EVERY example, so a sentence seen 300 times keeps its 300 outcomes
    for t, q, v in ej:
        it = preparado[(t, q)]; n = len(it["markers"])
        if Q[q]["type"] == "score": d = np.full(n, a.suave / (n - 1), np.float32); d[int(v)] = 1.0 - a.suave
        else: p = min(1 - a.suave, max(a.suave, float(v))); d = np.array([1 - p, p], np.float32)   # noul options are always [false, true]
        filas.append((it, d))
    modelo.train(); modelo.freeze(keys=["temperature"], recurse=False)
    pasos = a.epocas * math.ceil(len(filas) / a.lote); calienta = max(10, pasos // 20)
    opt = optim.AdamW(learning_rate=optim.join_schedules([optim.linear_schedule(0.0, a.lr, calienta), optim.cosine_decay(a.lr, pasos - calienta)], [calienta]), weight_decay=0.0)
    def perdida(m, b, y):
        z, _ = m(**b); return -(y * nn.log_softmax(z, axis=-1)).sum(-1).mean()
    paso_fn = nn.value_and_grad(modelo, perdida); R = random.Random(5); t0 = time.time(); paso = 0; media = None
    print(f"   {len(filas)} ejemplos, {pasos} pasos", flush=True)
    for ep in range(a.epocas):
        R.shuffle(filas)
        for i in range(0, len(filas), a.lote):
            g = filas[i:i + a.lote]; b = {k: mx.array(v) for k, v in collate_items([f[0] for f in g], pad, max_length=largo).items()}; y = np.zeros(tuple(b["marker_pos"].shape), np.float32)
            for j, f in enumerate(g): y[j, :len(f[1])] = f[1]
            l, grads = paso_fn(modelo, b, mx.array(y)); grads, _ = optim.clip_grad_norm(grads, 1.0); opt.update(modelo, grads); mx.eval(modelo.parameters(), opt.state, l)
            paso += 1; media = float(l) if media is None else 0.98 * media + 0.02 * float(l)
            if paso % 100 == 0 or paso == 10: print(f"   paso {paso}/{pasos}  perdida {media:.4f}  {(time.time() - t0) / paso:.2f} s/paso  faltan {(pasos - paso) * (time.time() - t0) / paso / 60:.1f} min", flush=True)
            if a.pasos and paso >= a.pasos: break
        if a.pasos and paso >= a.pasos: break
    if a.prueba: print("   (prueba: no se guarda)"); return
    if os.path.isdir(DESTINO): shutil.rmtree(DESTINO)
    os.makedirs(DESTINO); [shutil.copytree(os.path.join(ORIGEN, d), os.path.join(DESTINO, d)) for d in ("encoder", "tokenizer")]; shutil.copy(os.path.join(ORIGEN, "mlx_config.json"), DESTINO)
    cfg = json.load(open(os.path.join(ORIGEN, "rl_agent_config.json")))
    cfg["temperature_by_options"]["noul:2"] = 1.0; cfg["temperature_by_options"]["score:3-5"] = 1.0   # trained at temperature 1 on her questions
    cfg["de_ella"] = {"fecha": time.strftime("%Y-%m-%d"), "origen": "laya-typed-decisions-mlx", "datos": json.load(open(os.path.join(EX.SALIDA, "efectos.json")))["fuentes"], "muestra": info, "pasos": paso, "lr": a.lr, "script": "pruebas_laya/laya_de_ella.py"}
    json.dump(cfg, open(os.path.join(DESTINO, "rl_agent_config.json"), "w"), indent=2)
    mx.save_safetensors(os.path.join(DESTINO, "model.safetensors"), {k: v.astype(mx.float16) for k, v in tree_flatten(modelo.parameters())})
    print(f"   guardada en {DESTINO} ({(time.time() - t0) / 60:.1f} min)", flush=True)

def medir(n=None):
    """The original and hers through the path production uses (laya.load(...).predict), on the visits kept out of training."""
    import laya_mlx as laya
    F = EX.muestra_mide(n); salida = {}
    for nombre, ruta in (("Laya original", ORIGEN), ("Laya de ella", DESTINO)):
        if not os.path.isdir(ruta): continue
        ag = laya.load(ruta); t0 = time.time(); resp = []
        for f in F:
            r = ag.predict(PRE + f["texto"], Q)["answers"]
            resp.append({k: (int(max(r[k]["probabilities"], key=r[k]["probabilities"].get)) if Q[k]["type"] == "score" else r[k]["noul"]) for k in CLAVES})
        salida[nombre] = {"ms": 1000 * (time.time() - t0) / len(F), "tabla": EX.informe(f"{nombre}  [{1000 * (time.time() - t0) / len(F):.0f} ms por situacion]", F, resp), "resp": resp}
    json.dump(salida, open(SALIDA, "w"), ensure_ascii=False); print("   ->", SALIDA)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--medir", action="store_true"); ap.add_argument("--prueba", action="store_true")
    ap.add_argument("--todo", type=int, default=7000); ap.add_argument("--eng", type=int, default=12000); ap.add_argument("--solo", type=int, default=1000)
    ap.add_argument("--epocas", type=int, default=1); ap.add_argument("--lote", type=int, default=32); ap.add_argument("--lr", type=float, default=1.5e-5); ap.add_argument("--suave", type=float, default=0.03); ap.add_argument("--pasos", type=int, default=0)
    a = ap.parse_args()
    if not a.medir: entrenar(a)
    if not a.prueba: medir()
