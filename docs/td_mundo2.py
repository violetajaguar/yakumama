"""
td_mundo2.py - REPAIR after td_mundo.py (23 Oct 2026, 20:10). td_mundo.py read the GLSL MATs' uniform count as 0 and wrote the world
uniforms into blocks 0-3, over uSunDir / uCamPos / uIsland / uWind (ground), uSunDir / uCamPos / uTime (island), uSunDir / uCamPos (mtn).
This re-runs Dan's own setup scripts, which rebind EVERY uniform from scratch (their lists now include the world uniforms), then binds the
cacti flag and uFog again. Dan's brain must be running.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_mundo2.py').read())
"""
import os, time, traceback
LOG = '/tmp/td_out.txt'; TD = os.path.join(project.folder, 'td'); OSCIN = '/project1/oscin1'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_mundo2 (repair)', time.strftime('%H:%M:%S'))
def _run(path):
    _log('--- running', os.path.basename(path))
    try: exec(compile(open(path).read(), path, 'exec'), {}); _log('### ok', os.path.basename(path))
    except Exception: _log(traceback.format_exc()); _log('### FAILED', os.path.basename(path))
for s in ('setup_dibujo.py', 'setup_salar_island.py', 'setup_salar_mtn.py', 'setup_env.py'):   # setup_dibujo re-runs setup_salar_ground itself
    _run(os.path.join(TD, s))
def _blocks(mat):
    for f in (lambda: mat.seq.vec.numBlocks, lambda: len(mat.seq.vec), lambda: int(mat.par.vec.eval())):
        try:
            n = int(f())
            if n > 0: return n
        except Exception: pass
    return 40
_ch = lambda c: "op('%s')['ballena/env/%s']" % (OSCIN, c)
for mp in ('/project1/salar_ground/salar_ground_mat', '/project1/salar_island/salar_island_mat', '/project1/salar_mtn/salar_mtn_mat'):
    mat = op(mp)
    if mat is None: _log('  MISSING', mp); continue
    names = {}
    for i in range(_blocks(mat)):
        p = getattr(mat.par, 'vec%dname' % i, None)
        if p is None: break
        if p.eval(): names[p.eval()] = i
    _log('  %-45s %d uniforms: %s' % (mp, len(names), ' '.join(sorted(names, key=names.get))))
    for must in ('uSunDir', 'uCamPos'):
        if must not in names: _log('     !! %s is NOT bound' % must)
    if 'uFog' in names:
        vp = getattr(mat.par, 'vec%dvaluex' % names['uFog']); vp.expr = "(lambda c: c.eval() if c is not None else 1.2)(%s)" % _ch('fog_mult'); vp.mode = ParMode.EXPRESSION
        _log('     uFog.x -> fog_mult (now %.2f)' % vp.eval())
    _log('     errors:', mat.errors() or 'none')
cac = op('/project1/salar_cacti_models')
if cac is not None:
    try:
        cac.par.render.expr = "(lambda c: int(c.eval() > 0.5) if c is not None else 1)(%s)" % _ch('cactus'); cac.par.render.mode = ParMode.EXPRESSION
        _log('  cacti render flag follows ballena/env/cactus (now %s)' % cac.par.render.eval())
    except Exception as e: _log('  cacti flag:', str(e)[:80])
try:
    c = op(OSCIN)['ballena/env/mundo_i']; _log('  the brain says world index', c.eval() if c is not None else '(no channel)')
except Exception as e: _log('  mundo_i:', str(e)[:60])
# the setup scripts reset uGrade.z / uExpoT.y to 0 (the shaders tonemap themselves); since 23 Oct the frame is tonemapped ONCE
# (td/setup_tonemap.py), so without this the world is tonemapped twice and comes out washed white (seen 20:30, Violeta: "the salar is white")
_run('/Users/jaguar/Desktop/Yakumama/docs/td_interruptores.py')
_log('### td_mundo2 DONE -> Cmd+S')
