"""figuras_nazca.py - the figures she draws on the salar, shared by Blender (dibujo_salar.py) and the brain (cerebro_ballena.py -> TouchDesigner).
Each figure is a list of (x, y, pen_down) in units of the drawing radius (-1..1); pen_down False = fly there without drawing (a new stroke).
Figures: espiral (square spiral), zigzag, laberinto (hexagonal labyrinth, like the plotter video), ballena (the Nazca whale), and
cara(firma): THE FACE OF SOMEONE SHE REMEMBERS, recovered by classical multidimensional scaling from the 210 distances between 21 face
points that her memory keeps (memoria.py; never an image), drawn as eight straight strokes in that person's proportions."""
import math, random
PUNTOS = [33, 133, 362, 263, 1, 6, 2, 98, 327, 61, 291, 13, 14, 152, 234, 454, 10, 105, 334, 172, 397]   # memoria.py: the 21 face points
def _idx(p): return PUNTOS.index(p)
def espiral():
    pts = []; x = y = 0.0; paso = 0.12; d = 0
    for n in range(1, 17):
        dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][d % 4]; x += dx * paso * n; y += dy * paso * n; pts.append((x, y, n > 1)); d += 1
    m = max(max(abs(x), abs(y)) for x, y, _ in pts) or 1.0; return [(x / m, y / m, p) for x, y, p in pts]
def zigzag():
    pts = [(-1.0, -0.6, False)]
    for i in range(1, 11): pts.append((-1.0 + 0.2 * i, 0.6 if i % 2 else -0.6, True))
    return pts
def laberinto():
    pts = []
    for anillo in range(4, 0, -1):   # from the outside in, like the plotter
        r = anillo / 4.0; hueco = (anillo * 2) % 6
        esq = [(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k))) for k in range(6)]
        orden = [(hueco + 1 + k) % 6 for k in range(6)]   # start just after the gap, go round, stop before the gap
        pts.append((esq[orden[0]][0], esq[orden[0]][1], False))
        for k in orden[1:]: pts.append((esq[k][0], esq[k][1], True))
        if anillo > 1:   # the connector into the next ring through this ring's gap
            r2 = (anillo - 1) / 4.0; mid = math.radians(60 * hueco + 30)
            pts.append((r * 0.93 * math.cos(mid), r * 0.93 * math.sin(mid), True)); pts.append((r2 * math.cos(mid), r2 * math.sin(mid), True))
    return pts
def ballena():
    """the Nazca whale, as a few straight strokes: a long body, the fluke, a fin, an eye."""
    cuerpo = [(-1.0, 0.0), (-0.75, 0.22), (-0.3, 0.3), (0.3, 0.26), (0.75, 0.12), (1.0, 0.0), (0.75, -0.14), (0.3, -0.3), (-0.3, -0.3), (-0.75, -0.2), (-1.0, 0.0)]
    cola = [(-1.0, 0.0), (-1.25, 0.35), (-1.12, 0.0), (-1.25, -0.35), (-1.0, 0.0)]; aleta = [(0.15, -0.3), (0.05, -0.62), (0.4, -0.5)]; ojo = [(0.7, 0.03), (0.78, 0.09), (0.86, 0.03), (0.78, -0.03), (0.7, 0.03)]
    pts = []
    for trazo in (cuerpo, cola, aleta, ojo):
        pts.append((trazo[0][0] * 0.8, trazo[0][1] * 0.8, False)); pts += [(x * 0.8, y * 0.8, True) for x, y in trazo[1:]]
    return pts
def cara(firma):
    """the 210 distances -> 21 points (classical multidimensional scaling) -> 2D -> straight strokes: jaw, forehead, brows, eyes, nose, mouth."""
    import numpy as np
    n = 21; D = np.zeros((n, n), np.float64); iu = np.triu_indices(n, 1); D[iu] = firma; D = D + D.T
    J = np.eye(n) - np.ones((n, n)) / n; B = -0.5 * J @ (D ** 2) @ J; w, V = np.linalg.eigh(B); orden = np.argsort(w)[::-1][:3]
    X = V[:, orden] * np.sqrt(np.maximum(w[orden], 1e-9))
    # orient: chin -> forehead is +y, left eye at -x; flatten to the two axes with most spread (the face plane)
    X = X - X.mean(axis=0); U, S, Vt = np.linalg.svd(X, full_matrices=False); P = X @ Vt[:2].T
    arriba = P[_idx(10)] - P[_idx(152)]; ang = math.atan2(arriba[1], arriba[0]) - math.pi / 2; c, s_ = math.cos(-ang), math.sin(-ang)
    P = P @ np.array([[c, -s_], [s_, c]]).T
    if P[_idx(33)][0] > P[_idx(263)][0]: P[:, 0] *= -1
    esc = 0.9 / (np.abs(P).max() or 1.0); P = P * esc
    trazos = [[234, 172, 152, 397, 454], [454, 10, 234], [105, 6, 334], [33, 133], [362, 263], [6, 1, 2], [98, 2, 327], [61, 13, 291, 14, 61]]
    pts = []
    for tr in trazos:
        pts.append((float(P[_idx(tr[0])][0]), float(P[_idx(tr[0])][1]), False)); pts += [(float(P[_idx(k)][0]), float(P[_idx(k)][1]), True) for k in tr[1:]]
    return pts
FIGURAS = {"espiral": espiral, "zigzag": zigzag, "laberinto": laberinto, "ballena": ballena}

def elegir(nombre=None): return nombre if nombre in FIGURAS else random.choice(list(FIGURAS))
def puntos(nombre, firma=None, R=1.0):
    """the figure scaled to radius R; 'cara' needs the 210-distance firma (falls back to a random figure without it)."""
    if nombre == "cara" and firma is not None and len(firma) == 210: pts = cara(firma)
    else: pts = FIGURAS[elegir(nombre if nombre != "cara" else None)]()
    return [(x * R, y * R, p) for x, y, p in pts]
