#!/usr/bin/env python3
"""importar_cmu.py - nadadores REALES de la CMU Motion Capture Database (sujetos 125 y 126, "Swimming": Vicon, 120 Hz,
actores haciendo las brazadas en seco): pecho, espalda, mariposa y crol. Formato ASF/AMC, leido aqui a mano (esqueleto +
angulos por cuadro, cinematica directa) al esqueleto de 26 puntos de Paqarina. Los archivos se bajan de
mocap.cs.cmu.edu/subjects/<s>/<s>.asf y <s>_<nn>.amc (uso libre, se agradece la mencion a la CMU).

Salen como datasets/cuerpo_video/swim_cmu_<estilo>_<s>_<nn>.npz: por la regla de jepa_datos, mariposa y crol entran como
SURFACING (el cuerpo sale del agua a cada brazada) y pecho y espalda como FEEDING.

    venv_datos/bin/python importar_cmu.py ~/Desktop/cmu_nado
"""
import os, sys, glob, re, math, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
ESTILO = {"125_01": "breaststroke", "125_02": "breaststroke", "125_03": "breaststroke", "125_04": "breaststroke", "125_05": "butterfly", "125_06": "freestyle",
          "126_01": "backstroke", "126_02": "backstroke", "126_03": "breaststroke", "126_04": "breaststroke", "126_05": "breaststroke", "126_06": "butterfly", "126_07": "butterfly", "126_08": "butterfly", "126_09": "butterfly", "126_10": "freestyle", "126_11": "freestyle", "126_12": "freestyle"}
NOMBRES = ["nose", "eye_l", "eye_r", "ear_l", "ear_r", "shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "wrist_l", "wrist_r", "hip_l", "hip_r", "knee_l", "knee_r", "ankle_l", "ankle_r", "head", "neck", "pelvis", "bigtoe_l", "bigtoe_r", "smalltoe_l", "smalltoe_r", "heel_l", "heel_r"]
# punto de Paqarina -> (hueso de la CMU, "ini" = donde empieza, "fin" = donde termina)
MAPA = {"pelvis": ("root", "ini"), "neck": ("lowerneck", "ini"), "head": ("head", "fin"), "nose": ("head", "fin"), "shoulder_l": ("lhumerus", "ini"), "shoulder_r": ("rhumerus", "ini"), "elbow_l": ("lhumerus", "fin"), "elbow_r": ("rhumerus", "fin"),
        "wrist_l": ("lradius", "fin"), "wrist_r": ("rradius", "fin"), "hip_l": ("lfemur", "ini"), "hip_r": ("rfemur", "ini"), "knee_l": ("lfemur", "fin"), "knee_r": ("rfemur", "fin"), "ankle_l": ("ltibia", "fin"), "ankle_r": ("rtibia", "fin"),
        "bigtoe_l": ("ltoes", "fin"), "bigtoe_r": ("rtoes", "fin"), "heel_l": ("ltibia", "fin"), "heel_r": ("rtibia", "fin")}
def rot(ax, deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]), "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[ax]
def euler(angs, orden):   # ASF: la rotacion se aplica en el orden dado (p. ej. XYZ -> Rz . Ry . Rx)
    R = np.eye(3)
    for ax, a in zip(orden, angs): R = rot(ax, a) @ R
    return R
def leer_asf(ruta):
    txt = open(ruta).read(); huesos = {}; hijos = {}
    esc = 1.0 / float(re.search(r"length\s+([\d.]+)", txt).group(1)) * 0.0254   # 1/0.45 -> pulgadas -> metros
    raiz = re.search(r":root(.*?):bonedata", txt, re.S).group(1); orden_raiz = re.search(r"order\s+(.*)", raiz).group(1).split(); axis_raiz = re.search(r"axis\s+(\w+)", raiz).group(1).lower()
    huesos["root"] = dict(dir=np.zeros(3), largo=0.0, C=np.eye(3), dof=[d.lower() for d in orden_raiz], padre=None)
    for b in re.finditer(r"begin(.*?)end", re.search(r":bonedata(.*?):hierarchy", txt, re.S).group(1), re.S):
        t = b.group(1); nombre = re.search(r"name\s+(\S+)", t).group(1); d = np.array([float(x) for x in re.search(r"direction\s+(.*)", t).group(1).split()])
        largo = float(re.search(r"length\s+([\d.e+-]+)", t).group(1)) * esc; ax = re.search(r"axis\s+(.*)", t).group(1).split(); angs = [float(x) for x in ax[:3]]; orden = ax[3].lower() if len(ax) > 3 else "xyz"
        m = re.search(r"dof\s+(.*)", t); dof = [x.lower() for x in m.group(1).split()] if m else []
        huesos[nombre] = dict(dir=d / (np.linalg.norm(d) + 1e-9), largo=largo, C=euler(angs, orden), dof=dof, padre=None)
    for linea in re.search(r":hierarchy\s*begin(.*?)end", txt, re.S).group(1).strip().splitlines():
        p = linea.split()
        if len(p) > 1:
            for h in p[1:]: huesos[h]["padre"] = p[0]
    return huesos, esc
