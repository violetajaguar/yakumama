"""
td_run.py - run INSIDE TouchDesigner's textport. Runs the script whose path is in /tmp/td_next.txt and writes everything it
prints (and any traceback) to /tmp/td_out.txt, so the result can be read from outside TD (23 Oct 2026, driving the model swap
from Claude's session with screenshots too unreliable to read).

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_run.py').read())
"""
import io, contextlib, traceback, time
_ruta = open('/tmp/td_next.txt').read().strip()
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
    print('### td_run', time.strftime('%H:%M:%S'), _ruta)
    try:
        exec(compile(open(_ruta).read(), _ruta, 'exec'), globals())
        print('### done')
    except Exception:
        traceback.print_exc()
        print('### FAILED')
open('/tmp/td_out.txt', 'w').write(_buf.getvalue())
print(_buf.getvalue())
