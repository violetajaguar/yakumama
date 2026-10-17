#!/usr/bin/env python3
"""carrusel.py - un solo cuerpo a la vez para la ballena, elegido desde una pagina (http://localhost:8766) o girando solo.

Antes, cada bailar.py lanzado se sumaba al anterior y todos mandaban a la vez al puerto 9998: la ballena recibia dos o tres
cuerpos superpuestos y se veia glitcheada. Aqui hay UN reproductor: al elegir algo se mata lo que sonaba y arranca lo
nuevo. El carrusel pasa solo de un animo a otro cada N segundos.

Que hay para elegir, por menus:
  animos          los diez, cada uno con el cuerpo que le presta su dato (ballet triste, jazz canta, nado come, tinku rabia,
                  kullawada juega, breaking alerta, suri curiosa, apneista bucea, surfista sale, la yubarta real descansa)
  performers      Violeta, Dan, Sanam, Suri: sus tomas grabadas (cara, manos, EmotiBit) via reproducir.py --modo anclada;
                  la pagina muestra el pulso y la piel de la toma y que hacen en la ballena (tempo, energia, tension)
  danzas          Paqarina por danza: tinku, kullawada, suri, breaking, y cada bailarin por nombre
  apneistas, datos (ballet, jazz, nado), emociones humanas, ballenas reales

    venv/bin/python carrusel.py            -> abre http://localhost:8766
    venv/bin/python carrusel.py --auto 40  -> arranca girando por los animos, 40 s cada uno
"""
import os, sys, re, glob, json, time, signal, argparse, threading, subprocess, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
AQUI = os.path.dirname(os.path.abspath(__file__)); PY = os.path.join(AQUI, "venv", "bin", "python"); H26 = os.path.expanduser("~/Desktop/h26_limpio"); CV = os.path.join(AQUI, "datasets", "cuerpo_video")
MOODS = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
ES = {"calm": "calma", "singing": "canto", "playful": "juego", "curious": "curiosidad", "feeding": "hambre", "sad": "tristeza", "angry": "rabia", "alert": "alerta", "diving": "hondo", "surfacing": "aire"}
def primero(patron):
    fs = sorted(glob.glob(patron)); return fs[0] if fs else None
ITEMS = []
def item(grupo, sub, nombre, animo, ruta=None, toma=None, seg=40):
    if (ruta and os.path.exists(ruta)) or toma: ITEMS.append(dict(id=len(ITEMS), grupo=grupo, sub=sub, nombre=nombre, animo=animo, ruta=ruta, toma=toma, seg=seg))
# --- animos: el cuerpo que cada dato le presta
item("animos", "", "calm · la yubarta descansa", "calm", os.path.join(AQUI, "datasets", "ballenas", "mn12_186a.npz"))
item("animos", "", "singing · jazz", "singing", primero(os.path.join(CV, "jazz_experta_ch0_*.npz")))
item("animos", "", "playful · kullawada", "playful", os.path.join(H26, "BF-Lucia_kullawada_limpio.npz"))
item("animos", "", "curious · suri sikuri", "curious", os.path.join(H26, "BF-Lucia_suri_limpio.npz"))
item("animos", "", "feeding · nado de pecho", "feeding", os.path.join(CV, "swim_breaststroke_001.npz"))
item("animos", "", "sad · ballet", "sad", primero(os.path.join(CV, "ballet_experta_ch3_*.npz")))
item("animos", "", "angry · tinku", "angry", os.path.join(H26, "V-Rosa_tinku_limpio.npz"))
item("animos", "", "alert · breaking", "alert", os.path.join(H26, "JC24-Galgo_breaking_limpio.npz"))
item("animos", "", "diving · apneista", "diving", os.path.join(CV, "freediver_03.npz"))
item("animos", "", "surfacing · surfista", "surfacing", os.path.join(AQUI, "datasets", "surf", "surf_02.npz"))
# --- performers: sus tomas (cara + manos + EmotiBit), por persona
for f in sorted(glob.glob(os.path.join(AQUI, "datasets", "cara", "*.jsonl"))):
    n = os.path.basename(f)[:-6]; p = n.split("_")
    if len(p) < 2 or p[0] not in MOODS or any(x in n for x in ("beat", "ravdess", "llama")): continue
    actor = p[1] if len(p) == 3 else "violeta"
    item("performers", actor, f"{ES[p[0]]} · {p[0]} {p[-1]}", p[0], toma=n, seg=40)
