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
ap.add_argument("--volumen", type=float, default=0.8); ap.add_argument("--espejo", action="append", default=[]); ap.add_argument("--canta", action="store_true", help="ella canta la melodia humana con SU voz: su canto (singing.wav) resampleado al tono y la fuerza de la voz humana, tramo a tramo"); ap.add_argument("--muda", action="store_true", help="no suena la voz humana: solo mueve a la ballena con ella (el sonido lo pone otro, p. ej. su propio canto)"); ap.add_argument("--sin-ojos", action="store_true", help="no manda parpadeo: los ojos los pone la toma de un performer (carrusel)"); ap.add_argument("--ballena", action="store_true", help="suena la mezcla ballena+humana (por defecto suena la voz humana tal cual: la mezcla no gusto)")
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
CANTO_PROPIO = os.path.expanduser("~/Desktop/vocalset/ballena/_canto_propio.wav")   # su canto en PCM de 16 bits (el original es float de 32)
if not os.path.exists(CANTO_PROPIO): subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.expanduser("~/Desktop/Huk/whale sound/singing.wav"), "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", CANTO_PROPIO], check=False)
def ella_canta(fz, semi, sal, hop_s=0.2):
    """su voz (singing.wav) cantando la melodia de la voz humana: por cada tramo de 0.2 s, un trozo de su canto resampleado
    por 2^(semitonos/12) (sube o baja de tono con la cantante) y con la fuerza de la cantante; cruces de 20 ms."""
    y, sr2 = leer(CANTO_PROPIO); hop = int(hop_s * sr2); cruce = int(0.02 * sr2); pos = 0; out = np.zeros(int(len(fz) / FPS * sr2) + hop, np.float64); escrito = 0
    por_tramo = int(hop_s * FPS)
    for k in range(0, len(fz), por_tramo):
        s_ = float(np.mean(semi[k:k + por_tramo])); f_ = float(np.mean(fz[k:k + por_tramo])); fac = 2 ** (np.clip(s_, -14, 14) / 12)
        largo_fuente = int(hop * fac); seg = y[pos:pos + largo_fuente]
        if len(seg) < largo_fuente: pos = 0; seg = y[pos:pos + largo_fuente]
        pos += largo_fuente // 2   # avanza por su canto a medio paso: cada tramo humano suena un trozo distinto de su voz
        t_out = np.linspace(0, len(seg) - 1, hop); seg = np.interp(t_out, np.arange(len(seg)), seg) * (0.15 + 0.85 * f_)
        ini = escrito - cruce if escrito > cruce else 0; w = np.linspace(0, 1, min(cruce, len(seg)))
        if escrito > cruce: out[ini:ini + len(w)] = out[ini:ini + len(w)] * (1 - w) + seg[:len(w)] * w; out[ini + len(w): ini + len(seg)] = seg[len(w):]
        else: out[:len(seg)] = seg
        escrito = ini + len(seg)
    out = out[:escrito]; out = out / max(1e-6, np.abs(out).max()) * 0.9
    import struct
    wv = wave.open(sal, "wb"); wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(sr2); wv.writeframes((out * 32767).astype(np.int16).tobytes()); wv.close(); return sal
if a.canta:
    os.makedirs(CACHE, exist_ok=True); canto_wav = os.path.join(CACHE, "canta_" + os.path.basename(a.wav))
    if not os.path.exists(canto_wav): ella_canta(fz, semi, canto_wav)
print(f"   {nombre}: {dur:.1f} s | fuerza media {fz.mean():.2f} | altura ±{np.abs(semi).max():.0f} semitonos | notas {100 * (np.abs(semi) > 0.5).mean():.0f}% del tiempo")
if a.seco: sys.exit(0)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); espejos = [(h, int(p)) for h, p in (e.rsplit(":", 1) for e in a.espejo)]
jaw = 0.0; head = 0.0; yaw = 0.0; en = 0.0
import random; proximo_parpadeo = 2.0 + random.random() * 3.0; parpadeo_hasta = -1.0   # parpadea cada 2-5 s, 0.15 s cerrado
try:
    while True:
        fuente = canto_wav if a.canta else (voz_de_ballena(a.wav) if a.ballena else a.wav)
        rep = subprocess.Popen(["afplay", "-v", str(a.volumen), fuente], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if not a.muda else subprocess.Popen(["sleep", str(dur)]); t0 = time.time()
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
