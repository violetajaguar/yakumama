"""dibujo_salar.py - SHE DRAWS NAZCA LINES ON THE SALAR (18 Oct 2026). When her body decision says "dibujar" (decisiones.py: alone and
calm, curious or singing for a minute; or a known visitor standing still for two minutes), she picks a figure, flies low along its
waypoints with straight runs and sharp turns, and a line of salt and gold grows on the salar behind her. Figures: a square spiral, a
zigzag band, a hexagonal labyrinth (the plotter video), the Nazca whale, and THE FACE OF SOMEONE SHE REMEMBERS: her memory keeps only
the 210 distances between 21 face points (never an image); classical scaling recovers the shape of those points, and she draws them as
straight strokes in that person's own proportions. The forget button erases the memory, so the face can never be drawn again.
Loaded by receptor_ballena.py (like hermana_blender.py). Hooks in the receiver: driver_namespace["_ballena_destino"] (where she must go)
and ["_ballena_pos"] (where she is). Reads /tmp/ballena_cerebro.json (the decision), writes /tmp/ballena_dibujo.json (what she draws).
Test by hand: echo '{"figura": "laberinto"}' > /tmp/ballena_dibuja_ahora.json   (figura: espiral | zigzag | laberinto | ballena | cara)"""
import bpy, os, sys, json, time, math, random
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI) if AQUI not in sys.path else None; CEREBRO = "/tmp/ballena_cerebro.json"; ESTADO = "/tmp/ballena_dibujo.json"; AHORA = "/tmp/ballena_dibuja_ahora.json"
MEMORIA = os.path.join(AQUI, "datasets", "memoria.json")
R = 2.4            # radius of a drawing, in her units (the salar's open centre)
Z_LINEA = -2.52    # just above the salar (object Salar at z -2.6)
Z_VUELO = -1.6     # how low she flies while drawing (relative to her house height)
LLEGA = 0.18       # distance to a waypoint that counts as reached
RAPIDEZ = 0.35     # her speed toward each waypoint (0..1, the receiver's scale)
ENFRIAR_S = 480.0  # minimum rest between two drawings
VIDA_S = 3600.0    # a drawing fades after an hour
GROSOR = 0.035
st = {"activo": False, "figura": "", "puntos": [], "i": 0, "t0": 0.0, "fin_t": 0.0, "curva": None, "spline": None, "ultimo": None, "persona": None, "err": "", "leido": 0.0}
from figuras_nazca import PUNTOS, FIGURAS, cara, espiral, zigzag, laberinto, ballena, _idx   # the figures live in figuras_nazca.py (shared with the brain)
# ---------------- the line on the salar
def _material():
    m = bpy.data.materials.get("linea_salar")
    if m: return m
    m = bpy.data.materials.new("linea_salar"); m.use_nodes = True; n = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    n.inputs["Base Color"].default_value = (1.0, 0.86, 0.45, 1.0); ec = n.inputs.get("Emission Color") or n.inputs.get("Emission"); ec.default_value = (1.0, 0.8, 0.35, 1.0); n.inputs["Emission Strength"].default_value = 2.5
    return m
