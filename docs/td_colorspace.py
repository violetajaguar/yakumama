"""
td_colorspace.py - the double gamma (23 Oct 2026). /tmp/tm.png measured mean 231 where the tonemap's maths give 205: TD encodes
the tonemap's output once more on display, because it is tagged linear. This lists every colour-space parameter on the tonemap
TOP, render1 and window1 with its menu, and sets the tonemap's output space to the sRGB / "already encoded" option if one exists.
Then it saves /tmp/tm2.png for a second measurement. Run in the textport:

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_colorspace.py').read())
"""
import time
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_colorspace', time.strftime('%H:%M:%S'))
tm = op('/project1/tonemap'); r1 = op('/project1/render1'); w1 = op('/project1/window1')
for o in (tm, r1, w1):
    if o is None: continue
    for p in o.pars('*'):
        n = p.name.lower()
        if any(k in n for k in ('color', 'space', 'srgb', 'gamma', 'linear', 'transfer')):
            try: _log('  %-10s %-24s = %-16s menu %s' % (o.name, p.name, p.eval(), list(p.menuNames) if p.isMenu else '-'))
            except Exception as e: _log('  ', o.name, p.name, str(e)[:50])
try:
    _log('  project colour management:', {k: getattr(project, k) for k in dir(project) if 'color' in k.lower() or 'space' in k.lower()})
except Exception as e: _log('  project:', str(e)[:60])
cambiado = None
for p in tm.pars('*'):
    n = p.name.lower()
    if p.isMenu and any(k in n for k in ('colorspace', 'outputcolor', 'colourspace')):
        names = list(p.menuNames); pick = next((m for m in names if 'srgb' in m.lower()), None)
        if pick: p.val = pick; cambiado = (p.name, pick)
_log('  set on tonemap:', cambiado or 'no colour-space menu found on the tonemap TOP')
tm.save('/tmp/tm2.png'); _log('### saved /tmp/tm2.png')
