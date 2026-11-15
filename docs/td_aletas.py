"""
td_aletas.py - why are the fins not flapping? (23 Oct 2026). Run in TouchDesigner's textport:

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_aletas.py').read())

For the six fin bones and the jaw: what the OSC In CHOP receives, what the Rename CHOP exports, what the bone's Rotate parameters
hold and in which mode; then the same again two seconds later (TD's run with a delay) to see what moves. Writes /tmp/td_out.txt.
"""
import os, time
LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
def muestra(etiqueta):
    o = op('/project1/oscin1'); r = op('/project1/rename1'); w = op('/project1/whale')
    _log('###', etiqueta, time.strftime('%H:%M:%S'), '| oscin chans', o.numChans, '| rename chans', r.numChans)
    bones = [c for c in w.children if hasattr(c.par, 'rx')]
    modos = {}
    for b in bones:
        m = b.par.rx.mode.name; modos[m] = modos.get(m, 0) + 1
    _log('  bone COMPs with rx:', len(bones), '| rx modes:', modos)
    for nm in ('side_fine_L', 'side_fine_L_001', 'side_fine_L_002', 'side_fine_R1', 'side_fine_R_001', 'side_fine_R_002', 'mouth_inf_001', 'spine_002'):
        b = op('/project1/whale/' + nm)
        if b is None: _log('  ', nm, 'MISSING'); continue
        osc = [round(o[ch].eval(), 2) if ch in [c.name for c in o.chans()] else None for ch in ('ballena/b/%s/rx' % nm, 'ballena/b/%s/ry' % nm, 'ballena/b/%s/rz' % nm)]
        ren = [round(c.eval(), 2) for c in r.chans('%s:r*' % nm)]
        par = [round(getattr(b.par, k).eval(), 2) for k in ('rx', 'ry', 'rz')]; mode = [getattr(b.par, k).mode.name[:3] for k in ('rx', 'ry', 'rz')]
        _log(f'  {nm:16s} osc {osc} rename {ren} par {par} mode {mode}')
open(LOG, 'w').close()
muestra('now')
run("exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_aletas.py').read().replace(\"open(LOG, 'w').close()\\nmuestra('now')\\nrun(\", \"muestra('2 s later')\\n_x=(\"))", delayFrames=120)
