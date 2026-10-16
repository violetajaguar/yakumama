#!/usr/bin/env python3
"""yakumama_jepa.py - el JEPA de la ballena en NumPy puro (para Blender, TouchDesigner, la ballena fisica).

Pesos: modelos/jepa_pesos.npz (de jepa_entrenar.py). Mismas cuentas que alli.

    from yakumama_jepa import Jepa
    j = Jepa("modelos/jepa_pesos.npz")
    futuro = j.predecir(contexto, animo="playful")     # contexto: lista de hasta 48 dicts {canal: valor} (12/s); faltantes se omiten
    # futuro: lista de 24 dicts (los 2 s siguientes), en unidades originales
    j.generar("angry", segundos=20, actor_estilo=None)  # encadena predicciones: una actuacion que no se repite

Canales (24): head_yaw head_pitch jaw_open blink brow_up brow_down mouth_sad mouth_smile eye_yaw eye_pitch
l_palm_y r_palm_y l_palm_x r_palm_x mano_l mano_r hr eda | cuerpo_pitch cuerpo_roll cuerpo_yaw cuerpo_profundidad
cuerpo_energia cuerpo_suavidad. hr y eda vienen normalizados como en entrenar_movimiento ((hr-85)/30, eda/10).
"""
import os, numpy as np
MOODS = ["calm","singing","playful","curious","feeding","sad","angry","alert","diving","surfacing"]
def _gelu(x): return 0.5 * x * (1 + np.tanh(0.7978845608 * (x + 0.044715 * x ** 3)))
def _conv1d(x, W, b, stride=1, pad=0):
    """x: (Cin, L); W: (Cout, Cin, k)"""
    Cout, Cin, k = W.shape; xp = np.pad(x, ((0, 0), (pad, pad))); L = (xp.shape[1] - k) // stride + 1
    cols = np.stack([xp[:, i * stride:i * stride + k] for i in range(L)], 0)   # (L, Cin, k)
    return (cols.reshape(L, -1) @ W.reshape(Cout, -1).T + b).T                 # (Cout, L)
class Jepa:
    def __init__(self, ruta="modelos/jepa_pesos.npz"):
        z = np.load(ruta, allow_pickle=True); self.w = {k: z[k] for k in z.files}
        self.canales = [str(c) for c in z["canales"]]; self.NC = len(self.canales); self.media = z["media"]; self.desvio = z["desvio"]; self.C = int(z["C"]); self.T = int(z["T"])
    def _enc(self, pref, x, m):
        h = np.concatenate([x, m], 1).T   # (2NC, L)
        h = _gelu(_conv1d(h, self.w[f"{pref}.c1.weight"], self.w[f"{pref}.c1.bias"], 1, 2))
        h = _gelu(_conv1d(h, self.w[f"{pref}.c2.weight"], self.w[f"{pref}.c2.bias"], 2, 2))
        h = _gelu(_conv1d(h, self.w[f"{pref}.c3.weight"], self.w[f"{pref}.c3.bias"], 2, 1))
        if f"{pref}.fc.weight" in self.w and self.w[f"{pref}.fc.weight"].shape[1] == h.shape[0] * 6:   # pool adaptativo a 6 posiciones (LeJEPA)
            L = h.shape[1]; h = np.stack([h[:, (i * L) // 6:max((i * L) // 6 + 1, ((i + 1) * L + 5) // 6)].mean(1) for i in range(6)], 1)
        return h.flatten() @ self.w[f"{pref}.fc.weight"].T + self.w[f"{pref}.fc.bias"]
    def _mlp(self, pref, v, capas):
        for i in capas: v = v @ self.w[f"{pref}.net.{i}.weight"].T + self.w[f"{pref}.net.{i}.bias"]; v = _gelu(v) if i != capas[-1] else v
        return v
    def _matriz(self, contexto):
        """contexto: lista de dicts -> (C, NC) normalizado y mascara, rellenando por la izquierda si hay menos de C"""
        x = np.zeros((self.C, self.NC), np.float32); m = np.zeros((self.C, self.NC), np.float32); ctx = contexto[-self.C:]
        for i, r in enumerate(ctx):
            fila = self.C - len(ctx) + i
            for j, c in enumerate(self.canales):
                if r.get(c) is not None: x[fila, j] = (float(r[c]) - self.media[j]) / self.desvio[j]; m[fila, j] = 1.0
        if len(ctx) < self.C and len(ctx): x[:self.C - len(ctx)] = x[self.C - len(ctx)]; m[:self.C - len(ctx)] = m[self.C - len(ctx)]
        return x, m
    def predecir(self, contexto, animo=None, pedir=None):
        """los 24 cuadros siguientes. pedir: lista de canales que se quieren (por defecto los que trae el contexto)."""
        x, m = self._matriz(contexto); an = np.zeros(10, np.float32)
        if animo in MOODS: an[MOODS.index(animo)] = 1.0
        mt = np.array([1.0 if (pedir is None and m[-1, j] > 0) or (pedir and c in pedir) else 0.0 for j, c in enumerate(self.canales)], np.float32)
        u = np.concatenate([x[-1] * m[-1], m[-1]]); zc = self._enc("enc", x, m)
        zp = self._mlp("pred", np.concatenate([zc, u, an, mt]), (0, 3, 6))
        d = self._mlp("dec", np.concatenate([zp, u, an]), (0, 3, 6)).reshape(self.T, self.NC) + (x[-1] * m[-1])[None, :]
        vals = d * self.desvio + self.media
        return [{c: float(vals[t, j]) for j, c in enumerate(self.canales) if mt[j] > 0} for t in range(self.T)]
    def generar(self, animo, segundos=20.0, semilla=None, canales=None):
        """encadena predicciones de 2 s: una actuacion continua del animo (12 cuadros/s). semilla: contexto inicial (dicts)."""
        canales = canales or [c for c in self.canales if not c.startswith("cuerpo_") and c not in ("hr", "eda")]
        ctx = list(semilla) if semilla else [{c: float(self.media[j]) for j, c in enumerate(self.canales) if c in canales} for _ in range(self.C)]
        out = []
        while len(out) < int(segundos * 12):
            fut = self.predecir(ctx, animo, pedir=canales); out += fut; ctx = (ctx + fut)[-self.C:]
        return out[:int(segundos * 12)]
if __name__ == "__main__":
    import sys, json
    j = Jepa(os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelos", "jepa_pesos.npz")); animo = sys.argv[1] if len(sys.argv) > 1 else "playful"
    g = j.generar(animo, 6); print(f"{animo}: {len(g)} cuadros generados; primeros valores:", json.dumps({k: round(v, 3) for k, v in g[0].items()}))
    import statistics as st; print("desvio por canal en 6 s:", {c: round(st.pstdev([r[c] for r in g if c in r]), 3) for c in list(g[0])[:8]})
