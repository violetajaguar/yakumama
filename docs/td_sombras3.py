"""
td_sombras3.py - shadows WITHOUT losing the glint (23 Oct 2026): the sun (light1) and the salt bounce (light2) become CONE lights,
which keep their position (so the sun's highlight sweeps across her back as she moves, as it did with the point lights) and can
cast shadow maps (point lights cannot). The cone is opened wide (120 deg) so it covers her from Dan's 4000-unit positions. Soft
shadows, 2048 maps, casters = her geometry. SOMBRAS = 0 -> point lights, no shadows (Dan's August rig).

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_sombras3.py').read())
"""
import time
SOMBRAS = 1
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_sombras3', time.strftime('%H:%M:%S'), 'cone + shadows' if SOMBRAS else 'point, no shadows')
for nm in ('light1', 'light2'):
    l = op('/project1/' + nm)
    if l is None: _log('  ', nm, 'MISSING'); continue
    l.par.lighttype = 'cone' if SOMBRAS else 'point'
    for k, v in (('coneangle', 120), ('conedelta', 30), ('conerolloff', 0.0)):
        if hasattr(l.par, k): setattr(l.par, k, v)
    if hasattr(l.par, 'shadowtype'):
        names = list(l.par.shadowtype.menuNames); l.par.shadowtype = (next((m for m in names if 'soft' in m.lower()), names[-1]) if SOMBRAS else 'off')
    for k in ('shadowresolution1', 'shadowresolution2'):
        if hasattr(l.par, k): setattr(l.par, k, 2048)
    if hasattr(l.par, 'shadowcasters'): l.par.shadowcasters.val = 'whale' if SOMBRAS else ''   # HER ONLY (relative to /project1): with '*' the salt plane shadowed her belly from the bounce light below and drew a line across her
    if hasattr(l.par, 'maxshadowsoftness'): l.par.maxshadowsoftness = 0.4   # the shadow's blur
    for k, v in (('near', 50.0), ('far', 30000.0)):          # the shadow map is a render FROM the light: Dan's lights sit ~4000 units from her, the default far clip is 1000
        if hasattr(l.par, k): setattr(l.par, k, v)
    try: _ops = [o.path for o in l.par.shadowcasters.evalOPs()]
    except Exception as e: _ops = 'evalOPs: ' + str(e)[:40]
    _log('  %-7s near/far %s/%s casters resolve to %s' % (nm, l.par.near.eval() if hasattr(l.par, 'near') else '-', l.par.far.eval() if hasattr(l.par, 'far') else '-', _ops if not isinstance(_ops, list) else (len(_ops), _ops[:4])))
    _log('  %-7s type %s cone %s/%s shadow %s casters %r -> %s errors: %s' % (nm, l.par.lighttype.eval(), l.par.coneangle.eval() if hasattr(l.par, 'coneangle') else '-', l.par.conedelta.eval() if hasattr(l.par, 'conedelta') else '-', l.par.shadowtype.eval(), l.par.shadowcasters.val, l.par.shadowcasters.eval(), l.errors() or 'none'))
_log('### td_sombras3 DONE: the glint should sweep again and the mouth shade')
