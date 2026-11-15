"""
td_mar.py - THE SEA UNDER THE SALAR in the running TouchDesigner (26 Oct 2026, Violeta: "a sea as a setting so the salt can break
and the whale can go down into the sea when she is overwhelmed"; "can we test it on TD, to see how it will look"). Designed first
in mar.html (beside salar.html); this is its port. Dan's brain sends the world as before plus /ballena/env/mar, costra_h, rotura,
rotura_r, rotura_x, rotura_z (ballena_mundo.py, world `mar`). This patches the live project once:
  1. reloads salar_sky / salar_ground / salar_island / salar_mtn pixel shaders from td/shaders (salar_common.glsl now has the sea:
     under the salt the dome and every haze are water, the sky shows only through the hole; the ground draws the sea floor)
  2. appends the vec4 uniforms uMar, uRotura, uMarGeo to each of those GLSL MATs, bound to the brain's channels (0 without it)
  3. builds /project1/mar_fondo: the sea floor, a flat Grid SOP fondo_m metres UNDER the salt plane with td/shaders/mar_fondo.frag,
     rendered only when ballena/env/mar is 1 (and removes the 26 Oct mar_costra plane: the salt itself is the crust now,
     salar_ground.frag draws it from above with the break and from below as the ceiling)
Run it, then Cmd+S. To SEE the arc (27 Oct: "how it breaks and how she goes down and once in the experience") launch Dan's
renderer with  MUNDO=salar BALLENA_MAR=auto ./correr_td.sh : 20 s on the salt, the salt breaks under her over 20 s, she goes down
over 40 s with the camera, then she lives in the sea. MUNDO=mar starts in the sea. In the salar nothing changes. Logs to
/tmp/td_out.txt. Fish, coral and marine snow are still only in mar.html.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_mar.py').read())
"""
import os, time, traceback
LOG = '/tmp/td_out.txt'; TD = os.path.join(project.folder, 'td'); SH = os.path.join(TD, 'shaders'); OSCIN = '/project1/oscin1'; CAM = '/project1/cam1'
SALT_Y = -255.0; WORLD_SCALE = 100.0; GROUND_R_M = 480.0 * 6000 / 5200     # as setup_salar_ground.py: the salt plane, TD units per metre, the disc radius
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_mar', time.strftime('%H:%M:%S'))

def _shader_text(fn):
    out = []
    for ln in open(os.path.join(SH, fn), encoding='utf-8').read().split('\n'):
        if ln.strip().startswith('//#include'):
            inc = ln.strip().split()[1]; out.append(open(os.path.join(SH, inc), encoding='utf-8').read())
        else: out.append(ln)
    return '\n'.join(out)

def _ch(c, default='0.0'): return "(lambda c: c.eval() if c is not None else %s)(op('%s')['ballena/env/%s'])" % (default, OSCIN, c)
SEA = [('uMar',    (_ch('mar'), _ch('rotura'), _ch('rotura_r'), '0.0')),
       ('uRotura', (_ch('rotura_x'), _ch('rotura_z'), '0.0', '0.0')),
       ('uMarGeo', (str(SALT_Y), str(WORLD_SCALE), '%s - %s * %s' % (SALT_Y, WORLD_SCALE, _ch('fondo_m', '14.0')), '0.0'))]   # x = the salt plane, z = the sea floor

def _blocks(mat):
    """the real uniform block count (23 Oct: mat.par.vec read 0 and the first td_mundo run overwrote uSunDir/uCamPos)"""
    n = 0
    for f in (lambda: mat.seq.vec.numBlocks, lambda: len(mat.seq.vec)):
        try: n = int(f()); break
        except Exception: pass
    if n <= 0:
        for i in range(80):
            if getattr(mat.par, 'vec%dname' % i, None) is None: break
            n = i + 1
    return n

