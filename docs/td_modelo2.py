"""
td_modelo2.py - run INSIDE TouchDesigner, in the textport (23 Oct 2026): swap the whale's FBX for Brian's whale2.fbx
(the same whale with the eight copper jewels parented to spine.001; see docs/MODELO_NUEVO_TD.md).

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_modelo2.py').read())

It points /project1/whale at whale2.fbx, pulses Reload, and prints what the COMP now holds (bones, jewels, body).
Then run td/capture_rest_rotations.py on the clean rig, and the rest of the runbook.
"""
import os
w = op('/project1/whale')
nuevo = os.path.join(project.folder, 'whale2.fbx')
print('=' * 70)
print('before:', w.par.file.eval(), '| children:', len(w.children))
print('file exists:', os.path.exists(nuevo), nuevo)
w.par.file = nuevo
pulsed = []
for p in w.pars('reload*'):
    try: p.pulse(); pulsed.append(p.name)
    except Exception as e: print('  (could not pulse', p.name, e, ')')
print('reload pulsed:', pulsed or 'NO reload parameter found: press Reload on the FBX COMP')
kids = w.children
print('after:', w.par.file.eval(), '| children:', len(kids))
print('  bones found:', sum(1 for c in kids if c.type == 'bone'), '| jewels (joya_*):', [c.name for c in kids if c.name.startswith('joya')][:8])
print('  body:', op('/project1/whale/ballena_low') is not None, '| eye_L1:', op('/project1/whale/eye_L1') is not None, '| spine_001:', op('/project1/whale/spine_001') is not None)
print('  errors on the COMP:', w.errors() or 'none')
print('=' * 70)
