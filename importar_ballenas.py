#!/usr/bin/env python3
"""importar_ballenas.py - ballenas REALES: de una etiqueta con acelerometro (DTAG / CATS, formato animaltags .nc) a los
seis canales de cuerpo que conducen a Yakumama (cuerpo_cualidades.CUERPO), a 12 cuadros/s.

De donde salen los archivos: github.com/animaltags/tagtools_data (ejemplos publicos de animaltags.org):
    mn12_186a_raw.nc  yubarta (humpback), 10 h, acelerometro 32 Hz, magnetometro/presion 1 Hz, marco de la etiqueta
    testset7.nc       yubarta mn18_175d, Cape Cod 2018, 3 h, 1 Hz, ya en el marco del animal
    zc11_267a.nc      zifio de Cuvier, 18 h, 5 Hz, con rumbo
Como se traducen (lo mismo que mide el esqueleto de un bailarin, pero medido en el cuerpo de una ballena de verdad):
    cuerpo_pitch        nariz abajo (+) / arriba (-): -pitch / 60 grados       (a2pr: pitch = asin(Ax/|A|))
    cuerpo_roll         ladeo: roll / 90 grados                               (roll = atan2(Ay, Az))
    cuerpo_yaw          cuanto gira: d(rumbo)/dt / 0.5 rad/s                  (rumbo del magnetometro, nivelado con la gravedad)
    cuerpo_profundidad  -tanh(profundidad / 15 m): 0 en superficie, -1 hondo
    cuerpo_energia      aceleracion dinamica (lo que no es gravedad), suavizada, 0..1 por el percentil 90
    cuerpo_suavidad     1 - potencia por encima de 3 Hz (una ballena es suave: ~1)
Si la etiqueta esta en su propio marco (frame=tag), se nivela con la gravedad mediana y se orienta el eje adelante con
la direccion principal del aleteo. Guarda datasets/ballenas/<id>.npz (X, M, fps, canales, y las series crudas en
radianes y metros) e imprime las medidas reales: cuanto dura un buceo, con que pitch baja y sube, cuanto rola.

    venv_datos/bin/python importar_ballenas.py <carpeta con .nc>      (venv_datos: numpy + netCDF4, aparte de Huk)
"""
import os, sys, glob, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from cuerpo_cualidades import CUERPO
FPS = 12.0; G = 9.81
def remuestrear(x, fs, n_out):
    """x (n,) a fs Hz -> (n_out,) a FPS, promediando si fs > FPS e interpolando si fs < FPS. NaN se propagan por interp."""
    x = np.asarray(x, np.float64)
    if fs > FPS * 1.5:
        k = int(round(fs / FPS)); m = (len(x) // k) * k; xb = np.nanmean(x[:m].reshape(-1, k), axis=1); fs_b = fs / k
    else: xb, fs_b = x, fs
    t_out = np.arange(n_out) / FPS; t_b = np.arange(len(xb)) / fs_b
    return np.interp(t_out, t_b, xb, left=np.nan, right=np.nan)
def rot_a_vertical(v):
    """matriz R tal que R @ v apunta a +z (v unitario)."""
    v = v / np.linalg.norm(v); z = np.array([0.0, 0.0, 1.0]); c = float(np.dot(v, z))
    if c > 0.999999: return np.eye(3)
    if c < -0.999999: return np.diag([1.0, -1.0, -1.0])
    k = np.cross(v, z); s = np.linalg.norm(k); k /= s; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K
def cargar(ruta):
    import netCDF4 as nc
    d = nc.Dataset(ruta); V = d.variables
    A = np.array(V["A"][:] if "A" in V else V["Aa"][:], np.float64); fsA = float(V["A" if "A" in V else "Aa"].getncattr("sampling_rate"))
    marco = str((V["A"] if "A" in V else V["Aa"]).getncattr("frame")) if "frame" in (V["A"] if "A" in V else V["Aa"]).ncattrs() else "animal"
    P = np.array(V["P"][:], np.float64).ravel(); fsP = float(V["P"].getncattr("sampling_rate"))
    M = fsM = None
    for k in ("M", "Ma"):
        if k in V: M = np.array(V[k][:], np.float64); fsM = float(V[k].getncattr("sampling_rate"))
    H = fsH = None
    if "head" in V: H = np.array(V["head"][:], np.float64).ravel(); fsH = float(V["head"].getncattr("sampling_rate"))
    esp = str(d.getncattr("animal_species_common")) if "animal_species_common" in d.ncattrs() else "?"
    depid = str(d.getncattr("depid")) if "depid" in d.ncattrs() else os.path.basename(ruta)[:-3]
    return dict(A=A, fsA=fsA, marco=marco, P=P, fsP=fsP, M=M, fsM=fsM, H=H, fsH=fsH, especie=esp, depid=depid)
def convertir(T):
    A = T["A"]; n = int(len(T["P"]) / T["fsP"] * FPS)
    if np.nanmin(A) >= 0 and np.nanmax(A) < 4100: A = A - 2048.0          # cuentas sin signo de 12 bits (DTAG crudo): el cero esta en 2048
    if T["M"] is not None and np.nanmin(T["M"]) >= 0 and np.nanmax(T["M"]) < 4100: T["M"] = T["M"] - 2048.0
    A12 = np.stack([remuestrear(A[i], T["fsA"], n) for i in range(3)])            # (3, n) en 12/s
    esc = np.nanmedian(np.linalg.norm(A12, axis=0)); A12 = A12 / esc * G             # cuentas -> m/s2 (|A| mediano = g)
    P12 = remuestrear(T["P"], T["fsP"], n); P12 = np.clip(P12, 0, None)              # presion negativa = en el aire: 0
    M12 = np.stack([remuestrear(T["M"][i], T["fsM"], n) for i in range(3)]) if T["M"] is not None else None
    ok = np.isfinite(A12).all(0)
    if T["marco"] == "tag":   # nivelar: la gravedad mediana a +z; adelante = eje principal del aleteo en el plano horizontal
        R = rot_a_vertical(np.nanmedian(A12[:, ok], axis=1)); A12 = R @ np.nan_to_num(A12); M12 = None if M12 is None else R @ np.nan_to_num(M12)
        din = A12 - np.stack([np.convolve(A12[i], np.ones(int(FPS * 3)) / int(FPS * 3), "same") for i in range(3)])
        h = din[:2, ok]; w, v = np.linalg.eigh(np.cov(h)); adelante = v[:, np.argmax(w)]
        ang = np.arctan2(adelante[1], adelante[0]); Rz = np.array([[np.cos(-ang), -np.sin(-ang), 0], [np.sin(-ang), np.cos(-ang), 0], [0, 0, 1]])
        A12 = Rz @ A12; M12 = None if M12 is None else Rz @ M12
        A12[:, ~ok] = np.nan
    k = int(FPS * 2); grav = np.stack([np.convolve(np.nan_to_num(A12[i]), np.ones(k) / k, "same") for i in range(3)])   # pasa-bajos 0.5 s = gravedad
    gn = np.linalg.norm(grav, axis=0); gn[gn < 1e-6] = 1.0
    pitch = np.arcsin(np.clip(grav[0] / gn, -1, 1)); roll = np.arctan2(grav[1], grav[2])
    rumbo = None
    if M12 is not None:   # magnetometro llevado al plano horizontal con la gravedad de cada cuadro
        Mh = np.empty_like(M12)
        for i in range(0, n, 1):
            if not np.isfinite(M12[:, i]).all() or gn[i] < 1e-5: Mh[:, i] = np.nan; continue
            Mh[:, i] = rot_a_vertical(grav[:, i]) @ M12[:, i]
        rumbo = np.unwrap(np.nan_to_num(np.arctan2(Mh[1], Mh[0])))
    elif T["H"] is not None: rumbo = np.unwrap(np.nan_to_num(remuestrear(T["H"], T["fsH"], n)))
    din = np.nan_to_num(A12 - grav); odba = np.abs(din).sum(0)
    ema = np.zeros(n); e = 0.0
    for i in range(n): e = 0.9 * e + 0.1 * odba[i]; ema[i] = e
    energia = np.clip(ema / max(1e-6, np.nanpercentile(ema[ok], 90)), 0, 1)
    suav = np.full(n, np.nan); L = int(FPS * 4)
    for i in range(0, n - L, L):
        v = din[:, i:i + L].T
        F = np.abs(np.fft.rfft(v - v.mean(0), axis=0)) ** 2; f = np.fft.rfftfreq(L, 1 / FPS)
        hf = float(F[f > 3].sum() / max(1e-9, F[1:].sum())); suav[i:i + L] = float(np.clip(1 - (hf - 0.08) / 0.3, 0, 1))
    X = np.full((n, 6), np.nan, np.float32)
    X[:, 0] = np.clip(-pitch / (np.pi / 3), -1, 1); X[:, 1] = np.clip(roll / (np.pi / 2), -1, 1)
    if rumbo is not None: X[:, 2] = np.clip(np.gradient(rumbo) * FPS / 0.5, -1, 1)
    X[:, 3] = -np.tanh(np.nan_to_num(P12) / 15.0); X[:, 4] = energia * (1 - 0.4 * np.nan_to_num(suav, nan=0.5)); X[:, 5] = suav
    X[~ok] = np.nan; Mk = np.isfinite(X)
    return X, Mk, dict(pitch=pitch, roll=roll, rumbo=rumbo, prof=P12, ok=ok)
def medidas(depid, crudo):
    """lo que hace una ballena de verdad, en numeros, para calibrar comp_diving / comp_surfacing / comp_playful."""
    p = np.nan_to_num(crudo["prof"]); hondo = p > 10; i = 0; buceos = []
    while i < len(p):
        if hondo[i]:
            j = i
            while j < len(p) and hondo[j]: j += 1
            if (j - i) / FPS > 20: buceos.append((i, j))
            i = j
        else: i += 1
    print(f"  {depid}: {len(p) / FPS / 3600:.1f} h | profundidad max {p.max():.0f} m | buceos >10 m: {len(buceos)}")
    if buceos:
        dur = [(j - i) / FPS for i, j in buceos]; maxp = [p[i:j].max() for i, j in buceos]
        pit = crudo["pitch"]; baja = [np.degrees(np.nanmean(pit[i:i + int(FPS * 15)])) for i, j in buceos]; sube = [np.degrees(np.nanmean(pit[j - int(FPS * 15):j])) for i, j in buceos]
        sup = [(buceos[k + 1][0] - buceos[k][1]) / FPS for k in range(len(buceos) - 1)]
        print(f"    buceo: dura {np.median(dur):.0f} s (mediana, {np.percentile(dur, 10):.0f}-{np.percentile(dur, 90):.0f}) | llega a {np.median(maxp):.0f} m | baja con pitch {np.median(baja):+.0f} grados, sube con {np.median(sube):+.0f} | entre buceos en superficie {np.median(sup) if sup else 0:.0f} s")
    r = np.degrees(np.abs(np.nan_to_num(crudo["roll"]))); print(f"    roll: mediana {np.median(r):.0f} grados, 99% {np.percentile(r, 99):.0f}, max {r.max():.0f} | cuadros con roll > 60: {(r > 60).mean() * 100:.1f}%")
    if crudo["rumbo"] is not None:
        g = np.abs(np.gradient(crudo["rumbo"]) * FPS); print(f"    giro: mediana {np.degrees(np.median(g)):.1f} grados/s, 95% {np.degrees(np.percentile(g, 95)):.1f}")
def main(carpeta):
    sal = os.path.join(AQUI, "datasets", "ballenas"); os.makedirs(sal, exist_ok=True); total = 0
    for f in sorted(glob.glob(os.path.join(carpeta, "*.nc"))):
        try: T = cargar(f)
        except Exception as e: print("  (no se pudo leer", os.path.basename(f), e, ")"); continue
        if not np.isfinite(T["P"]).any() or np.nanmax(T["P"]) < 2: print(f"  {T['depid']}: sin profundidad (prueba de banco), se salta"); continue
        X, Mk, crudo = convertir(T)
        np.savez_compressed(os.path.join(sal, T["depid"] + ".npz"), X=X, M=Mk, fps=FPS, canales=np.array(CUERPO), especie=T["especie"], depid=T["depid"],
                            pitch=crudo["pitch"].astype(np.float32), roll=crudo["roll"].astype(np.float32), rumbo=(crudo["rumbo"] if crudo["rumbo"] is not None else np.full(len(X), np.nan)).astype(np.float32), prof=crudo["prof"].astype(np.float32))
        medidas(T["depid"] + f" ({T['especie']})", crudo); total += len(X) / FPS
        print("    canales:", " ".join(f"{c[7:]} {np.nanmean(X[:, i]):+.2f}±{np.nanstd(X[:, i]):.2f}" for i, c in enumerate(CUERPO)))
    print(f"importadas {total / 3600:.1f} h de ballenas reales -> datasets/ballenas/")
if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/ballenas"))