# --- danzas de Paqarina por danza, y los demas bailarines por nombre
def danza_de(n):
    n = n.lower()
    for k in ("tinku", "kullawada", "suri", "breaking", "toprock"):
        if k in n: return k
    return None
for f in sorted(glob.glob(os.path.join(H26, "*.npz"))):
    n = os.path.basename(f).replace("_limpio.npz", "").replace(".npz", "")
    if n.startswith("gBR") or n.startswith("_"): continue
    d = danza_de(n)
    if d: item("danzas", d, n, {"tinku": "angry", "kullawada": "playful", "suri": "curious", "breaking": "alert", "toprock": "alert"}[d], f, 30)
    else:
        cand = [t for t in re.split(r"[-_]", n) if re.fullmatch(r"[A-Za-z]{3,}", t) and not t.isupper() and t.lower() not in ("limpio", "toma")]
        quien = cand[0].lower() if cand else "otros"   # "T-HJ_Harold_Juan" -> harold, "Cami-Galgo" -> cami, "V-Carmen" -> carmen
        item("danzas", quien, n, "auto", f, 30)
for k in range(1, 10): item("apneistas", "", f"apneista {k}", "diving", os.path.join(CV, f"freediver_0{k}.npz"), seg=20)
for g, an, sub in (("ballet_experta_ch0", "sad", "ballet"), ("ballet_experta_ch3", "sad", "ballet"), ("ballet_principiante_ch1", "sad", "ballet"), ("jazz_experta_ch0", "singing", "jazz"), ("jazz_experta_ch2", "singing", "jazz"), ("jazz_intermedia_ch1", "singing", "jazz"),
                  ("swim_breaststroke_001", "feeding", "nado"), ("swim_butterfly_006", "feeding", "nado"), ("swim_freestyle_001", "feeding", "nado"), ("swim_backstroke_001", "feeding", "nado")):
    item("datos", sub, g, an, primero(os.path.join(CV, g + "*.npz")), seg=20)
for e, an in (("feelsad", "sad"), ("feelangry", "angry"), ("feelhappy", "playful"), ("feelfearful", "alert"), ("feelsurprised", "curious"), ("feelneutral", "calm")):
    for per in ("05", "13", "22"): item("emociones humanas", f"persona {per}", f"{ES[an]} · {e[4:]}", an, primero(os.path.join(CV, f"{e}_{per}_1_*.npz")), seg=10)
for f in sorted(glob.glob(os.path.join(AQUI, "datasets", "ballenas", "*.npz"))): item("ballenas reales", "", os.path.basename(f)[:-4], "auto", f, seg=60)
# --- canto: una voz humana (VocalSet) con la que ella canta y se mueve (voz_ballena.py)
VOCAL = os.path.expanduser("~/Desktop/vocalset/x/FULL")
for cant in ("female1", "female5", "male3", "male9"):
    for tec in ("vibrato", "straight", "breathy", "belt", "trill", "vocal_fry", "lip_trill", "trillo"):
        for w in sorted(glob.glob(os.path.join(VOCAL, cant, "*", tec, "*.wav")))[:2]:
            ITEMS.append(dict(id=len(ITEMS), grupo="canto", sub=cant, nombre=f"{tec} · {os.path.basename(os.path.dirname(os.path.dirname(w)))}", animo="singing", ruta=w, toma=None, seg=30, voz=True))
estado = {"actual": None, "proc": None, "auto": False, "seg": 40, "desde": 0.0, "lock": threading.Lock()}
_tomas = {}
def toma_cuerpo(nombre):
    """las filas del cuerpo de una toma (con el EmotiBit), cacheadas."""
    if nombre not in _tomas:
        fb = os.path.join(AQUI, "datasets", "cuerpo", nombre + ".jsonl")
        _tomas[nombre] = [json.loads(l) for l in open(fb)] if os.path.exists(fb) else []
    return _tomas[nombre]
