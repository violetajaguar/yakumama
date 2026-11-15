"""
td_todo_2.py - the second half of the model swap, with Dan's brain RUNNING (its channels must exist): skin tint, the salt light,
tongue blue / teeth gold. Then Cmd+S.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_todo_2.py').read())
"""
import os, time, traceback
TD = os.path.join(project.folder, 'td'); LOG = '/tmp/td_out.txt'
def _log(*a):
    s = ' '.join(str(x) for x in a); print(s)
    with open(LOG, 'a') as f: f.write(s + '\n')
def _run(path):
    try:
        exec(compile(open(path).read(), path, 'exec'), {}); _log('### ok', os.path.basename(path))
    except Exception:
        _log(traceback.format_exc()); _log('### FAILED', os.path.basename(path))
open(LOG, 'w').close(); _log('### td_todo_2', time.strftime('%H:%M:%S'), 'oscin channels:', op('/project1/oscin1').numChans)
_run(os.path.join(TD, 'setup_skin.py'))
_run(os.path.join(TD, 'setup_whale_light.py'))
_run('/Users/jaguar/Desktop/Yakumama/docs/td_colores.py')
_log('### TODO_2 DONE', time.strftime('%H:%M:%S'), '-> Cmd+S')
