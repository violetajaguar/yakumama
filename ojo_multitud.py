#!/usr/bin/env python3
"""ojo_multitud.py - HER CROWD EYE (18 Oct 2026, for the MozFest premiere). The jaguar's camera (Huk, jaguaress/cam.py) with the cloud
removed: OpenPose runs ON the OAK-D for everyone in view, the stereo depth gives each person a distance, and nothing leaves the Mac.
Every frame it sends to the recorder (UDP 9995, same port as the sister) one JSON:
    {"personas": [{"id": 3, "x": -0.2, "distancia_m": 1.4, "quieto": 0.8, "mano_mesa": 0/1, "manos_arriba": 0/1}, ...], "n": 2}
The recorder picks WHOM she attends with decisiones.elegir_foco (feeding or the jewel crown first, then a known face, ...).
    venv_datos/bin/python -I ojo_multitud.py                 run, sending
    venv_datos/bin/python -I ojo_multitud.py --prueba 8      8 s, print only
    --mesa x0,y0,x1,y1   the table in the frame, 0..1 (a wrist inside it = a hand on the sister's table)
Keypoints: Nose Neck R-Sho R-Elb R-Wr L-Sho L-Elb L-Wr R-Hip R-Knee R-Ank L-Hip L-Knee L-Ank R-Eye L-Eye R-Ear L-Ear.
"""
import os, sys, json, time, math, socket, argparse
from datetime import timedelta
import numpy as np, cv2, depthai as dai
AQUI = os.path.dirname(os.path.abspath(__file__)); BLOB = os.path.join(AQUI, "modelos", "human-pose-estimation-0001_openvino_2022.1_6shave.blob")
ap = argparse.ArgumentParser(); ap.add_argument("--prueba", type=float, default=0); ap.add_argument("--puerto", type=int, default=9995); ap.add_argument("--mesa", default="0.25,0.55,0.75,1.0")
ap.add_argument("--fps", type=float, default=8.0); ap.add_argument("--ver", action="store_true", help="show the frame with skeletons (needs a display)"); ap.add_argument("--foto", default="", help="save one annotated frame here after 3 s and exit"); a = ap.parse_args()
W, H = 456, 256; NP = 18; MIN_PUNTOS = 7; MIN_SCORE = 3.0; DIST_MAX = 7.0
PAIRS = [[1, 2], [1, 5], [2, 3], [3, 4], [5, 6], [6, 7], [1, 8], [8, 9], [9, 10], [1, 11], [11, 12], [12, 13], [1, 0], [0, 14], [14, 16], [0, 15], [15, 17], [2, 17], [5, 16]]
MAPIDX = [[31, 32], [39, 40], [33, 34], [35, 36], [41, 42], [43, 44], [19, 20], [21, 22], [23, 24], [25, 26], [27, 28], [29, 30], [47, 48], [49, 50], [53, 54], [51, 52], [55, 56], [37, 38], [45, 46]]
NOSE, NECK, RWR, LWR, RSHO, LSHO = 0, 1, 4, 7, 2, 5
def keypoints(prob, th=0.3):
    sm = cv2.GaussianBlur(prob, (3, 3), 0, 0); mask = np.uint8(sm > th); out = []
    cnts, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        bm = cv2.fillConvexPoly(np.zeros(mask.shape), c, 1); _, _, _, loc = cv2.minMaxLoc(sm * bm); out.append(loc + (prob[loc[1], loc[0]],))
    return out
def valid_pairs(outputs, det):
    vp, inv = [], []
    for k in range(len(MAPIDX)):
        pafA = cv2.resize(outputs[0, MAPIDX[k][0]], (W, H)); pafB = cv2.resize(outputs[0, MAPIDX[k][1]], (W, H)); cA = det[PAIRS[k][0]]; cB = det[PAIRS[k][1]]
        if not cA or not cB: inv.append(k); vp.append([]); continue
        pares = np.zeros((0, 3))
        for i in range(len(cA)):
            mj, ms, found = -1, -1, 0
            for j in range(len(cB)):
                d = np.subtract(cB[j][:2], cA[i][:2]).astype(np.float64); n = np.linalg.norm(d)
                if not n: continue
                d /= n; xs = np.linspace(cA[i][0], cB[j][0], 10); ys = np.linspace(cA[i][1], cB[j][1], 10)
                paf = np.array([[pafA[int(round(y)), int(round(x))], pafB[int(round(y)), int(round(x))]] for x, y in zip(xs, ys)]); sc = paf @ d
                if (np.sum(sc > 0.2) / 10.0) > 0.4 and sc.mean() > ms: mj, ms, found = j, sc.mean(), 1
            if found: pares = np.append(pares, [[cA[i][3], cB[mj][3], ms]], axis=0)
        vp.append(pares)
    return vp, inv
