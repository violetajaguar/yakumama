"""
td_sombras.py - her own shadows (23 Oct 2026, Violeta: "shadows inside her mouth"). Turns on shadow maps on the sun (light1)
and the salt bounce (light2): her jaws then occlude the light, so the inside of the mouth, the underside of the fins and the
tail's fold go dark; her PBR skin receives them, the salar shaders light themselves and are not affected. The sky fill (light3),
the ambient and the environment light keep filling softly, so the mouth is dark, not black. SOMBRAS = 0 switches them off.
Logs to /tmp/td_out.txt.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_sombras.py').read())
"""
import time
SOMBRAS = 1
RES = 2048          # shadow map size; 4096 is sharper, costs more
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_sombras', time.strftime('%H:%M:%S'), 'on' if SOMBRAS else 'off')
for nm, want in (('light1', True), ('light2', True), ('light3', False)):
    l = op('/project1/' + nm)
    if l is None: _log('  ', nm, 'MISSING'); continue
    pars = {p.name: p for p in l.pars('*') if 'shadow' in p.name.lower()}
    if not pars: _log('  ', nm, 'has no shadow parameters:', sorted(p.name for p in l.pars('*'))[:30]); continue
    st = pars.get('shadowtype')
    if st is not None:
        names = list(st.menuNames); pick = 'off' if not (SOMBRAS and want) else next((m for m in names if 'soft' in m.lower()), next((m for m in names if 'hard' in m.lower()), names[-1]))
        st.val = pick if pick in names else names[0]
    for k in ('shadowresolution1', 'shadowresolution2', 'shadowres', 'shadowmapres'):
        if k in pars: pars[k].val = RES
    if 'shadowcasters' in pars: pars['shadowcasters'].val = '/project1/whale/*' if (SOMBRAS and want) else ''   # what occludes: her, all her pieces
    if 'maxshadowsoftness' in pars: pars['maxshadowsoftness'].val = 0.25
    _log('  %-7s %s' % (nm, {k: (p.eval() if not p.isMenu else p.eval()) for k, p in sorted(pars.items())}))
r = op('/project1/render1')
if r is not None:
    sp = {p.name: p.eval() for p in r.pars('*') if 'shadow' in p.name.lower()}
    _log('  render1 shadow pars:', sp or 'none (shadows are on the lights)')
_log('### td_sombras DONE: look inside her mouth and under the fins; SOMBRAS = 0 to undo')