def leer_amc(ruta):
    cuadros = []; actual = None
    for linea in open(ruta):
        linea = linea.strip()
        if not linea or linea.startswith("#") or linea.startswith(":"): continue
        if linea.isdigit(): actual = {}; cuadros.append(actual); continue
        p = linea.split(); actual[p[0]] = [float(x) for x in p[1:]]
    return cuadros
def fk(huesos, esc, cuadro):
    pos = {}; R = {}
    r = cuadro.get("root", [0] * 6); dof = huesos["root"]["dof"]; t = np.zeros(3); angs = {"rx": 0, "ry": 0, "rz": 0}
    for k, v in zip(dof, r):
        if k in ("tx", "ty", "tz"): t["xyz".index(k[1])] = v * esc
        else: angs[k] = v
    R["root"] = euler([angs["rx"], angs["ry"], angs["rz"]], "xyz"); pos["root"] = (t, t)
    orden = [n for n in huesos if n != "root"]; pendientes = list(orden)
    while pendientes:
        for n in list(pendientes):
            h = huesos[n]; p = h["padre"]
            if p not in R: continue
            angs = {"rx": 0, "ry": 0, "rz": 0}
            for k, v in zip(h["dof"], cuadro.get(n, [])): angs[k] = v
            Rl = h["C"] @ euler([angs["rx"], angs["ry"], angs["rz"]], "xyz") @ h["C"].T
            R[n] = R[p] @ Rl; ini = pos[p][1]; fin = ini + R[n] @ (h["dir"] * h["largo"]); pos[n] = (ini, fin); pendientes.remove(n)
    return pos
def importar(carpeta, cada=5):
    sal = os.path.join(AQUI, "datasets", "cuerpo_video"); os.makedirs(sal, exist_ok=True); total = 0
    for amc in sorted(glob.glob(os.path.join(carpeta, "*.amc"))):
        clave = os.path.basename(amc)[:-4]; estilo = ESTILO.get(clave)
        if not estilo: continue
        huesos, esc = leer_asf(os.path.join(carpeta, clave.split("_")[0] + ".asf")); cuadros = leer_amc(amc)[::cada]; fps = 120.0 / cada
        B = np.full((len(cuadros), len(NOMBRES), 3), np.nan)
        for i, c in enumerate(cuadros):
            pos = fk(huesos, esc, c)
            for k, nombre in enumerate(NOMBRES):
                if nombre in MAPA:
                    hueso, lado = MAPA[nombre]
                    if hueso in pos: B[i, k] = pos[hueso][0 if lado == "ini" else 1]
        B = B[:, :, [0, 2, 1]] * np.array([1, -1, 1])   # CMU: y arriba -> z arriba
        np.savez_compressed(os.path.join(sal, f"swim_cmu_{estilo}_{clave}.npz"), body=B.astype(np.float32), joint_names=np.array(NOMBRES), fps=fps, origen="cmu", archivo=os.path.basename(amc))
        total += len(B) / fps; print(f"  {clave} {estilo:12s} {len(B) / fps:5.1f} s | cabeza-pelvis z {np.nanmean(B[:, NOMBRES.index('head'), 2] - B[:, NOMBRES.index('pelvis'), 2]):+.2f} m")
    print(f"importados {total / 60:.1f} min de nado real (CMU 125/126) -> datasets/cuerpo_video/swim_cmu_*")
if __name__ == "__main__": importar(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/cmu_nado"))
