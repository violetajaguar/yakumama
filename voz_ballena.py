#!/usr/bin/env python3
"""voz_ballena.py - ella canta con una voz humana y se mueve con esa voz. VocalSet (Wilkins et al. 2018, Zenodo 1193957,
CC BY 4.0): 20 cantantes, 10 horas, tecnicas (vibrato, belt, breathy, trill, straight, tonos largos, arpegios...).

Suena el wav (afplay) y, al mismo tiempo, cada cuadro (30/s) manda a Blender lo que la voz hace:
    jaw_open        la boca abre con la fuerza de la voz (RMS)
    head_pitch      la cabeza sube y baja con la altura de la nota (semitonos respecto de la nota media de la toma)
    cuerpo_yaw      el cuerpo gira despacio hacia donde va la melodia (subida +, bajada -)
    cuerpo_energia  la fuerza de la voz
    emotibit_hr     60 + 50 * fuerza: el latido sigue al canto
con animo singing (cabeza abajo, colgada, como la yubarta que canta) y anclada. Flag red=1 para que la boca pese 0.6.

    venv/bin/python voz_ballena.py ~/Desktop/vocalset/x/FULL/female1/arpeggios/vibrato/f1_arpeggios_vibrato_a.wav --loop
    venv/bin/python voz_ballena.py <wav> --seco       (sin mandar ni sonar: imprime lo que mide)
"""
import os, sys, json, time, wave, socket, argparse, subprocess, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("wav"); ap.add_argument("--loop", action="store_true"); ap.add_argument("--seco", action="store_true"); ap.add_argument("--puerto", type=int, default=9998)
ap.add_argument("--volumen", type=float, default=0.8); ap.add_argument("--espejo", action="append", default=[]); ap.add_argument("--sin-ojos", action="store_true", help="no manda parpadeo: los ojos los pone la toma de un performer (carrusel)"); ap.add_argument("--humana", action="store_true", help="suena la voz humana tal cual (por defecto suena como ballena: una octava abajo, bajo el agua, con eco, con la misma melodia)")
a = ap.parse_args()
CACHE = os.path.expanduser("~/Desktop/vocalset/ballena")
def voz_de_ballena(wav):
    """la voz humana vuelta ballena sin dejar de ser humana: la version ballena (una octava abajo, bajo el agua, eco) mezclada
    con la voz original mas fina encima. Misma duracion. Se guarda en ~/Desktop/vocalset/ballena/ la primera vez."""
    os.makedirs(CACHE, exist_ok=True); sal = os.path.join(CACHE, os.path.basename(wav))
    if not os.path.exists(sal):
        # mezcla ballena + humana: la ballena (una octava abajo, bajo el agua, eco) lleva el peso; la voz humana queda encima, mas fina, para que se oigan sus tonos
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-filter_complex",
                        "[0:a]asplit=2[h][b];[b]asetrate=22050,aresample=44100,atempo=2.0,lowpass=f=1600,aecho=0.7:0.6:280|640:0.45|0.3,volume=2.0[bal];[h]highpass=f=180,lowpass=f=5000,aecho=0.6:0.4:120:0.25,volume=0.55[hum];[bal][hum]amix=inputs=2:normalize=0,alimiter=limit=0.9[a]", "-map", "[a]", sal], check=False)
    return sal if os.path.exists(sal) else wav