def _bind(mat, unis, label):
    n = _blocks(mat); have = {}
    for i in range(n):
        nm = getattr(mat.par, 'vec%dname' % i).eval()
        if nm: have[nm] = i
    if not have: raise RuntimeError('no uniforms found on ' + label + ': refusing to write into block 0')
    for uname, exprs in unis:
        if uname in have: vi = have[uname]
        else: vi = n; n += 1; mat.par.vec = n
        getattr(mat.par, 'vec%dname' % vi).val = uname
        for comp, ex in zip('xyzw', exprs):
            vp = getattr(mat.par, 'vec%dvalue%s' % (vi, comp)); vp.expr = ex; vp.mode = ParMode.EXPRESSION
        try: shown = ' '.join('%.2f' % getattr(mat.par, 'vec%dvalue%s' % (vi, comp)).eval() for comp in 'xyzw')
        except Exception: shown = '?'
        _log('     vec%-2d %-8s = %s' % (vi, uname, shown))
    _log('     errors:', mat.errors() or 'none')

# 1 + 2: the existing surfaces learn the sea
for mp, frag in (('/project1/salar_sky/salar_sky_mat', 'salar_sky.frag'), ('/project1/salar_ground/salar_ground_mat', 'salar_ground.frag'),
                 ('/project1/salar_island/salar_island_mat', 'salar_island.frag'), ('/project1/salar_mtn/salar_mtn_mat', 'salar_mtn.frag')):
    mat = op(mp)
    if mat is None: _log('  MISSING', mp); continue
    try:
        pd = mat.par.pdat.eval(); dat = mat.op(pd) if isinstance(pd, str) else pd
        if dat is None: dat = op(pd)
        dat.text = _shader_text(frag); _log('  %-45s shader reloaded from %s (%d chars)' % (mp, frag, len(dat.text)))
        _bind(mat, SEA, mp)
    except Exception: _log(traceback.format_exc())

