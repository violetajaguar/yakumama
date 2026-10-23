"""
td_memoria.py - run INSIDE TouchDesigner, in the textport, to find the node that leaks (21 Oct 2026).

TouchDesigner on this Mac grows ~70 MB per minute (1.8 GB at open -> 13 GB after 3 h), with the same rate whether or not her brain,
Dan's brain, the drawing or any input is running (measured 21 Oct 10:40: zero input, same growth). So it is a node cooking every
frame inside the project. TD reports memory per operator (cpuMemory / gpuMemory), so: run this once, wait two minutes, run it again,
and the node whose number climbs is the one. Paste the two outputs to Claude.

    exec(open('/Users/jaguar/Desktop/Yakumama/docs/td_memoria.py').read())

REPORT ONLY: it changes nothing.
"""
import time
_t = time.strftime("%H:%M:%S")
rows = []
for o in op('/').findChildren(maxDepth=6):
    try:
        c = int(getattr(o, 'cpuMemory', 0) or 0); g = int(getattr(o, 'gpuMemory', 0) or 0)
    except Exception:
        continue
    if c + g > 2 * 1024 * 1024:   # over 2 MB
        rows.append((c + g, c, g, o.path, o.type))
rows.sort(reverse=True)
tot_c = sum(r[1] for r in rows); tot_g = sum(r[2] for r in rows)
print("=" * 78)
print(f"TD MEMORY BY OPERATOR  {_t}   (listed: {tot_c / 1e9:.2f} GB cpu, {tot_g / 1e9:.2f} GB gpu, nodes over 2 MB)")
print(f"{'total MB':>9} {'cpu MB':>8} {'gpu MB':>8}  path  (type)")
for s, c, g, p, t in rows[:40]:
    print(f"{s / 1e6:9.1f} {c / 1e6:8.1f} {g / 1e6:8.1f}  {p}  ({t})")
try:
    print(f"\nproject: {project.name}   frame {absTime.frame}   fps {int(project.cookRate)}   up {absTime.seconds / 60:.0f} min")
except Exception:
    pass
print("=" * 78)
print("Run again in 2 minutes and compare: the line that grows is the leak.")