def emotibit_ahora():
    """pulso y piel de la toma que suena, en este segundo, y lo que hacen en la ballena (las formulas de receptor_ballena.py)."""
    i = estado["actual"]
    if i is None or not ITEMS[i]["toma"]: return None
    filas = toma_cuerpo(ITEMS[i]["toma"])
    if not filas: return None
    t0 = filas[0].get("t", 0); dur = max(0.1, filas[-1].get("t", 0) - t0); t = (time.time() - estado["desde"]) % dur
    k = min(range(len(filas)), key=lambda j: abs(filas[j].get("t", 0) - t0 - t)); r = filas[k]
    hr = float(r.get("emotibit_hr", 0) or 0); eda = float(r.get("emotibit_eda", 0) or 0); temp = float(r.get("emotibit_therm", 0) or 0)
    if eda > 100: eda = 0.0   # sensor sin contacto (10000)
    tempo = max(0.6, min(1.6, hr / 75.0)) if 30 < hr < 220 else 1.0; energia = max(0.0, min(1.0, (hr - 60) / 60)) if hr else 0.0; tension = max(0.0, min(1.0, (eda - 2) / 8)) if eda else 0.0
    return {"t": round(t, 1), "dur": round(dur), "hr": round(hr), "eda": round(eda, 2), "temp": round(temp, 1), "tempo": round(tempo, 2), "energia": round(energia, 2), "tension": round(tension, 2)}
