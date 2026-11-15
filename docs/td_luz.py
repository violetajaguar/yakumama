"""
td_luz.py - REPORT ONLY (23 Oct 2026): how she is lit versus how the world is drawn. Run in the textport:

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_luz.py').read())

Prints: the render chain the projector shows (window1 -> ... -> render1), whether the shared tonemap exists, the lights and their
colours as evaluated, the environment map (size, live or black), the camera's fog settings, and the palette channels the brain sends.
"""
import time
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_luz', time.strftime('%H:%M:%S'))
R = op('/project1/render1'); O = op('/project1/oscin1'); W1 = op('/project1/window1')
_log('window1 shows:', W1.par.winop.eval() if W1 and hasattr(W1.par, 'winop') else '?')
for nm in ('tonemap', 'alma_over', 'render1', 'render_refl', 'env_sky', 'env_light', 'whale_normal', 'whale_pbr_body', 'cam1', 'cam_refl', 'salar_ground', 'salar_sky'):
    o = op('/project1/' + nm); _log('  %-14s %s' % (nm, (o.type + ' ' + ('%dx%d' % (o.width, o.height) if hasattr(o, 'width') else '') + (' inputs ' + str([i.path for i in o.inputs]) if hasattr(o, 'inputs') and o.inputs else '')) if o else 'MISSING'))
lv = R.par.lights.eval(); lights = (lv.split() if isinstance(lv, str) else [getattr(x, 'path', str(x)) for x in lv])
for lp in lights:
    l = op(lp)
    if l is None: continue
    col = [round(float(getattr(l.par, 'lightcolor' + c).eval()), 2) for c in 'rgb' if hasattr(l.par, 'lightcolor' + c)]
    pos = [round(float(getattr(l.par, k).eval()), 0) for k in ('tx', 'ty', 'tz') if hasattr(l.par, k)]
    dim = round(float(l.par.dimmer.eval()), 2) if hasattr(l.par, 'dimmer') else '-'
    _log('  light %-22s %-20s colour %s dimmer %s pos %s%s' % (l.name, l.type, col, dim, pos, ('  map ' + str(l.par.envlightmap.eval())) if hasattr(l.par, 'envlightmap') else ''))
cam = op('/project1/cam1')
if cam is not None:
    fog = {k: getattr(cam.par, k).eval() for k in ('fog', 'fogcolorr', 'fogcolorg', 'fogcolorb', 'fogdensity', 'fognear', 'fogfar') if hasattr(cam.par, k)}
    _log('  camera fog:', fog or 'no fog pars', '| fov', cam.par.fov.eval() if hasattr(cam.par, 'fov') else '?')
pal = {c.name.split('/')[-1]: round(c.eval(), 2) for c in O.chans('ballena/env/pal_*')} if O else {}
_log('  palette from the brain:', pal)
env = op('/project1/env_sky')
if env is not None:
    try: _log('  env_sky pixel (centre):', [round(v, 2) for v in env.sample(x=env.width // 2, y=env.height // 2)], 'top:', [round(v, 2) for v in env.sample(x=env.width // 2, y=env.height - 2)], 'bottom:', [round(v, 2) for v in env.sample(x=env.width // 2, y=1)])
    except Exception as e: _log('  env_sky sample:', str(e)[:60])
expo = [round(c.eval(), 2) for c in O.chans('ballena/env/expo')] if O else []
_log('  exposure channel:', expo, '| sky lock golden:', 'see ballena_td.py SKY_LOCK_GOLDEN')
_log('### td_luz DONE')
