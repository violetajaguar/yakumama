#!/usr/bin/env python3
"""prueba_datos.py - WHAT IS ARRIVING (22 Oct 2026, Violeta: "a little webapp to test what data is arriving").

One page, refreshed every second, with every input of the installation and how fresh it is:
  her brain's packet (UDP 9993 probe: mood, position, journey, the printed body told and measured, proprioception, wind),
  her decision window (/tmp/ballena_cerebro.json: decision, policy, people, weather from Open-Meteo),
  Laya on the mini (/tmp/ballena_laya.json), Qwen on the mini (ollama /api/tags),
  the ESP32 bridge (logs/joy.log: joystick, touch), Dan's renderer (logs/ballena_td.log: fps, Qwen), her eye (logs/ojo.log).
Standard library only; reads logs and files, binds UDP 9993 (her brain must send --salida 127.0.0.1:9993; correr_todo.sh does).

    venv/bin/python prueba_datos.py            -> http://localhost:8767   (also from the mini: http://192.168.50.172:8767)
"""
import json, os, socket, threading, time, urllib.request, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
AQUI = os.path.dirname(os.path.abspath(__file__)); L = os.path.join(AQUI, "logs")
PUERTO = int(os.environ.get("PRUEBA_PUERTO", 8767)); MINI = os.environ.get("MINI", "192.168.50.104")
S = {"paquete": None, "paquete_t": 0.0, "paquete_n": 0, "paquete_hz": 0.0, "ollama": None, "ollama_t": 0.0, "cuerpo": []}   # cuerpo: last 120 s of (t, told L, told R, measured L, R, temps, her reading), 5/s -> /cuerpo.json
def _udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("127.0.0.1", 9993)); s.settimeout(1.0); n0, t0 = 0, time.time()
    while True:
        try:
            d = json.loads(s.recv(65535)); S["paquete"] = d; S["paquete_t"] = time.time(); S["paquete_n"] += 1
            cf = d.get("cuerpo_fisico") or {}; m = cf.get("medido") or {}; pr = d.get("propio") or {}
            if m and (not S["cuerpo"] or time.time() - S["cuerpo"][-1][0] >= 0.2):
                S["cuerpo"].append([round(time.time(), 2), cf.get("aleta_i"), cf.get("aleta_d"), m.get("fl"), m.get("fr"), m.get("fl_temp"), m.get("fr_temp"), pr.get("sujeta"), pr.get("excitada"), d.get("animo")]); del S["cuerpo"][:-600]
        except Exception: pass
        if time.time() - t0 >= 2.0: S["paquete_hz"] = (S["paquete_n"] - n0) / (time.time() - t0); n0, t0 = S["paquete_n"], time.time()
def _ollama():
    while True:
        try:
            with urllib.request.urlopen(f"http://{MINI}:11434/api/tags", timeout=3) as r: S["ollama"] = [m.get("name") for m in json.loads(r.read()).get("models", [])]; S["ollama_t"] = time.time()
        except Exception as e: S["ollama"] = f"no: {type(e).__name__}"
        time.sleep(15)
def _cola(path, n=2500):
    try:
        with open(path, "rb") as f: f.seek(0, 2); sz = f.tell(); f.seek(max(0, sz - n)); return f.read().decode("utf-8", "replace").splitlines(), time.time() - os.path.getmtime(path)
    except Exception: return [], None
def _json(path):
    try: d = json.load(open(path)); return d, time.time() - float(d.get("t") or 0)
    except Exception: return None, None
def fila(nombre, edad, bien_s, detalle):
    estado = "sin datos" if edad is None else ("vivo" if edad < bien_s else ("tarde" if edad < 5 * bien_s else "muerto"))
    return {"fuente": nombre, "hace": (None if edad is None else round(edad, 1)), "estado": estado, "detalle": detalle}
