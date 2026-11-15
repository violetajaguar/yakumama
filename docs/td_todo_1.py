"""
td_todo_1.py - ONE line in TouchDesigner's textport does the first half of the model swap (23 Oct 2026):
import whale2.fbx, wait for the import, capture the rest pose, build her face chain (setup_shapes_sop, fix_blendshape_names,
setup_shapes_fbx). Dan's brain must be STOPPED while this runs (the rest capture needs a clean rig). Each stage schedules the next
with TD's run(..., delayFrames=...) by re-reading this file (a delayed call runs in another scope, so the stage lives in a file).

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_todo_1.py').read())

Then start Dan's brain and run docs/td_todo_2.py (skin, light, colours) and Cmd+S.
"""
import os, time, traceback
ME = '/Users/jaguar/Desktop/Yakumama/docs/td_todo_1.py'
TD = os.path.join(project.folder, 'td'); LOG = '/tmp/td_out.txt'; STAGE = '/tmp/td_stage.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
def _run(path):
    try:
        exec(compile(open(path).read(), path, 'exec'), {}); _log('### ok', os.path.basename(path))
    except Exception:
        _log(traceback.format_exc()); _log('### FAILED', os.path.basename(path))
def _next(n, frames):
    open(STAGE, 'w').write(str(n)); run("exec(open('%s').read())" % ME, delayFrames=frames)
try: stage = int(open(STAGE).read().strip() or 1)
except Exception: stage = 1
if stage == 1:
    open(LOG, 'w').close()
    w = op('/project1/whale'); w.par.file = os.path.join(project.folder, 'whale2.fbx'); w.par.imp.pulse()
    _log('### td_todo_1', time.strftime('%H:%M:%S'), 'import pulsed for', w.par.file.eval()[-10:], '| children before', len(w.children))
    _next(2, 2400)   # ~40 s for the import
elif stage == 2:
    w = op('/project1/whale'); _log('after import: children', len(w.children), '| body', op('/project1/whale/ballena_low') is not None, '| jewel pieces', len(w.findChildren(name='joya_*', maxDepth=4)), '| base pieces', [c.name for c in w.children if c.name.startswith('base')])
    _log('rest offsets: NOT captured here (23 Oct: a capture after the export exists reads the OSC channels, not the import); docs/rest_desde_fbx.py writes them from the FBX'); _next(3, 60)
elif stage == 3:
    _run(os.path.join(TD, 'setup_shapes_sop.py')); _next(4, 60)
elif stage == 4:
    _run(os.path.join(TD, 'fix_blendshape_names.py')); _next(5, 60)
else:
    _run(os.path.join(TD, 'setup_shapes_fbx.py'))
    try: os.remove(STAGE)
    except Exception: pass
    _log('### TODO_1 DONE', time.strftime('%H:%M:%S'), "-> start Dan's brain, then td_todo_2.py")
