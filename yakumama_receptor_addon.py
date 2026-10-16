bl_info = {"name": "Yakumama receptor", "author": "Yakumama", "version": (1, 2), "blender": (4, 2, 0), "category": "Animation",
           "description": "Carga receptor_ballena.py (panel Ballena, UDP 9998) cada vez que se abre whale.blend"}
import bpy, os, sys
def _ruta():
    """receptor_ballena.py: donde diga YAKUMAMA_DIR, o ~/Desktop/Yakumama, o una carpeta Yakumama al lado de la de whale.blend"""
    c = [os.environ.get("YAKUMAMA_DIR", ""), os.path.expanduser("~/Desktop/Yakumama")]
    try:
        if bpy.data.filepath: c.append(os.path.join(os.path.dirname(os.path.dirname(bpy.data.filepath)), "Yakumama"))
    except AttributeError: pass   # al registrar el add-on bpy.data todavia esta restringido
    return next((os.path.join(d, "receptor_ballena.py") for d in c if d and os.path.exists(os.path.join(d, "receptor_ballena.py"))), os.path.expanduser("~/Desktop/Yakumama/receptor_ballena.py"))
RUTA = _ruta()
_estado = {"cargado_para": None}
def _cargar(*_):
    try:
        if "side_fine.R" not in bpy.data.objects: return False
        global RUTA; RUTA = _ruta()
        if not os.path.exists(RUTA): print("Yakumama: no existe", RUTA, file=sys.stderr); return False
        if _estado["cargado_para"] == bpy.data.filepath and "_ballena" in bpy.app.driver_namespace: return True
        exec(compile(open(RUTA).read(), RUTA, "exec"), {"__name__": "__main__", "__file__": RUTA, "YAKUMAMA_DIR": os.path.dirname(RUTA)})
        _estado["cargado_para"] = bpy.data.filepath; print("Yakumama: receptor cargado desde", RUTA, file=sys.stderr); return True
    except Exception as e:
        import traceback; print("Yakumama: receptor fallo:", e, file=sys.stderr); traceback.print_exc(); return False
def _on_load(*_):
    _estado["cargado_para"] = None; _cargar()
def _vigilar():
    _cargar(); return 2.0   # cada 2 s: si se abre la ballena (o se recarga el archivo), carga el receptor
def register():
    print("Yakumama: addon registrado", file=sys.stderr)
    if _on_load not in bpy.app.handlers.load_post: bpy.app.handlers.load_post.append(_on_load)
    if not bpy.app.timers.is_registered(_vigilar): bpy.app.timers.register(_vigilar, first_interval=1.0, persistent=True)
def unregister():
    if _on_load in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(_on_load)
    if bpy.app.timers.is_registered(_vigilar): bpy.app.timers.unregister(_vigilar)
