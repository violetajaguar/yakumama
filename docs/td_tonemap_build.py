"""
td_tonemap_build.py - runs Dan's td/setup_tonemap.py in BUILD mode without editing his file (23 Oct 2026): one display
transform for her and the world (exposure -> ACES -> saturation -> gamma) after render1; window1 then shows /project1/tonemap.
Everything it changes is read back and kept; running it with MODE 'revert' (see below) undoes it. Logs to /tmp/td_out.txt.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_tonemap_build.py').read())
"""
import io, contextlib, traceback, time, os
MODE = 'build'   # 'build' | 'revert' | 'diag'
LOG = '/tmp/td_out.txt'; src = os.path.join(project.folder, 'td', 'setup_tonemap.py')
code = open(src).read().replace("MODE = 'diag'", "MODE = %r" % MODE, 1)
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    print('### td_tonemap', MODE, time.strftime('%H:%M:%S'))
    try: exec(compile(code, src, 'exec'), {}); print('### done')
    except Exception: traceback.print_exc(); print('### FAILED')
open(LOG, 'w').write(buf.getvalue()); print(buf.getvalue())