def personwise(vp, inv, kl):
    P = -1 * np.ones((0, 19))
    for k in range(len(MAPIDX)):
        if k in inv: continue
        pa, pb = vp[k][:, 0], vp[k][:, 1]; ia, ib = PAIRS[k]
        for i in range(len(vp[k])):
            idx = next((j for j in range(len(P)) if P[j][ia] == pa[i]), -1)
            if idx >= 0: P[idx][ib] = pb[i]; P[idx][-1] += kl[int(pb[i]), 2] + vp[k][i][2]
            elif k < 17:
                row = -1 * np.ones(19); row[ia] = pa[i]; row[ib] = pb[i]; row[-1] = sum(kl[vp[k][i, :2].astype(int), 2]) + vp[k][i][2]; P = np.vstack([P, row])
    return P
def decodificar(nn):
    heat = np.array(nn.getLayerFp16("Mconv7_stage2_L2"), dtype="float32").reshape((1, 19, 32, 57)); pafs = np.array(nn.getLayerFp16("Mconv7_stage2_L1"), dtype="float32").reshape((1, 38, 32, 57))
    out = np.concatenate((heat, pafs), axis=1); det = []; kl = np.zeros((0, 3)); kid = 0
    for r in range(NP):
        kps = keypoints(cv2.resize(out[0, r], (W, H))); kl = np.vstack([kl, *kps]) if kps else kl; det.append([kp + (kid + i,) for i, kp in enumerate(kps)]); kid += len(kps)
    vp, inv = valid_pairs(out, det); return kl, personwise(vp, inv, kl)
def personas_de(kl, P, depth, mesa):
    """one dict per person: neck position, metres (median depth around the neck), wrists on the table / above the shoulders."""
    out = []
    for row in P:
        pts = {j: kl[int(row[j])][:2] for j in range(NP) if row[j] != -1}
        if (NECK not in pts and NOSE not in pts) or len(pts) < MIN_PUNTOS or row[-1] < MIN_SCORE: continue   # a reflection on a screen gives 6-7 weak points; a person gives 9+
        nx, ny = pts.get(NECK, pts.get(NOSE)); x0, x1, y0, y1 = max(0, int(nx) - 5), min(W, int(nx) + 6), max(0, int(ny) - 5), min(H, int(ny) + 6)
        dz = depth[y0:y1, x0:x1]; dz = dz[np.nonzero(dz)]; m = float(np.median(dz)) / 1000.0 if dz.size else None
        sho_y = min([pts[j][1] for j in (RSHO, LSHO) if j in pts] or [ny])
        mano_mesa = any(mesa[0] * W <= pts[j][0] <= mesa[2] * W and mesa[1] * H <= pts[j][1] <= mesa[3] * H for j in (RWR, LWR) if j in pts)
        manos_arriba = any(pts[j][1] < sho_y for j in (RWR, LWR) if j in pts)
        if m is None or m > DIST_MAX: continue   # no depth or beyond the room: not a person she can attend
        out.append({"x": round((nx / W) * 2 - 1, 3), "y": round(ny / H, 3), "distancia_m": round(m, 2) if m else None, "mano_mesa": int(mano_mesa), "manos_arriba": int(manos_arriba), "puntos": len(pts)})
    return out
class Rastro:
    """ids that persist from frame to frame (nearest neck), and stillness per id."""
    def __init__(self): self.v = {}; self.n = 0
    def asignar(self, ps, t):
        usados = set()
        for p in ps:
            mejor, dm = None, 0.12
            for i, v in self.v.items():
                if i in usados: continue
                d = math.hypot(p["x"] - v["x"], (p["y"] - v["y"]) * 0.5)
                if d < dm: mejor, dm = i, d
            if mejor is None: self.n += 1; mejor = self.n; self.v[mejor] = {"x": p["x"], "y": p["y"], "quieto": 0.5, "t": t, "t0": t}
            v = self.v[mejor]; mov = math.hypot(p["x"] - v["x"], p["y"] - v["y"]); v["quieto"] = 0.9 * v["quieto"] + 0.1 * (1.0 if mov < 0.01 else 0.0)
            v.update(x=p["x"], y=p["y"], t=t); p["id"] = mejor; p["quieto"] = round(v["quieto"], 2); p["segundos"] = round(t - v["t0"], 1); usados.add(mejor)
        for i in [i for i, v in self.v.items() if t - v["t"] > 1.5]: self.v.pop(i)
        return ps
