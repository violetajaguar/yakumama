#!/usr/bin/env python3
"""memoria.py - la memoria de Yakumama: a quien conoce, sin fotos.

Una persona se recuerda por una FIRMA: las distancias 3D entre 21 puntos de la malla de la cara (ojos, nariz, boca,
menton, mejillas, frente, cejas, mandibula) normalizadas por la distancia entre los ojos, tomadas en cuadros con la
cara tranquila (boca cerrada, sin sonrisa, sin parpadeo) y promediadas por mediana en el encuentro. Son 210 numeros
que no se pueden volver imagen. La memoria vive en datasets/memoria.json, solo en esta Mac, y cada persona se puede
olvidar (boton Olvidar en el panel del grabador, o Memoria().olvidar(id)).

Lo que guarda de cada persona: cuantas veces vino, cuando, con que estilo le contesto la ballena, que animos trajo,
su pulso medio, y los archivos de sus encuentros (datasets/visitas/).
"""
import json, os, time, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(AQUI, "datasets", "memoria.json")
# indices de la malla de MediaPipe (478 puntos): puntos estables de la cara
PUNTOS = [33, 133, 362, 263, 1, 6, 2, 98, 327, 61, 291, 13, 14, 152, 234, 454, 10, 105, 334, 172, 397]
OJO_IZQ, OJO_DER = 33, 263
UMBRAL = 0.025      # distancia media por debajo de la cual es la misma persona (se calibra con gente conocida)
MIN_CUADROS = 25    # cuadros tranquilos necesarios para tener una firma
def firma_cuadro(puntos):
    """puntos: lista de 478 (x, y, z). Devuelve 210 distancias normalizadas o None."""
    try:
        P = np.array([[puntos[i].x, puntos[i].y, puntos[i].z] for i in PUNTOS], np.float32)
        ojos = float(np.linalg.norm(P[PUNTOS.index(OJO_IZQ)] - P[PUNTOS.index(OJO_DER)]))
        if ojos < 1e-4: return None
        D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2) / ojos
        iu = np.triu_indices(len(PUNTOS), 1); return D[iu]
    except Exception: return None
def cara_tranquila(bs):
    """bs: blendshapes {nombre: valor}. True si la cara esta relajada (la firma no debe depender del gesto)."""
    return (bs.get("jawOpen", 0) < 0.25 and bs.get("mouthSmileLeft", 0) < 0.3 and bs.get("mouthSmileRight", 0) < 0.3
            and bs.get("eyeBlinkLeft", 0) < 0.5 and bs.get("eyeBlinkRight", 0) < 0.5 and bs.get("mouthPucker", 0) < 0.4)
def firma_encuentro(cuadros):
    """mediana de las firmas de cuadro de un encuentro (lista de vectores) o None si hay pocos."""
    if len(cuadros) < MIN_CUADROS: return None
    return np.median(np.array(cuadros, np.float32), axis=0)
def distancia(a, b): return float(np.mean(np.abs(np.asarray(a, np.float32) - np.asarray(b, np.float32))))
class Memoria:
    def __init__(self, archivo=ARCHIVO):
        self.archivo = archivo; self.personas = {}
        try: self.personas = json.load(open(archivo))
        except Exception: self.personas = {}
    def guardar(self):
        os.makedirs(os.path.dirname(self.archivo), exist_ok=True)
        tmp = self.archivo + ".tmp"; json.dump(self.personas, open(tmp, "w"), ensure_ascii=False, indent=1); os.replace(tmp, self.archivo)
    def buscar(self, firma):
        """(id, distancia) de la persona mas parecida, o (None, distancia) si nadie esta bajo el umbral."""
        mejor, dmin = None, 9e9
        for pid, p in self.personas.items():
            d = distancia(firma, p["firma"])
            if d < dmin: mejor, dmin = pid, d
        return (mejor if dmin < UMBRAL else None), dmin
    def registrar(self, firma, estilo=None, animos=None, pulso=None, archivo=None, pid=None):
        """suma un encuentro a una persona conocida (pid) o crea una nueva. Devuelve el id."""
        ahora = time.strftime("%Y-%m-%d %H:%M")
        if pid is None or pid not in self.personas:
            pid = f"v{len(self.personas) + 1:04d}"
            self.personas[pid] = {"firma": [round(float(x), 5) for x in firma], "visitas": 0, "primera": ahora, "ultima": ahora, "estilo": None, "animos": {}, "pulso": None, "encuentros": []}
        p = self.personas[pid]; p["visitas"] += 1; p["ultima"] = ahora
        # la firma se afina con cada visita (media movil), para que una cara cambie despacio con la memoria
        p["firma"] = [round(float(0.8 * a + 0.2 * b), 5) for a, b in zip(p["firma"], firma)]
        if estilo: p["estilo"] = estilo
        for a, n in (animos or {}).items(): p["animos"][a] = p["animos"].get(a, 0) + n
        if pulso: p["pulso"] = round(float(pulso) if not p["pulso"] else 0.7 * p["pulso"] + 0.3 * float(pulso), 1)
        if archivo: p["encuentros"] = (p["encuentros"] + [archivo])[-50:]
        self.guardar(); return pid
    def olvidar(self, pid):
        """borra a la persona de la memoria (y sus encuentros guardados)."""
        p = self.personas.pop(pid, None)
        if p:
            for f in p.get("encuentros", []):
                try: os.remove(os.path.join(AQUI, "datasets", "visitas", f))
                except Exception: pass
            self.guardar()
        return p is not None
    def resumen(self):
        return {pid: {"visitas": p["visitas"], "ultima": p["ultima"], "estilo": p["estilo"], "animos": p["animos"], "pulso": p["pulso"]} for pid, p in self.personas.items()}
if __name__ == "__main__":
    import sys
    m = Memoria()
    if len(sys.argv) > 2 and sys.argv[1] == "olvidar": print("olvidada" if m.olvidar(sys.argv[2]) else "no estaba", sys.argv[2])
    else:
        print(f"{len(m.personas)} personas en la memoria")
        for pid, p in m.resumen().items(): print(f"  {pid}: {p['visitas']} visitas, ultima {p['ultima']}, estilo {p['estilo']}, animos {p['animos']}, pulso {p['pulso']}")
