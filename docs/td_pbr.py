"""
td_pbr.py - her satin skin and the copper jewels, as PBR, in small logged steps (23 Oct 2026). Dan's td/setup_pbr.py does the same
for the body but hangs TouchDesigner on this build inside its probes, so this one builds without probing and writes a line to
/tmp/td_out.txt before every step (if TD ever stalls, the log says where). Run in the textport, with Dan's brain RUNNING:

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_pbr.py').read())

What it builds (nothing imported is deleted; /project1/pbr_originals keeps every geometry's original material path):
  /project1/whale_normal         Movie File In TOP, whale2.fbm/ballena_normal.png
  /project1/whale_pbr_body       PBR MAT: base colour <- /ballena/env/skin_r|g|b (her mood colour), metallic 0, roughness 0.30, her normal map
  /project1/whale_pbr_eye        PBR MAT: the glb's 'ojo': base 0.105, metallic 0.80, roughness 0.14
  /project1/joya_pbr_joya        PBR MAT from the 'joya3 XL' maps (base colour, metallic, roughness, normal)
  /project1/joya_pbr_joya_flor   PBR MAT from the 'joya1' maps
  /project1/joya_pbr_joyas       PBR MAT from the 'base joyas1' maps (the flower base and the nose piece)
  /project1/env_light            Environment Light COMP on env_sky, added to render1's lights (copper needs something to reflect)
  every geometry under /project1/whale: body-material geos -> whale_pbr_body (tongue and teeth keep their painted Phong),
  eye geos -> eye, joya* geos -> their jewel MAT. The skin-deform parameters are copied from the imported MAT, as Dan does.
REVERT = True puts every geometry back on its imported material.
"""
import os, json, time, traceback
REVERT = False
LOG = '/tmp/td_out.txt'; ROOT = op('/project1'); W = op('/project1/whale'); O = op('/project1/oscin1'); R = op('/project1/render1')
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
def setp(o, names, v, expr=False):
    for n in names:
        p = getattr(o.par, n, None)
        if p is None: continue
        try:
            if expr: p.expr = v; p.mode = ParMode.EXPRESSION
            else: p.val = v
            return n
        except Exception as e: _log('   (', o.path, n, 'not set:', str(e)[:60], ')')
    return None
def mat_of(g):
    try: return g.par.material.eval()
    except Exception: return None
def copy_deform(src, dst):
    n = 0
    if src is None: return 0
    for q in src.pars('*'):
        nm = q.name.lower()
        if not any(k in nm for k in ('deform', 'skel', 'capt', 'bone')): continue
        d = getattr(dst.par, q.name, None)
        if d is None: continue
        try:
            if q.mode == ParMode.EXPRESSION: d.expr = q.expr; d.mode = ParMode.EXPRESSION
            else: d.val = q.val
            n += 1
        except Exception as e: _log('   deform', q.name, str(e)[:50])
    return n
open(LOG, 'w').close(); _log('### td_pbr', time.strftime('%H:%M:%S'), 'REVERT' if REVERT else 'build')
geos = [c for c in W.children if c.type == 'geo'] + [g for b in W.children for g in b.children if g.type == 'geo']   # the jewel pieces ride under the bone spine_001
orig = ROOT.op('pbr_originals')
if orig is None: orig = ROOT.create(textDAT, 'pbr_originals')
saved = json.loads(orig.text or '{}')
for g in geos:
    if g.path not in saved: saved[g.path] = (mat_of(g).path if mat_of(g) else '')
orig.text = json.dumps(saved, indent=1)
_log('geos', len(geos), '| originals kept for', len(saved))
if REVERT:
    for g in geos:
        p = saved.get(g.path, '')
        if p: g.par.material = p
    _log('### reverted'); raise SystemExit
