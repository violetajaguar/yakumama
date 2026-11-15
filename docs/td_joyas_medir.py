# measure the jewel pieces against her body inside TD (23 Oct): where they are, how big, what transform they carry
w = op('/project1/whale')
def info(c):
    try: b = c.computeBounds(includeChildren=False); size = tuple(round(v, 1) for v in b.size); mn = tuple(round(v, 1) for v in b.min)
    except Exception as e: size, mn = ('?', str(e)[:40]), None
    try: m = c.worldTransform; sc = tuple(round(v, 3) for v in m.decompose()[0]); tr = tuple(round(v, 1) for v in m.decompose()[2])
    except Exception as e: sc, tr = ('?', str(e)[:30]), None
    return f"{c.path:40s} parent {c.parent().name:14s} size {size} min {mn} worldScale {sc} worldT {tr}"
print(info(op('/project1/whale/ballena_low')))
print(info(op('/project1/whale/spine_001')))
js = [c for c in w.findChildren(maxDepth=5) if c.name.lower().startswith('joya')]
print('jewel ops:', len(js))
for c in js[:5]: print(info(c))
print('types among jewels:', sorted({c.type for c in js}))
