"""
td_todo_3.py - the world onto the shared tonemap, then her haze (23 Oct 2026). Dan's setup_tonemap.py reported that the salar
materials and the env map have no uGrade / uExpoT uniform bound ("rebuild it with its setup script"): until they are rebuilt they
tonemap themselves inline AND go through the new pass, twice, while she goes through it once. This runs Dan's world setup scripts
in order (sky, the drawing canvas which re-runs the ground itself, mountains, island, cacti, env map), each logged, then the camera
fog (docs/td_niebla.py). Dan's brain must be RUNNING (palette and dib_* channels).

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_todo_3.py').read())
"""
import os, time, traceback
TD = os.path.join(project.folder, 'td'); LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
def _run(path):
    _log('--- running', os.path.basename(path), time.strftime('%H:%M:%S'))
    try:
        exec(compile(open(path).read(), path, 'exec'), {}); _log('### ok', os.path.basename(path))
    except Exception:
        _log(traceback.format_exc()); _log('### FAILED', os.path.basename(path))
open(LOG, 'w').close(); _log('### td_todo_3', time.strftime('%H:%M:%S'))
for s in ('setup_salar_sky.py', 'setup_dibujo.py', 'setup_salar_mtn.py', 'setup_salar_island.py', 'setup_salar_cacti_models.py', 'setup_env.py'):
    _run(os.path.join(TD, s))
_run('/Users/jaguar/Desktop/Yakumama/docs/td_niebla.py')
for nm in ('salar_sky/salar_sky_mat', 'salar_ground/salar_ground_mat', 'salar_mtn/salar_mtn_mat', 'salar_island/salar_island_mat', 'salar_cacti_models/salar_cacti_models_mat'):
    m = op('/project1/' + nm)
    _log('  %-40s %s' % (nm, ('errors: ' + (m.errors() or 'none')) if m else 'MISSING'))
_log('### TODO_3 DONE', time.strftime('%H:%M:%S'), '-> look at her in the world, then Cmd+S')
