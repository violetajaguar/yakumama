#!/usr/bin/env python3
"""ojo_ofrendas.py - el ojo de las manos: reconoce cual de las 29 ofrendas (o manos vacias, otras cosas, su hermana) tiene la persona.

Como ve: busca la mano (MediaPipe Hands), recorta un cuadrado ajustado alrededor (la criatura asoma entre los dedos, asi
que la mano fija la escala: de cerca o a un metro el recorte se ve igual), lo pasa por DINOv2 (ViT-S/14, 384 dims; o
MobileNetV3 si el clasificador se entreno con el) y una regresion logistica entrenada con entrenar_ofrendas.py sobre
ofrendas_fotos/ dice la clase. Sin mano a la vista mira el centro del cuadro entero (asi ve a la hermana sobre la mesa).

    from ojo_ofrendas import Ojo
    ojo = Ojo(); v = ojo.ver(cuadro_rgb)
    v = {"clase": "03_saltamontes_verde", "p": 0.91, "id": 3, "nombre": "saltamontes verde (...)", "tipo": "insecto",
         "reaccion": {"n": 4, "texto": "Empieza a saltar"}, "boca": "pez", "mano": 1, "caja": [x, y, lado], "color": [r, g, b]}
    boca: "pez" = una de las 29 ofrendas (ella la acepta), "no_pez" = otra cosa en la mano, "nada" = manos vacias, nada, o duda.
    (se mantiene el nombre pez|no_pez|nada que ya usan decisiones.py y el cerebro; la criatura exacta va en clase/id/reaccion)

Prueba con la camara de la Mac o con fotos:   venv/bin/python ojo_ofrendas.py [--camara 0 | --fotos ofrendas_fotos/05_flor_amarilla]
DINOv2 se baja una vez por torch.hub (~85 MB) a ~/.cache/torch/hub; despues no hace falta internet.
"""
import os, json, pickle, time
import numpy as np, cv2

AQUI = os.path.dirname(os.path.abspath(__file__))
EMBEDDER_MOBILENET = os.path.join(AQUI, "modelos", "mobilenet_v3_large_embedder.tflite")
CLASIFICADOR = os.path.join(AQUI, "modelos", "ofrendas_clf.pkl")
CATALOGO = os.path.join(AQUI, "docs", "ofrendas", "ofrendas.json")
LADO = 224          # lo que ve la red
PAD = 1.35          # cuadrado = PAD x la caja de la mano (ajustado: la mano manda la escala)
MINIMO = 96         # px: por debajo de esto la mano esta demasiado lejos para ver que tiene
NO_OFRENDA = ("manos_vacias", "otras_cosas", "hermana_dorada")


def _silencio():
    os.environ.setdefault("GLOG_minloglevel", "2"); os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