def datos():
    t = time.time(); filas = []
    p = S["paquete"]; ep = (t - S["paquete_t"]) if p else None
    if p:
        cf = p.get("cuerpo_fisico") or {}; m = cf.get("medido") or {}; pr = p.get("propio") or {}; vj = p.get("viaje") or {}
        filas.append(fila("her brain -> packet 9993", ep, 1.0, f"{S['paquete_hz']:.0f} pkt/s | {p.get('animo')} ({p.get('fuente')}) | at ({p.get('x', 0):+.2f}, {p.get('y', 0):+.2f}, {p.get('z', 0):+.2f}) | journey {vj.get('destino') or '-'} h {vj.get('altura', '-')} | show {p.get('show')} imitates {p.get('imita')} | wind of hers {p.get('viento')}"))
        filas.append(fila("printed whale: board alive (via Dan's brain)", (None if not cf else (0.0 if cf.get('viva') else 99.0)), 1.0, f"fins told L {cf.get('aleta_i')} R {cf.get('aleta_d')} tail {cf.get('cola')} lid {cf.get('parpado')}" if cf else "no cuerpo_fisico in the packet"))
        filas.append(fila("printed whale: fins MEASURED (SERVO line)", (0.0 if m else None), 1.0, (f"L {m.get('fl')} deg {m.get('fl_temp')} C load {m.get('fl_load')} | R {m.get('fr')} deg {m.get('fr_temp')} C load {m.get('fr_load')} | her reading: held {pr.get('sujeta')} tired {pr.get('cansada')} excited {pr.get('excitada')}" if m else "the board is not sending SERVO: (or Dan's brain does not forward it)")))
        if p.get("sala") is not None: filas.append(fila("the room (Pro on the mini -> 5005)", 0.0, 1.0, str(p.get("sala"))))
    else: filas.append(fila("her brain -> packet 9993", None, 1.0, "nothing on 9993: is cerebro_ballena.py running with --salida 127.0.0.1:9993?"))
    w, ew = _json("/tmp/ballena_cerebro.json")
    if w:
        c = w.get("clima") or {}; cs = w.get("cuerpo_sentido") or {}
        filas.append(fila("her decision window (/tmp/ballena_cerebro.json)", ew, 8.0, f"policy {w.get('politica')} | person {w.get('persona')} known {w.get('conocida')} people {w.get('personas_n')} ({w.get('foco_razon') or '-'}) | {w.get('animo')} {int(w.get('segundos') or 0)} s | decision {w.get('decision')} | fixed {w.get('fijo') or '-'}"))
        filas.append(fila("weather (Open-Meteo via Dan's brain)", (ew if c and c.get('temperatura') is not None else None), 8.0, f"wind {c.get('viento')} m/s gusts {c.get('rachas')} | sun {c.get('sol')} night {c.get('noche')} | rain hers {c.get('lluvia')} real {c.get('lluvia_real')} mm | water {c.get('agua')} | {c.get('temperatura')} C hum {c.get('humedad')}% clouds {c.get('nubes')}% {c.get('presion')} hPa uv {c.get('uv')}"))
        filas.append(fila("her ear / eye senses in the decision", ew, 8.0, f"touch {w.get('tacto')} {w.get('tacto_zona') or ''} | offering {w.get('ofrenda')} id {w.get('ofrenda_id')} reaction {w.get('reaccion')} | sees sister {w.get('ve_hermana')} phone {w.get('ve_telefono')} | body {cs}"))
    else: filas.append(fila("her decision window", None, 8.0, "no /tmp/ballena_cerebro.json"))
    la, el = _json("/tmp/ballena_laya.json")
    filas.append(fila(f"Laya on the mini ({MINI})", el, 12.0, (f"engaged {la.get('engaged')} maltrato {la.get('maltrato')} retreat {la.get('retirarse')} gift {la.get('regalo')} | perform {la.get('perform', '-')} visit {la.get('visit', '-')} imitate {la.get('imitate', '-')} speak {la.get('speak', '-')} | {la.get('ms')} ms | \"{la.get('situacion')}\"" if la else "no /tmp/ballena_laya.json")))
    filas.append(fila(f"Qwen on the mini (ollama {MINI}:11434)", (t - S["ollama_t"]) if S["ollama_t"] else None, 30.0, str(S["ollama"])))
    lj, ej = _cola(os.path.join(L, "joy.log")); ult = next((x for x in reversed(lj) if "🕹" in x), ""); fins = next((x for x in reversed(lj) if "fins measured" in x), "")
    filas.append(fila("ESP32 bridge (logs/joy.log)", ej, 3.0, f"{ult.strip()} | last fins line in log: {fins.strip() or 'none'}"))
    lt, et = _cola(os.path.join(L, "ballena_td.log")); st = next((x for x in reversed(lt) if "🐋" in x), ""); ol = next((x for x in reversed(lt) if "ollama" in x.lower()), "")
    filas.append(fila("Dan's brain / renderer (logs/ballena_td.log)", et, 3.0, f"{st.strip()[:170]} | {ol.strip()[:80]}"))
    lo, eo = _cola(os.path.join(L, "ojo.log")); so = next((x for x in reversed(lo) if x.strip()), "")
    filas.append(fila("her eye, the recorder (logs/ojo.log)", eo, 10.0, so.strip()[:200]))
    lc, ec = _cola(os.path.join(L, "cerebro.log")); sc = next((x for x in reversed(lc) if x.strip()), ""); sb = next((x for x in reversed(lc) if "[body]" in x), "")
    filas.append(fila("her brain's log (logs/cerebro.log)", ec, 10.0, f"{sc.strip()[:140]} | {sb.strip()[-120:]}"))
    return {"t": t, "hora": time.strftime("%H:%M:%S"), "filas": filas}
