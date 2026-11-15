"""
td_niebla.py - the world's haze on her too (23 Oct 2026, Violeta: "she looks green-screened into the world").
The salar shaders fog every surface toward the horizon colour with  1 - exp(-dist_m * 0.0011 * FOG),  FOG = 1.2
(td/shaders/salar_island.frag, setup_salar_ground.py). She had no fog at all. This turns on the camera's exponential fog
with the same density (TD units: 100 per metre) and the palette's horizon colour, live from the brain, so she fades into the
distance exactly as the salt does. Run AFTER the tonemap (so her fog colour and the world share one colour space):

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_niebla.py').read())

NIEBLA = 0 turns it off again. GANANCIA scales the density by eye (1.0 = the world's).
"""
import time
NIEBLA = 1; GANANCIA = 0.4   # 23 Oct evening: at the world's full density she vanished from the aerial shots; less haze on her than on the salt
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_niebla', time.strftime('%H:%M:%S'))
for cp in ('/project1/cam1', '/project1/cam_refl'):
    cam = op(cp)
    if cam is None: _log('  ', cp, 'MISSING'); continue
    try:
        if not NIEBLA: cam.par.fog = 'off'; _log('  ', cp, 'fog off'); continue
        menu = list(cam.par.fog.menuNames); modo = 'exp' if 'exp' in menu else menu[-1]
        cam.par.fog = modo
        dens = 0.0011 * 1.2 * GANANCIA / 100.0          # per TD unit, the world's law
        cam.par.fogdensity = dens
        for c in 'rgb':
            p = getattr(cam.par, 'fogcolor' + c); p.expr = "op('/project1/oscin1')['ballena/env/pal_hor_%s']" % c; p.mode = ParMode.EXPRESSION
        _log('  ', cp, 'fog', cam.par.fog.eval(), 'density', round(dens, 7), 'colour <- pal_hor (now', [round(float(getattr(cam.par, 'fogcolor' + c).eval()), 2) for c in 'rgb'], ')')
    except Exception as e: _log('  ', cp, 'fog error:', str(e)[:80])
_log('### td_niebla DONE')