class Recorte:
    """la mano y el cuadrado que la rodea. hands=None crea su propio MediaPipe Hands."""
    def __init__(self, hands=None, estatico=False):
        _silencio(); import mediapipe as mp
        self.mp = mp; self.ultima = None
        self.hands = hands or mp.solutions.hands.Hands(static_image_mode=estatico, max_num_hands=2, model_complexity=1, min_detection_confidence=0.3, min_tracking_confidence=0.3)

    def mano(self, rgb):
        """(cx, cy, tam) de la(s) mano(s) en px, o None si no hay mano. Queda tambien en self.ultima."""
        h, w = rgb.shape[:2]; r = self.hands.process(rgb); self.ultima = None
        if not r.multi_hand_landmarks: return None
        xs = [l.x * w for hl in r.multi_hand_landmarks for l in hl.landmark]; ys = [l.y * h for hl in r.multi_hand_landmarks for l in hl.landmark]
        self.ultima = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(max(xs) - min(xs), max(ys) - min(ys)))
        return self.ultima

    def caja(self, rgb, pad=PAD):
        """[x, y, lado] del cuadrado alrededor de la(s) mano(s), o None si no hay mano."""
        m = self.mano(rgb); return self.cuadrado(rgb, *m, pad=pad) if m else None

    @staticmethod
    def cuadrado(rgb, cx, cy, tam, pad=PAD):
        h, w = rgb.shape[:2]; lado = int(min(max(tam * pad, MINIMO), min(h, w)))
        x = int(min(max(cx - lado / 2, 0), w - lado)); y = int(min(max(cy - lado / 2, 0), h - lado))
        return [x, y, lado]

    @staticmethod
    def centro(rgb):
        h, w = rgb.shape[:2]; lado = min(h, w); return [(w - lado) // 2, (h - lado) // 2, lado]

    @staticmethod
    def cortar(rgb, caja, espejo=False, lejos=0):
        """recorte LADO x LADO. lejos=N: antes lo baja a N px y lo vuelve a subir (asi se ve una mano a un metro: menos detalle)."""
        x, y, l = caja; c = rgb[y:y + l, x:x + l]
        if lejos and lejos < l: c = cv2.resize(c, (lejos, lejos), interpolation=cv2.INTER_AREA)
        c = cv2.resize(c, (LADO, LADO), interpolation=cv2.INTER_AREA if c.shape[0] > LADO else cv2.INTER_LINEAR)
        return np.ascontiguousarray(c[:, ::-1]) if espejo else c


class _Dino:
    """DINOv2 ViT-S/14 (384 dims) por torch.hub; en la GPU de la Mac (mps) si hay."""
    dims = 384
    def __init__(self):
        import torch; self.torch = torch
        self.dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        self.m = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14", verbose=False).eval().to(self.dev)
        self.media = torch.tensor([0.485, 0.456, 0.406], device=self.dev).view(1, 3, 1, 1); self.desv = torch.tensor([0.229, 0.224, 0.225], device=self.dev).view(1, 3, 1, 1)
    def __call__(self, recortes):
        t = self.torch
        with t.no_grad():
            x = t.from_numpy(np.stack(recortes)).to(self.dev).permute(0, 3, 1, 2).float() / 255.0
            f = t.nn.functional.normalize(self.m((x - self.media) / self.desv), dim=1)
        return f.cpu().numpy().astype(np.float32)


class _Mobilenet:
    """MobileNetV3 large de MediaPipe (1280 dims), CPU, 4 ms."""
    dims = 1280
    def __init__(self):
        _silencio(); import mediapipe as mp
        from mediapipe.tasks import python as mpp; from mediapipe.tasks.python import vision
        self.mp = mp
        self.e = vision.ImageEmbedder.create_from_options(vision.ImageEmbedderOptions(base_options=mpp.BaseOptions(model_asset_path=EMBEDDER_MOBILENET), l2_normalize=True))
    def __call__(self, recortes):
        return np.stack([np.asarray(self.e.embed(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(r))).embeddings[0].embedding, dtype=np.float32) for r in recortes])