# 3: the sea floor (and the 26 Oct crust plane goes: the salt itself is the crust now)
try:
    root = op('/project1'); fbx = op('/project1/whale')
    old = root.op('mar_costra')
    if old is not None: old.destroy(); _log('  removed /project1/mar_costra (the salt plane is the crust now)')
    g = root.op('mar_fondo')
    if g is None:
        g = root.create(geometryCOMP, 'mar_fondo'); g.nodeX, g.nodeY = (fbx.nodeX if fbx else 0), (fbx.nodeY - 330 if fbx else 0); _log('  created', g.path)
    g.par.tx, g.par.tz = 0.0, 0.0
    g.par.ty.expr = '%s - %s * %s' % (SALT_Y, WORLD_SCALE, _ch('fondo_m', '14.0')); g.par.ty.mode = ParMode.EXPRESSION
    grid = g.op('grid1') or g.create(gridSOP, 'grid1')
    side = 2.0 * GROUND_R_M * WORLD_SCALE
    for nm, val in (('orient', 'zx'), ('sizex', side), ('sizey', side), ('rows', 24), ('cols', 24)):   # 27 Oct: subdivided (a straight edge crossed the hole on the 2 x 2 grid)
        p_ = getattr(grid.par, nm, None)
        if p_ is None: _log('     grid1 has no', nm, '- pars:', sorted({q.name for q in grid.pars('*')})[:30]); continue
        try: setattr(grid.par, nm, val)
        except Exception as e: _log('     grid1.%s = %s failed: %s' % (nm, val, str(e)[:60]))
    grid.cook(force=True)
    try:
        pts = grid.points; _log('     grid1: %d points, |x| max %.0f  y %.0f..%.0f  |z| max %.0f' % (len(pts), max(abs(q.x) for q in pts), min(q.y for q in pts), max(q.y for q in pts), max(abs(q.z) for q in pts)))
    except Exception as e: _log('     grid1 points:', str(e)[:60])
    gout = g.op('out1') or g.create(outSOP, 'out1'); gout.inputConnectors[0].connect(grid)
    for c in g.children:
        if c.family == 'SOP': c.render = (c is gout)      # exactly one SOP renders (the z-fight of 2026-08-19)
    def _dat(name, fn):
        d = g.op(name) or g.create(textDAT, name); d.text = _shader_text(fn); return d
    vdat, fdat = _dat('vert', 'mar_fondo.vert'), _dat('frag', 'mar_fondo.frag')
    mat = g.op('mar_fondo_mat') or g.create(glslMAT, 'mar_fondo_mat')
    mat.par.vdat = vdat.name; mat.par.pdat = fdat.name; g.par.material = mat.path
    try: mat.par.cullface = 'off'
    except Exception: pass
    P = lambda c: "op('%s')['ballena/env/%s']" % (OSCIN, c)
    WANT = [('uSunDir', (P('sky_x'), P('sky_y'), P('sky_z'), '0.0')),
            ('uCamPos', tuple("op('%s').worldTransform.decompose()[2][%d]" % (CAM, i) for i in range(3)) + ('0.0',)),
            ('uTime',   ('absTime.seconds', '0.0', '0.0', '0.0')), ('uExpo', (P('expo'), '0.0', '0.0', '0.0')),
            ('uScale',  (str(WORLD_SCALE), '0.0', '0.0', '0.0')), ('uRain', (P('rain'), '0.0', '0.0', '0.0')),
            ('uFog',    (_ch('fog_mult', '1.2'), '0.0', '0.0', '0.0'))] + \
           [('uPal' + k.capitalize(), (P('pal_%s_r' % k), P('pal_%s_g' % k), P('pal_%s_b' % k), '0.0')) for k in ('zen', 'mid', 'hor', 'amb', 'sun')] + \
           [('uGrade',  (P('grade_sat'), P('grade_expo'), '1.0', '0.0'))] + SEA + \
           [('uFondoA', (_ch('fondo_a_r'), _ch('fondo_a_g'), _ch('fondo_a_b'), _ch('mar'))), ('uFondoB', (_ch('fondo_b_r'), _ch('fondo_b_g'), _ch('fondo_b_b'), '0.0')),
            ('uFondoC', (_ch('fondo_c_r'), _ch('fondo_c_g'), _ch('fondo_c_b'), '0.0'))]     # uGrade.z = 1: the frame is tonemapped once (setup_tonemap.py)
    mat.par.vec = len(WANT)
    for vi, (uname, exprs) in enumerate(WANT):
        getattr(mat.par, 'vec%dname' % vi).val = uname
        for comp, ex in zip('xyzw', exprs):
            vp = getattr(mat.par, 'vec%dvalue%s' % (vi, comp)); vp.expr = ex; vp.mode = ParMode.EXPRESSION
    _log('  %-45s %d uniforms bound; errors: %s' % (mat.path, len(WANT), mat.errors() or 'none'))
    g.par.render.expr = "(lambda c: int(c.eval() > 0.5) if c is not None else 0)(op('%s')['ballena/env/mar'])" % OSCIN; g.par.render.mode = ParMode.EXPRESSION
    _log('  mar_fondo: at y = %.0f (%.0f m under the salt), %.0f m across, renders only in the sea (now %s)' % (g.par.ty.eval(), (SALT_Y - g.par.ty.eval()) / WORLD_SCALE, side / WORLD_SCALE, g.par.render.eval()))
except Exception: _log(traceback.format_exc())
try:
    c = op(OSCIN)['ballena/env/mar']; _log('  the brain says mar =', c.eval() if c is not None else '(no channel: relaunch with MUNDO=mar ./correr_td.sh)')
except Exception as e: _log('  mar:', str(e)[:60])
_log('### td_mar DONE -> Cmd+S.  The arc:  MUNDO=salar BALLENA_MAR=auto ./correr_td.sh   (the sea from the start: MUNDO=mar)')
