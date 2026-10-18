#!/usr/bin/env python3
"""coreografia.py - SHE PERFORMS A SCORE Violeta writes. One line per phrase:
    <mood> <seconds>s [inventa | frases | cuerpo:<take or dancer npz>] [hacia:publico|fondo|izquierda|derecha|casa|alrededor] [sin-acro] [poema]
inventa = the diffusion invents (default); frases = real phrases along her plan; cuerpo:X = a real body translated onto her.
hacia = where she goes in the salar (the viewer is at the front). poema = she writes and reads a poem during the phrase (through the app).
"repetir" as the last line loops the piece. Scores live in coreografias/<name>.txt.

    venv/bin/python coreografia.py coreografias/ejemplo_salar.txt
"""
import os, sys, time, glob, json, signal, subprocess, urllib.request
AQUI = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable; MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
def leer(ruta):
    frases = []; repetir = False
    for linea in open(ruta, encoding="utf-8"):
        linea = linea.split("#")[0].strip()
        if not linea: continue
        if linea.lower().startswith("repetir"): repetir = True; continue
        p = linea.split(); m = p[0].lower()
        if m not in MOODS: print(f"   (unknown mood '{m}', skipped)"); continue
        f = dict(animo=m, seg=float(p[1].rstrip("s")) if len(p) > 1 else 30.0, modo="inventa", cuerpo=None, hacia="libre", acro=1, poema=False)
        for tok in p[2:]:
            t = tok.lower()
            if t in ("inventa", "frases", "continuar"): f["modo"] = t
            elif t.startswith("cuerpo:"): f["cuerpo"] = tok[7:]
            elif t.startswith("hacia:"): f["hacia"] = t[6:]
            elif t == "sin-acro": f["acro"] = 0
            elif t == "poema": f["poema"] = True
        frases.append(f)
    return frases, repetir
def ruta_cuerpo(x):
    if os.path.exists(x): return x
    for pat in (os.path.expanduser(f"~/Desktop/h26_limpio/{x}*.npz"), os.path.join(AQUI, "datasets", "cuerpo_video", f"{x}*.npz")):
        c = sorted(glob.glob(pat))
        if c: return c[0]
    return x   # a performer take name
def correr(ruta, puerto=9998):
    frases, repetir = leer(ruta); print(f"   score {os.path.basename(ruta)}: {len(frases)} phrases, {sum(f['seg'] for f in frases):.0f} s" + (", repeating" if repetir else ""), flush=True)
    proc = None
    def parar(*_):
        if proc and proc.poll() is None: proc.terminate()
        sys.exit(0)
    signal.signal(signal.SIGTERM, parar); signal.signal(signal.SIGINT, parar)
    while True:
        for k, f in enumerate(frases):
            if proc and proc.poll() is None: proc.terminate(); time.sleep(0.15)
            if f["cuerpo"]:
                r = ruta_cuerpo(f["cuerpo"]); cmd = [PY, os.path.join(AQUI, "retarget_ballena.py"), r, "--tocar", "--loop", "--animo", f["animo"], "--puerto", str(puerto)]
            else:
                cmd = [PY, os.path.join(AQUI, "jepa_mueve.py"), f["animo"], "--modo", f["modo"], "--hacia", f["hacia"], "--acro", str(f["acro"]), "--ruido", "0.3", "--etiqueta", f"coreo:{os.path.basename(ruta)[:-4]}:{k + 1}", "--puerto", str(puerto)]
            print(f"   {k + 1:2d}. {f['animo']:10s} {f['seg']:4.0f} s  {f['modo'] if not f['cuerpo'] else 'cuerpo ' + f['cuerpo'][:24]:28s} hacia {f['hacia']}" + ("  + poema" if f["poema"] else ""), flush=True)
            proc = subprocess.Popen(cmd, cwd=AQUI, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if f["poema"]:
                try: urllib.request.urlopen("http://127.0.0.1:8766/poema_nuevo", timeout=3).read()
                except Exception: pass
            json.dump({"tramo": f"coreo:{os.path.basename(ruta)[:-4]} {k + 1}/{len(frases)} {f['animo']}", "modo": "coreografia", "t": 0, "dur": int(f["seg"]), "loop": repetir, "hora": time.time()}, open("/tmp/ballena_coreografia.json", "w"))
            time.sleep(f["seg"])
        if not repetir: break
    if proc and proc.poll() is None: proc.terminate()
if __name__ == "__main__": correr(sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "coreografias", "ejemplo_salar.txt"))