try:
    # 1. her normal map
    _log('step 1: normal map TOP')
    nt = ROOT.op('whale_normal') or ROOT.create(moviefileinTOP, 'whale_normal')
    setp(nt, ['file'], os.path.join(project.folder, 'whale2.fbm', 'ballena_normal.png'))
    # 2. body and eye PBR, deform params from the imported MATs
    _log('step 2: body / eye PBR')
    body = ROOT.op('whale_pbr_body') or ROOT.create(pbrMAT, 'whale_pbr_body'); eye = ROOT.op('whale_pbr_eye') or ROOT.create(pbrMAT, 'whale_pbr_eye')
    for c, ch in zip('rgb', ('skin_r', 'skin_g', 'skin_b')): setp(body, ['basecolor' + c, 'diff' + c], "op('/project1/oscin1')['ballena/env/%s']" % ch, expr=True)
    setp(body, ['metallic'], 0.0); setp(body, ['roughness'], 0.30); setp(body, ['normalmap'], nt.path); setp(body, ['normalstrength', 'normalscale', 'bumpscale'], 1.0); setp(body, ['applypointcolor'], False); setp(body, ['specularlevel'], 0.5)
    for c, v in zip('rgb', (0.105, 0.105, 0.105)): setp(eye, ['basecolor' + c, 'diff' + c], v)
    setp(eye, ['metallic'], 0.80); setp(eye, ['roughness'], 0.14); setp(eye, ['applypointcolor'], False)
    src_body = mat_of(op('/project1/whale/ballena_low')); src_eye = next((m for m in op('/project1/whale/eye_L').findChildren(maxDepth=2) if m.family == 'MAT' and m.name.startswith('ojo')), None) if op('/project1/whale/eye_L') else None
    _log('   deform pars copied: body', copy_deform(src_body, body), 'eye', copy_deform(src_eye or src_body, eye))
    # 3. the jewels: one PBR per material family, from the maps TD extracted into whale2.fbm
    _log('step 3: jewel PBR')
    maps = {'joya': 'joya3 XL_Material_%s.png', 'joya_flor': 'joya1_Material.001_%s.png', 'joyas': 'base joyas1_joyas_%s.png'}
    jmats = {}
    for fam, pat in maps.items():
        m = ROOT.op('joya_pbr_' + fam) or ROOT.create(pbrMAT, 'joya_pbr_' + fam); jmats[fam] = m
        for kind, parnames in (('BaseColor', ['basecolormap', 'colormap']), ('Metallic', ['metallicmap']), ('Roughness', ['roughnessmap']), ('Normal', ['normalmap'])):
            t = ROOT.op('tex_%s_%s' % (fam, kind.lower())) or ROOT.create(moviefileinTOP, 'tex_%s_%s' % (fam, kind.lower()))
            setp(t, ['file'], os.path.join(project.folder, 'whale2.fbm', pat % kind)); setp(m, parnames, t.path)
        setp(m, ['metallic'], 1.0); setp(m, ['roughness'], 1.0); setp(m, ['applypointcolor'], False)
        for c in 'rgb': setp(m, ['basecolor' + c, 'diff' + c], 1.0)
        copy_deform(src_body, m)
    # 3b. tongue and teeth: PBR too, constant colours (23 Oct: on Phong a distant/cone sun gave a white specular at night)
    _log('step 3b: tongue / teeth PBR')
    lengua = ROOT.op('whale_pbr_lengua') or ROOT.create(pbrMAT, 'whale_pbr_lengua'); dientes = ROOT.op('whale_pbr_dientes') or ROOT.create(pbrMAT, 'whale_pbr_dientes')
    for c, v in zip('rgb', (0.10, 0.30, 0.95)): setp(lengua, ['basecolor' + c, 'diff' + c], v)
    setp(lengua, ['metallic'], 0.0); setp(lengua, ['roughness'], 0.55); setp(lengua, ['applypointcolor'], False)
    for c, v in zip('rgb', (1.00, 0.78, 0.20)): setp(dientes, ['basecolor' + c, 'diff' + c], v)
    setp(dientes, ['metallic'], 0.85); setp(dientes, ['roughness'], 0.35); setp(dientes, ['applypointcolor'], False)
    copy_deform(src_body, lengua); copy_deform(src_body, dientes)
    # 4. assign
    _log('step 4: assign')
    n = {'body': 0, 'eye': 0, 'joya': 0, 'kept': 0}
    for g in geos:
        m = mat_of(g); mn = (m.name.lower() if m else ''); gn = g.name.lower()
        if gn == 'lengua_low': g.par.material = lengua.path; n['kept'] += 1; continue   # blue, constant, PBR
        if gn == 'dientes_low': g.par.material = dientes.path; n['kept'] += 1; continue  # gold, constant, PBR
        if gn.startswith('joya_') or gn.startswith('base_') or mn.startswith('joya'):
            fam = 'joyas' if gn.startswith('base_') else ('joya_flor' if mn.startswith('joya_flor') else 'joya')
            g.par.material = jmats[fam].path; n['joya'] += 1
        elif mn.startswith('ballena'): g.par.material = body.path; n['body'] += 1
        elif mn.startswith('ojo'): g.par.material = eye.path; n['eye'] += 1
        elif gn.startswith('eye'): g.par.material = eye.path; n['eye'] += 1
    _log('   assigned', n)
    # 5. environment light on env_sky, for the copper
    _log('step 5: environment light')
    env = ROOT.op('env_light')
    if env is None:
        for tn in ('environmentlightCOMP', 'envlightCOMP'):
            try: env = ROOT.create(eval(tn), 'env_light'); break
            except Exception as e: _log('   ', tn, str(e)[:50])
    if env is not None:
        setp(env, ['envlightmap', 'map'], '/project1/env_sky'); setp(env, ['dimmer'], 1.0)
        lv = R.par.lights.eval(); paths = (lv.split() if isinstance(lv, str) else [getattr(x, 'path', str(x)) for x in lv])
        if env.path not in paths: R.par.lights = ' '.join(paths + [env.path])
        _log('   render1 lights:', R.par.lights.eval())
    _log('### td_pbr DONE', time.strftime('%H:%M:%S'), '| errors on body MAT:', body.errors() or 'none', '| Cmd+S if she looks right; REVERT = True in the file and run again to undo')
except Exception:
    _log(traceback.format_exc()); _log('### td_pbr FAILED')
