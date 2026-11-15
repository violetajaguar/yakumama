"""
td_peces.py - THE FISH in the running TouchDesigner (27 Oct 2026, Violeta: "needs to have coral fishes"; "why the fish aren't in the
file?"). Four schools, as in mar.html: clownfish and yellow around the light under the hole, blue chromis over the reef, slow
angelfish between, and a second school passing far. Each school is ONE instanced Geometry COMP (/project1/mar_peces_0..3): a unit
sphere, N instances placed by a table (a point in a unit ball per fish), and td/shaders/mar_peces.vert swims the whole school on
the GPU (td/shaders/mar_peces.frag lights them like the sea floor). They render only in the sea (ballena/env/mar) and live under
the salt plane, so from the air they show only through the hole. Needs td_mar.py run first (the sea uniforms exist in the brain).
Run it once, then Cmd+S. Logs to /tmp/td_out.txt.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_peces.py').read())
"""
import os, time, traceback, random
LOG = '/tmp/td_out.txt'; TD = os.path.join(project.folder, 'td'); SH = os.path.join(TD, 'shaders'); OSCIN = '/project1/oscin1'; CAM = '/project1/cam1'
SALT_Y = -255.0; WORLD_SCALE = 100.0
# the schools: n fish, centre (x, z m in the salar's frame; y m from the salt plane, negative = below), orbit radius m, spread m, speed, size m, palette
SCHOOLS = [dict(n=240, c=(0.0, -6.0, 0.0),    r=15.0, s=(12.0, 3.0, 12.0), v=0.11, sz=0.30, pal=0),   # around the light under the hole
           dict(n=200, c=(42.0, -9.0, -28.0), r=11.0, s=(8.0, 2.5, 8.0),   v=0.17, sz=0.17, pal=1),   # blue chromis, over the reef side
           dict(n=70,  c=(-38.0, -5.0, 34.0), r=16.0, s=(10.0, 3.0, 10.0), v=0.07, sz=0.48, pal=2),   # angelfish, slow
           dict(n=120, c=(10.0, -4.0, 60.0),  r=22.0, s=(14.0, 3.5, 14.0), v=0.09, sz=0.26, pal=0)]   # a second school passing far
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
open(LOG, 'w').close(); _log('### td_peces', time.strftime('%H:%M:%S'))

def _shader_text(fn):
    out = []
    for ln in open(os.path.join(SH, fn), encoding='utf-8').read().split('\n'):
        if ln.strip().startswith('//#include'):
            inc = ln.strip().split()[1]; out.append(open(os.path.join(SH, inc), encoding='utf-8').read())
        else: out.append(ln)
    return '\n'.join(out)
def _ch(c, default='0.0'): return "(lambda c: c.eval() if c is not None else %s)(op('%s')['ballena/env/%s'])" % (default, OSCIN, c)
def _setpar(o_, names, value, label):
    for nm in names:
        p_ = getattr(o_.par, nm, None)
        if p_ is not None:
            try: setattr(o_.par, nm, value); return nm
            except Exception: continue
    _log('     %s: none of %s on %s; pars: %s' % (label, names, o_.path, sorted({q.name for q in o_.pars('*')})[:40])); return None

P = lambda c: "op('%s')['ballena/env/%s']" % (OSCIN, c)
SEA = [('uMar',    (_ch('mar'), _ch('rotura'), _ch('rotura_r'), '0.0')),
       ('uRotura', (_ch('rotura_x'), _ch('rotura_z'), '0.0', '0.0')),
       ('uMarGeo', (str(SALT_Y), str(WORLD_SCALE), '%s - %s * %s' % (SALT_Y, WORLD_SCALE, _ch('fondo_m', '14.0')), '0.0'))]
BASE = [('uSunDir', (P('sky_x'), P('sky_y'), P('sky_z'), '0.0')),
        ('uCamPos', tuple("op('%s').worldTransform.decompose()[2][%d]" % (CAM, i) for i in range(3)) + ('0.0',)),
        ('uTime',   ('absTime.seconds', '0.0', '0.0', '0.0')), ('uExpo', (P('expo'), '0.0', '0.0', '0.0')),
        ('uScale',  (str(WORLD_SCALE), '0.0', '0.0', '0.0')), ('uRain', (P('rain'), '0.0', '0.0', '0.0')),
        ('uFog',    (_ch('fog_mult', '1.2'), '0.0', '0.0', '0.0'))] + \
       [('uPal' + k.capitalize(), (P('pal_%s_r' % k), P('pal_%s_g' % k), P('pal_%s_b' % k), '0.0')) for k in ('zen', 'mid', 'hor', 'amb', 'sun')] + \
       [('uGrade',  (P('grade_sat'), P('grade_expo'), '1.0', '0.0'))] + SEA