def pipeline():
    pl = dai.Pipeline(); cam = pl.create(dai.node.ColorCamera); cam.setPreviewSize(W, H); cam.setCamera("color"); cam.setInterleaved(False); cam.setFps(15)
    ml = pl.create(dai.node.MonoCamera); ml.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P); ml.setCamera("left"); ml.setFps(15)
    mr = pl.create(dai.node.MonoCamera); mr.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P); mr.setCamera("right"); mr.setFps(15)
    st = pl.create(dai.node.StereoDepth); st.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.DEFAULT); st.setLeftRightCheck(True); st.setDepthAlign(dai.CameraBoardSocket.CAM_A)
    st.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7); ml.out.link(st.left); mr.out.link(st.right)   # depth comes at its own size (width must be a multiple of 16); resized on the host
    nn = pl.create(dai.node.NeuralNetwork); nn.setBlobPath(BLOB); cam.preview.link(nn.input)
    sy = pl.create(dai.node.Sync); sy.setSyncThreshold(timedelta(milliseconds=80)); st.depth.link(sy.inputs["depth"]); cam.preview.link(sy.inputs["rgb"]); nn.out.link(sy.inputs["nn"])
    xo = pl.create(dai.node.XLinkOut); xo.setStreamName("xout"); sy.out.link(xo.input); return pl
if __name__ == "__main__":
    mesa = tuple(float(v) for v in a.mesa.split(",")); sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rastro = Rastro(); t0 = time.time(); n = 0; ult = 0.0
    with dai.Device(pipeline()) as dev:
        q = dev.getOutputQueue(name="xout", maxSize=1, blocking=False); print(f"   ojo multitud: OAK-D {dev.getDeviceName() if hasattr(dev, 'getDeviceName') else ''} | pose on device | -> UDP {a.puerto} | table {mesa}")
        while True:
            g = q.get(); t = time.time()
            if t - ult < 1.0 / a.fps: continue
            ult = t; kl, P = decodificar(g["nn"]); depth = cv2.resize(g["depth"].getFrame(), (W, H), interpolation=cv2.INTER_NEAREST); ps = rastro.asignar(personas_de(kl, P, depth, mesa), t); n += 1
            pk = {"personas": ps, "n": len(ps), "t": round(t, 3)}
            if a.prueba: print(f"{t - t0:5.1f}s  n={len(ps)}  " + "  ".join(f"#{p['id']} {p['distancia_m']}m x={p['x']:+.2f} quieto={p['quieto']} mesa={p['mano_mesa']} arriba={p['manos_arriba']} pts={p['puntos']}" for p in ps))
            else: sock.sendto(json.dumps(pk).encode(), ("127.0.0.1", a.puerto))
            if a.ver:
                fr = g["rgb"].getCvFrame()
                for p in ps: cv2.putText(fr, f"#{p['id']} {p['distancia_m']}m", (int((p['x'] + 1) / 2 * W), int(p['y'] * H)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imshow("ojo multitud", fr); cv2.waitKey(1)
            if a.foto and t - t0 > 3.0:
                fr = g["rgb"].getCvFrame()
                for row in P:
                    for i, j in PAIRS:
                        if row[i] != -1 and row[j] != -1: cv2.line(fr, tuple(int(v) for v in kl[int(row[i])][:2]), tuple(int(v) for v in kl[int(row[j])][:2]), (0, 255, 255), 1)
                for p in ps: cv2.putText(fr, f"#{p['id']} {p['distancia_m']}m", (int((p['x'] + 1) / 2 * W), int(p['y'] * H)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
                cv2.rectangle(fr, (int(mesa[0] * W), int(mesa[1] * H)), (int(mesa[2] * W), int(mesa[3] * H)), (255, 0, 255), 1); cv2.imwrite(a.foto, fr); print("   foto ->", a.foto); break
            if a.prueba and t - t0 > a.prueba: print(f"   {n} frames in {t - t0:.1f} s"); break