class _Color:
    """histograma HSV de los pixeles saturados del centro del recorte (lo pintado, no la piel ni la pared): 16 matices x 2 saturaciones x 2 brillos = 64."""
    dims = 64
    def __call__(self, recortes):
        out = []
        for r in recortes:
            c = r[LADO // 6: -LADO // 6, LADO // 6: -LADO // 6]; hsv = cv2.cvtColor(np.ascontiguousarray(c), cv2.COLOR_RGB2HSV)
            m = (hsv[..., 1] > 90) & (hsv[..., 2] > 60); m &= ~((hsv[..., 0] >= 3) & (hsv[..., 0] <= 22) & (hsv[..., 1] < 150))   # fuera la piel (naranja palido)
            h = cv2.calcHist([hsv], [0, 1, 2], m.astype(np.uint8), [16, 2, 2], [0, 180, 90, 256, 60, 256]).flatten().astype(np.float32)
            n = h.sum(); out.append(h / n if n > 0 else h)
        return np.stack(out)


BLOQUES = {"dino": _Dino, "mobilenet": _Mobilenet, "color": _Color}


class Rasgos:
    """embedding de recortes 224x224 RGB. nombre: 'dino', 'mobilenet', 'color' o combinaciones 'dino+color' (bloques concatenados,
    cada uno normalizado; 'color' entra multiplicado por peso_color). __call__(lista de recortes) -> (n, dims) float32."""
    def __init__(self, nombre="dino+color", peso_color=1.0):
        self.nombre = nombre; self.peso_color = peso_color; self.bloques = [(b, BLOQUES[b]()) for b in nombre.split("+")]
        self.dims = sum(x.dims for _, x in self.bloques)

    def __call__(self, recortes):
        partes = []
        for b, x in self.bloques:
            f = x(recortes); f = f / np.maximum(np.linalg.norm(f, axis=1, keepdims=True), 1e-6)
            partes.append(f * (self.peso_color if b == "color" else 1.0))
        return np.concatenate(partes, axis=1).astype(np.float32)


class Ojo:
    """ver(cuadro_rgb) -> dict con clase, p, id, nombre, tipo, reaccion, boca, mano, caja. Carga el clasificador de modelos/ofrendas_clf.pkl."""
    def __init__(self, clasificador=CLASIFICADOR, catalogo=CATALOGO, minimo_p=0.5, hands=None):
        with open(clasificador, "rb") as fh: m = pickle.load(fh)
        self.clf, self.clases, self.espejo, self.pad = m["clf"], list(m["clases"]), bool(m.get("espejo", True)), float(m.get("pad", PAD))
        self.rec = Recorte(hands=hands); self.rasgos = Rasgos(m.get("rasgos", "dino"), float(m.get("peso_color", 1.0))); self.minimo_p = minimo_p
        cat = json.load(open(catalogo)) if os.path.exists(catalogo) else {"criaturas": []}
        self.criaturas = {c.get("carpeta") or c["archivo"][:-4]: c for c in cat["criaturas"]}

    @staticmethod
    def color_criatura(recorte):
        """[r, g, b] 0..1 del color pintado dominante en el recorte (pixeles saturados que no son piel), o None."""
        c = recorte[LADO // 8: -LADO // 8, LADO // 8: -LADO // 8]; hsv = cv2.cvtColor(np.ascontiguousarray(c), cv2.COLOR_RGB2HSV)
        m = (hsv[..., 1] > 120) & (hsv[..., 2] > 120) & ~((hsv[..., 0] >= 0) & (hsv[..., 0] <= 22) & (hsv[..., 1] < 190))   # pintado y vivo; fuera piel, madera, pelo (naranja/rojo apagado)
        if m.sum() < 40: return None
        hist = np.bincount(hsv[..., 0][m] // 10, minlength=18); k = int(np.argmax(hist)); sel = m & (hsv[..., 0] // 10 == k)
        return [round(float(v) / 255.0, 3) for v in np.median(c[sel].reshape(-1, 3), axis=0)]

    def ver(self, rgb):
        caja = self.rec.caja(rgb, pad=self.pad); mano = caja is not None
        if not mano: caja = Recorte.centro(rgb)
        vistas = [Recorte.cortar(rgb, caja)] + ([Recorte.cortar(rgb, caja, espejo=True)] if self.espejo else [])
        pr = self.clf.predict_proba(self.rasgos(vistas)).mean(0); k = int(np.argmax(pr)); clase = self.clases[k]; p = float(pr[k])
        v = {"clase": clase, "p": round(p, 3), "mano": int(mano), "caja": caja, "id": None, "nombre": clase, "tipo": None, "reaccion": None, "boca": "nada", "color": self.color_criatura(vistas[0])}
        if p < self.minimo_p: v["clase"] = "duda"; return v
        if clase == "otras_cosas": v["boca"] = "no_pez"
        elif clase not in NO_OFRENDA and clase in self.criaturas:
            c = self.criaturas[clase]; v.update(id=c["id"], nombre=c["nombre"], tipo=c.get("tipo"), reaccion=c.get("reaccion"), boca="pez")
        return v


if __name__ == "__main__":
    import argparse, glob
    ap = argparse.ArgumentParser(); ap.add_argument("--camara", type=int, default=0); ap.add_argument("--fotos", default=""); a = ap.parse_args()
    ojo = Ojo()
    if a.fotos:
        for f in sorted(glob.glob(os.path.join(a.fotos, "*.jpg")))[:40]:
            v = ojo.ver(cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB)); print(f"{os.path.basename(f)}  {v['clase']:32s} p={v['p']:.2f} mano={v['mano']}  -> {v['boca']}  {(v['reaccion'] or {}).get('texto', '')}")
    else:
        cap = cv2.VideoCapture(a.camara)
        while True:
            ok, bgr = cap.read()
            if not ok: break
            t = time.time(); v = ojo.ver(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)); ms = (time.time() - t) * 1000
            x, y, l = v["caja"]; cv2.rectangle(bgr, (x, y), (x + l, y + l), (0, 255, 0) if v["mano"] else (0, 160, 255), 2)
            cv2.putText(bgr, f"{v['clase']} {v['p']:.2f} ({ms:.0f} ms)  {(v['reaccion'] or {}).get('texto', '')}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow("ojo de las manos", bgr)
            if cv2.waitKey(1) & 0xFF == ord("q"): break