FPS = 30.0
def leer(ruta):
    w = wave.open(ruta, "rb"); sr = w.getframerate(); n = w.getnframes(); ch = w.getnchannels(); sw = w.getsampwidth(); raw = w.readframes(n); w.close()
    dt = {1: np.int8, 2: np.int16, 4: np.int32}[sw]; x = np.frombuffer(raw, dt).astype(np.float64) / float(2 ** (8 * sw - 1))
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    return x, sr
def analizar(x, sr):
    """por cuadro: fuerza (RMS normalizada 0..1) y altura (semitonos respecto de la mediana), con autocorrelacion."""
    hop = int(sr / FPS); win = 2048; n = max(1, (len(x) - win) // hop); fuerza = np.zeros(n); f0 = np.full(n, np.nan)
    for i in range(n):
        s = x[i * hop: i * hop + win]; fuerza[i] = np.sqrt(np.mean(s ** 2))
        if fuerza[i] < 0.01: continue
        s = s - s.mean(); ac = np.correlate(s, s, "full")[win - 1:]; lo, hi = int(sr / 1000), int(sr / 80)
        if ac[0] <= 0: continue
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] / ac[0] > 0.3: f0[i] = sr / k
    fz = np.clip(fuerza / max(1e-6, np.percentile(fuerza, 95)), 0, 1)
    semi = 12 * np.log2(f0 / np.nanmedian(f0)) if np.isfinite(f0).any() else np.zeros(n)
    semi = np.where(np.isfinite(semi), semi, 0.0)
    return fz, semi
x, sr = leer(a.wav); fz, semi = analizar(x, sr); n = len(fz); dur = n / FPS; nombre = os.path.basename(a.wav)[:-4]
print(f"   {nombre}: {dur:.1f} s | fuerza media {fz.mean():.2f} | altura ±{np.abs(semi).max():.0f} semitonos | notas {100 * (np.abs(semi) > 0.5).mean():.0f}% del tiempo")
if a.seco: sys.exit(0)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); espejos = [(h, int(p)) for h, p in (e.rsplit(":", 1) for e in a.espejo)]
jaw = 0.0; head = 0.0; yaw = 0.0; en = 0.0
import random; proximo_parpadeo = 2.0 + random.random() * 3.0; parpadeo_hasta = -1.0   # parpadea cada 2-5 s, 0.15 s cerrado
try:
    while True:
        rep = subprocess.Popen(["afplay", "-v", str(a.volumen), a.wav if a.humana else voz_de_ballena(a.wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); t0 = time.time()
        for i in range(n):
            jaw = 0.75 * jaw + 0.25 * float(fz[i]); en = 0.9 * en + 0.1 * float(fz[i])
            head = 0.85 * head + 0.15 * float(np.clip(semi[i] / 8.0, -1, 1)) * 0.6                  # una octava arriba = cabeza 0.6 arriba
            yaw = 0.95 * yaw + 0.05 * float(np.clip((semi[min(n - 1, i + 3)] - semi[max(0, i - 3)]) / 4.0, -1, 1))   # hacia donde va la melodia
            tt = time.time() - t0
            if tt >= proximo_parpadeo: parpadeo_hasta = tt + 0.15; proximo_parpadeo = tt + 2.0 + random.random() * 3.0
            pkt = {"actor_animo": "singing", "anclada": 1, "red": 1, "water": 0.8, "jaw_open": round(min(1.0, 1.2 * jaw), 3), **({} if a.sin_ojos else {"blink": 1.0 if tt < parpadeo_hasta else 0.0}), "head_pitch": round(head, 3), "head_yaw": round(0.3 * yaw, 3),
                   "cuerpo_pitch": -0.4, "cuerpo_yaw": round(0.5 * yaw, 3), "cuerpo_energia": round(0.2 + 0.6 * en, 3), "cuerpo_suavidad": 0.9, "emotibit_hr": round(60 + 50 * en, 1), "bailarin": "voz:" + nombre, "soltar_manual": 1 if i < 30 else 0}
            d = json.dumps(pkt).encode(); s.sendto(d, ("127.0.0.1", a.puerto))
            for h, p in espejos: s.sendto(d, (h, p))
            if i % 30 == 0: json.dump({"tramo": "voz:" + nombre, "modo": "anclada", "t": round(i / FPS), "dur": round(dur), "loop": a.loop, "hora": time.time()}, open("/tmp/ballena_reproduciendo.json", "w"))
            esp = t0 + i / FPS - time.time()
            if esp > 0: time.sleep(esp)
        rep.wait()
        if not a.loop: break
        time.sleep(1.0)
except KeyboardInterrupt: pass
finally:
    try: rep.terminate()
    except Exception: pass
