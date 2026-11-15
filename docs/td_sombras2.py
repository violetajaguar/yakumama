"""
td_sombras2.py - shadows, second attempt (23 Oct 2026): the sun and the salt bounce become DISTANT lights (TD shadow-maps cone and
distant lights, not point lights; a distant light keeps the Look At direction Dan's script sets, so her lighting direction is the
same), shadow casters set by pattern and read back as .val, soft shadows on. SOMBRAS = 0 puts the lights back to point, no shadows.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_sombras2.py').read())
"""
import time
SOMBRAS = 1
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_sombras2', time.strftime('%H:%M:%S'), 'on' if SOMBRAS else 'off')
for nm in ('light1', 'light2'):
    l = op('/project1/' + nm)
    if l is None: _log('  ', nm, 'MISSING'); continue
    lt = getattr(l.par, 'lighttype', None)
    if lt is not None:
        names = list(lt.menuNames); want = next((m for m in names if 'dist' in m.lower()), None) if SOMBRAS else next((m for m in names if 'point' in m.lower()), None)
        if want: lt.val = want
        _log('  %-7s light type %s (menu %s)' % (nm, lt.eval(), names))
    if hasattr(l.par, 'shadowtype'):
        names = list(l.par.shadowtype.menuNames); l.par.shadowtype = (next((m for m in names if 'soft' in m.lower()), names[-1]) if SOMBRAS else 'off')
    for k in ('shadowresolution1', 'shadowresolution2'):
        if hasattr(l.par, k): setattr(l.par, k, 2048)
    if hasattr(l.par, 'shadowcasters'):
        for pat in ('/project1/whale/*', 'whale/*', '/project1/whale'):
            try: l.par.shadowcasters.val = pat if SOMBRAS else ''; break
            except Exception as e: _log('   casters', pat, str(e)[:50])
        _log('  %-7s shadowtype %s casters .val=%r eval=%s res %s' % (nm, l.par.shadowtype.eval(), l.par.shadowcasters.val, l.par.shadowcasters.eval(), l.par.shadowresolution1.eval() if hasattr(l.par, 'shadowresolution1') else '?'))
    _log('  %-7s errors: %s' % (nm, l.errors() or 'none'))
_log('### td_sombras2 DONE: open her jaw in your mind and look inside; SOMBRAS = 0 to undo')
