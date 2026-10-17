#!/usr/bin/env python3
"""carrusel.py - un solo cuerpo a la vez para la ballena, elegido desde una pagina (http://localhost:8766) o girando solo.

Antes, cada bailar.py lanzado se sumaba al anterior y todos mandaban a la vez al puerto 9998: la ballena recibia dos o tres
cuerpos superpuestos y se veia glitcheada. Aqui hay UN reproductor: al elegir algo se mata lo que sonaba y arranca lo
nuevo (bailar.py, con el animo de ese cuerpo). El carrusel pasa solo de uno a otro cada N segundos.

Que hay para elegir: los diez animos, cada uno con el cuerpo que le presta su dato (ballet triste, jazz canta, nado come,
tinku rabia, kullawada juega, breaking alerta, suri curiosa, apneista bucea, surfista sale, la yubarta real descansa);
los bailarines de Paqarina; los nueve apneistas; muestras de ballet, jazz, nado y emociones humanas; las ballenas reales.

    venv/bin/python carrusel.py            -> abre http://localhost:8766 (y lo abre en el navegador)
    venv/bin/python carrusel.py --auto 40  -> arranca girando, 40 s cada uno
"""
import os, sys, glob, json, time, signal, argparse, threading, subprocess, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
AQUI = os.path.dirname(os.path.abspath(__file__)); PY = os.path.join(AQUI, "venv", "bin", "python"); H26 = os.path.expanduser("~/Desktop/h26_limpio"); CV = os.path.join(AQUI, "datasets", "cuerpo_video")
MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
def primero(patron):
    fs = sorted(glob.glob(patron)); return fs[0] if fs else None
# --- el menu: (grupo, nombre, animo, archivo, segundos a mostrar en el carrusel)
ITEMS = []
def item(grupo, nombre, animo, ruta, seg=40):
    if ruta and os.path.exists(ruta): ITEMS.append(dict(id=len(ITEMS), grupo=grupo, nombre=nombre, animo=animo, ruta=ruta, seg=seg))
item("animos", "calm · la yubarta descansa", "calm", os.path.join(AQUI, "datasets", "ballenas", "mn12_186a.npz"))
item("animos", "singing · jazz", "singing", primero(os.path.join(CV, "jazz_experta_ch0_*.npz")))
item("animos", "playful · kullawada", "playful", os.path.join(H26, "BF-Lucia_kullawada_limpio.npz"))
item("animos", "curious · suri sikuri", "curious", os.path.join(H26, "BF-Lucia_suri_limpio.npz"))
item("animos", "feeding · nado de pecho", "feeding", os.path.join(CV, "swim_breaststroke_001.npz"))
item("animos", "sad · ballet", "sad", primero(os.path.join(CV, "ballet_experta_ch3_*.npz")))
item("animos", "angry · tinku", "angry", os.path.join(H26, "V-Rosa_tinku_limpio.npz"))
item("animos", "alert · breaking", "alert", os.path.join(H26, "JC24-Galgo_breaking_limpio.npz"))
item("animos", "diving · apneista", "diving", os.path.join(CV, "freediver_03.npz"))
item("animos", "surfacing · surfista", "surfacing", os.path.join(AQUI, "datasets", "surf", "surf_02.npz"))
for f in sorted(glob.glob(os.path.join(H26, "*.npz")))[:400]:
    n = os.path.basename(f).replace("_limpio.npz", "").replace(".npz", "")
    if n.startswith("gBR") or n.startswith("_"): continue
    item("bailarines", n, "auto", f, 30)
for k in range(1, 10): item("apneistas", f"apneista {k}", "diving", os.path.join(CV, f"freediver_0{k}.npz"), 20)
for g, an in (("ballet_experta_ch0", "sad"), ("ballet_experta_ch4", "sad"), ("jazz_experta_ch1", "singing"), ("jazz_experta_ch2", "singing"), ("swim_butterfly_006", "feeding"), ("swim_freestyle_001", "feeding"), ("swim_backstroke_001", "feeding")):
    item("datos", g, an, primero(os.path.join(CV, g + "*.npz")), 20)
for e, an in (("feelsad", "sad"), ("feelangry", "angry"), ("feelhappy", "playful"), ("feelfearful", "alert"), ("feelsurprised", "curious"), ("feelneutral", "calm")):
    item("emociones humanas", e[4:], an, primero(os.path.join(CV, e + "_13_1_*.npz")), 10)
for f in sorted(glob.glob(os.path.join(AQUI, "datasets", "ballenas", "*.npz"))): item("ballenas reales", os.path.basename(f)[:-4], "auto", f, 60)
estado = {"actual": None, "proc": None, "auto": False, "seg": 40, "desde": 0.0, "lock": threading.Lock()}
def matar_todo():
    subprocess.run(["pkill", "-f", "bailar.py"], capture_output=True); subprocess.run(["pkill", "-f", "generar_animo.py"], capture_output=True); subprocess.run(["pkill", "-f", "reproducir.py"], capture_output=True)
def tocar(i):
    with estado["lock"]:
        it = ITEMS[i]; matar_todo(); time.sleep(0.2)
        cmd = [PY, os.path.join(AQUI, "bailar.py"), it["ruta"], "--animo", it["animo"], "--loop"]
        estado["proc"] = subprocess.Popen(cmd, cwd=AQUI, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); estado["actual"] = i; estado["desde"] = time.time()
        print(f"  -> {it['grupo']} / {it['nombre']} ({it['animo']})", flush=True)
