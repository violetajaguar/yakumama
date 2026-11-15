"""
td_ajuste.py - her look by eye (23 Oct 2026): RUGOSIDAD (0 mirror .. 1 matte) on her PBR skin, ENV (environment light strength),
then Dan's light script (its MOONLIGHT / LIGHT_GAIN live in td/setup_whale_light.py). Edit the numbers, run the line again.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_ajuste.py').read())
"""
import os
RUGOSIDAD = 0.12   # was 0.30 -> 0.20 -> 0.12: a tighter sun highlight (the glint)
ESPECULAR = 1.0    # PBR specular level, was 0.5
ENV       = 1.4    # environment light dimmer, was 1.0
SOL       = 1.5    # the sun light's dimmer, was 1.0 (the bounce and fill stay)
b = op('/project1/whale_pbr_body'); e = op('/project1/env_light'); l1 = op('/project1/light1')
if b:
    b.par.roughness = RUGOSIDAD; print('body roughness', b.par.roughness.eval())
    if hasattr(b.par, 'specularlevel'): b.par.specularlevel = ESPECULAR; print('specular level', b.par.specularlevel.eval())
if e and hasattr(e.par, 'dimmer'): e.par.dimmer = ENV; print('env light dimmer', e.par.dimmer.eval())
exec(compile(open(os.path.join(project.folder, 'td', 'setup_whale_light.py')).read(), 'setup_whale_light.py', 'exec'), {})
if l1 is not None and hasattr(l1.par, 'dimmer'): l1.par.dimmer = SOL; print('sun dimmer', l1.par.dimmer.eval())   # after the light script, which resets dimmers to 1
print('### ajuste done: roughness', RUGOSIDAD, 'specular', ESPECULAR, 'env', ENV, 'sun', SOL, '| moonlight / gain as in td/setup_whale_light.py')
