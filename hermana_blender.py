"""hermana_blender.py - THE GOLDEN SISTER inside whale.blend (18 Oct 2026, 'pretend the golden whale is the sister').
Appends the robot sister (modelos/hermana_dorada.blend: resin head and jaw, printed fins, turbine, the gold nazca crown, the wire
nervures, the LED spine, nine touch lines) next to the digital whale and drives her from the same packets the receiver gets:
  - her resin and LED spine glow with the digital whale's colour (the lights inside the real sister do the same)
  - the turbine spins at the tail speed; the jaw opens when a fish is offered (ofrenda = pez)
  - the gold crown lights when the jewel is touched; the touch lines light one per flower stem touched
  - a refusal (palm over the flowers, pull on the jewel, a non-fish in the mouth): everything dark, turbine stopped, jaw shut, 6 s
Loaded by receptor_ballena.py at the end of its file; it writes /tmp/hermana_dorada.json so the state can be checked from outside."""
import bpy, os, json, time, math
AQUI = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.join(AQUI, "modelos", "hermana_dorada.blend"); ESTADO = "/tmp/hermana_dorada.json"
LUGAR = (2.6, -1.4, -0.35); ESCALA = 0.008; GIRO_Z = math.radians(90)
CUERPO = ("resina_cabeza", "resina_impresa"); LEDS = ("espina_led", "ojo_led"); CORONA = "nazca"; TOQUES = [f"toque_{i}" for i in range(1, 10)]
st = {"ang": 0.0, "oscuro_hasta": 0.0, "come_hasta": 0.0, "t": 0.0, "ok": False, "err": ""}
def _principled(nombre):
    m = bpy.data.materials.get(nombre)
    if not m or not m.use_nodes: return None
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
def _emision(nombre, rgb, fuerza):
    n = _principled(nombre)
    if not n: return
    ec = n.inputs.get("Emission Color") or n.inputs.get("Emission"); es = n.inputs.get("Emission Strength")
    if ec is not None: ec.default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    if es is not None: es.default_value = fuerza
def _base(nombre, rgb):
    n = _principled(nombre)
    if n and n.inputs.get("Base Color") is not None: n.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
def cargar():
    if "Hermana" in bpy.data.collections: st["ok"] = True; return True
    if not os.path.exists(LIB): st["err"] = "no library"; return False
    with bpy.data.libraries.load(LIB, link=False) as (src, dst): dst.collections = [c for c in src.collections if c == "Hermana"]
    col = next((c for c in dst.collections if c), None)
    if col is None: st["err"] = "no collection"; return False
    bpy.context.scene.collection.children.link(col)
    raiz = bpy.data.objects.get("Hermana_raiz")
    if raiz: raiz.location = LUGAR; raiz.scale = (ESCALA,) * 3; raiz.rotation_euler = (0.0, 0.0, GIRO_Z)
    st["ok"] = True; print(f"  hermana dorada: {len(col.all_objects)} objetos en {LUGAR}"); return True
def color_ballena():
    n = _principled("ballena")
    try: return tuple(n.inputs["Base Color"].default_value[:3]) if n else (0.5, 0.5, 0.5)
    except Exception: return (0.5, 0.5, 0.5)
def paso():
    try:
        if not st["ok"] and not cargar(): return 2.0
        ns = bpy.app.driver_namespace; d = ns.get("_ballena_d") or {}; t = time.time(); dt = min(0.1, t - st["t"]) if st["t"] else 0.033; st["t"] = t
        tacto = float(d.get("tacto") or 0); zona = str(d.get("tacto_zona") or ""); ofrenda = str(d.get("ofrenda") or ""); flores_n = int(d.get("flores_n") or 0)
        if (tacto > 0.85 and zona in ("flores", "joya")) or ofrenda == "no_pez": st["oscuro_hasta"] = t + 6.0
        if ofrenda == "pez" and t > st["oscuro_hasta"]: st["come_hasta"] = t + 6.0
        oscuro = t < st["oscuro_hasta"]; come = t < st["come_hasta"]
        col = (0.02, 0.02, 0.03) if oscuro else color_ballena()
        for m in CUERPO: _base(m, col); _emision(m, col, 0.0 if oscuro else 0.8)
        vista = bool(d.get("ve_hermana"))   # she is being held up in front of the eye: she glows
        for m in LEDS: _emision(m, col, 0.0 if oscuro else (5.0 if vista else 2.0))
        _emision(CORONA, (1.0, 0.85, 0.4), 0.0 if oscuro else (5.0 if (zona == "joya" and tacto > 0.3) else (2.0 if vista else 0.4)))
        for i, m in enumerate(TOQUES): _emision(m, (1.0, 1.0, 1.0), 3.0 if (not oscuro and zona == "flores" and tacto > 0.3 and i < max(1, flores_n)) else 0.0)
        vel = 0.0 if oscuro else float(ns.get("_ballena_turbina_vel") or 1.0) * (1.6 if come else 1.0)
        st["ang"] += vel * dt * 3.0; turb = bpy.data.objects.get("P7_turbina")
        if turb: turb.rotation_euler = (0.0, st["ang"], 0.0)
        mand = bpy.data.objects.get("P1_mandibula")
        if mand: mand.rotation_euler = (math.radians(-18 if come else 0), 0.0, 0.0)
        if int(t * 4) != int((t - dt) * 4):
            try: json.dump({"t": t, "ok": st["ok"], "oscuro": oscuro, "come": come, "zona": zona, "tacto": tacto, "ofrenda": ofrenda, "flores_n": flores_n, "vel": vel, "color": [round(c, 2) for c in col]}, open(ESTADO, "w"))
            except Exception: pass
    except Exception as e:
        st["err"] = str(e)
        try: json.dump({"t": time.time(), "ok": st["ok"], "err": st["err"]}, open(ESTADO, "w"))
        except Exception: pass
    return 1.0 / 30.0
def instalar():
    ns = bpy.app.driver_namespace
    if "_hermana_paso" in ns and bpy.app.timers.is_registered(ns["_hermana_paso"]): bpy.app.timers.unregister(ns["_hermana_paso"])
    ns["_hermana_paso"] = paso; bpy.app.timers.register(paso, first_interval=0.5); print("  hermana dorada: instalada (modelos/hermana_dorada.blend)")
