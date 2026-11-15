"""
td_interruptores.py - flip the world's tonemap switches by hand (23 Oct 2026). Dan's setup_tonemap.py looks for the uGrade /
uExpoT uniforms through the MAT's `vec` count and says "not bound" although the rebuilt materials carry them. This walks every
vecN slot (up to 48) on the five salar MATs and the env map, finds uGrade / uExpoT, sets uGrade.z = 1 and uExpoT.y = 1 as
CONSTANTS (so the shaders output linear and /project1/tonemap does the one display transform), and reads them back.
APAGAR = True sets them to 0 again (the world tonemaps itself inline, as before). Logs to /tmp/td_out.txt.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_interruptores.py').read())
"""
import time
APAGAR = False
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
def slot(o, uname):
    for i in range(48):
        p = getattr(o.par, 'vec%dname' % i, None)
        if p is not None and p.eval() == uname: return i
    return None
def flip(path, uname, comp, val):
    o = op(path)
    if o is None: _log('  %-46s MISSING' % path); return
    i = slot(o, uname)
    if i is None: _log('  %-46s %s not among vec0..47: %s' % (path, uname, [getattr(o.par, 'vec%dname' % k).eval() for k in range(12) if getattr(o.par, 'vec%dname' % k, None)])); return
    vp = getattr(o.par, 'vec%dvalue%s' % (i, comp)); vp.expr = ''; vp.mode = ParMode.CONSTANT; vp.val = val
    _log('  %-46s %s (vec%d).%s = %s   errors: %s' % (path, uname, i, comp, vp.eval(), o.errors() or 'none'))
open(LOG, 'w').close(); _log('### td_interruptores', time.strftime('%H:%M:%S'), 'off' if APAGAR else 'on')
v = 0.0 if APAGAR else 1.0
for nm in ('salar_sky/salar_sky_mat', 'salar_ground/salar_ground_mat', 'salar_mtn/salar_mtn_mat', 'salar_island/salar_island_mat', 'salar_cacti_models/salar_cacti_models_mat'):
    flip('/project1/' + nm, 'uGrade', 'z', v)
flip('/project1/env_sky', 'uExpoT', 'y', v)
_log('### DONE: the world outputs linear and the tonemap does the display transform once' if not APAGAR else '### DONE: switches off')