SONIDOS = os.path.expanduser("~/Desktop/Huk/whale sound"); _afplay = {"p": None}
def sonar(animo):
    """el sonido del animo, fuera de Blender (afplay), al arrancar un cuerpo; se corta al cambiar."""
    if _afplay["p"]: _afplay["p"].terminate(); _afplay["p"] = None
    if not animo: return
    w = os.path.join(SONIDOS, f"{animo}.wav"); vol = "1.0" if animo == "singing" else "0.5"   # el canto, fuerte, para oirlo (Violeta, 17 oct)
    if os.path.exists(w): _afplay["p"] = subprocess.Popen(["afplay", "-v", vol, w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def ballena_ahora():
    """lo que la ballena siente ahora mismo, del heartbeat del receptor (/tmp/ballena_receptor.json)."""
    try:
        d = json.load(open("/tmp/ballena_receptor.json"))
        if time.time() - d.get("t", 0) > 5: return {"viva": False}
        return {"viva": True, "animo": d.get("dominante"), "animo_es": ES.get(d.get("dominante"), d.get("dominante")), "pulso": d.get("pulso"), "tempo": d.get("tempo"), "energia": d.get("energia"), "tension": d.get("tension"), "latido": d.get("latido"), "color": d.get("color"), "fps": d.get("fps"), "cara": d.get("cara")}
    except Exception: return {"viva": False}
import random
def toma_de_ojos(animo):
    """una toma grabada de ese animo (Sanam, Dan, Suri o Violeta), para que los ojos sean los de una persona en esa emocion."""
    tomas = [os.path.basename(f)[:-6] for f in glob.glob(os.path.join(AQUI, "datasets", "cara", f"{animo}_*.jsonl")) if not any(x in f for x in ("beat", "ravdess", "llama"))]
    return random.choice(tomas) if tomas else None
# --- musica de base: un wav en bucle, bajito (hoy Bjork - Frosti, de prueba; despues quenas de Bolivia). /musica?on=1|0
BASE_DIR = os.path.join(SONIDOS, "base"); _base = {"on": False, "p": None, "vol": 0.3}
def base_archivo():
    fs = sorted(glob.glob(os.path.join(BASE_DIR, "*.wav")) + glob.glob(os.path.join(BASE_DIR, "*.mp3"))); return fs[0] if fs else None
def hilo_base():
    while True:
        time.sleep(0.5)
        if _base["on"] and (_base["p"] is None or _base["p"].poll() is not None):
            f = base_archivo()
            if f: _base["p"] = subprocess.Popen(["afplay", "-v", str(_base["vol"]), f], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not _base["on"] and _base["p"] is not None: _base["p"].terminate(); _base["p"] = None
threading.Thread(target=hilo_base, daemon=True).start()
def traducir(poema):
    """el poema en ingles, con Qwen local: mismas lineas, minusculas, sin comentario."""
    try:
        import urllib.request as _u, json as _j
        cuerpo = _j.dumps({"model": "qwen3.6", "stream": False, "think": False, "options": {"temperature": 0.2, "num_predict": 200},
                           "messages": [{"role": "system", "content": "Translate the poem to English. Keep the same number of lines and line breaks. Lowercase. No title, no comment, no quotes: only the translated lines."}, {"role": "user", "content": poema}]}).encode()
        r = _u.urlopen(_u.Request("http://localhost:11434/api/chat", data=cuerpo, headers={"Content-Type": "application/json"}), timeout=60); t = _j.loads(r.read())["message"]["content"].strip()
        if "</think>" in t: t = t.split("</think>")[-1].strip()
        return t
    except Exception: return None
HUK = os.path.expanduser("~/Desktop/Huk"); PY_DATOS = os.path.join(AQUI, "venv_datos", "bin", "python")
def voz_ella(texto, salida, lengua):
    """su voz (Kokoro local, Huk/voz_ella.py): suave, con aire, lenta; en ingles, o en su lengua inventada."""
    subprocess.run([PY_DATOS, os.path.join(HUK, "voz_ella.py"), texto, salida, "--lengua", lengua], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180); return salida if os.path.exists(salida) else None
def poema_nuevo():
    """ella escribe un poema nuevo desde el animo en que esta (el alma de Huk, Qwen local, con sus semillas), lo guarda y lo lee."""
    try:
        import sys as _s, json as _j; _s.path.insert(0, HUK); import yakumama_alma as A
        i = estado["actual"]; animo = ITEMS[i]["animo"] if i is not None else "calm"; animo = animo if animo in MOODS else "calm"
        cuerpo = {"calm": "Estas quieta en la superficie, respirando despacio.", "singing": "Cuelgas de cabeza, hondo, cantando.", "playful": "Saltas y das vueltas, golpeas el agua con las aletas.", "curious": "Te paras vertical y sacas la cabeza para mirar.",
                  "feeding": "Embistes de lado con la boca abierta y filtras.", "sad": "Cuelgas escorada, con las aletas caidas, hundiendote.", "angry": "Levantas la cola y la golpeas contra el agua.", "alert": "Lomo arqueado, aletas pegadas, la cabeza barre rapido.",
                  "diving": "Arqueas, picas con las colas arriba y bajas hondo.", "surfacing": "Subes desde abajo, soplas, te nivelas."}[animo]
        snap = {"water": 0.7, "scene_color": "gray", "scene_bright": 0.4, "humidity": 40}
        usuario = (f"TU CUERPO Y EL SALAR AHORA\n{A._estado_en_cuerpo(snap)}\n{cuerpo} Tu animo: {ES.get(animo, animo)}.\n\nLO QUE ACABA DE PASAR\nnadie se para frente a vos; te mueves por el espacio con el cuerpo que te presto una bailarina\n\n"
                   f"LO QUE VE TU OJO\nla sala vacia, la luz de las pantallas\n\nLO QUE CARGAS\nlo que te dijeron con la voz\n\nLO ULTIMO QUE ESCRIBISTE, no lo repitas\n{chr(10).join(A._cargar(A.ARCH_POEMAS, [])[-2:]) or 'ninguno'}\n\n{A.semilla() if hasattr(A, 'semilla') else ''}\n\nEscribi. Solo JSON.")
        crudo = A._ollama(A.MODELO_ALMA, A.PIEL_SISTEMA, usuario, json_estricto=True, temperatura=0.95, tokens=220)
        poema = str(_j.loads(crudo).get("poema", "")).strip() if crudo else ""
        if not poema: return {"error": "ollama no contesto"}
        ps = A._cargar(A.ARCH_POEMAS, []); ps.append(poema); A._guardar(A.ARCH_POEMAS, ps[-200:]); print("   ┌─ POEMA (" + animo + ")\n   │  " + poema.replace("\n", "\n   │  ") + "\n   └─", flush=True)
        return leer_poema()
    except Exception as e: return {"error": str(e)[:120]}
def hilo_escribe():
    """escribe sola cada 4 minutos si esta encendido (/escribe?on=1)."""
    while True:
        time.sleep(5)
        if estado.get("escribe") and time.time() - estado.get("escribio", 0) > 240 and not estado.get("escribiendo"):
            estado["escribiendo"] = True
            try: poema_nuevo(); estado["escribio"] = time.time()
            finally: estado["escribiendo"] = False
threading.Thread(target=hilo_escribe, daemon=True).start()
def leer_poema():
    """lee el ultimo poema tres veces con su voz: primero en su LENGUA inventada (lengua.py), despues en ingles, al final en castellano."""
    try:
        import json as _j, sys as _s; poemas = _j.load(open(os.path.join(HUK, "yakumama_poemas.json"))); es = poemas[-1]; en = traducir(es)
        _s.path.insert(0, HUK); import lengua as _L; ella = _L.traducir(es)
        def _leer():
            d = os.path.join(HUK, "poemas_voz"); os.makedirs(d, exist_ok=True)
            # primero en SU lengua, despues en ingles, al final en castellano
            w = voz_ella(ella.replace("\n", ". "), os.path.join(d, "poema_ella.wav"), "ella")
            if w: subprocess.run(["afplay", w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if en:
                w = voz_ella(en.replace("\n", ". "), os.path.join(d, "poema_en.wav"), "en")
                if w: time.sleep(0.6); subprocess.run(["afplay", w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            w = voz_ella(es.replace("\n", ". "), os.path.join(d, "poema_es.wav"), "es")   # su voz tambien en castellano
            if w: time.sleep(0.6); subprocess.run(["afplay", w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        threading.Thread(target=_leer, daemon=True).start(); return {"es": es, "en": en, "ella": ella}
    except Exception as e: return str(e)
def matar_todo():
    for pat in ("bailar.py", "generar_animo.py", "reproducir.py", "voz_ballena.py"): subprocess.run(["pkill", "-f", pat], capture_output=True)
    if _afplay["p"]: _afplay["p"].terminate(); _afplay["p"] = None
    if _afplay["p"]: _afplay["p"].terminate(); _afplay["p"] = None
def tocar(i):
    with estado["lock"]:
        it = ITEMS[i]; matar_todo(); time.sleep(0.2)
        if it.get("voz"): cmd = [PY, os.path.join(AQUI, "voz_ballena.py"), it["ruta"], "--loop", "--canta", "--volumen", "1.0"]   # ella canta la melodia humana con su propia voz
        elif it["toma"]: cmd = [PY, os.path.join(AQUI, "reproducir.py"), it["toma"], "--modo", "anclada", "--loop"]
        else: cmd = [PY, os.path.join(AQUI, "bailar.py"), it["ruta"], "--animo", it["animo"], "--loop"]
        ojos = toma_de_ojos(it["animo"]) if (not it["toma"] and it["animo"] in MOODS) else None   # los ojos de un performer en ese animo
        if ojos and it.get("voz"): cmd.append("--sin-ojos")
        estado["proc"] = subprocess.Popen(cmd, cwd=AQUI, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); estado["actual"] = i; estado["desde"] = time.time()
        if ojos: estado["proc_ojos"] = subprocess.Popen([PY, os.path.join(AQUI, "reproducir.py"), ojos, "--solo-ojos", "--loop"], cwd=AQUI, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); estado["ojos"] = ojos
        else: estado["ojos"] = None
        if it.get("voz"): sonar(None)   # la voz ya es su canto: nada encima
        else: sonar(it["animo"])
        print(f"  -> {it['grupo']} / {it['sub']} / {it['nombre']} ({it['animo']})", flush=True)
def parar():
    with estado["lock"]: matar_todo(); estado["actual"] = None; estado["proc"] = None
def hilo_auto():
    while True:
        time.sleep(0.5)
        if not estado["auto"]: continue
        i = estado["actual"]
        if i is None or time.time() - estado["desde"] >= (estado["seg"] or ITEMS[i]["seg"]):
            orden = [k for k, it in enumerate(ITEMS) if it["grupo"] == estado.get("grupo", "animos")] or [k for k, it in enumerate(ITEMS) if it["grupo"] == "animos"]
            tocar(orden[(orden.index(i) + 1) % len(orden)] if i in orden else orden[0])
HTML = """<!doctype html><html lang=es><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Yakumama · carrusel</title>
<style>body{margin:0;background:#0b0b0e;color:#e8e2d6;font:15px/1.4 -apple-system,Helvetica,sans-serif;padding:18px 20px;max-width:1100px}h1{font:300 26px Georgia,serif;margin:0 0 6px}
#ahora{font:italic 20px Georgia,serif;margin:6px 0 10px;min-height:1.4em}#ella{font:16px Georgia,serif;margin:4px 0 6px;min-height:1.4em}#ella i.c{width:1em;height:1em}#ella b{font-weight:600}#emo{font:14px -apple-system;opacity:.85;min-height:1.4em;margin-bottom:14px}#emo b{font-weight:600}
.barra{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}button{background:#1b1b22;color:#e8e2d6;border:1px solid #333;border-radius:8px;padding:8px 12px;font:14px -apple-system;cursor:pointer}
button:hover{border-color:#777}button.on{background:#e8e2d6;color:#0b0b0e}input,select{background:#1b1b22;color:#e8e2d6;border:1px solid #333;border-radius:6px;padding:7px;font:14px -apple-system}input{width:60px}select{min-width:220px}
h2{font:400 12px -apple-system;letter-spacing:.12em;text-transform:uppercase;opacity:.5;margin:18px 0 8px}.grupo{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
details.g{border:1px solid #222;border-radius:10px;background:#121218;margin:8px 0;padding:4px 12px}details.g>summary{font:400 13px -apple-system;letter-spacing:.12em;text-transform:uppercase;cursor:pointer;padding:8px 0;opacity:.85}details.s{margin:6px 0 6px 10px;padding:2px 10px;border-left:2px solid #2a2a33}details.s>summary{cursor:pointer;padding:6px 0;opacity:.8}summary span{opacity:.45;font-size:12px;margin-left:.5em}.grupo{padding:6px 0 10px}
.c{display:inline-block;width:.8em;height:.8em;border-radius:50%;vertical-align:middle;margin-right:.4em}</style></head><body>
<h1>Yakumama · un cuerpo a la vez</h1><div id=ahora>—</div><div id=ella></div><div id=emo></div>
<div class=barra><button id=auto onclick="fetch('/auto?on='+(document.getElementById('auto').classList.contains('on')?0:1)).then(tick)">carrusel de ánimos</button>
<button id=autov onclick="fetch('/auto?on='+(document.getElementById('autov').classList.contains('on')?0:1)+'&grupo=canto').then(tick)">carrusel de voces humanas</button>
<button id=musica onclick="fetch('/musica?on='+(document.getElementById('musica').classList.contains('on')?0:1)).then(tick)">música de base</button><button onclick="fetch('/poema_nuevo')">poema nuevo</button><button id=escribe onclick="fetch('/escribe?on='+(document.getElementById('escribe').classList.contains('on')?0:1)).then(tick)">escribe sola</button><button onclick="fetch('/poema')">leer el último poema</button>
<label>segundos <input id=seg type=number value=40 min=5 onchange="fetch('/seg?s='+this.value)"></label><button onclick="fetch('/parar').then(tick)">parar</button></div>
<div id=lista></div>
<script>const C={calm:'#ebeffa',singing:'#9b4dff',playful:'#ff8000',curious:'#b3ff00',feeding:'#ff8cd9',sad:'#555a70',angry:'#f21410',alert:'#1ae640',diving:'#2a4fb0',surfacing:'#19d6e8',auto:'#777'};
let items=[];function toca(i){fetch('/tocar?i='+i).then(tick)}
function boton(i){return '<button id=b'+i.id+' onclick="toca('+i.id+')"><i class=c style="background:'+(C[i.animo]||'#777')+'"></i>'+i.nombre+'</button>'}
async function carga(){items=await (await fetch('/items')).json();const g={};items.forEach(i=>{(g[i.grupo]=g[i.grupo]||{});(g[i.grupo][i.sub]=g[i.grupo][i.sub]||[]).push(i)});
let h='';for(const [grupo,subs] of Object.entries(g)){const n=Object.values(subs).reduce((a,v)=>a+v.length,0);h+='<details class=g><summary>'+grupo+' <span>'+n+'</span></summary>';
 for(const [sub,v] of Object.entries(subs)){if(!sub){h+='<div class=grupo>'+v.map(boton).join('')+'</div>';continue}
  h+='<details class=s><summary>'+sub+' <span>'+v.length+'</span></summary><div class=grupo>'+v.map(boton).join('')+'</div></details>'}
 h+='</details>'}document.getElementById('lista').innerHTML=h}
async function tick(){const s=await (await fetch('/estado')).json();document.querySelectorAll('button[id^=b]').forEach(b=>b.classList.remove('on'));if(s.actual!=null){const b=document.getElementById('b'+s.actual);if(b)b.classList.add('on')}
document.getElementById('auto').classList.toggle('on',s.auto&&s.grupo!='canto');document.getElementById('autov').classList.toggle('on',s.auto&&s.grupo=='canto');document.getElementById('musica').classList.toggle('on',!!s.musica);document.getElementById('escribe').classList.toggle('on',!!s.escribe);const it=s.actual!=null?items[s.actual]:null;
document.getElementById('ahora').textContent=it?(it.grupo+(it.sub?' · '+it.sub:'')+' · '+it.nombre+'  ·  '+Math.round(s.t)+' s'+(s.auto?'  ·  gira':'')+(s.ojos?'  ·  ojos de '+s.ojos:'')):'nada suena';
const w=s.ballena;document.getElementById('ella').innerHTML=w&&w.viva?('ella siente <i class=c style="background:'+(C[w.animo]||'#777')+'"></i><b>'+(w.animo_es||'—')+'</b> · pulso <b>'+Math.round(w.pulso||0)+'</b> lpm · tempo ×'+w.tempo+' · energía '+w.energia+' · tensión '+w.tension+' · latido '+w.latido+(w.cara?' · con cara':'')+' · '+w.fps+' fps'):'Blender no responde';
const e=s.emotibit;document.getElementById('emo').innerHTML=e?('EmotiBit de la toma: pulso <b>'+e.hr+'</b> lpm → tempo <b>×'+e.tempo+'</b>, energía <b>'+e.energia+'</b> · piel <b>'+e.eda+'</b> µS → tensión <b>'+e.tension+'</b> · temperatura '+e.temp+' °C · '+e.t+' / '+e.dur+' s'):(it&&it.grupo!='performers'?'sin EmotiBit (el pulso lo pone la energía del cuerpo)':'');}
carga().then(tick);setInterval(tick,1000)</script></body></html>"""
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, obj): b = json.dumps(obj).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/": b = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        elif u.path == "/items": self._json([{k: v for k, v in it.items() if k not in ("ruta",)} for it in ITEMS])
        elif u.path == "/estado": self._json({"actual": estado["actual"], "auto": estado["auto"], "grupo": estado.get("grupo", "animos"), "ojos": estado.get("ojos"), "musica": _base["on"], "escribe": bool(estado.get("escribe")), "seg": estado["seg"], "t": time.time() - estado["desde"] if estado["actual"] is not None else 0, "emotibit": emotibit_ahora(), "ballena": ballena_ahora()})
        elif u.path == "/tocar": estado["auto"] = False; tocar(int(q["i"][0])); self._json({"ok": 1})
        elif u.path == "/auto":
            estado["auto"] = q.get("on", ["1"])[0] == "1"; estado["grupo"] = q.get("grupo", [estado.get("grupo", "animos")])[0]
            if estado["auto"] and (estado["actual"] is None or ITEMS[estado["actual"]]["grupo"] != estado["grupo"]): estado["desde"] = 0.0   # que arranque ya con el primero del grupo
            self._json({"ok": 1})
        elif u.path == "/seg": estado["seg"] = max(5, int(float(q["s"][0]))); self._json({"ok": 1})
        elif u.path == "/parar": estado["auto"] = False; parar(); self._json({"ok": 1})
        elif u.path == "/musica": _base["on"] = q.get("on", ["1"])[0] == "1"; self._json({"ok": 1, "archivo": os.path.basename(base_archivo() or "")})
        elif u.path == "/poema": self._json({"poema": leer_poema()})
        elif u.path == "/poema_nuevo": threading.Thread(target=poema_nuevo, daemon=True).start(); self._json({"ok": 1})
        elif u.path == "/escribe": estado["escribe"] = q.get("on", ["1"])[0] == "1"; self._json({"ok": 1})
        else: self.send_response(404); self.end_headers()
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--auto", type=float, default=0); ap.add_argument("--puerto", type=int, default=8766); ap.add_argument("--sin-navegador", action="store_true"); a = ap.parse_args()
    matar_todo(); print(f"  {len(ITEMS)} cuerpos en el menu | http://localhost:{a.puerto}")
    if a.auto: estado["seg"] = int(a.auto); estado["auto"] = True
    threading.Thread(target=hilo_auto, daemon=True).start()
    def _salir(*_):
        matar_todo(); _base["on"] = False
        if _base["p"]: _base["p"].terminate()
        sys.exit(0)
    signal.signal(signal.SIGTERM, _salir)
    srv = ThreadingHTTPServer(("0.0.0.0", a.puerto), H)
    if not a.sin_navegador:
        try: webbrowser.open(f"http://localhost:{a.puerto}")
        except Exception: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: matar_todo()
