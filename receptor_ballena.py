import bpy, socket, json, time, math, os, random
# receptor_ballena.py = Text.017 de whale.blend + MODO SOLO CARA (Yakumama).
# Si el paquete trae "solo_cara": 1 (tecla c en grabar_ballena.py) la ballena se queda quieta y solo la cara sigue
# al actor: cabeza (head_yaw/head_pitch), boca (jaw_open), parpadeo (blink), cejas (brow_up -> asombrado,
# brow_down -> angry) y mouth_sad -> sad. Sin poses de animo, sin ola de nado, sin aletas, sin turbina, sin nadar.
# Correr en Blender: Text editor > Open > este archivo > Run Script (Alt+P). Reemplaza al receptor que este corriendo.

"""
Ballena — Movement from Brian's poses

10 colors -> 10 emotions -> 10 sounds.

COLOR → MOOD MAP:
  red→angry  orange→playful  yellow→curious  green→feeding
  cyan→surfacing  blue→calm  purple→singing  pink→alert
  white→diving  black→sad

N-panel (press N in 3D viewport, tab "Ballena"):
  Mouth, Tongue
  Auto Turn, Follow Hand, Color Track
  Brain (Qwen) — checkbox: blend in LLM mood weights
  Color Follow — body materials tint toward scene color
  Virtual joystick — drive yaw/pitch from the panel
  Music Volume — base track (Tidal Echoes.mp3) plays continuously
  Sound Volume — mood-triggered whale sounds
  Turbine button
"""

UDP_PORT = 9998
VERSION = "2026-10-17k juguetona naranja brillante, curiosidad limon"
MIRADA_AMP = 0.35   # radianes de giro del ojo con la mirada al maximo (eye_yaw/eye_pitch = ±1)
MIRADA_ESPEJO = False   # True: el actor mira a su derecha y la ballena mira a SU izquierda (como un espejo)
# Ojos: en whale.blend el hueso "eye.R" deforma la malla del ojo IZQUIERDO (x<0) y "eye.L" la del DERECHO (x>0).
# Eje 0 = adelante(+)/atras, eje 2 = arriba(+)/abajo en el izquierdo y al reves en el derecho; eje 1 no se ve.
OJO_IZQ, OJO_DER = 'eye.R', 'eye.L'
SMOOTH = 0.15

# ============================================================
# SOUND LIBRARY
# ============================================================
SOUNDS_DIR = next((d for d in (os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else "", "whale sound"), os.path.expanduser("~/Desktop/Huk/whale sound")) if os.path.isdir(d)), os.path.expanduser("~/Desktop/Huk/whale sound"))   # al lado de whale.blend, o en Huk

SOUNDS = {
    "singing":   ["singing.wav"],
    "playful":   ["playful.wav"],
    "sad":       ["sad.wav"],
    "alert":     ["alert.wav"],
    "feeding":   ["feeding.wav"],
    "curious":   ["curious.wav"],
    "angry":     ["angry.wav"],
    "calm":      ["calm.wav"],
    "diving":    ["diving.wav"],
    "surfacing": ["surfacing.wav"],
}

# Base music — loops continuously under everything else.
# Volume controlled by "Music Volume" slider in the N-panel.
AMBIENT_LOOP = "Tidal Echoes.mp3"

SOUND_COOLDOWN = 4.0

# ============================================================
# COLOR → MOOD
# ============================================================
COLOR_TO_MOOD = {
    "red":     "angry",
    "orange":  "playful",
    "yellow":  "curious",
    "green":   "feeding",
    "cyan":    "surfacing",
    "blue":    "calm",
    "purple":  "singing",
    "pink":    "alert",
    "white":   "diving",
    "black":   "sad",
}

# color de piel por animo (inverso de COLOR_TO_MOOD, aclarado para que siga leyendose como piel)
MOOD_RGB = {   # saturados: se ven desde lejos y en cualquier luz
    "angry":     (0.95, 0.08, 0.06),
    "playful":   (1.00, 0.50, 0.00),   # naranja brillante (curious es amarillo limon: que no se confundan)
    "curious":   (0.70, 1.00, 0.00),   # amarillo limon, verdoso: a 45 grados del naranja de playful en la rueda
    "feeding":   (0.05, 0.80, 0.15),
    "surfacing": (0.00, 0.90, 0.95),
    "calm":      (0.92, 0.94, 0.98),   # plateada, clara
    "singing":   (0.62, 0.10, 0.95),
    "alert":     (1.00, 0.25, 0.65),
    "diving":    (0.02, 0.10, 0.55),
    "sad":       (0.10, 0.12, 0.20),
}
SCENE_COLORS_RGB = {
    "red":     (0.85, 0.15, 0.15),
    "orange":  (0.95, 0.50, 0.10),
    "yellow":  (0.95, 0.85, 0.10),
    "green":   (0.20, 0.75, 0.25),
    "cyan":    (0.20, 0.80, 0.85),
    "blue":    (0.15, 0.30, 0.85),
    "purple":  (0.55, 0.20, 0.80),
    "pink":    (0.95, 0.50, 0.75),
    "white":   (0.90, 0.90, 0.92),
    "black":   (0.05, 0.05, 0.07),
    "gray":    (0.45, 0.45, 0.45),
    "neutral": (0.70, 0.70, 0.75),
}

# ============================================================
# N-PANEL CONTROLS
# ============================================================
YAKUMAMA = globals().get("YAKUMAMA_DIR") or (os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() and __file__ else os.path.expanduser("~/Desktop/Yakumama"))   # la carpeta de este archivo (el add-on la pasa)
def _tomas_items(self, context):
    try: fs = sorted(f[:-6] for f in os.listdir(os.path.join(YAKUMAMA, "datasets", "cara")) if f.endswith(".jsonl"))
    except Exception: fs = []
    return [(f, f, "") for f in fs] or [("", "(sin tomas)", "")]
def _reproduciendo():
    try:
        e = json.load(open("/tmp/ballena_reproduciendo.json"))
        if time.time() - e.get("hora", 0) < 3: return e
    except Exception: pass
    return None
class BallenaProps(bpy.types.PropertyGroup):
    toma: bpy.props.EnumProperty(name="Toma", items=_tomas_items, description="Tramo grabado en datasets/ (cara + cuerpo)")
    modo_toma: bpy.props.EnumProperty(name="Modo", items=[("anclada", "Anclada", "cuerpo entero, sin viajar"), ("cuerpo", "Cuerpo", "cuerpo entero, viaja"), ("cara", "Solo cara", "cuerpo quieto"), ("fija", "Cara, cabeza fija", "solo boca, parpadeo y cejas")], default="anclada")
    loop_toma: bpy.props.BoolProperty(name="Repetir", default=False)
    actor_red: bpy.props.StringProperty(name="Estilo de", default="auto", description="auto = el actor al que mas se parece la visita (parecido del grabador); o un nombre: violeta, sanam, suri, dan; o promedio")
    comportamiento: bpy.props.EnumProperty(name="Comportamiento", default="auto", description="Posicion y movimiento del cuerpo, de las fotos de NOAA (referencias/noaa_comportamientos)", items=[
        ("auto", "Automático (ánimo)", "el animo viene del actor, los colores o el cerebro"),
        ("calm", "calm · logging", "quieta en la superficie, respiracion lenta"),
        ("singing", "singing · canto", "cabeza abajo, casi inmovil, cola apenas levantada"),
        ("playful", "playful · flipper slap + breach", "golpea con las aletas, rola, y salta cada 12 s"),
        ("curious", "curious · spyhopping", "se levanta vertical y gira despacio"),
        ("feeding", "feeding · lunge + snaking", "embiste con la boca abierta y filtra ondulando"),
        ("sad", "sad · colgando", "cabeza y cola caidas, lentisima"),
        ("angry", "angry · lobtailing", "levanta la cola y la golpea"),
        ("alert", "alert · rounding out", "lomo arqueado, cabeza escaneando"),
        ("diving", "diving · high fluking dive", "nariz abajo, cola vertical, en ciclos"),
        ("surfacing", "surfacing · blow", "sube, sopla, se nivela")])
    mouth_scale: bpy.props.FloatProperty(
        name="Mouth", default=1.0, min=0.0, max=3.0, soft_max=2.5)
    tongue_scale: bpy.props.FloatProperty(
        name="Tongue", default=0.0, min=0.0, max=2.0, soft_max=1.5)
    auto_turn_scale: bpy.props.FloatProperty(
        name="Auto Turn", default=0.3, min=0.0, max=2.0, soft_max=1.5)
    follow_hand: bpy.props.FloatProperty(
        name="Follow Hand", default=0.0, min=0.0, max=1.0)
    color_track: bpy.props.FloatProperty(
        name="Color Track", default=0.0, min=0.0, max=1.0,
        description="Turn body yaw toward color's X position (needs color_x from ballena2.py)")
    color_follow: bpy.props.FloatProperty(
        name="Color Follow", default=0.0, min=0.0, max=1.0)
    use_brain: bpy.props.BoolProperty(
        name="Brain (Qwen)", default=False,
        description="Blend in Qwen brain mood weights at 30%. Off = pure color performance.")
    virtual_joy_x: bpy.props.FloatProperty(
        name="V-Joy X", default=0.0, min=-1.0, max=1.0, soft_min=-1.0, soft_max=1.0,
        description="Virtual joystick X (yaw). Combines with real joystick. -1 = full left, +1 = full right.")
    virtual_joy_y: bpy.props.FloatProperty(
        name="V-Joy Y", default=0.0, min=-1.0, max=1.0, soft_min=-1.0, soft_max=1.0,
        description="Virtual joystick Y (pitch/depth). Combines with real joystick. -1 = dive, +1 = surface.")
    music_volume: bpy.props.FloatProperty(
        name="Music Volume", default=0.25, min=0.0, max=1.5, soft_max=1.0,
        description="Base music track volume. Set low so mood sounds sit on top.")
    sound_volume: bpy.props.FloatProperty(
        name="Sound Volume", default=0.7, min=0.0, max=1.5, soft_max=1.0,
        description="Mood-triggered whale sound volume.")