root = op('/project1'); fbx = op('/project1/whale'); random.seed(7)
for i, S in enumerate(SCHOOLS):
    try:
        name = 'mar_peces_%d' % i
        g = root.op(name)
        if g is None:
            g = root.create(geometryCOMP, name); g.nodeX, g.nodeY = (fbx.nodeX + 180 * (i + 1) if fbx else 200 * i), (fbx.nodeY - 330 if fbx else 0); _log('  created', g.path)
        g.par.tx, g.par.ty, g.par.tz = 0.0, 0.0, 0.0        # the shader builds world positions itself
        sph = g.op('sphere1') or g.create(sphereSOP, 'sphere1')
        for nm, val in (('rows', 8), ('cols', 6), ('radx', 1.0), ('rady', 1.0), ('radz', 1.0)):
            p_ = getattr(sph.par, nm, None)
            if p_ is not None: setattr(sph.par, nm, val)
        gout = g.op('out1') or g.create(outSOP, 'out1'); gout.inputConnectors[0].connect(sph)
        for c in g.children:
            if c.family == 'SOP': c.render = (c is gout)
        # the school: one row per fish, a point in a unit ball (denser in the middle)
        tab = g.op('escuela') or g.create(tableDAT, 'escuela'); tab.clear(); tab.appendRow(['tx', 'ty', 'tz'])
        for k in range(S['n']):
            u = random.random(); a = random.random() * 6.283; b = (2 * random.random() - 1); r = u ** (1.0 / 3.0); sb = (1 - b * b) ** 0.5
            tab.appendRow(['%.4f' % (r * sb * __import__('math').cos(a)), '%.4f' % (r * b), '%.4f' % (r * sb * __import__('math').sin(a))])
        _setpar(g, ['instancing'], True, 'instancing')
        _setpar(g, ['instanceop'], tab.path, 'instance table')
        for ax in 'xyz': _setpar(g, ['instancet' + ax], 't' + ax, 'instance t' + ax)
        def _dat(nm, fn):
            d = g.op(nm) or g.create(textDAT, nm); d.text = _shader_text(fn); return d
        vdat, fdat = _dat('vert', 'mar_peces.vert'), _dat('frag', 'mar_peces.frag')
        mat = g.op('mar_peces_mat') or g.create(glslMAT, 'mar_peces_mat')
        mat.par.vdat = vdat.name; mat.par.pdat = fdat.name; g.par.material = mat.path
        try: mat.par.cullface = 'off'
        except Exception: pass
        cx, cy, cz = S['c']; sx, sy, sz_ = S['s']
        WANT = BASE + [('uSchool', (str(cx), str(cy), str(cz), str(S['r']))), ('uSpread', (str(sx), str(sy), str(sz_), '0.0')),
                       ('uFish', (str(S['v']), str(S['sz']), str(S['pal']), '0.0'))]
        mat.par.vec = len(WANT)
        for vi, (uname, exprs) in enumerate(WANT):
            getattr(mat.par, 'vec%dname' % vi).val = uname
            for comp, ex in zip('xyzw', exprs):
                vp = getattr(mat.par, 'vec%dvalue%s' % (vi, comp)); vp.expr = ex; vp.mode = ParMode.EXPRESSION
        g.par.render.expr = "(lambda c: int(c.eval() > 0.5) if c is not None else 0)(op('%s')['ballena/env/mar'])" % OSCIN; g.par.render.mode = ParMode.EXPRESSION
        _log('  %-24s %d fish, palette %d, centre (%.0f, %.0f, %.0f) m, instancing %s; mat errors: %s' % (g.path, S['n'], S['pal'], cx, cy, cz, g.par.instancing.eval() if hasattr(g.par, 'instancing') else '?', mat.errors() or 'none'))
    except Exception: _log(traceback.format_exc())
try:
    c = op(OSCIN)['ballena/env/mar']; _log('  the brain says mar =', c.eval() if c is not None else '(no channel)')
except Exception as e: _log('  mar:', str(e)[:60])
_log('### td_peces DONE -> Cmd+S. The fish show under the salt (MUNDO=mar, or after the break in BALLENA_MAR=auto)')