def _nueva_curva(nombre):
    cd = bpy.data.curves.new(nombre, 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = GROSOR; cd.bevel_resolution = 2; cd.materials.append(_material())
    ob = bpy.data.objects.new(nombre, cd); bpy.context.scene.collection.objects.link(ob); return ob
def _nuevo_trazo():
    sp = st["curva"].data.splines.new('POLY'); st["spline"] = sp; st["ultimo"] = None
def _punto(x, y):
    sp = st["spline"]
    if sp is None: _nuevo_trazo(); sp = st["spline"]
    if st["ultimo"] is None: sp.points[0].co = (x, y, Z_LINEA, 1.0)
    else: sp.points.add(1); sp.points[-1].co = (x, y, Z_LINEA, 1.0)
    st["ultimo"] = (x, y)
def _persona_conocida(cer):
    pid = cer.get("id_persona")
    if not pid: return None, None
    try: p = json.load(open(MEMORIA)).get(pid)
    except Exception: p = None
    return (pid, p["firma"]) if p and p.get("firma") and len(p["firma"]) == 210 else (None, None)
def empezar(figura, cer=None):
    cer = cer or {}; pts = None; st["persona"] = None
    if figura == "cara":
        pid, firma = _persona_conocida(cer)
        if firma: pts = cara(firma); st["persona"] = pid
        else: figura = random.choice(list(FIGURAS))
    if pts is None: pts = FIGURAS.get(figura, espiral)()
    for ob in [o for o in bpy.data.objects if o.name.startswith("Dibujo_salar")]: bpy.data.objects.remove(ob, do_unlink=True)   # one drawing at a time
    st.update(activo=True, figura=figura, puntos=[(x * R, y * R, p) for x, y, p in pts], i=0, t0=time.time(), curva=_nueva_curva("Dibujo_salar"), spline=None, ultimo=None)
    print(f"  dibujo en el salar: {figura}" + (f" (la cara de {st['persona']})" if st["persona"] else "") + f", {len(st['puntos'])} puntos")
def terminar():
    st["activo"] = False; st["fin_t"] = time.time(); bpy.app.driver_namespace.pop("_ballena_destino", None)
def paso():
    try:
        ns = bpy.app.driver_namespace; t = time.time()
        if t - st["leido"] > 1.0:   # the decision, once a second; a hand trigger any time
            st["leido"] = t
            try: cer = json.load(open(CEREBRO))
            except Exception: cer = {}
            if os.path.exists(AHORA):
                try: pedido = json.load(open(AHORA))
                except Exception: pedido = {}
                os.remove(AHORA); empezar(str(pedido.get("figura") or "laberinto"), cer)
            elif not st["activo"] and t - st["fin_t"] > ENFRIAR_S and (cer.get("decision") or {}).get("con_cuerpo") == "dibujar" and t - cer.get("t", 0) < 10:
                empezar("cara" if cer.get("conocida") else random.choice(list(FIGURAS)), cer)
            elif st["activo"] and (cer.get("fijo") in ("tiron", "palma", "no_pez", "lente")): terminar()   # a refusal interrupts the drawing
            if st["curva"] and not st["activo"] and st["fin_t"] and t - st["fin_t"] > VIDA_S:   # the salt wind erases it
                try: bpy.data.objects.remove(st["curva"], do_unlink=True)
                except Exception: pass
                st["curva"] = None
            try: json.dump({"t": t, "activo": st["activo"], "figura": st["figura"], "persona": st["persona"], "progreso": round(st["i"] / max(1, len(st["puntos"])), 2) if st["activo"] else None, "err": st["err"]}, open(ESTADO, "w"))
            except Exception: pass
        if not st["activo"]: return 1.0 / 30.0
        pos = ns.get("_ballena_pos")
        if not pos: return 1.0 / 30.0
        x, y, pluma = st["puntos"][st["i"]]
        ns["_ballena_destino"] = {"x": x, "y": y, "z": Z_VUELO, "rap": RAPIDEZ, "t": t}
        px, py = pos[0], pos[1]
        if pluma:   # the line follows her actual path toward the waypoint
            if st["ultimo"] is None or math.hypot(px - st["ultimo"][0], py - st["ultimo"][1]) > 0.06: _punto(px, py)
        if math.hypot(px - x, py - y) < LLEGA:
            if pluma: _punto(x, y)
            st["i"] += 1
            if st["i"] >= len(st["puntos"]): terminar(); print("  dibujo terminado:", st["figura"]); return 1.0 / 30.0
            if not st["puntos"][st["i"]][2]: st["spline"] = None; st["ultimo"] = None   # pen up: next stroke starts a new spline
            elif st["ultimo"] is None: _punto(x, y)
    except Exception as e:
        st["err"] = str(e)
    return 1.0 / 30.0
def instalar():
    ns = bpy.app.driver_namespace
    if "_dibujo_paso" in ns and bpy.app.timers.is_registered(ns["_dibujo_paso"]): bpy.app.timers.unregister(ns["_dibujo_paso"])
    ns["_dibujo_paso"] = paso; bpy.app.timers.register(paso, first_interval=0.5); print("  dibujo en el salar: instalado (figuras: espiral, zigzag, laberinto, ballena, cara)")
