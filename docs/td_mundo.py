"""
td_mundo.py - HER WORLDS in the running TouchDesigner (23 Oct 2026, Violeta: "another world like el Salar in Tiupampa por Vila Vila,
and Mars, red earth"). ballena_mundo.py (Dan's package) defines the worlds and Dan's brain sends them as /ballena/env/tierra_*,
isla_*, mtn_*, cactus, fog_mult. This patches the live project once so the world shows:
  1. reloads salar_ground / salar_island / salar_mtn pixel shaders from td/shaders (with the //#include expanded, as the setup scripts do)
  2. appends the new vec4 uniforms (uTierraA-D, uIslaA-C, uMtnA-B) to each GLSL MAT, bound to the brain's channels
  3. uFog.x follows the world's haze (ballena/env/fog_mult; falls back to 1.2 without the brain)
  4. the cacti's render flag follows ballena/env/cactus (off on Mars; on without the brain)
  5. re-runs td/setup_env.py so the env map that lights her takes the ground's colour
Run it in any world (in the salar nothing visible changes); then Cmd+S. To SEE another world relaunch Dan's brain with
MUNDO=marte ./correr_todo.sh (or MUNDO=tiupampa). Logs to /tmp/td_out.txt.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_mundo.py').read())
"""
import os, time, traceback
LOG = '/tmp/td_out.txt'; TD = os.path.join(project.folder, 'td'); SH = os.path.join(TD, 'shaders'); OSCIN = '/project1/oscin1'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_mundo', time.strftime('%H:%M:%S'))

def _shader_text(fn):
    out = []
    for ln in open(os.path.join(SH, fn), encoding='utf-8').read().split('\n'):
        if ln.strip().startswith('//#include'):
            inc = ln.strip().split()[1]; out.append(open(os.path.join(SH, inc), encoding='utf-8').read())
        else: out.append(ln)
    return '\n'.join(out)

def _ch(c): return "op('%s')['ballena/env/%s']" % (OSCIN, c)
WORLDS = {
    '/project1/salar_ground/salar_ground_mat': ('salar_ground.frag', [
        ('uTierraA', ('tierra_a_r', 'tierra_a_g', 'tierra_a_b', 'tierra_a_w')), ('uTierraB', ('tierra_b_r', 'tierra_b_g', 'tierra_b_b', 'tierra_b_w')),
        ('uTierraC', ('tierra_c_r', 'tierra_c_g', 'tierra_c_b')), ('uTierraD', ('tierra_d_x', 'tierra_d_y', 'tierra_d_z', 'tierra_d_w'))]),
    '/project1/salar_island/salar_island_mat': ('salar_island.frag', [
        ('uIslaA', ('isla_a_r', 'isla_a_g', 'isla_a_b', 'isla_a_w')), ('uIslaB', ('isla_b_r', 'isla_b_g', 'isla_b_b')), ('uIslaC', ('isla_c_r', 'isla_c_g', 'isla_c_b'))]),
    '/project1/salar_mtn/salar_mtn_mat': ('salar_mtn.frag', [
        ('uMtnA', ('mtn_a_r', 'mtn_a_g', 'mtn_a_b', 'mtn_a_w')), ('uMtnB', ('mtn_b_r', 'mtn_b_g', 'mtn_b_b'))]),
}
for mp, (frag, unis) in WORLDS.items():
    mat = op(mp)
    if mat is None: _log('  MISSING', mp); continue
    try:
        pd = mat.par.pdat.eval(); dat = mat.op(pd) if isinstance(pd, str) else pd
        if dat is None: dat = op(pd)
        dat.text = _shader_text(frag); _log('  %-45s shader reloaded from %s (%d chars)' % (mp, frag, len(dat.text)))
    except Exception as e: _log('  ', mp, 'shader reload failed:', str(e)[:100]); continue
    try:
        # the real block count (23 Oct 20:10: mat.par.vec read 0 and the first run overwrote uSunDir/uCamPos; td_mundo2.py repaired it)
        n = 0
        for f in (lambda: mat.seq.vec.numBlocks, lambda: len(mat.seq.vec)):
            try: n = int(f()); break
            except Exception: pass
        have = {}
        if n <= 0:
            for i in range(60):
                p_ = getattr(mat.par, 'vec%dname' % i, None)
                if p_ is None: break
                n = i + 1
        for i in range(n):
            nm = getattr(mat.par, 'vec%dname' % i).eval()
            if nm: have[nm] = i
        if not have: raise RuntimeError('no uniforms found on ' + mp + ': refusing to write into block 0')
        for uname, chans in unis:
            if uname in have: vi = have[uname]
            else: vi = n; n += 1; mat.par.vec = n
            getattr(mat.par, 'vec%dname' % vi).val = uname
            for comp, c in zip('xyzw', chans):
                vp = getattr(mat.par, 'vec%dvalue%s' % (vi, comp)); vp.expr = _ch(c); vp.mode = ParMode.EXPRESSION
            try: shown = ' '.join('%.3f' % getattr(mat.par, 'vec%dvalue%s' % (vi, comp)).eval() for comp in 'xyzw'[:len(chans)])
            except Exception: shown = '?'
            _log('     vec%-2d %-9s = %s' % (vi, uname, shown))
        if uname.startswith('uTierra') or uname.startswith('uIsla'):
            fi = have.get('uFog')
            if fi is not None:
                vp = getattr(mat.par, 'vec%dvaluex' % fi); vp.expr = "(lambda c: c.eval() if c is not None else 1.2)(%s)" % _ch('fog_mult'); vp.mode = ParMode.EXPRESSION
                _log('     uFog.x -> fog_mult (now %.2f)' % vp.eval())
        _log('     errors:', mat.errors() or 'none')
    except Exception: _log(traceback.format_exc())

# the cacti follow the world (none on Mars)
cac = op('/project1/salar_cacti_models')
if cac is not None:
    try:
        cac.par.render.expr = "(lambda c: int(c.eval() > 0.5) if c is not None else 1)(%s)" % _ch('cactus'); cac.par.render.mode = ParMode.EXPRESSION
        _log('  cacti render flag follows ballena/env/cactus (now %s)' % cac.par.render.eval())
    except Exception as e: _log('  cacti flag:', str(e)[:80])
else: _log('  salar_cacti_models MISSING')

# the env map that lights her
try:
    exec(compile(open(os.path.join(TD, 'setup_env.py')).read(), 'setup_env.py', 'exec'), {}); _log('  setup_env.py re-run (uTierraA bound)')
except Exception: _log(traceback.format_exc())
try:
    c = op(OSCIN)['ballena/env/mundo_i']; _log('  the brain says world index', c.eval() if c is not None else '(no channel: Dan\'s brain not restarted yet)')
except Exception as e: _log('  mundo_i:', str(e)[:60])
_log('### td_mundo DONE -> Cmd+S. Another world: MUNDO=marte ./correr_todo.sh  (or tiupampa)')