def parar():
    with estado["lock"]: matar_todo(); estado["actual"] = None; estado["proc"] = None
def hilo_auto():
    while True:
        time.sleep(0.5)
        if not estado["auto"]: continue
        i = estado["actual"]
        if i is None or time.time() - estado["desde"] >= (estado["seg"] if estado["seg"] else ITEMS[i]["seg"]):
            orden = [k for k, it in enumerate(ITEMS) if it["grupo"] == "animos"]
            sig = orden[(orden.index(i) + 1) % len(orden)] if i in orden else orden[0]; tocar(sig)
HTML = """<!doctype html><html lang=es><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Yakumama · carrusel</title>
<style>body{margin:0;background:#0b0b0e;color:#e8e2d6;font:15px/1.4 -apple-system,Helvetica,sans-serif;padding:18px 20px}h1{font:300 26px Georgia,serif;margin:0 0 6px}
#ahora{font:italic 20px Georgia,serif;margin:6px 0 14px;min-height:1.4em}
.barra{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}button{background:#1b1b22;color:#e8e2d6;border:1px solid #333;border-radius:8px;padding:8px 12px;font:14px -apple-system;cursor:pointer}
button:hover{border-color:#777}button.on{background:#e8e2d6;color:#0b0b0e}button.animo{font-weight:600}input{width:60px;background:#1b1b22;color:#e8e2d6;border:1px solid #333;border-radius:6px;padding:6px}
h2{font:400 12px -apple-system;letter-spacing:.12em;text-transform:uppercase;opacity:.5;margin:18px 0 8px}.grupo{display:flex;flex-wrap:wrap;gap:8px}
.c{display:inline-block;width:.8em;height:.8em;border-radius:50%;vertical-align:middle;margin-right:.4em}</style></head><body>
<h1>Yakumama · un cuerpo a la vez</h1><div id=ahora>—</div>
<div class=barra><button id=auto onclick="fetch('/auto?on='+(document.getElementById('auto').classList.contains('on')?0:1)).then(tick)">carrusel de ánimos</button>
<label>segundos <input id=seg type=number value=40 min=5 onchange="fetch('/seg?s='+this.value)"></label><button onclick="fetch('/parar').then(tick)">parar</button></div>
<div id=lista></div>
<script>const C={calm:'#ebeffa',singing:'#9b4dff',playful:'#ff7300',curious:'#ffd900',feeding:'#33c04d',sad:'#555a70',angry:'#f21410',alert:'#ff4da6',diving:'#2a4fb0',surfacing:'#19d6e8',auto:'#777'};
let items=[];async function carga(){items=await (await fetch('/items')).json();const g={};items.forEach(i=>{(g[i.grupo]=g[i.grupo]||[]).push(i)});
document.getElementById('lista').innerHTML=Object.entries(g).map(([k,v])=>'<h2>'+k+'</h2><div class=grupo>'+v.map(i=>'<button id=b'+i.id+(k=='animos'?' class=animo':'')+' onclick="fetch(\\'/tocar?i='+i.id+'\\').then(tick)"><i class=c style="background:'+(C[i.animo]||'#777')+'"></i>'+i.nombre+'</button>').join('')+'</div>').join('')}
async function tick(){const s=await (await fetch('/estado')).json();document.querySelectorAll('button[id^=b]').forEach(b=>b.classList.remove('on'));if(s.actual!=null){const b=document.getElementById('b'+s.actual);if(b)b.classList.add('on')}
document.getElementById('auto').classList.toggle('on',s.auto);document.getElementById('ahora').textContent=s.actual!=null?(items[s.actual].grupo+' · '+items[s.actual].nombre+'  ·  '+Math.round(s.t)+' s'+(s.auto?'  ·  gira':'')):'nada suena';}
carga().then(tick);setInterval(tick,1000)</script></body></html>"""
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, obj): b = json.dumps(obj).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/": b = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        elif u.path == "/items": self._json([{k: v for k, v in it.items() if k != "ruta"} for it in ITEMS])
        elif u.path == "/estado": self._json({"actual": estado["actual"], "auto": estado["auto"], "seg": estado["seg"], "t": time.time() - estado["desde"] if estado["actual"] is not None else 0})
        elif u.path == "/tocar": estado["auto"] = False; tocar(int(q["i"][0])); self._json({"ok": 1})
        elif u.path == "/auto": estado["auto"] = q.get("on", ["1"])[0] == "1"; self._json({"ok": 1})
        elif u.path == "/seg": estado["seg"] = max(5, int(float(q["s"][0]))); self._json({"ok": 1})
        elif u.path == "/parar": estado["auto"] = False; parar(); self._json({"ok": 1})
        else: self.send_response(404); self.end_headers()
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--auto", type=float, default=0, help="arranca girando, N segundos por animo"); ap.add_argument("--puerto", type=int, default=8766); a = ap.parse_args()
    matar_todo(); print(f"  {len(ITEMS)} cuerpos en el menu | http://localhost:{a.puerto}")
    if a.auto: estado["seg"] = int(a.auto); estado["auto"] = True
    threading.Thread(target=hilo_auto, daemon=True).start()
    signal.signal(signal.SIGTERM, lambda *_: (matar_todo(), sys.exit(0)))
    try: webbrowser.open(f"http://localhost:{a.puerto}")
    except Exception: pass
    try: ThreadingHTTPServer(("0.0.0.0", a.puerto), H).serve_forever()
    except KeyboardInterrupt: matar_todo()
