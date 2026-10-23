#!/usr/bin/env python3
"""ventana_ofrendas.py - a screen to watch her with the 29 offerings (20 Oct 2026). http://localhost:8766
Left: what her eye sees in the hands (last looks), the offering her brain took, its reaction, her mood and her six answers, come/rehusa/lente,
and what Dan's brain renders. Right: the 29 creatures; the one in her mouth lit up; the ones already tried tonight ticked (logs/ofrendas_probadas.json).
Reads files only (/tmp/ballena_cerebro.json, logs/ojo.log, logs/ballena_td.log, the recorder's /ventana_estado): it touches nothing."""
import json, os, re, time, subprocess, urllib.request, http.server, socketserver, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
CAT = json.load(open(os.path.join(AQUI, "docs", "ofrendas", "ofrendas.json")))["criaturas"]
sys.path.insert(0, AQUI)
try:
    from reacciones_ofrendas import REACCIONES
    EFX = {str(n): {"animo": r.get("animo"), "come": bool(r.get("come")), "dibujo": bool(r.get("dibujo")), "voz": r.get("voz")} for n, r in REACCIONES.items()}
except Exception: EFX = {}
PROBADAS = os.path.join(AQUI, "logs", "ofrendas_probadas.json")
try: probadas = json.load(open(PROBADAS))
except Exception: probadas = {}
def tail(f, n):
    try: return subprocess.run(["tail", "-n", str(n), os.path.join(AQUI, "logs", f)], capture_output=True, text=True).stdout
    except Exception: return ""
def estado():
    try: c = json.load(open("/tmp/ballena_cerebro.json"))
    except Exception: c = {}
    try: w = json.load(urllib.request.urlopen("http://127.0.0.1:8765/ventana_estado", timeout=1))
    except Exception: w = {}
    miradas = re.findall(r"\[ojo manos\] (\S+) p=([0-9.]+) mano=(\d)(?: -> (\S+)| \(sin voto\))", tail("ojo.log", 40))[-6:]
    td = re.findall(r"mood \S+ → (\S+)\s+her brain \((\w+)\)", tail("ballena_td.log", 60)); td = td[-1] if td else ("-", "-")
    dib = re.findall(r"drawing: ([^\n]+)", tail("ballena_td.log", 400)); dib = dib[-1][:60] if dib else ""
    oid = c.get("ofrenda_id")
    if oid: probadas[str(oid)] = {"t": time.time(), "reaccion": c.get("reaccion")}; json.dump(probadas, open(PROBADAS, "w"))
    return {"t": time.strftime("%H:%M:%S"), "cerebro": c, "ventana": {"objeto": w.get("objeto"), "lineas": [l.get("texto", "")[:120] for l in (w.get("lineas") or [])[-3:]]},
            "miradas": [{"clase": m[0], "p": float(m[1]), "mano": m[2], "voto": m[3] or ""} for m in miradas], "td": {"animo": td[0], "fuente": td[1], "dibujo": dib},
            "probadas": probadas}
HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Yakumama · las 29 ofrendas</title><style>
body{margin:0;background:#07080f;color:#e8e6df;font:15px/1.4 -apple-system,Helvetica,Arial}#g{display:grid;grid-template-columns:440px 1fr;height:100vh}
#l{padding:18px;border-right:1px solid #223;overflow:auto}#r{padding:14px;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;align-content:start}
h1{font-size:15px;letter-spacing:.2em;color:#c9a24a;margin:0 0 12px}.k{color:#8b8fa3;font-size:12px;text-transform:uppercase;letter-spacing:.1em;margin-top:14px}
.big{font-size:26px;font-weight:600}.mood{font-size:34px;font-weight:700;color:#c9a24a}.card{background:#10121c;border:1px solid #223;border-radius:8px;padding:6px;position:relative}
.card img{width:100%;height:110px;object-fit:cover;border-radius:5px;filter:saturate(.7)}.card .n{font-size:12px;margin-top:4px;min-height:34px}.card .rx{font-size:11px;color:#8b8fa3}
.card.on{border-color:#ffcf5a;box-shadow:0 0 22px #ffcf5a88}.card.on img{filter:none}.card.ok::after{content:"✓";position:absolute;top:6px;right:9px;color:#5ad27a;font-weight:700;font-size:18px}
.mir{font-family:Menlo,monospace;font-size:12px;color:#aab}.rehusa{color:#ff6a5a;font-weight:700}.come{color:#5ad27a;font-weight:700}.lente{color:#ff6a5a}.dec span{display:inline-block;margin:2px 10px 2px 0}
.lin{color:#c9a24a;font-style:italic;font-size:13px}</style></head><body><div id="ban" style="display:none;position:fixed;left:0;right:0;top:0;z-index:9;background:#0b0c16ee;border-bottom:2px solid #ffcf5a;padding:14px 24px"><div id="ban1" style="font-size:40px;font-weight:700;color:#ffcf5a"></div><div id="ban2" style="font-size:30px;color:#e8e6df;margin-top:4px"></div></div><div id="g"><div id="l">
<h1>YAKUMAMA · LAS 29 OFRENDAS</h1><div class="k">lo que ve en las manos (últimas miradas)</div><div id="mir" class="mir"></div>
<div class="k">ofrenda en su boca</div><div id="of" class="big">—</div><div id="rx"></div>
<div class="k">su ánimo</div><div id="mood" class="mood">—</div><div id="flags"></div>
<div class="k">sus respuestas</div><div id="dec" class="dec"></div>
<div class="k">lo que escribe</div><div id="lin"></div>
<div class="k">TouchDesigner (cerebro de Dan)</div><div id="td"></div>
<div class="k">probadas esta noche</div><div id="prob"></div></div><div id="r"></div></div>
<script>
const CAT=__CAT__;const R=document.getElementById('r');
for(const c of CAT){const d=document.createElement('div');d.className='card';d.id='c'+c.id;d.innerHTML=`<img src="/img/${c.archivo}"><div class="n"><b>${String(c.id).padStart(2,'0')}</b> ${c.nombre}</div><div class="rx">${c.reaccion?c.reaccion.n+' · '+c.reaccion.texto:''}</div>`;R.appendChild(d);}
async function tick(){try{const s=await (await fetch('/estado')).json();const c=s.cerebro||{};
document.getElementById('mir').innerHTML=(s.miradas||[]).map(m=>`${m.clase} <span style="color:#8b8fa3">p=${m.p.toFixed(2)} mano=${m.mano}</span> ${m.voto?'→ <b>'+m.voto+'</b>':''}`).join('<br>')||'—';
const oid=c.ofrenda_id;const cr=CAT.find(x=>x.id==oid);document.getElementById('of').textContent=cr?String(cr.id).padStart(2,'0')+' · '+cr.nombre:(c.ofrenda==='no_pez'?'algo que no es una ofrenda':'—');
const rx=c.reaccion;document.getElementById('rx').innerHTML=rx?(typeof rx==='object'?`reacción <b>${rx.n}</b>: ${rx.texto||''} <span style="color:#8b8fa3">fase ${rx.fase??''}</span>`:`reacción <b>${rx}</b>: ${(cr&&cr.reaccion)?cr.reaccion.texto:''}`):'';
document.getElementById('mood').textContent=c.animo||'—';const B=document.getElementById('ban');if(cr&&rx){B.style.display='block';document.getElementById('ban1').textContent=String(cr.id).padStart(2,'0')+' · '+cr.nombre.split(' (')[0];document.getElementById('ban2').textContent='reacción '+(typeof rx==='object'?rx.n:rx)+': '+((typeof rx==='object'?rx.texto:null)||(cr.reaccion||{}).texto||'');}else{B.style.display='none';}const f=[];if(c.fijo==='lente'||c.ve_telefono)f.push('<span class="lente">un lente apuntando</span>');if(c.ve_hermana)f.push('<span style="color:#ffcf5a">su hermana dorada en las manos</span>');
if(c.ofrenda==='no_pez')f.push('<span class="rehusa">REHÚSA</span>');if((c.decision||{}).boca==='comer')f.push('<span class="come">COME</span>');if(c.persona)f.push(c.conocida?'conocida':'desconocida');document.getElementById('flags').innerHTML=f.join(' · ');
const d=c.decision||{};document.getElementById('dec').innerHTML=['distancia','con_cuerpo','voz','memoria','color','boca'].map(k=>`<span>${k}: <b>${d[k]||'—'}</b></span>`).join('');
document.getElementById('lin').innerHTML=(s.ventana.lineas||[]).map(l=>`<div class="lin">${l}</div>`).join('')+(s.ventana.objeto?`<div>ventana: <b>${s.ventana.objeto}</b></div>`:'');
document.getElementById('td').innerHTML=`ánimo <b>${s.td.animo}</b> (${s.td.fuente})${s.td.dibujo?'<br>dibujo: '+s.td.dibujo:''}`;
const pr=Object.keys(s.probadas||{});document.getElementById('prob').textContent=pr.length?pr.map(x=>String(x).padStart(2,'0')).sort().join(' · ')+`  (${pr.length}/29)`:'ninguna todavía';
for(const x of CAT){const e=document.getElementById('c'+x.id);e.classList.toggle('on',x.id==oid);e.classList.toggle('ok',pr.includes(String(x.id)));}
if(cr){document.getElementById('c'+cr.id).scrollIntoView({block:'nearest'});}
}catch(e){}}setInterval(tick,1000);tick();
</script></body></html>"""
LISTA = """<!doctype html><html><head><meta charset="utf-8"><title>Yakumama · las 29 reacciones</title><style>
body{margin:0;background:#07080f;color:#e8e6df;font:18px/1.45 -apple-system,Helvetica,Arial;padding:18px 28px}h1{font-size:15px;letter-spacing:.2em;color:#c9a24a;margin:0 0 14px}
.r{display:grid;grid-template-columns:52px 1fr;gap:0 14px;padding:9px 12px;border-left:3px solid #223;margin-bottom:6px;border-radius:0 8px 8px 0}
.r .id{font-size:26px;font-weight:700;color:#8b8fa3}.r .nom{color:#c9a24a;font-size:15px}.r .tx{font-size:22px;font-weight:600}.r .fx{color:#8b8fa3;font-size:14px}
.r.on{background:#1a1706;border-left-color:#ffcf5a;box-shadow:0 0 24px #ffcf5a55}.r.on .id{color:#ffcf5a}.r.ok .id::after{content:" ✓";color:#5ad27a;font-size:16px}
#now{position:sticky;top:0;background:#07080fee;padding:8px 0 12px;font-size:16px;color:#8b8fa3;z-index:2}</style></head><body>
<h1>YAKUMAMA · LAS 29 REACCIONES</h1><div id="now">—</div><div id="L"></div>
<script>const CAT=__CAT__;const EFX=__EFX__;const L=document.getElementById('L');
for(const c of CAT){const r=c.reaccion||{};const e=EFX[String(r.n)]||{};const d=document.createElement('div');d.className='r';d.id='r'+c.id;
d.innerHTML=`<div class="id">${String(c.id).padStart(2,'0')}</div><div><div class="nom">${c.nombre}</div><div class="tx">${r.n?'reacción '+r.n+' · ':''}${r.texto||''}</div><div class="fx">${[e.animo,e.come?'come':'',e.dibujo?'dibuja':'',e.voz||''].filter(Boolean).join(' · ')}</div></div>`;L.appendChild(d);}
async function tick(){try{const s=await (await fetch('/estado')).json();const c=s.cerebro||{};const oid=c.ofrenda_id;const pr=Object.keys(s.probadas||{});
for(const x of CAT){const el=document.getElementById('r'+x.id);el.classList.toggle('on',x.id==oid);el.classList.toggle('ok',pr.includes(String(x.id)));}
const cr=CAT.find(x=>x.id==oid);document.getElementById('now').textContent=cr?`ahora: ${String(cr.id).padStart(2,'0')} · ${cr.nombre.split(' (')[0]} · ánimo ${c.animo||'—'}`:`ahora: nada en su boca · ánimo ${c.animo||'—'}`;
if(cr){const el=document.getElementById('r'+cr.id);const b=el.getBoundingClientRect();if(b.top<80||b.bottom>window.innerHeight-20)el.scrollIntoView({block:'center',behavior:'smooth'});}}catch(e){}}
setInterval(tick,1000);tick();</script></body></html>"""
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/estado"): b = json.dumps(estado()).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
        elif self.path.startswith("/img/"):
            f = os.path.join(AQUI, "docs", "ofrendas", os.path.basename(self.path[5:]))
            if os.path.exists(f): self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.end_headers(); self.wfile.write(open(f, "rb").read())
            else: self.send_response(404); self.end_headers()
        elif self.path.startswith("/lista"): b = LISTA.replace("__CAT__", json.dumps(CAT)).replace("__EFX__", json.dumps(EFX)).encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
        else: b = HTML.replace("__CAT__", json.dumps(CAT)).encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
class S(socketserver.ThreadingTCPServer): allow_reuse_address = True
print(f"   las 29 ofrendas: http://localhost:{PUERTO}  (y en la red, en la ip de esta Mac)", flush=True)
S(("0.0.0.0", PUERTO), H).serve_forever()