class BALLENA_OT_reproducir(bpy.types.Operator):
    bl_idname = "ballena.reproducir"; bl_label = "Reproducir"; bl_description = "Manda la toma elegida a la ballena (reproducir.py)"
    def execute(self, context):
        import subprocess, signal
        p = context.scene.ballena; ns = bpy.app.driver_namespace
        bpy.ops.ballena.parar()
        if not p.toma: self.report({'WARNING'}, "no hay tomas"); return {'CANCELLED'}
        p.comportamiento = "auto"   # la toma manda
        cmd = [os.path.join(YAKUMAMA, "venv", "bin", "python"), "-u", os.path.join(YAKUMAMA, "reproducir.py"), p.toma, "--modo", p.modo_toma] + (["--loop"] if p.loop_toma else [])
        ns["_ballena_reproductor"] = subprocess.Popen(cmd, cwd=YAKUMAMA, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.report({'INFO'}, f"reproduciendo {p.toma}"); return {'FINISHED'}
class BALLENA_OT_actuar(bpy.types.Operator):
    bl_idname = "ballena.actuar"; bl_label = "Actuar con la red"; bl_description = "La ballena actua el animo elegido en Comportamiento con lo que aprendio del actor (generar_animo.py)"
    def execute(self, context):
        import subprocess
        p = context.scene.ballena; ns = bpy.app.driver_namespace; bpy.ops.ballena.parar()
        animo = p.comportamiento if p.comportamiento != "auto" else None
        cmd = [os.path.join(YAKUMAMA, "venv", "bin", "python"), "-u", os.path.join(YAKUMAMA, "generar_animo.py")] + ([animo] if animo else ["--todos"]) + ["--segundos", "60" if animo else "30", "--modo", p.modo_toma if p.modo_toma in ("anclada", "cuerpo", "cara") else "anclada"] + ["--actor", ((bpy.app.driver_namespace.get("_ballena_estilo") or "promedio") if (p.actor_red or "auto").strip().lower() == "auto" else p.actor_red.strip().lower())]
        p.comportamiento = "auto"
        ns["_ballena_reproductor"] = subprocess.Popen(cmd, cwd=YAKUMAMA, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.report({'INFO'}, f"actuando {animo or 'los diez'}"); return {'FINISHED'}
class BALLENA_OT_parar(bpy.types.Operator):
    bl_idname = "ballena.parar"; bl_label = "Parar"; bl_description = "Para la reproduccion (la del panel o una lista externa)"
    def execute(self, context):
        import subprocess
        ns = bpy.app.driver_namespace; pr = ns.get("_ballena_reproductor")
        import signal as _sg
        if pr and pr.poll() is None:
            try: pr.send_signal(_sg.SIGINT)   # como Ctrl-C: reproducir.py borra su estado
            except Exception: pass
        ns["_ballena_reproductor"] = None
        try: subprocess.run(["pkill", "-f", "playlist"], capture_output=True); subprocess.run(["pkill", "-INT", "-f", "reproducir.py"], capture_output=True); subprocess.run(["pkill", "-INT", "-f", "generar_animo.py"], capture_output=True)
        except Exception: pass
        try: os.remove("/tmp/ballena_reproduciendo.json")
        except Exception: pass
        return {'FINISHED'}
class BALLENA_OT_turbine(bpy.types.Operator):
    bl_idname = "ballena.toggle_turbine"
    bl_label = "Toggle Turbine"

    def execute(self, context):
        ns = bpy.app.driver_namespace
        ns["_ballena_turbine_manual"] = not ns.get("_ballena_turbine_manual", False)
        state = "ON" if ns["_ballena_turbine_manual"] else "OFF"
        self.report({'INFO'}, f"Turbine {state}")
        return {'FINISHED'}

class BALLENA_OT_test_sound(bpy.types.Operator):
    bl_idname = "ballena.test_sound"
    bl_label = "Test"

    def execute(self, context):
        dom = bpy.app.driver_namespace.get("_ballena_dominant", "calm")
        play_mood_sound(dom, force=True)
        return {'FINISHED'}

class BALLENA_OT_reset_vjoy(bpy.types.Operator):
    bl_idname = "ballena.reset_vjoy"
    bl_label = "Center"
    bl_description = "Reset virtual joystick to centre"

    def execute(self, context):
        p = context.scene.ballena
        p.virtual_joy_x = 0.0
        p.virtual_joy_y = 0.0
        return {'FINISHED'}

class BALLENA_PT_panel(bpy.types.Panel):
    bl_label = "Ballena"
    bl_idname = "BALLENA_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Ballena"

    def draw(self, context):
        layout = self.layout
        if not hasattr(context.scene, 'ballena'):
            layout.label(text="(not registered)")
            return
        p = context.scene.ballena
        ns = bpy.app.driver_namespace
        col = layout.column(align=True)

        col.label(text="Tomas grabadas")
        col.prop(p, "toma", text="")
        col.prop(p, "modo_toma", text="")
        row = col.row(align=True); row.operator("ballena.reproducir", text="Reproducir", icon='PLAY'); row.operator("ballena.parar", text="Parar", icon='SNAP_FACE'); row.prop(p, "loop_toma", text="", icon='FILE_REFRESH')
        e = _reproduciendo()
        col.label(text=(f"▶ {e['tramo']}  {e['t']}/{e['dur']} s  ({e['modo']}{', repite' if e.get('loop') else ''})" if e else "(nada reproduciendose)"))
        col.separator()
        col.label(text="Sentidos (lo que le llega)")
        se = ns.get("_ballena_sentidos", {})
        col.label(text=f"ánimo: {se.get('dominante','—')}  ←  {se.get('fuente','—')}")
        col.label(text=f"actor: {'cara vista' if se.get('cara') else 'sin cara'}" + (f", ve {se['actor']}" if se.get('actor') else "") + (f", manos {se['manos']}" if se.get('manos') else ""))
        col.label(text=f"pulso: {se['hr']:.0f} lpm · piel {se['eda']:.1f} µS · {se['therm']:.1f} °C" if se.get('hr') else "pulso: sin EmotiBit")
        col.label(text=f"entorno: color {se.get('color','—')} · agua {se.get('agua','—')} · cerebro {se.get('cerebro','—')}")
        col.separator()
        col.label(text="Comportamiento (fotos NOAA)")
        col.prop(p, "comportamiento", text="")
        col.prop(p, "actor_red")
        _e = bpy.app.driver_namespace.get("_ballena_estilo")
        col.label(text=f"Ahora es: {_e}" if _e else "Ahora es: nadie (promedio)", icon='USER')
        _v = latest_data.get('visita') if 'latest_data' in globals() else None
        if _v: col.label(text=("Te conozco: " + str(_v)) if latest_data.get('conocida') else "Cara nueva", icon='HEART' if latest_data.get('conocida') else 'ADD')
        col.operator("ballena.actuar", text="Actuar con la red (lo aprendido del actor)", icon='OUTLINER_OB_ARMATURE')
        col.separator()
        col.label(text="Mouth + Tongue")
        col.prop(p, "mouth_scale", slider=True)
        col.prop(p, "tongue_scale", slider=True)
        col.separator()

        col.label(text="Body motion")
        col.prop(p, "auto_turn_scale", slider=True)
        col.prop(p, "follow_hand", slider=True)
        col.prop(p, "color_track", slider=True)
        cx = ns.get("_ballena_color_x", None)
        if cx is None:
            col.label(text="color_x: (not received)")
        else:
            col.label(text=f"color_x: {cx:.2f}")
        col.separator()

        col.label(text="Mind")
        col.prop(p, "use_brain", toggle=True)
        col.separator()

        col.label(text="Color tint")
        col.prop(p, "color_follow", slider=True)
        seen = ns.get("_ballena_seen_color", "—")
        dom = ns.get("_ballena_dominant", "—")
        col.label(text=f"seeing: {seen}  →  {dom}")
        col.separator()

        col.label(text="Virtual joystick")
        col.prop(p, "virtual_joy_x", slider=True)
        col.prop(p, "virtual_joy_y", slider=True)
        col.operator("ballena.reset_vjoy", text="Center", icon='RECOVER_LAST')
        col.separator()

        col.label(text="Music (base track)")
        col.prop(p, "music_volume", slider=True)
        amb_ok = ns.get("_ballena_ambient_handle", None) is not None
        col.label(text=f"Tidal Echoes: {'looping' if amb_ok else 'not loaded'}")
        col.separator()

        col.label(text="Sound (mood)")
        col.prop(p, "sound_volume", slider=True)
        ok = ns.get("_ballena_audio_ok", False)
        files = ns.get("_ballena_sound_count", 0)
        col.label(text=f"audio: {'ready' if ok else 'no device'}  ({files} files)")
        col.operator("ballena.test_sound", text="Test current mood")
        col.separator()

        turbine_on = ns.get("_ballena_turbine_manual", False)
        col.operator(
            "ballena.toggle_turbine",
            text=f"Turbine: {'ON' if turbine_on else 'OFF'}",
            icon='PROP_ON' if turbine_on else 'PROP_OFF',
            depress=turbine_on,
        )

_guardado = {}
try:   # al re-ejecutar el script, re-registrar BallenaProps borra los ajustes del panel: se guardan y se restauran
    _p = bpy.context.scene.ballena
    _guardado = {k: getattr(_p, k) for k in ("mouth_scale", "tongue_scale", "auto_turn_scale", "follow_hand", "color_track", "color_follow", "use_brain", "virtual_joy_x", "virtual_joy_y", "music_volume", "sound_volume", "toma", "modo_toma", "loop_toma", "actor_red", "comportamiento")}
except Exception: pass
for cls in (BALLENA_PT_panel, BALLENA_OT_reset_vjoy, BALLENA_OT_test_sound, BALLENA_OT_turbine, BALLENA_OT_reproducir, BALLENA_OT_parar, BALLENA_OT_actuar, BallenaProps):
    try: bpy.utils.unregister_class(cls)
    except: pass
bpy.utils.register_class(BallenaProps)
bpy.utils.register_class(BALLENA_OT_reproducir)
bpy.utils.register_class(BALLENA_OT_parar)
bpy.utils.register_class(BALLENA_OT_actuar)
bpy.utils.register_class(BALLENA_OT_turbine)
bpy.utils.register_class(BALLENA_OT_test_sound)
bpy.utils.register_class(BALLENA_OT_reset_vjoy)
bpy.utils.register_class(BALLENA_PT_panel)
bpy.types.Scene.ballena = bpy.props.PointerProperty(type=BallenaProps)
for _k, _v in _guardado.items():
    try: setattr(bpy.context.scene.ballena, _k, _v)
    except Exception: pass

# ============================================================
# AUDIO
# ============================================================
# El sonido dentro de Blender (aud) tiro Blender dos veces el 16-17 oct con "mutex lock failed" justo despues de un
# ♪ de animo: queda APAGADO salvo BALLENA_SONIDO=1 en el entorno. Los sonidos de animo los pone el carrusel (afplay).
SONIDO_EN_BLENDER = os.environ.get("BALLENA_SONIDO") == "1"
try:
    import aud
    _audio_available = SONIDO_EN_BLENDER
except ImportError:
    _audio_available = False

ns = bpy.app.driver_namespace
if _audio_available and "_ballena_audio_device" not in ns:
    try:
        ns["_ballena_audio_device"] = aud.Device()
        ns["_ballena_audio_ok"] = True
        print(f"  Audio: device initialised")
    except Exception as e:
        ns["_ballena_audio_device"] = None
        ns["_ballena_audio_ok"] = False
        print(f"  Audio: device init failed: {e}")
elif not _audio_available:
    ns["_ballena_audio_ok"] = False

audio_device = ns.get("_ballena_audio_device") if _audio_available else None
sound_cache = ns.setdefault("_ballena_sound_cache", {})

def inventory_sounds():
    found = 0
    if not os.path.isdir(SOUNDS_DIR): return found
    all_files = set(os.listdir(SOUNDS_DIR))
    for mood, names in SOUNDS.items():
        for n in names:
            if n in all_files: found += 1
    if AMBIENT_LOOP and AMBIENT_LOOP in all_files: found += 1
    return found

ns["_ballena_sound_count"] = inventory_sounds()
print(f"  Audio: {ns['_ballena_sound_count']} files found in {SOUNDS_DIR}")

ns.setdefault("_ballena_sound_last", {})

def get_sound_volume():
    try: return float(bpy.context.scene.ballena.sound_volume)
    except: return 0.7

def get_music_volume():
    try: return float(bpy.context.scene.ballena.music_volume)
    except: return 0.25

def play_mood_sound(mood, force=False):
    if not audio_device: return
    files = SOUNDS.get(mood, [])
    if not files: return
    now = time.time()
    last = ns["_ballena_sound_last"].get(mood, 0)
    if not force and (now - last) < SOUND_COOLDOWN: return
    candidates = []
    for fn in files:
        p = os.path.join(SOUNDS_DIR, fn)
        if os.path.exists(p): candidates.append(p)
    if not candidates or not SONIDO_EN_BLENDER: return
    path = random.choice(candidates)
    try:
        snd = sound_cache.get(path)
        if snd is None:
            snd = aud.Sound(path)
            sound_cache[path] = snd
        handle = audio_device.play(snd)
        handle.volume = max(0.0, get_sound_volume())
        ns["_ballena_sound_last"][mood] = now
        print(f"  ♪ {mood}: {os.path.basename(path)}")
    except Exception as e:
        print(f"  Audio play error: {e}")

def start_ambient_loop():
    """Start the base music track on infinite loop."""
    if not audio_device or not AMBIENT_LOOP: return None
    path = os.path.join(SOUNDS_DIR, AMBIENT_LOOP)
    if not os.path.exists(path):
        print(f"  Base music: {AMBIENT_LOOP} not found in {SOUNDS_DIR}")
        return None
    try:
        snd = aud.Sound(path)
        handle = audio_device.play(snd)
        handle.loop_count = -1
        handle.volume = get_music_volume()
        print(f"  ♪ Base music: {AMBIENT_LOOP} (looping)")
        return handle
    except Exception as e:
        print(f"  Base music error: {e}")
        return None

# Stop any previous ambient handle (from a prior Alt+P), start fresh
old_ambient = ns.get("_ballena_ambient_handle")
if old_ambient is not None:
    try: old_ambient.stop()
    except: pass
ns["_ballena_ambient_handle"] = start_ambient_loop()

# ============================================================
# BRIAN'S POSES
# ============================================================
POSES = {
    "calm": {
        "head":         (0.0, 0, 0),
        "spine":        (0.0, 0, 0),
        "spine.001":    (0.0, 0, 0),
        "spine.002":    (0.0, 0, 0),
        "spine.003":    (0.0, 0, 0),
        "spine.004":    (0.0, 0, 0),
        "spine.005":    (0.0, 0, 0),
        "mouth_inf.001":(0.0, 0, 0),
        "mouth_inf.002":(0.0, 0, 0),
        "eye.L":        (0.0, 0, 0),
        "eye.R":        (0.0, 0, 0),
        "side_fine.L":  (0, 0, 0.05),
        "side_fine.L.001":(0, 0, 0.03),
        "side_fine.L.002":(0, 0, 0.02),
        "side_fine.R":  (0, 0, -0.05),
        "side_fine.R.001":(0, 0, -0.03),
        "side_fine.R.002":(0, 0, -0.02),
        "back_fin.U":   (0, 0, 0),
        "back_fin.L":   (0, 0, 0),
        "back_fin.R":   (0, 0, 0),
    },
    "singing": {
        "head":         (-0.08, 0, 0),
        "spine":        (-0.03, 0, 0),
        "spine.001":    (0.02, 0, 0),
        "spine.002":    (-0.02, 0, 0),
        "spine.003":    (0.02, 0, 0),
        "spine.004":    (-0.01, 0, 0),
        "spine.005":    (0.01, 0, 0),
        "mouth_inf.001":(0.3, 0, 0),
        "mouth_inf.002":(0.2, 0, 0),
        "eye.L":        (-0.05, 0, 0),
        "eye.R":        (-0.05, 0, 0),
        "side_fine.L":  (0, 0, 0.15),
        "side_fine.L.001":(0, 0, 0.1),
        "side_fine.L.002":(0, 0, 0.07),
        "side_fine.R":  (0, 0, -0.15),
        "side_fine.R.001":(0, 0, -0.1),
        "side_fine.R.002":(0, 0, -0.07),
        "back_fin.U":   (0, 0, 0.05),
        "back_fin.L":   (0, 0, -0.05),
        "back_fin.R":   (0, 0, 0.05),
    },
    "playful": {
        "head":         (0.25, 0, 0),
        "spine":        (0.15, 0, 0),
        "spine.001":    (0.1, 0, 0),
        "spine.002":    (0.05, 0, 0),
        "spine.003":    (-0.05, 0, 0),
        "spine.004":    (-0.15, 0, 0),
        "spine.005":    (-0.2, 0, 0),
        "mouth_inf.001":(0.15, 0, 0),
        "mouth_inf.002":(0.1, 0, 0),
        "eye.L":        (0.1, 0.1, 0),
        "eye.R":        (0.1, -0.1, 0),
        "side_fine.L":  (0, 0, 0.4),
        "side_fine.L.001":(0, 0, 0.3),
        "side_fine.L.002":(0, 0, 0.2),
        "side_fine.R":  (0, 0, -0.4),
        "side_fine.R.001":(0, 0, -0.3),
        "side_fine.R.002":(0, 0, -0.2),
        "back_fin.U":   (0, 0, 0.2),
        "back_fin.L":   (0, 0, -0.25),
        "back_fin.R":   (0, 0, 0.25),
    },
    "curious": {
        "head":         (0.2, 0, 0),
        "spine":        (0.1, 0, 0),
        "spine.001":    (0.06, 0, 0),
        "spine.002":    (0.03, 0, 0),
        "spine.003":    (0.0, 0, 0),
        "spine.004":    (-0.03, 0, 0),
        "spine.005":    (-0.05, 0, 0),
        "mouth_inf.001":(0.05, 0, 0),
        "mouth_inf.002":(0.03, 0, 0),
        "eye.L":        (0.08, 0.05, 0),
        "eye.R":        (0.08, -0.05, 0),
        "side_fine.L":  (0, 0, 0.12),
        "side_fine.L.001":(0, 0, 0.08),
        "side_fine.L.002":(0, 0, 0.05),
        "side_fine.R":  (0, 0, -0.12),
        "side_fine.R.001":(0, 0, -0.08),
        "side_fine.R.002":(0, 0, -0.05),
        "back_fin.U":   (0, 0, 0.05),
        "back_fin.L":   (0, 0, -0.05),
        "back_fin.R":   (0, 0, 0.05),
    },
    "feeding": {
        "head":         (-0.08, 0, 0),
        "spine":        (-0.02, 0, 0),
        "spine.001":    (0.0, 0, 0),
        "spine.002":    (0.02, 0, 0),
        "spine.003":    (0.0, 0, 0),
        "spine.004":    (-0.02, 0, 0),
        "spine.005":    (0.0, 0, 0),
        "mouth_inf.001":(0.6, 0, 0),
        "mouth_inf.002":(0.4, 0, 0),
        "eye.L":        (-0.03, 0.05, 0),
        "eye.R":        (-0.03, -0.05, 0),
        "side_fine.L":  (0, 0, 0.3),
        "side_fine.L.001":(0, 0, 0.2),
        "side_fine.L.002":(0, 0, 0.15),
        "side_fine.R":  (0, 0, -0.3),
        "side_fine.R.001":(0, 0, -0.2),
        "side_fine.R.002":(0, 0, -0.15),
        "back_fin.U":   (0, 0, 0.1),
        "back_fin.L":   (0, 0, -0.1),
        "back_fin.R":   (0, 0, 0.1),
    },
    "sad": {
        "head":         (-0.25, 0, 0),
        "spine":        (-0.1, 0, 0),
        "spine.001":    (-0.08, 0, 0),
        "spine.002":    (-0.06, 0, 0),
        "spine.003":    (-0.04, 0, 0),
        "spine.004":    (-0.02, 0, 0),
        "spine.005":    (0.0, 0, 0),
        "mouth_inf.001":(0.0, 0, 0),
        "mouth_inf.002":(0.0, 0, 0),
        "eye.L":        (-0.15, 0, 0),
        "eye.R":        (-0.15, 0, 0),
        "side_fine.L":  (0, 0, -0.05),
        "side_fine.L.001":(0, 0, -0.03),
        "side_fine.L.002":(0, 0, -0.02),
        "side_fine.R":  (0, 0, 0.05),
        "side_fine.R.001":(0, 0, 0.03),
        "side_fine.R.002":(0, 0, 0.02),
        "back_fin.U":   (0, 0, 0),
        "back_fin.L":   (0, 0, 0),
        "back_fin.R":   (0, 0, 0),
    },
    "angry": {
        "head":         (-0.1, 0, 0),
        "spine":        (0.05, 0, 0),
        "spine.001":    (0.03, 0, 0),
        "spine.002":    (0.0, 0, 0),
        "spine.003":    (-0.05, 0, 0),
        "spine.004":    (0.15, 0, 0),
        "spine.005":    (0.25, 0, 0),
        "mouth_inf.001":(0.0, 0, 0),
        "mouth_inf.002":(0.0, 0, 0),
        "eye.L":        (0.05, 0, 0),
        "eye.R":        (0.05, 0, 0),
        "side_fine.L":  (0, 0, -0.1),
        "side_fine.L.001":(0, 0, -0.08),
        "side_fine.L.002":(0, 0, -0.05),
        "side_fine.R":  (0, 0, 0.1),
        "side_fine.R.001":(0, 0, 0.08),
        "side_fine.R.002":(0, 0, 0.05),
        "back_fin.U":   (0, 0, -0.05),
        "back_fin.L":   (0, 0, 0.05),
        "back_fin.R":   (0, 0, -0.05),
    },
    "alert": {
        "head":         (0.05, 0, 0),
        "spine":        (0.0, 0, 0),
        "spine.001":    (0.0, 0, 0),
        "spine.002":    (0.0, 0, 0),
        "spine.003":    (0.0, 0, 0),
        "spine.004":    (0.0, 0, 0),
        "spine.005":    (0.0, 0, 0),
        "mouth_inf.001":(0.0, 0, 0),
        "mouth_inf.002":(0.0, 0, 0),
        "eye.L":        (0.03, 0, 0),
        "eye.R":        (0.03, 0, 0),
        "side_fine.L":  (0, 0, 0.03),
        "side_fine.L.001":(0, 0, 0.02),
        "side_fine.L.002":(0, 0, 0.01),
        "side_fine.R":  (0, 0, -0.03),
        "side_fine.R.001":(0, 0, -0.02),
        "side_fine.R.002":(0, 0, -0.01),
        "back_fin.U":   (0, 0, 0),
        "back_fin.L":   (0, 0, 0),
        "back_fin.R":   (0, 0, 0),
    },
    "diving": {
        "head":         (-0.3, 0, 0),
        "spine":        (-0.15, 0, 0),
        "spine.001":    (-0.1, 0, 0),
        "spine.002":    (-0.06, 0, 0),
        "spine.003":    (-0.03, 0, 0),
        "spine.004":    (0.05, 0, 0),
        "spine.005":    (0.1, 0, 0),
        "mouth_inf.001":(0.0, 0, 0),
        "mouth_inf.002":(0.0, 0, 0),
        "eye.L":        (-0.1, 0, 0),
        "eye.R":        (-0.1, 0, 0),
        "side_fine.L":  (0, 0, -0.05),
        "side_fine.L.001":(0, 0, -0.03),
        "side_fine.L.002":(0, 0, -0.02),
        "side_fine.R":  (0, 0, 0.05),
        "side_fine.R.001":(0, 0, 0.03),
        "side_fine.R.002":(0, 0, 0.02),
        "back_fin.U":   (0, 0, 0),
        "back_fin.L":   (0, 0, 0),
        "back_fin.R":   (0, 0, 0),
    },
    "surfacing": {
        "head":         (0.3, 0, 0),
        "spine":        (0.15, 0, 0),
        "spine.001":    (0.1, 0, 0),
        "spine.002":    (0.05, 0, 0),
        "spine.003":    (0.0, 0, 0),
        "spine.004":    (-0.05, 0, 0),
        "spine.005":    (-0.1, 0, 0),
        "mouth_inf.001":(0.2, 0, 0),
        "mouth_inf.002":(0.15, 0, 0),
        "eye.L":        (0.1, 0, 0),
        "eye.R":        (0.1, 0, 0),
        "side_fine.L":  (0, 0, 0.3),
        "side_fine.L.001":(0, 0, 0.2),
        "side_fine.L.002":(0, 0, 0.15),
        "side_fine.R":  (0, 0, -0.3),
        "side_fine.R.001":(0, 0, -0.2),
        "side_fine.R.002":(0, 0, -0.15),
        "back_fin.U":   (0, 0, 0.15),
        "back_fin.L":   (0, 0, -0.15),
        "back_fin.R":   (0, 0, 0.15),
    },
}

OSCILLATIONS = {
    "calm":      [("spine.004", 2, 0.02, 0.15), ("spine.005", 2, 0.03, 0.15)],
    "singing":   [("spine.003", 2, 0.04, 0.2), ("spine.004", 2, 0.06, 0.2), ("spine.005", 2, 0.08, 0.2),
                  ("mouth_inf.001", 0, 0.15, 0.8)],
    "playful":   [("spine.003", 2, 0.08, 0.4), ("spine.004", 2, 0.12, 0.4), ("spine.005", 2, 0.15, 0.4),
                  ("head", 2, 0.1, 0.25)],
    "curious":   [("head", 2, 0.12, 0.12), ("eye.L", 1, 0.08, 0.15), ("eye.R", 1, 0.08, 0.15)],
    "feeding":   [("spine.003", 2, 0.05, 0.3), ("spine.004", 2, 0.08, 0.3), ("spine.005", 2, 0.1, 0.3),
                  ("head", 2, 0.08, 0.1)],
    "sad":       [("spine.004", 2, 0.01, 0.05), ("spine.005", 2, 0.015, 0.05)],
    "angry":     [("spine.003", 2, 0.15, 0.8), ("spine.004", 2, 0.2, 0.8), ("spine.005", 2, 0.25, 0.8),
                  ("head", 2, 0.08, 0.5)],
    "alert":     [],
    "diving":    [("spine.003", 2, 0.04, 0.25), ("spine.004", 2, 0.06, 0.25), ("spine.005", 2, 0.08, 0.25)],
    "surfacing": [("spine.003", 2, 0.05, 0.3), ("spine.004", 2, 0.08, 0.3), ("spine.005", 2, 0.1, 0.3)],
}

SHAPES = {
    "calm":      {"parpadeo": 0.1, "angry": 0, "sad": 0, "asombrado": 0},
    "singing":   {"parpadeo": 0.05, "angry": 0, "sad": 0, "asombrado": 0.1},
    "playful":   {"parpadeo": 0, "angry": 0, "sad": 0, "asombrado": 0.4},
    "curious":   {"parpadeo": 0, "angry": 0, "sad": 0, "asombrado": 0.5},
    "feeding":   {"parpadeo": 0.05, "angry": 0, "sad": 0, "asombrado": 0.2},
    "sad":       {"parpadeo": 0.3, "angry": 0, "sad": 0.8, "asombrado": 0},
    "angry":     {"parpadeo": 0.1, "angry": 0.8, "sad": 0, "asombrado": 0},
    "alert":     {"parpadeo": 0, "angry": 0.2, "sad": 0, "asombrado": 0.3},
    "diving":    {"parpadeo": 0.15, "angry": 0, "sad": 0, "asombrado": 0},
    "surfacing": {"parpadeo": 0, "angry": 0, "sad": 0, "asombrado": 0.3},
}

# ============================================================
# SETUP
# ============================================================
armature = bpy.data.objects.get("side_fine.R")
if not armature:
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break
if armature:
    for pb in armature.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0); pb.location = (0.0, 0.0, 0.0); pb.scale = (1.0, 1.0, 1.0)   # limpia la pose guardada en el .blend (aletas atravesadas, etc.)
    print(f"  Armature: {armature.name} ({len(armature.pose.bones)} bones)")
whale_mesh = None
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.data.shape_keys:
        if any(k.name in ["parpadeo", "angry", "sad", "asombrado"] for k in obj.data.shape_keys.key_blocks):
            whale_mesh = obj
            break
if whale_mesh:
    print(f"  Mesh: {whale_mesh.name}")
    try:   # que la vista 3D muestre el color del material (en Solido con color Aleatorio/Unico/Textura el tinte no se ve)
        for _scr in bpy.data.screens:
            for _ar in _scr.areas:
                if _ar.type == 'VIEW_3D':
                    for _sp in _ar.spaces:
                        if _sp.type == 'VIEW_3D' and _sp.shading.type == 'SOLID' and _sp.shading.color_type in ('RANDOM', 'SINGLE', 'TEXTURE', 'VERTEX'):
                            _sp.shading.color_type = 'MATERIAL'; print("  vista 3D: color del sombreado -> Material (para ver el color del animo)")
    except Exception as e: print("  (sombreado:", e, ")")

# ============================================================
# STATE
# ============================================================
latest_data = {}
current_rots = {}
whale_mood = {}
turbine_active = False
turbine_angle = 0.0
prev_btn = 0
start_time = time.time()

if "_ballena_log" not in bpy.app.driver_namespace:
    bpy.app.driver_namespace["_ballena_log"] = {
        "mood_counts": {}, "colors_seen": {}, "water_states": {},
        "peak_moods": {}, "total_frames": 0, "mood_sequence": [],
        "start_time": time.time()
    }

prev_log = bpy.app.driver_namespace["_ballena_log"]
if prev_log["total_frames"] > 200:
    s = prev_log
    duration = (time.time() - s.get("start_time", time.time())) / 60.0
    total = max(1, s["total_frames"])
    moods = s["mood_counts"]
    if moods:
        top_mood = max(moods, key=moods.get)
        top_pct = moods[top_mood] / total * 100
        try:
            with open("/tmp/ballena_session.json", "w") as f:
                json.dump({"duration_min": duration, "total_frames": total,
                          "top_mood": top_mood, "top_mood_pct": top_pct,
                          "mood_counts": moods, "colors_seen": s["colors_seen"],
                          "water_states": s["water_states"],
                          "journey": s["mood_sequence"], "written_at": time.time()}, f)
        except: pass

bpy.app.driver_namespace["_ballena_log"] = {
    "mood_counts": {}, "colors_seen": {}, "water_states": {},
    "peak_moods": {}, "total_frames": 0, "mood_sequence": [],
    "start_time": time.time()
}
session_log = bpy.app.driver_namespace["_ballena_log"]

# ============================================================
# UDP
# ============================================================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except: pass
sock.bind(("127.0.0.1", UDP_PORT))
sock.setblocking(False)

# ============================================================
# HELPERS
# ============================================================
def sm(key, target, factor=SMOOTH):
    cur = current_rots.get(key, 0.0)
    new = cur + (target - cur) * factor
    current_rots[key] = new
    return new
LIMITES = {}   # 'hueso:eje': (min, max) en radianes
# SIN ARQUEAR HACIA ATRAS: la nariz sube como mucho ~26 grados (0.45), baja hasta ~40 (-0.7); la columna no se curva
# con la cola arriba mas de 0.12 por hueso; la cabeza no se echa atras mas de 0.35.
LIMITES['root:0'] = (-0.7, 0.45); LIMITES['head:0'] = (-0.5, 0.35)
for _b in ('spine', 'spine.001', 'spine.002', 'spine.003', 'spine.004', 'spine.005'): LIMITES[f'{_b}:0'] = (-0.12, 0.3)
for _suf, _sg in (('.L', 1), ('.R', -1)):
    for _b, _k in (('side_fine' + _suf, 1.0), ('side_fine' + _suf + '.001', 0.7), ('side_fine' + _suf + '.002', 0.5)):
        _lo, _hi = -0.35 * _k, 0.3 * _k            # barrido (eje 2): medido con la malla, mas alla entra en el flanco o la cabeza
        LIMITES[f'{_b}:2'] = (_lo, _hi) if _sg > 0 else (-_hi, -_lo)
        LIMITES[f'{_b}:1'] = (-0.5 * _k, 0.9 * _k) if _sg > 0 else (-0.9 * _k, 0.5 * _k)   # aleteo: abajo -0.5, arriba 0.9
        LIMITES[f'{_b}:0'] = (-0.35 * _k, 0.35 * _k)                                        # ladeo: con mas, cruza el flanco
def rot(bone_name, angle, axis, smooth_factor=SMOOTH):
    lim = LIMITES.get(f'{bone_name}:{axis}')
    if lim: angle = max(lim[0], min(lim[1], angle))
    val = sm(f'{bone_name}:{axis}', angle, smooth_factor)
    try: armature.pose.bones[bone_name].rotation_euler[axis] = val
    except: pass
def loc(bone_name, x, y, z):
    try:
        pb = armature.pose.bones[bone_name]
        pb.location.x = sm(f'{bone_name}:lx', x, 0.06)
        pb.location.y = sm(f'{bone_name}:ly', y, 0.06)
        pb.location.z = sm(f'{bone_name}:lz', z, 0.06)
    except: pass
def shape(key_name, value, factor=0.08):
    if whale_mesh and whale_mesh.data.shape_keys:
        try:
            whale_mesh.data.shape_keys.key_blocks[key_name].value = sm(f'sk:{key_name}', max(0, min(1, value)), factor)
        except: pass

# Suavizado de entrada: el tracking de la cara llega con ruido cuadro a cuadro; cada canal se promedia
# (EMA) antes de mover nada. El parpadeo no (tiene que ser rapido). Factor mas chico = mas suave.
SUAVE = {"head_yaw": 0.15, "head_pitch": 0.15, "jaw_open": 0.25, "brow_up": 0.15, "brow_down": 0.15, "mouth_sad": 0.15,
         "mouth_smile": 0.15, "eye_yaw": 0.12, "eye_pitch": 0.12, "tongue_out": 0.2, "l_palm_y": 0.1, "r_palm_y": 0.1,
         "l_palm_x": 0.1, "r_palm_x": 0.1, "l_depth": 0.1, "r_depth": 0.1}
_suave = {}
def suavizar(d):
    out = dict(d)
    for k, f in SUAVE.items():
        if k in d:
            try: v = float(d[k])
            except Exception: continue
            prev = _suave.get(k)
            out[k] = v if prev is None else prev + (v - prev) * f
            _suave[k] = out[k]
        else: _suave.pop(k, None)   # sin dato (mano fuera de cuadro): arranca de cero cuando vuelva
    return out

def read_controls():
    try:
        p = bpy.context.scene.ballena
        return (p.mouth_scale, p.tongue_scale, p.auto_turn_scale,
                p.follow_hand, p.color_track, p.color_follow,
                p.use_brain, p.virtual_joy_x, p.virtual_joy_y,
                p.music_volume, p.sound_volume)
    except: return 1.0, 0.0, 0.3, 0.0, 0.0, 0.0, False, 0.0, 0.0, 0.25, 0.7

def tint_body(target_rgb, lerp_amount):
    if not whale_mesh: return
    try:   # color de objeto (sombreado Solido en modo Objeto) tambien, para que se vea en cualquier vista
        c = whale_mesh.color; whale_mesh.color = (c[0] + (target_rgb[0] - c[0]) * lerp_amount, c[1] + (target_rgb[1] - c[1]) * lerp_amount, c[2] + (target_rgb[2] - c[2]) * lerp_amount, 1.0)
    except Exception: pass
    for slot in whale_mesh.material_slots:
        mat = slot.material
        if not mat: continue
        try:
            cur = mat.diffuse_color
            mat.diffuse_color = (
                cur[0] + (target_rgb[0] - cur[0]) * lerp_amount,
                cur[1] + (target_rgb[1] - cur[1]) * lerp_amount,
                cur[2] + (target_rgb[2] - cur[2]) * lerp_amount,
                cur[3])
        except: pass
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    bc = node.inputs.get("Base Color")
                    if bc is not None:
                        c = bc.default_value
                        bc.default_value = (
                            c[0] + (target_rgb[0] - c[0]) * lerp_amount,
                            c[1] + (target_rgb[1] - c[1]) * lerp_amount,
                            c[2] + (target_rgb[2] - c[2]) * lerp_amount,
                            c[3])
                    break

# ============================================================
# WHALE BRAIN
# ============================================================
def compute_mood(d):
    water = float(d.get('water', 0))
    color_name = str(d.get('scene_color', 'neutral'))
    perf_sad = float(d.get('mouth_sad', 0))
    perf_brow_up = float(d.get('brow_up', 0))
    perf_brow_down = float(d.get('brow_down', 0))
    perf_jaw = float(d.get('jaw_open', 0))
    bright = float(d.get('scene_bright', 0.5))
    bright_delta = float(d.get('scene_bright_delta', 0))
    m = {k: 0.0 for k in POSES.keys()}

    if water < 0.05:    m["sad"] = 0.3;   m["alert"] = 0.2
    elif water < 0.35:  m["curious"] = 0.2; m["alert"] = 0.15
    elif water < 0.7:   m["calm"] = 0.2;  m["playful"] = 0.15
    elif water < 0.85:  m["calm"] = 0.2;  m["singing"] = 0.2
    else:               m["calm"] = 0.25; m["singing"] = 0.25

    if color_name in COLOR_TO_MOOD:
        target = COLOR_TO_MOOD[color_name]
        for k in m: m[k] *= 0.4
        m[target] += 0.9

    if bright < 0.2: m["calm"] += 0.2; m["singing"] += 0.1
    if bright_delta > 0.3: m["alert"] = max(m["alert"], 0.5)

    if perf_sad > 0.6: m["sad"] += (perf_sad - 0.4) * 0.3
    if perf_brow_up > 0.5: m["curious"] += perf_brow_up * 0.2
    if perf_brow_down > 0.3: m["alert"] += perf_brow_down * 0.2
    if perf_jaw > 0.3: m["feeding"] += perf_jaw * 0.3; m["singing"] += perf_jaw * 0.15
    smile = max(0, (1.0 - perf_sad) * perf_brow_up - 0.2)
    if smile > 0.1: m["playful"] += smile * 0.3

    for k in m: m[k] = max(0, min(1, m[k]))
    for k in m:
        prev = whale_mood.get(k, m[k])
        m[k] = prev + (m[k] - prev) * 0.25
    whale_mood.update(m)
    return m

# ============================================================
# COMPORTAMIENTOS (referencia real: NOAA Stellwagen, ver referencias/noaa_comportamientos)
# Cada animo es un MOVIMIENTO en el tiempo, no una pose fija. Ejes del rig (medidos):
#   root eje 0 = cabeceo (+ nariz arriba), eje 1 = ROLIDO (el eje Y del hueso va a lo largo del cuerpo), eje 2 = GIRO
#   (el script original giraba con el eje 1: en realidad rolaba la ballena y las aletas salian por el lomo y la panza)
#   columna eje 0: negativo = sube (cola arriba), positivo = baja;  head eje 0: + = arriba
#   aletas eje 1 = aleteo (+ arriba), eje 0 = ladeo;  back_fin.U eje 0 = inclinacion de la cola
# ============================================================
def _onda(t, periodo, fase=0.0): return math.sin(2 * math.pi * (t / periodo + fase))
def _pulso(t, periodo, ancho=0.25, fase=0.0):
    """0..1: un pico corto cada `periodo` s (ancho = fraccion del periodo que dura)."""
    x = ((t / periodo + fase) % 1.0) / ancho
    return math.sin(x * math.pi) if x < 1.0 else 0.0
def _rampa(t, periodo, desde, hasta):
    """1 entre `desde` y `hasta` (fracciones del periodo) bajando a 0 despues, 0 antes."""
    f = (t / periodo) % 1.0
    if f < desde: return 0.0
    if f < hasta: return 1.0
    return max(0.0, 1.0 - (f - hasta) / max(1e-6, 1.0 - hasta))
# cada comportamiento devuelve tambien: cara = (parpadeo, angry, sad, asombrado), mirada = (yaw, pitch), spin = vueltas
# sobre su eje (radianes, sin suavizar), depth = cuanto sube (+) o baja (-) en z
def _suave01(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def comp_calm(t):      # LOGGING: quieta en la superficie, respiracion lenta (7 s); ojos entrecerrados. FIRMA: la quietud, plana.
    resp = _onda(t, 7)
    return dict(pitch=0.02 * resp, roll=0.03 * resp, yaw=0.0, head=0.0, spine=[0.015 * _onda(t, 7, -i * 0.08) for i in range(6)],
                fluke=0.0, flap=0.08 * _onda(t, 5), ladeo=0.0, jaw=0.0, cara=(0.5, 0.0, 0.0, 0.0), mirada=(0.0, -0.2), spin=0.0, depth=0.0)
def comp_singing(t):   # CANTO: el cantor cuelga cabeza abajo (~40 grados), casi inmovil, hondo; la boca pulsa con la nota. FIRMA: colgar de cabeza, quieta, boca.
    nota = 0.5 + 0.5 * _onda(t, 2.5)
    return dict(pitch=-0.62, roll=0.02 * _onda(t, 9), yaw=0.0, head=-0.2, spine=[0, 0, -0.02, -0.04, -0.06, -0.08],
                fluke=0.05, flap=0.0, ladeo=0.0, jaw=0.1 + 0.25 * nota, cara=(0.75, 0.0, 0.0, 0.1), mirada=(0.0, -0.4), spin=0.0, depth=-0.6)
PLAYFUL_VUELTAS = 2   # vueltas completas en el breach (2 = como la foto de NOAA; 0 = salta y se ladea hasta 30 grados, nunca queda boca abajo)
def comp_playful(t):   # FLIPPER SLAPPING + rolido, y un BREACH cada 12 s con DOS VUELTAS sobre su eje. FIRMA: el salto con vueltas, las aletas que golpean.
    sube = _pulso(t, 12, 0.22, 0.0); cae = _pulso(t, 12, 0.22, -0.2)
    f = (t / 12) % 1.0; vueltas = PLAYFUL_VUELTAS * 2 * math.pi * _suave01(f / 0.42) if (f < 0.42 and PLAYFUL_VUELTAS) else 0.0
    salto = max(sube, cae); slap = _onda(t, 1.6) * (1 - salto)
    return dict(pitch=0.45 * sube + 0.15 * cae, roll=0.25 * _onda(t, 4) * (1 - salto) + (0.0 if PLAYFUL_VUELTAS else 0.5 * math.sin(math.pi * min(1.0, f / 0.42)) * (1 if f < 0.42 else 0)), yaw=0.0, head=0.15 * sube,
                spine=[-k * sube for k in (0.02, 0.03, 0.05, 0.07, 0.09, 0.1)], fluke=-0.25 * sube,
                flap=0.2 + 0.3 * slap + 0.7 * salto, ladeo=0.25 * _onda(t, 1.6, 0.25) * (1 - salto), jaw=0.15 + 0.15 * sube,
                cara=(0.0, 0.0, 0.0, 0.6), mirada=(0.3 * _onda(t, 1.6), 0.4), spin=vueltas, depth=0.9 * sube)
def comp_curious(t):   # SPYHOPPING: vertical, saca la cabeza del agua y gira DESPACIO todo el cuerpo (14 s); ojos muy abiertos. FIRMA: vertical, alta, girando lenta.
    return dict(pitch=0.45, roll=0.0, yaw=0.5 * _onda(t, 14), head=0.2, spine=[0.05, 0.05, 0.03, 0, -0.02, -0.03],
                fluke=0.0, flap=0.2 + 0.05 * _onda(t, 3), ladeo=0.0, jaw=0.0, cara=(0.0, 0.0, 0.0, 0.9), mirada=(0.8 * _onda(t, 5), 0.5), spin=0.0, depth=0.7)
def comp_feeding(t):   # LUNGE lateral: embestida con la boca abierta RODANDO de lado (la yubarta real rola mas de 60 grados al comer), cierra despacio filtrando. FIRMA: boca y rolido juntos.
    emb = _pulso(t, 6, 0.3); cierra = _rampa(t, 6, 0.3, 0.45)
    return dict(pitch=0.35 * emb, roll=0.65 * emb, yaw=0.0, head=0.2 * emb, spine=[0.04 * _onda(t, 3, -i * 0.15) for i in range(6)],
                fluke=-0.15 * emb, flap=0.2 + 0.2 * emb, ladeo=0.2 * emb, jaw=max(0.7 * emb, 0.35 * cierra), cara=(0.2 + 0.4 * emb, 0.0, 0.0, 0.3), mirada=(0.0, -0.7), spin=0.0, depth=0.3 * emb)
def comp_sad(t):       # colgando y ESCORADA: cabeza y cola caidas, aletas caidas, un ladeo fijo como un animal enfermo, se hunde despacio (20 s). FIRMA: escora y aletas caidas, casi sin moverse.
    hund = 0.5 + 0.5 * _onda(t, 20, -0.25)
    return dict(pitch=-0.2, roll=0.14, yaw=0.0, head=-0.35, spine=[0.03, 0.06, 0.1, 0.15, 0.2, 0.25],
                fluke=0.2, flap=-0.35 + 0.02 * _onda(t, 8), ladeo=0.1, jaw=0.0, cara=(0.55, 0.0, 1.0, 0.0), mirada=(0.0, -0.9), spin=0.0, depth=-0.7 - 0.3 * hund)
def comp_angry(t):     # LOBTAILING: levanta la cola despacio y la GOLPEA (3.2 s), sacude la cabeza; cara furiosa. FIRMA: el golpe de cola.
    arriba = 0.5 + 0.5 * _onda(t, 3.2, 0.25); golpe = _pulso(t, 3.2, 0.12, 0.5)
    cola = -0.5 * arriba + 0.35 * golpe
    return dict(pitch=-0.2, roll=0.05 * golpe, yaw=0.12 * _onda(t, 0.8) * golpe, head=-0.15 - 0.1 * golpe, spine=[0, 0.02, cola * 0.2, cola * 0.4, cola * 0.7, cola],
                fluke=0.3 * arriba - 0.4 * golpe, flap=-0.15, ladeo=0.0, jaw=0.05 + 0.2 * golpe, cara=(0.25, 1.0, 0.0, 0.0), mirada=(0.0, 0.1), spin=0.0, depth=0.0)
def comp_alert(t):     # ROUNDING OUT: lomo arqueado, baja, aletas pegadas, la cabeza escanea RAPIDO (1.2 s) y cada 5 s un respingo. FIRMA: tensa, rapida, sin subir.
    susto = _pulso(t, 5, 0.1)
    return dict(pitch=0.0 - 0.1 * susto, roll=0.0, yaw=0.1 * _onda(t, 2.4), head=-0.1 + 0.15 * _onda(t, 1.2) + 0.1 * susto, spine=[0.08, 0.13, 0.15, 0.13, 0.08, 0.03],
                fluke=0.05 * susto, flap=-0.1, ladeo=0.0, jaw=0.0, cara=(0.0, 0.3, 0.0, 0.7), mirada=(0.9 * _onda(t, 1.2), 0.2), spin=0.0, depth=0.0)
def comp_diving(t):    # HIGH FLUKING DIVE (medido en una yubarta real: baja a 67 grados con las colas arriba, sube a 57): arquea, pica, COLAS ARRIBA, baja hondo (14 s), vuelve. FIRMA: el arco y las colas verticales.
    f = (t / 14) % 1.0
    arco = _pulso(t, 14, 0.12, 0.0); pica = _suave01(f / 0.3) if f < 0.3 else 1.0; hondo = _rampa(t, 14, 0.3, 0.65); vuelve = max(0.0, (f - 0.65) / 0.35) if f > 0.65 else 0.0
    nariz = pica * (1 - vuelve)
    return dict(pitch=-0.7 * nariz + 0.1 * arco, roll=0.0, yaw=0.0, head=-0.2 * nariz, spine=[0.06 * arco, 0.04 * arco - 0.03 * nariz, -0.08 * nariz, -0.15 * nariz, -0.25 * nariz, -0.4 * nariz],
                fluke=-0.5 * nariz, flap=0.1, ladeo=0.0, jaw=0.0, cara=(0.6, 0.0, 0.0, 0.0), mirada=(0.0, -0.8), spin=0.0, depth=-1.8 * max(hondo, nariz * 0.8))
def comp_surfacing(t): # BLOW: sube a 45 grados, SOPLA arriba (boca, cabeza, aletas), se nivela y descansa en superficie (9 s). FIRMA: la subida y el soplo.
    f = (t / 9) % 1.0; sube = _suave01(f / 0.35) if f < 0.35 else max(0.0, 1 - (f - 0.35) / 0.25); soplo = _pulso(t, 9, 0.12, 0.62); arriba = _rampa(t, 9, 0.3, 0.75)
    return dict(pitch=0.45 * sube, roll=0.0, yaw=0.0, head=0.2 * sube + 0.3 * soplo, spine=[-0.03 * sube, -0.05 * sube, -0.06 * sube, -0.04 * sube, 0, 0.03 * sube],
                fluke=-0.1 * sube, flap=0.25 + 0.4 * soplo, ladeo=0.0, jaw=0.08 + 0.4 * soplo, cara=(0.1, 0.0, 0.0, 0.3 + 0.5 * soplo), mirada=(0.0, 0.6), spin=0.0, depth=1.2 * arriba)
COMPORTAMIENTOS = {"calm": comp_calm, "singing": comp_singing, "playful": comp_playful, "curious": comp_curious, "feeding": comp_feeding,
                   "sad": comp_sad, "angry": comp_angry, "alert": comp_alert, "diving": comp_diving, "surfacing": comp_surfacing}
# cuanto se nota el latido en cada animo (0..1), por lo que midio el EmotiBit al actor: calm casi nada, angry/feeding todo
# la cola (turbina) gira distinto en cada animo: radianes por segundo, o "pulso" = una vuelta por latido del actor
TURBINA_ANIMO = {"calm": 0.6, "sad": 0.25, "diving": 0.9, "surfacing": 1.8, "curious": 1.4, "feeding": 2.5, "alert": 3.0, "playful": 4.0, "angry": 7.0, "singing": "pulso"}
LATIDO_ANIMO = {"calm": 0.1, "sad": 0.2, "singing": 0.3, "diving": 0.3, "surfacing": 0.5, "curious": 0.5, "alert": 0.8, "playful": 0.8, "feeding": 1.0, "angry": 1.0}
COMP_CERO = dict(pitch=0.0, roll=0.0, yaw=0.0, head=0.0, spine=[0.0] * 6, fluke=0.0, flap=0.0, ladeo=0.0, jaw=0.0, cara=(0.0, 0.0, 0.0, 0.0), mirada=(0.0, 0.0), spin=0.0, depth=0.0)
def comportamiento(t, dom, sec, w_dom=0.8):
    a = COMPORTAMIENTOS.get(dom, comp_calm)(t); b = COMPORTAMIENTOS.get(sec, comp_calm)(t); w = 1.0 - w_dom
    out = {k: a[k] * w_dom + b[k] * w for k in a if k not in ("spine", "cara", "mirada")}
    out["spine"] = [x * w_dom + y * w for x, y in zip(a["spine"], b["spine"])]
    out["cara"] = tuple(x * w_dom + y * w for x, y in zip(a["cara"], b["cara"])); out["mirada"] = tuple(x * w_dom + y * w for x, y in zip(a["mirada"], b["mirada"]))
    return out

# ============================================================
# ANIMATION
# ============================================================
# ENERGIA DEL ESTILO: cuanto mueve el cuerpo cada actor, medido en sus tomas (movimiento de cabeza por cuadro: violeta
# 0.027, sanam 0.035, suri 0.035, dan 0.043), como factor sobre el comportamiento del animo. Violeta actua quieta y
# con la cara; Dan con todo el cuerpo. Con promedio o sin estilo, 1.0.
ESTILO_ENERGIA = {"violeta": 0.7, "sanam": 1.0, "suri": 1.15, "dan": 1.35}
_red_estilo = {"modelo": None, "t0": None, "estilo": None}
def completar_con_red(d, t):
    """la visita trae su cara y su animo; lo que no trae (manos, pulso, piel) lo pone la red con el estilo del actor
    al que se parece (`estilo` en el paquete, del parecido del grabador). Asi nunca es una grabacion: es el animo de la
    visita actuado con el cuerpo de una persona grabada. Si no hay estilo ni animo, no toca nada."""
    p = bpy.context.scene.ballena; elegido = (p.actor_red or "auto").strip().lower()
    estilo = d.get('estilo') if elegido == "auto" else (None if elegido == "promedio" else elegido)
    bpy.app.driver_namespace["_ballena_estilo"] = d.get('estilo')
    animo = d.get('actor_animo') or (p.comportamiento if p.comportamiento != "auto" else None)
    if not animo or (estilo is None and elegido == "auto" and not d.get('estilo')): return d
    try:
        if _red_estilo["modelo"] is None:
            import sys; sys.path.insert(0, YAKUMAMA); import importlib, yakumama_modelo; importlib.reload(yakumama_modelo)
            _red_estilo["modelo"] = yakumama_modelo.Modelo(os.path.join(YAKUMAMA, "modelos", "movimiento_pesos.npz"))
        if _red_estilo["estilo"] != estilo: _red_estilo["estilo"] = estilo; _red_estilo["t0"] = t
        pk = _red_estilo["modelo"].paquete(animo, t - _red_estilo["t0"], actor=estilo)
    except Exception as e:
        if _red_estilo.get("err") != str(e): _red_estilo["err"] = str(e); print(f"   (red de estilo: {e})")
        return d
    out = dict(d)
    if 'l_palm_y' not in d and 'r_palm_y' not in d:
        for k in ('l_palm_y', 'l_palm_x', 'r_palm_y', 'r_palm_x'):
            if k in pk: out[k] = pk[k]
    if not d.get('emotibit_hr'): out['emotibit_hr'] = pk['emotibit_hr']
    if not d.get('emotibit_eda'): out['emotibit_eda'] = pk['emotibit_eda']
    return out
def breathe():
    _n = time.time(); breathe._cuadros = getattr(breathe, "_cuadros", 0) + 1
    if _n - getattr(breathe, "_fps_t", 0) >= 1.0: breathe._fps = breathe._cuadros / max(1e-3, _n - getattr(breathe, "_fps_t", _n - 1)); breathe._cuadros = 0; breathe._fps_t = _n
    global turbine_active, turbine_angle, prev_btn
    try:
        while True:
            data, _ = sock.recvfrom(4096)
            try: latest_data.update(json.loads(data.decode()))
            except: pass
    except: pass
    d = suavizar(latest_data)
    t = time.time()
    d = completar_con_red(d, t)
    m = compute_mood(d)
    solo_cara = bool(d.get('solo_cara', 0))
    cabeza_fija = int(d.get('solo_cara', 0) or 0) == 2   # 2 = ni la cabeza se mueve: solo boca, parpadeo y cejas
    anclada = bool(d.get('anclada', 0))   # tecla a: el cuerpo se mueve (poses, aletas, columna) pero no viaja por el espacio
    quieta = solo_cara or anclada         # nada mueve el hueso root: ni mano, ni joystick, ni nado, ni profundidad
    cara_actor = solo_cara or ('blink' in d and 'jaw_open' in d)   # hay cara trackeada: boca, parpadeo y cejas son del actor en todos los modos

    (mouth_scale, tongue_scale, auto_turn_scale, follow_hand,
     color_track, color_follow, use_brain,
     virtual_joy_x, virtual_joy_y,
     music_volume, sound_volume) = read_controls()

    if use_brain and 'whale_curious' in d:
        for k in m:
            brain_val = float(d.get(f'whale_{k}', m[k]))
            m[k] = m[k] * 0.7 + brain_val * 0.3
    actor = d.get('actor_animo')   # el reconocedor del grabador: el animo que ve en la cara del actor manda, entero
    try:
        if d.get('soltar_manual') and bpy.context.scene.ballena.comportamiento != "auto":
            bpy.context.scene.ballena.comportamiento = "auto"; print("  menu Comportamiento -> Automatico (llego una toma)")
        manual = bpy.context.scene.ballena.comportamiento   # el panel manda sobre todo lo demas
        if manual != "auto": actor = manual
    except Exception: pass
    if actor in m:
        for k in m: m[k] = 1.0 if k == actor else 0.0
        whale_mood.update(m)

    dominant = max(m, key=m.get)
    bpy.app.driver_namespace["_ballena_dominant"] = dominant
    sorted_moods = sorted(m.items(), key=lambda x: -x[1])
    dom_name = sorted_moods[0][0]
    sec_name = sorted_moods[1][0] if len(sorted_moods) > 1 else dom_name
    # PULSO DEL ACTOR -> tempo, energia y latido del cuerpo (EmotiBit via grabar_ballena.py / reproducir.py)
    #   tempo: 75 lpm = ritmo normal; 120 lpm = todo un 60% mas rapido; 50 lpm = mas lento.  energia: sube con el pulso.
    #   latido: cada latido, un pulso corto recorre el cuerpo (escala de la columna, aletas, cabeza).  eda alta -> mas tension.
    try: hr = float(d.get('emotibit_hr', 0) or 0)
    except Exception: hr = 0.0
    if not hasattr(breathe, '_hr'): breathe._hr = 75.0; breathe._latido = 0.0; breathe._tiempo = 0.0; breathe._t_prev = t
    if 30 < hr < 220: breathe._hr += (hr - breathe._hr) * 0.05
    tempo = max(0.6, min(1.6, breathe._hr / 75.0)) if 30 < hr < 220 else 1.0
    energia = max(0.0, min(1.0, (breathe._hr - 60.0) / 60.0)) if 30 < hr < 220 else 0.0
    try: eda = float(d.get('emotibit_eda', 0) or 0)
    except Exception: eda = 0.0
    tension = max(0.0, min(1.0, (eda - 2.0) / 8.0)) if 0.1 < eda < 1000 else 0.0
    breathe._tiempo += (t - breathe._t_prev) * tempo; breathe._t_prev = t          # reloj del comportamiento, acelerado por el pulso
    if 30 < hr < 220:
        breathe._latido += breathe._hr / 60.0 * 2 * math.pi * (t - breathe._t_prev + 0.033)
        beat = max(0.0, math.sin(breathe._latido)) ** 4
    else: beat = 0.0
    # COMPORTAMIENTO del animo (movimiento real, ver arriba); en solo cara el cuerpo descansa
    comp = COMP_CERO if solo_cara else comportamiento(breathe._tiempo, dom_name, sec_name, 1.0 if actor in m else 0.8)   # con actor: un solo animo, sin mezcla
    excitacion = max(0.0, min(1.0, 0.6 * energia + 0.4 * tension))
    fuerza_latido = LATIDO_ANIMO.get(dom_name, 0.5) * (0.5 + 0.5 * excitacion)   # calm ~0.05-0.1, angry/feeding hasta 1
    beat *= fuerza_latido
    if not solo_cara:
        comp = dict(comp)
        k_est = ESTILO_ENERGIA.get(str(d.get('estilo') or ''), 1.0)   # el cuerpo se mueve con la energia del actor cuyo estilo lleva
        if k_est != 1.0:
            for kk in ("head", "flap", "ladeo", "fluke"): comp[kk] = comp[kk] * k_est
            comp["spine"] = [v * k_est for v in comp["spine"]]
        if 'cuerpo_pitch' in d:   # UN CUERPO HUMANO CONDUCE (bailar.py): no copia el esqueleto, suma sus cualidades al comportamiento del animo
            q = lambda k, lo=-1.0, hi=1.0: max(lo, min(hi, float(d.get(k, 0) or 0)))
            comp["pitch"] -= 0.45 * q('cuerpo_pitch')          # inclinado adelante -> nariz abajo
            comp["roll"] += 0.35 * q('cuerpo_roll')             # torcido -> se ladea
            comp["yaw"] += 0.5 * q('cuerpo_yaw')                # gira el cuerpo -> gira ella
            comp["depth"] += 0.6 * q('cuerpo_profundidad')      # agachado -> baja; salto -> sube (medio: una visita parada no debe hundirla)
            ke = 0.4 + 1.3 * q('cuerpo_energia', 0.0, 1.0)      # la energia del cuerpo escala todo lo demas
            for kk in ("flap", "ladeo", "fluke"): comp[kk] = comp[kk] * ke
            comp["spine"] = [v * ke for v in comp["spine"]]
        comp["head"] = comp["head"] + 0.03 * beat + 0.06 * tension * _onda(t, 0.9)   # el latido asoma en la cabeza; la tension la hace vibrar
        comp["flap"] = comp["flap"] + 0.06 * beat + 0.1 * energia; comp["fluke"] = comp["fluke"] - 0.05 * beat
        if dom_name == "singing" and cara_actor:   # CANTO: el cuerpo se mueve con la boca del actor
            canto = max(0.0, min(1.0, float(d.get('jaw_open', 0))))
            comp["head"] += 0.35 * canto; comp["flap"] += 0.3 * canto; comp["fluke"] -= 0.1 * canto   # (la cabeza del animo pesa 30% cuando hay actor: por eso 0.35)
            comp["spine"] = [v - 0.04 * canto * (i / 5.0) for i, v in enumerate(comp["spine"])]   # la cola se levanta apenas con la nota
            comp["roll"] += 0.08 * canto * _onda(t, 2.5)                                          # y se mece
    spine_bones = ['spine', 'spine.001', 'spine.002', 'spine.003', 'spine.004', 'spine.005']
    for i, bone in enumerate(spine_bones):
        rot(bone, comp["spine"][i], 0, 0.04); rot(bone, 0.0, 1, 0.04); rot(bone, 0.0, 2, 0.04)   # eje 2: la ola de nado se suma abajo
    rot('head', comp["head"] * (0.3 if 'head_yaw' in d else 1.0), 0, 0.04); rot('head', 0.0, 1, 0.04); rot('head', 0.0, 2, 0.04)
    rot('back_fin.U', comp["fluke"], 0, 0.05); rot('back_fin.U', 0.0, 2, 0.05)
    rot('back_fin.L', comp["fluke"] * 0.5, 0, 0.05); rot('back_fin.L', 0.0, 2, 0.05)
    rot('back_fin.R', comp["fluke"] * 0.5, 0, 0.05); rot('back_fin.R', 0.0, 2, 0.05)
    rot('root', comp["pitch"], 0, 0.03)
    if comp["spin"] > 0.001:   # vueltas (playful): directo, sin suavizar
        current_rots['root:1'] = comp["roll"] + comp["spin"]; breathe._girando = True
        try: armature.pose.bones['root'].rotation_euler[1] = current_rots['root:1']
        except Exception: pass
    else:
        if getattr(breathe, '_girando', False):   # termino: normalizar para que no se desenrolle al reves
            v = current_rots.get('root:1', 0.0) % (2 * math.pi); current_rots['root:1'] = v - 2 * math.pi if v > math.pi else v; breathe._girando = False
        rot('root', comp["roll"], 1, 0.03)   # eje 1 = rolido
    if not cara_actor:
        for e in ('eye.L', 'eye.R'): rot(e, 0.0, 0, 0.1); rot(e, 0.0, 1, 0.1); rot(e, 0.0, 2, 0.1)

    # JAW
    singing = m.get("singing", 0); feeding = m.get("feeding", 0)
    calm = m.get("calm", 0)
    jaw = max(0.0, comp["jaw"]); mouth_scale = 1.0   # la boca del animo a escala completa (el slider Mouth era del sistema viejo)
    if cara_actor:   # boca = la del actor, rango completo (ignora el slider Mouth del panel)
        g_boca = 0.6 if d.get('red') else 0.25   # actor real: tope 0.25 rad (boca -40%); la red actuando un estilo: casi completa, para que se vea la diferencia
        jaw = max(max(0.0, min(1.0, float(d.get('jaw_open', 0)))) * g_boca, comp["jaw"]); mouth_scale = 1.0   # la boca del animo a escala completa, gana la mas abierta
        tongue_scale = 0.0   # el sway automatico no: la lengua sale con tongue_out (Face Landmarker via grabar_ballena.py)
        lengua = max(0.0, min(1.0, float(d.get('tongue_out', 0))))
        if lengua > 0.2: jaw = max(jaw, 0.1 + 0.2 * lengua)   # para que se vea, la boca se abre un poco
    jaw_lo_x = jaw * 1.2 * mouth_scale
    jaw_lo2_x = jaw * 0.8 * mouth_scale
    rot('mouth_inf.001', jaw_lo_x, 0, 0.08)
    rot('mouth_inf.002', jaw_lo2_x, 0, 0.08)
    rot('mouth_sup.001', -jaw * 0.4 * mouth_scale, 0, 0.08)
    rot('mouth_sup.002', -jaw * 0.3 * mouth_scale, 0, 0.08)

    # TONGUE
    mouth_open = max(0.0, jaw_lo_x)
    gate = min(1.0, mouth_open / 0.3)
    tongue_curl = math.sin(t * 1.5) * 0.15 * gate
    tongue_sway = math.sin(t * 0.9) * 0.20 * gate
    feed_curl_down = -feeding * 0.25 * gate
    tongue_pct = (0.3, 0.45, 0.6, 0.75, 0.9, 1.0)
    try:   # LENGUA AFUERA: se empuja la raiz hacia adelante por su eje (y) y se levanta apenas
        armature.pose.bones['tongue.001'].location.y = sm('tongue:ly', 0.6 * lengua if solo_cara else 0.0, 0.25)
    except: pass
    if solo_cara: rot('tongue.001', 0.1 * lengua, 0, 0.25)
    for i, b in enumerate(('tongue.001','tongue.002','tongue.003','tongue.004','tongue.005','tongue.006')):
        pct = tongue_pct[i]
        if solo_cara and b == 'tongue.001': rot(b, 0.0, 1, 0.15); rot(b, 0.0, 2, 0.15); continue
        rot(b, (tongue_curl + feed_curl_down) * pct * tongue_scale, 0, 0.08)
        rot(b, 0.0, 1, 0.15)
        rot(b, tongue_sway * pct * tongue_scale, 2, 0.08)

    # BREATHING
    surfacing = m.get("surfacing", 0); alert_v = m.get("alert", 0)
    br = 0.25 + surfacing * 0.5 + alert_v * 0.2
    breath = math.sin(t * br) * (0.06 + surfacing * 0.1)
    if jaw < 0.1 and not cara_actor:
        rot('mouth_sup.001', breath, 0, 0.06)
        rot('mouth_sup.002', breath * 0.6, 0, 0.06)

    # OSCILLATION
    osc = []   # (las OSCILLATIONS viejas se reemplazaron por COMPORTAMIENTOS)
    calm_dampen = max(0.1, 1.0 - calm * 0.8)
    for bone, axis, amp, freq in osc:
        phase = hash(bone) * 0.1
        val = math.sin(t * freq * 2 * math.pi + phase) * amp * calm_dampen
        cur = current_rots.get(f'{bone}:{axis}', 0.0)
        rot(bone, cur + val, axis, 0.06)

    # FIN OSCILLATION
    playful = m.get("playful", 0); angry = m.get("angry", 0)
    fin_speed = 0.3 + playful * 0.8 + feeding * 0.5 + angry * 1.2
    fin_amp = (0.05 + playful * 0.2 + feeding * 0.15 + surfacing * 0.2 + angry * 0.15) * calm_dampen * (1.0 + 0.6 * energia)
    fin_speed *= tempo
    fin_wave = 0.0 if solo_cara else math.sin(t * fin_speed) * fin_amp
    # ALAS: en modo cuerpo cada mano del actor levanta o baja la aleta de su lado (palm_y: 0 arriba, 1 abajo).
    ALAS_CRUZADAS = False   # True si la mano izquierda mueve la aleta derecha (MediaPipe etiqueta en espejo)
    manos = {'.L': d.get('l_palm_y'), '.R': d.get('r_palm_y')}
    if ALAS_CRUZADAS: manos = {'.L': manos['.R'], '.R': manos['.L']}
    if not hasattr(breathe, '_alas'): breathe._alas = {'.L': 0.0, '.R': 0.0}
    for suffix in ['.L', '.R']:
        sign = 1 if suffix == '.L' else -1
        objetivo = 0.0
        if manos[suffix] is not None:   # en todos los modos: la altura de la mano manda el aleteo de su lado
            try: objetivo = (0.5 - max(0.0, min(1.0, float(manos[suffix])))) * 1.0   # mano arriba -> aleta arriba (eje 1, hasta ~29 grados)
            except Exception: objetivo = 0.0
        breathe._alas[suffix] += (objetivo - breathe._alas[suffix]) * 0.08   # suave (~0.4 s): sin temblor de la mano
        alas = breathe._alas[suffix]
        alas += comp["flap"]
        rot(f'side_fine{suffix}', alas * sign, 1, 0.1)
        rot(f'side_fine{suffix}.001', alas * 0.35 * sign, 1, 0.1)
        rot(f'side_fine{suffix}.002', alas * 0.15 * sign, 1, 0.1)
        rot(f'side_fine{suffix}', 0.12 * sign, 2, 0.04); rot(f'side_fine{suffix}.001', 0.08 * sign, 2, 0.04); rot(f'side_fine{suffix}.002', 0.05 * sign, 2, 0.04)
    # LADEO: una mano mas alta que la otra -> una aleta sube y la otra baja (eje 0), como un viraje
    if not hasattr(breathe, '_ladeo'): breathe._ladeo = 0.0
    try:
        if manos['.L'] is not None and manos['.R'] is not None:
            obj_ladeo = (float(manos['.R']) - float(manos['.L'])) * 0.6   # izquierda mas alta -> ladeo positivo
        else: obj_ladeo = 0.0
    except Exception: obj_ladeo = 0.0
    breathe._ladeo += (obj_ladeo - breathe._ladeo) * 0.08
    ladeo = breathe._ladeo + comp["ladeo"]
    for suffix, sign in (('.L', 1), ('.R', -1)):   # signos espejados en eje 0 = una sube y la otra baja (ver renders)
        rot(f'side_fine{suffix}', ladeo * sign, 0, 0.1)
        rot(f'side_fine{suffix}.001', ladeo * 0.35 * sign, 0, 0.1)
        rot(f'side_fine{suffix}.002', ladeo * 0.15 * sign, 0, 0.1)
        cur0 = current_rots.get(f'side_fine{suffix}:2', 0.0)
        cur1 = current_rots.get(f'side_fine{suffix}.001:2', 0.0)
        cur2 = current_rots.get(f'side_fine{suffix}.002:2', 0.0)
        rot(f'side_fine{suffix}', cur0 + fin_wave * sign, 2, 0.04)
        rot(f'side_fine{suffix}.001', cur1 + fin_wave * 0.7 * sign, 2, 0.04)
        rot(f'side_fine{suffix}.002', cur2 + fin_wave * 0.5 * sign, 2, 0.04)

    # PERFORMER HEAD
    head_yaw = max(-1.0, min(1.0, float(d.get('head_yaw', 0))))
    head_pitch = max(-0.8, min(0.8, float(d.get('head_pitch', 0))))
    if cabeza_fija: head_yaw = head_pitch = 0.0
    pw = (0.8 if d.get('red') else 0.5) if (solo_cara or 'head_yaw' in d) else 0.2 + m.get("alert", 0) * 0.3   # con cara: la cabeza sigue al actor (~14 grados; la red con estilo, ~23)
    cur_head_z = current_rots.get('head:2', 0.0)
    cur_head_x = current_rots.get('head:0', 0.0)
    rot('head', cur_head_z + (-head_yaw * pw * 0.5), 2, 0.05)
    rot('head', cur_head_x + (-head_pitch * pw * 0.8), 0, 0.05)
    if cara_actor:   # ojos: mirada real del actor (eye_yaw/eye_pitch, blendshapes) o, si no hay, hacia donde apunta la nariz
        if 'eye_yaw' in d:
            ey = max(-1.0, min(1.0, float(d.get('eye_yaw', 0)) + 0.6 * comp["mirada"][0])); ep = max(-1.0, min(1.0, float(d.get('eye_pitch', 0)) + 0.6 * comp["mirada"][1]))
            if MIRADA_ESPEJO: ey = -ey
            # mirar a la derecha: el ojo izquierdo gira hacia adelante y el derecho hacia atras; arriba: los dos arriba
            rot(OJO_IZQ, ey * MIRADA_AMP, 0, 0.3);  rot(OJO_DER, -ey * MIRADA_AMP, 0, 0.3)
            rot(OJO_IZQ, ep * MIRADA_AMP, 2, 0.3);  rot(OJO_DER, -ep * MIRADA_AMP, 2, 0.3)
            rot(OJO_IZQ, 0.0, 1, 0.3); rot(OJO_DER, 0.0, 1, 0.3)
        else:
            rot('eye.L', head_pitch * 0.15, 0, 0.1); rot('eye.R', head_pitch * 0.15, 0, 0.1)
            rot('eye.L', head_yaw * 0.15, 1, 0.1);   rot('eye.R', -head_yaw * 0.15, 1, 0.1)
    if not cara_actor and not solo_cara:   # sin actor: la mirada del animo
        ey, ep = comp["mirada"]
        rot(OJO_IZQ, ey * MIRADA_AMP, 0, 0.2); rot(OJO_DER, -ey * MIRADA_AMP, 0, 0.2); rot(OJO_IZQ, ep * MIRADA_AMP, 2, 0.2); rot(OJO_DER, -ep * MIRADA_AMP, 2, 0.2)

    # SHAPE KEYS
    w_sad = m.get("sad", 0); curious = m.get("curious", 0)
    sk_targets = SHAPES.get(dom_name, {})
    if not hasattr(breathe, '_blink_timer'): breathe._blink_timer = 0
    if not hasattr(breathe, '_blink_val'): breathe._blink_val = 0
    breathe._blink_timer += 0.033
    blink_interval = 3.5 - alert_v * 1.5 + calm * 3.0
    if not hasattr(breathe, '_blink_hold'): breathe._blink_hold = 0
    if breathe._blink_timer > blink_interval:
        breathe._blink_timer = 0
        breathe._blink_val = 1.0; breathe._blink_hold = 5   # cerrado 5 cuadros, como el parpadeo del actor
    if breathe._blink_hold > 0: breathe._blink_hold -= 1
    else: breathe._blink_val = max(0, breathe._blink_val - 0.033 / 0.12)
    if dom_name == "calm": sleep_val = 0.6 + calm * 0.3
    elif dom_name == "sad": sleep_val = 0.4 + w_sad * 0.3
    elif dom_name == "singing": sleep_val = 0.3
    else: sleep_val = 0.0
    parpadeo = max(breathe._blink_val, sleep_val)
    parpadeo = max(0, min(1, parpadeo))
    c_parp, c_angry, c_sad, c_asom = comp["cara"]   # expresion del animo (comportamiento)
    if cara_actor:   # la del actor encima de la del animo
        shape('parpadeo', max(float(d.get('blink', 0)), c_parp), 0.6)   # rapido: un parpadeo dura 3-5 cuadros
        shape('angry', max(float(d.get('brow_down', 0)), c_angry))
        shape('sad', max(float(d.get('mouth_sad', 0)), c_sad))
        shape('asombrado', max(float(d.get('brow_up', 0)), c_asom))
    else:
        shape('parpadeo', max(parpadeo, c_parp), 0.6)   # rapido, si no el parpadeo automatico no se ve
        shape('angry', max(c_angry, min(1, sk_targets.get("angry", 0) * 1.5 + angry * 0.6)))
        shape('sad', max(c_sad, min(1, sk_targets.get("sad", 0) * 1.3 + w_sad * 0.5)))
        shape('asombrado', max(c_asom, min(1, sk_targets.get("asombrado", 0) * 1.3 + curious * 0.4 + surfacing * 0.3)))

    # COLOR DE PIEL POR ANIMO: la piel vira al color del animo dominante (mismo mapa color->animo de Brian, mas suave);
    # el slider Color Follow sigue mandando si esta subido (tinte por el color de la escena)
    seen_color = str(d.get('scene_color', 'neutral'))
    bpy.app.driver_namespace["_ballena_seen_color"] = seen_color
    ropa = d.get('color_ropa')   # el grabador lo manda solo cuando a ella le gusta la ropa de la visita (a veces, no siempre)
    if getattr(breathe, "_dom_color", None) != dominant: breathe._dom_color = dominant; breathe._color_animo_hasta = t + 6.0   # cambio de animo: 6 s con SU color, aunque lleve la ropa
    habla_el_animo = t < getattr(breathe, "_color_animo_hasta", 0.0)
    if isinstance(ropa, (list, tuple)) and len(ropa) == 3 and bool(d.get('visita')) and not habla_el_animo:
        mr = MOOD_RGB.get(dominant, (0.5, 0.5, 0.5)); mezcla = tuple(0.75 * float(ropa[i]) + 0.25 * mr[i] for i in range(3))   # su ropa, con un cuarto del animo
        tint_body(mezcla, lerp_amount=0.02)   # ~2 s: se tine despacio
    elif color_follow >= 0.5 and seen_color in COLOR_TO_MOOD and not cara_actor:   # el color de la escena solo cuando NO hay nadie: con una cara, manda el animo (la luz de la sala la dejaba dorada)
        tint_body(SCENE_COLORS_RGB[seen_color], lerp_amount=0.04 * color_follow)
    elif dominant in MOOD_RGB:
        tint_body(MOOD_RGB[dominant], lerp_amount=0.04)   # ~1 s de transicion

    # SMILE → APPROACH
    perf_sad = float(d.get('mouth_sad', 0))
    perf_brow_up = float(d.get('brow_up', 0))
    perf_jaw = float(d.get('jaw_open', 0))
    smile = max(0, (1.0 - perf_sad) * perf_brow_up - 0.2)
    if smile > 0.1 and not solo_cara:
        approach_speed = smile * 0.02
        if not hasattr(breathe, '_auto_y'): breathe._auto_y = 0.0
        breathe._auto_y -= approach_speed

    # S-SHAPE SWIM
    water = float(d.get('water', 0))
    swim_energy = m.get("playful",0)*0.8 + m.get("feeding",0)*0.5 + m.get("singing",0)*0.3 + m.get("angry",0)*0.7
    swim_energy *= calm_dampen
    swim_energy += 0.3 * energia                    # pulso alto: nada con mas fuerza
    if solo_cara: water = 0.0; swim_energy = 0.0   # sin nado automatico ni ola en la columna
    if anclada: water = 0.0                        # sin nado automatico, pero la ola de la columna sigue
    swim_speed = 0.2 + swim_energy * 1.2
    swim_amp = 0.01 + swim_energy * 0.12
    spine_bones = ['spine', 'spine.001', 'spine.002', 'spine.003', 'spine.004', 'spine.005']
    for i, bone in enumerate(spine_bones):
        phase = -i * 0.7
        amp = swim_amp * (0.3 + i * 0.14)
        wave = 0.0 if solo_cara else math.sin(t * swim_speed * 2 * math.pi + phase) * amp
        cur = current_rots.get(f'{bone}:2', 0.0)
        rot(bone, cur + wave, 2, 0.04)

    # HANDS + JOYSTICK
    lx = float(d.get('l_palm_x', 0.5))
    ly = float(d.get('l_palm_y', 0.5))
    lz = float(d.get('l_depth', 0.15))
    hand_present = ('l_palm_x' in d) and not quieta
    if hand_present:
        hx, hz, hy = (lx-0.5)*-4.0, (0.5-ly)*6.0, (lz-0.15)*3.0
    else:
        hx, hy, hz = 0, 0, 0

    # Combine real joystick + virtual joystick. Real values are
    # deadzoned first; virtual adds on top, then clamp to [-1, 1].
    jx_real = float(d.get('joy_x', 0))
    jy_real = float(d.get('joy_y', 0))
    if abs(jx_real) < 0.08: jx_real = 0
    if abs(jy_real) < 0.08: jy_real = 0
    jx = max(-1.0, min(1.0, jx_real + virtual_joy_x))
    jy = max(-1.0, min(1.0, jy_real + virtual_joy_y))
    if quieta: jx = jy = 0.0   # ni joystick ni panel mueven el cuerpo
    jbtn = int(d.get('joy_btn', 0))

    if not hasattr(breathe, '_wy'): breathe._wy = 0.0
    if not hasattr(breathe, '_wz'): breathe._wz = 0.0
    if not hasattr(breathe, '_auto_x'): breathe._auto_x = 0.0
    if not hasattr(breathe, '_auto_y'): breathe._auto_y = 0.0

    # YAW PRIORITY: Follow Hand > Color Track > Joystick > Auto
    hand_follow_active = hand_present and (follow_hand > 0.02)
    color_x_raw = None if quieta else d.get('color_x', None)
    cx = None
    if color_x_raw is not None:
        try:
            cx = float(color_x_raw)
            bpy.app.driver_namespace["_ballena_color_x"] = cx
        except: cx = None
    color_track_active = (cx is not None) and (color_track > 0.02) and (not hand_follow_active)

    if hand_follow_active:
        target_wy = -(lx - 0.5) * 2.5
        target_wz = (0.5 - ly) * 2.0
        lerp_wy = 0.12 * follow_hand
        lerp_wz = 0.08 * follow_hand
        breathe._wy = breathe._wy * (1 - lerp_wy) + target_wy * lerp_wy
        breathe._wz = breathe._wz * (1 - lerp_wz) + target_wz * lerp_wz
        auto_turn = 0.0
    elif color_track_active:
        target_wy = -(cx - 0.5) * 2.5
        lerp_wy = 0.10 * color_track
        breathe._wy = breathe._wy * (1 - lerp_wy) + target_wy * lerp_wy
        auto_turn = 0.0
    else:
        auto_turn = 0.0
        should_swim = water > 0.5 and calm < 0.4 and abs(jx) < 0.01
        if should_swim:
            base_turn = 0.008
            mood_turn = m.get("playful",0) * 0.015 + m.get("curious",0) * 0.01 + m.get("angry",0) * 0.02
            change_rate = 0.03 + m.get("curious",0) * 0.05
            direction = 1 if math.sin(t * change_rate) > 0 else -1
            auto_turn = (base_turn + mood_turn) * direction * auto_turn_scale
        breathe._wy += jx * 0.03 + auto_turn
        breathe._wz += jy * 0.02

    rot('root', breathe._wy + comp["yaw"], 2, 0.06)   # eje 2 = giro (el original usaba el 1 y rolaba)
    breathe._wz = max(-5, min(5, breathe._wz))

    auto_z = 0
    should_swim = (not hand_follow_active) and (not color_track_active) and water > 0.5 and calm < 0.4 and abs(jx) < 0.01
    if should_swim:
        swim_fwd = (0.01 + swim_energy * 0.03) * auto_turn_scale
        breathe._auto_x += math.sin(breathe._wy) * swim_fwd
        breathe._auto_y += math.cos(breathe._wy) * swim_fwd
        auto_z = math.sin(t * 0.15) * 0.3 * water
    elif water > 0.5 and calm >= 0.4:
        breathe._auto_x *= 0.998
        breathe._auto_y *= 0.998

    depth_y = 0.0 if quieta else -m.get("diving",0) * 0.2 + m.get("surfacing",0) * 0.15
    final_x = hx + breathe._auto_x
    final_y = hy + depth_y + breathe._auto_y
    final_z = hz + breathe._wz + (auto_z if water > 0.5 else 0) + comp["depth"]   # diving baja, surfacing y curious suben
    loc('root', sm('bfx',final_x,0.03), sm('bfy',final_y,0.03), sm('bfz',final_z,0.03))

    # TURBINE
    if jbtn == 1 and prev_btn == 0: turbine_active = not turbine_active
    prev_btn = jbtn
    manual_turbine = bpy.app.driver_namespace.get("_ballena_turbine_manual", False)
    energy = m.get("playful",0)*0.7 + m.get("feeding",0)*0.5 + m.get("alert",0)*0.4 + m.get("singing",0)*0.3
    # COLA (turbina): velocidad por animo, al ritmo del pulso en singing; el boton manual y el joystick la aceleran
    if not solo_cara:
        vel = TURBINA_ANIMO.get(dom_name, 1.0)
        if vel == "pulso": turbine_angle = breathe._latido if (30 < hr < 220) else turbine_angle + 1.2 * 0.033   # una vuelta por latido
        else: turbine_angle += (vel * tempo + (15.0 if (turbine_active or manual_turbine) else 0.0)) * 0.033
        rot('turbine', turbine_angle, 2, 1.0)

    # LATIDO: el cuerpo late al ritmo del corazon del actor (emotibit_hr, EmotiBit via grabar_ballena.py)
    try:   # el latido recorre la columna: spine (pecho) primero, luego .001 y .002 con un poco de retraso
        if not hasattr(breathe, '_beats'): breathe._beats = [0.0] * 6
        breathe._beats = [beat] + breathe._beats[:-1]
        for i, b in enumerate(('spine', 'spine.001', 'spine.002')):
            esc = 1.0 + (0.045, 0.035, 0.02)[i] * breathe._beats[i * 2]
            if f'latido{i}' not in current_rots: current_rots[f'latido{i}'] = 1.0
            armature.pose.bones[b].scale = (sm(f'latido{i}', esc, 0.6),) * 3
    except Exception: pass

    # MOOD SOUND
    if not hasattr(breathe, '_last_mood'):
        breathe._last_mood = None
    if dominant != breathe._last_mood:
        if sound_volume > 0.01:
            play_mood_sound(dominant)
        breathe._last_mood = dominant

    # BASE MUSIC volume — flat, controlled by music_volume slider
    ambient = bpy.app.driver_namespace.get("_ballena_ambient_handle")
    if ambient is not None:
        try:
            ambient.volume = max(0.0, music_volume)
        except: pass

    # SESSION TRACKING
    if not hasattr(breathe, '_fc'): breathe._fc = 0
    breathe._fc += 1
    session_log["total_frames"] = breathe._fc
    color = d.get('scene_color', '?')
    water = float(d.get('water', 0))
    wl = "DRY" if water < 0.05 else "TIP" if water < 0.35 else "HALF" if water < 0.7 else "SUB" if water < 0.95 else "DEEP"
    session_log["mood_counts"][dominant] = session_log["mood_counts"].get(dominant, 0) + 1
    for k, v in m.items(): session_log["peak_moods"][k] = max(session_log["peak_moods"].get(k, 0), v)
    session_log["colors_seen"][color] = session_log["colors_seen"].get(color, 0) + 1
    session_log["water_states"][wl] = session_log["water_states"].get(wl, 0) + 1
    if len(session_log["mood_sequence"]) == 0 or session_log["mood_sequence"][-1] != dominant:
        session_log["mood_sequence"].append(dominant)
        if len(session_log["mood_sequence"]) > 30: session_log["mood_sequence"].pop(0)
    if breathe._fc % 15 == 0:
        try:
            _wb = {k[6:]: float(v) for k, v in d.items() if k.startswith('whale_')}
            bpy.app.driver_namespace["_ballena_sentidos"] = {
                "dominante": dominant, "fuente": ("menú" if (manual != "auto") else ("actor (reconocedor)" if d.get('actor_animo') else ("cerebro Qwen" if use_brain and _wb else "color de la escena"))),
                "cara": bool(cara_actor), "actor": d.get('actor_animo'), "estilo": d.get('estilo'), "bailarin": d.get('bailarin'), "manos": ("2" if ('l_palm_y' in d and 'r_palm_y' in d) else ("1" if ('l_palm_y' in d or 'r_palm_y' in d) else "")),
                "hr": float(d.get('emotibit_hr') or 0) or None, "eda": float(d.get('emotibit_eda') or 0), "therm": float(d.get('emotibit_therm') or 0),
                "color": d.get('scene_color', '—'), "agua": wl if 'wl' in dir() else d.get('water', '—'), "cerebro": (max(_wb, key=_wb.get) if _wb else "—")}
        except Exception: pass
    if breathe._fc % 30 == 0:
        try:
            for w in bpy.data.window_managers[0].windows:
                for ar in w.screen.areas:
                    if ar.type == 'VIEW_3D': ar.tag_redraw()
        except Exception: pass
    if breathe._fc % 60 == 0:
        try:
            with open("/tmp/ballena_receptor.json", "w") as f:
                try: _manual = bpy.context.scene.ballena.comportamiento
                except Exception: _manual = "?"
                _col = None
                try:
                    for _sl in whale_mesh.material_slots:
                        if _sl.material and _sl.material.use_nodes:
                            for _n in _sl.material.node_tree.nodes:
                                if _n.type == 'BSDF_PRINCIPLED': _col = [round(v, 2) for v in _n.inputs["Base Color"].default_value[:3]]; break
                        if _col: break
                except Exception: pass
                json.dump({"version": VERSION, "t": time.time(), "fps": round(getattr(breathe, "_fps", 0.0), 1), "reproduciendo_animacion": bool(getattr(bpy.context.screen, "is_animation_playing", False)) if bpy.context.screen else None, "cuadro": bpy.context.scene.frame_current, "accion": (armature.animation_data.action.name if armature.animation_data and armature.animation_data.action else None), "dominante": dominant, "manual": _manual, "pulso": round(float(getattr(breathe, "_hr", 75.0)), 1), "tempo": round(float(tempo), 2), "energia": round(float(energia), 2), "tension": round(float(tension), 2), "latido": round(float(fuerza_latido), 2), "objeto_rot": [round(float(v), 3) for v in armature.rotation_euler], "objeto_loc": [round(float(v), 2) for v in armature.location], "malla_rot": ([round(float(v), 3) for v in whale_mesh.rotation_euler] if whale_mesh else None), "actor": d.get('actor_animo'), "color": _col, "color_follow": round(color_follow, 2), "material": [sl.material.name for sl in whale_mesh.material_slots if sl.material] if whale_mesh else None, "solo_cara": int(d.get('solo_cara', 0) or 0), "anclada": int(bool(d.get('anclada', 0))),
                           "cara": bool(cara_actor), "fin_L": [round(v, 2) for v in armature.pose.bones['side_fine.L'].rotation_euler], "fin_R": [round(v, 2) for v in armature.pose.bones['side_fine.R'].rotation_euler],
                           "pose": {pb.name: [round(v, 3) for v in pb.rotation_euler] for pb in armature.pose.bones},
                           "root_loc": [round(v, 3) for v in armature.pose.bones['root'].location],
                           "shapes": {k.name: round(k.value, 2) for k in whale_mesh.data.shape_keys.key_blocks} if whale_mesh and whale_mesh.data.shape_keys else {}}, f)
        except Exception: pass
    if breathe._fc % 90 == 0:
        yd = math.degrees(breathe._wy) % 360
        if actor in m: mode = f"ACTOR:{actor}"
        elif cabeza_fija: mode = "SOLO CARA (cabeza fija)"
        elif solo_cara: mode = "SOLO CARA"
        elif anclada: mode = "ANCLADA"
        elif hand_follow_active: mode = "FOLLOW"
        elif color_track_active: mode = f"TRACK({cx:.2f})"
        else: mode = "auto"
        tb = "TURB" if (turbine_active or manual_turbine or energy > 0.6) else "----"
        brain = "B" if use_brain else "-"
        vjoy = ""
        if abs(virtual_joy_x) > 0.05 or abs(virtual_joy_y) > 0.05:
            vjoy = f" vjoy=({virtual_joy_x:+.2f},{virtual_joy_y:+.2f})"
        expected = COLOR_TO_MOOD.get(color, "?")
        match = "OK" if expected == dominant else f"({expected})"
        print(f"  {dominant.upper():10s} | {color:8s} {match} water={wl} "
              f"yaw={yd:.0f}deg | brain={brain} {mode} {tb} "
              f"mus={music_volume:.2f} snd={sound_volume:.2f}{vjoy}")
    return 0.033

# ============================================================
# REGISTER
# ============================================================
if "_ballena" in bpy.app.driver_namespace:
    old = bpy.app.driver_namespace["_ballena"]
    if bpy.app.timers.is_registered(old):
        bpy.app.timers.unregister(old)
bpy.app.driver_namespace["_ballena"] = breathe
bpy.app.timers.register(breathe)
print()
print("BALLENA — 10 colors → 10 emotions → 10 sounds  [+ modo SOLO CARA: tecla c en grabar_ballena.py]")
print(f"  receptor_ballena.py version {VERSION}")
print(f"  Base music: {AMBIENT_LOOP}")
print(f"  Sound folder: {SOUNDS_DIR}")
print( "  Press N → Ballena tab. Music Volume slider sets base track level.")
print( "  Virtual joystick: V-Joy X (yaw) and V-Joy Y (pitch). Center button resets.")
print()
print(f"  UDP {UDP_PORT}")
print()

# ============================================================
# AUTO-RECARGA: si este archivo cambia en disco, se vuelve a ejecutar solo (no hace falta pegar nada en Blender)
# ============================================================
RUTA_RECEPTOR = os.path.join(YAKUMAMA, "receptor_ballena.py")
_ns = bpy.app.driver_namespace
if "_ballena_recarga" in _ns and bpy.app.timers.is_registered(_ns["_ballena_recarga"]):
    bpy.app.timers.unregister(_ns["_ballena_recarga"])
_mtime0 = os.path.getmtime(RUTA_RECEPTOR) if os.path.exists(RUTA_RECEPTOR) else 0
def _recargar():
    try:
        if os.path.getmtime(RUTA_RECEPTOR) > _mtime0:
            print("  receptor_ballena.py cambio: recargando...")
            exec(compile(open(RUTA_RECEPTOR).read(), RUTA_RECEPTOR, "exec"), {"__name__": "__main__"})
            return None   # el nuevo registra su propio vigilante
    except Exception as e:
        import traceback; print(f"  (recarga fallo: {e})"); traceback.print_exc()
    return 2.0
_ns["_ballena_recarga"] = _recargar
bpy.app.timers.register(_recargar, first_interval=2.0)
print("  Auto-recarga: cada 2 s mira si receptor_ballena.py cambio.")