PAGINA = """<!doctype html><html><head><meta charset="utf-8"><title>Yakumama: what is arriving</title>
<style>body{font:14px/1.4 -apple-system,Helvetica,sans-serif;background:#111;color:#ddd;margin:16px}h1{font-size:18px;font-weight:600;margin:0 0 4px}small{color:#888}
table{border-collapse:collapse;width:100%;margin-top:12px}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid #2a2a2a;vertical-align:top}th{color:#999;font-weight:500}
.vivo{color:#4ade80}.tarde{color:#fbbf24}.muerto{color:#f87171}.sin{color:#777}td.d{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#bbb;word-break:break-word}</style></head>
<body><h1>Yakumama: what is arriving</h1><small id="hora">...</small>
<table><thead><tr><th style="width:26%">source</th><th style="width:7%">ago</th><th style="width:7%">state</th><th>what it says</th></tr></thead><tbody id="b"></tbody></table>
<script>
async function tick(){try{const r=await fetch('/datos.json',{cache:'no-store'});const d=await r.json();document.getElementById('hora').textContent='updated '+d.hora+' (every second)';
document.getElementById('b').innerHTML=d.filas.map(f=>`<tr><td>${f.fuente}</td><td>${f.hace==null?'-':f.hace+' s'}</td><td class="${f.estado=='sin datos'?'sin':f.estado}">${f.estado}</td><td class="d">${f.detalle.replace(/&/g,'&amp;').replace(/</g,'&lt;')}</td></tr>`).join('');}catch(e){document.getElementById('hora').textContent='no answer from prueba_datos.py';}}
tick();setInterval(tick,1000);</script></body></html>"""
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/datos.json"): b = json.dumps(datos(), ensure_ascii=False).encode(); ct = "application/json"
        elif self.path.startswith("/cuerpo.json"): b = json.dumps({"campos": ["t", "told_L", "told_R", "meas_L", "meas_R", "temp_L", "temp_R", "held", "excited", "animo"], "filas": S["cuerpo"]}).encode(); ct = "application/json"
        else: b = PAGINA.encode(); ct = "text/html; charset=utf-8"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
if __name__ == "__main__":
    threading.Thread(target=_udp, daemon=True).start(); threading.Thread(target=_ollama, daemon=True).start()
    print(f"what is arriving: http://localhost:{PUERTO}  (UDP 9993 probe, files, logs)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PUERTO), H).serve_forever()
