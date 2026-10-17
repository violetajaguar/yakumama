#!/usr/bin/env python3
"""leer_mat_opaco.py - saca las matrices numericas de un .mat con tablas de MATLAB (objetos MCOS opacos, que scipy no
lee): recorre a mano el flujo de elementos del espacio de trabajo. Devuelve [(contexto, array)]. Lo usa importar_surf.py."""
import zlib, struct, numpy as np
from scipy.io import loadmat
DT = {1: np.int8, 2: np.uint8, 3: np.int16, 4: np.uint16, 5: np.int32, 6: np.uint32, 7: np.float32, 9: np.float64, 12: np.int64, 13: np.uint64, 16: np.uint8}
def _elems(buf, off=0):
    while off + 8 <= len(buf):
        t, n = struct.unpack_from("<II", buf, off)
        if t >> 16: n, t = t >> 16, t & 0xFFFF; data = buf[off + 4: off + 4 + n]; off += 8
        else: data = buf[off + 8: off + 8 + n]; off += 8 + ((n + 7) // 8) * 8
        yield t, data
def _matriz(data, ctx, out):
    it = _elems(data)
    try: tf, flags = next(it); clase = flags[0]
    except StopIteration: return
    if clase == 17:   # opaco (MCOS): nombre, sistema, clase, y el dato en un miMATRIX
        for tt, d in it:
            if tt == 14: _matriz(d, ctx + "#", out)
        return
    try: td, dims = next(it); dims = np.frombuffer(dims, np.int32); tn, nombre = next(it); nombre = nombre.rstrip(b"\x00").decode(errors="ignore")
    except StopIteration: return
    ctx = ctx + ("/" + nombre if nombre else "")
    if 6 <= clase <= 15:
        try: tv, val = next(it)
        except StopIteration: return
        if tv in DT:
            a = np.frombuffer(val, DT[tv])
            if a.size == int(np.prod(dims)): a = a.reshape(dims[::-1]).T
            if clase in (6, 7) and a.size > 1: out.append((ctx, a.astype(np.float64)))
            elif clase == 9 and a.size > 200: _flujo(a.tobytes(), ctx + "|", out)
    elif clase == 4:   # texto
        try: tv, val = next(it); out.append((ctx, val.decode("utf-16-le" if tv == 4 else "latin-1", errors="ignore")))
        except StopIteration: pass
    elif clase == 1:
        for tt, d in it:
            if tt == 14: _matriz(d, ctx + "{}", out)
    elif clase == 2:
        try: tl, fl = next(it); fl = struct.unpack("<i", fl[:4])[0]; tnm, names = next(it)
        except StopIteration: return
        campos = [names[i:i + fl].rstrip(b"\x00").decode(errors="ignore") for i in range(0, len(names), fl)]; k = 0
        for tt, d in it:
            if tt == 14: _matriz(d, ctx + "." + campos[k % max(1, len(campos))], out); k += 1
def _flujo(buf, ctx, out):
    off = 8 if buf[:4] == b"\x00\x01IM" else 0
    for t, d in _elems(buf, off):
        if t == 15:
            try: _flujo(zlib.decompress(d), ctx, out)
            except Exception: pass
        elif t == 14: _matriz(d, ctx, out)
def leer(ruta):
    m = loadmat(ruta); out = []
    if "__function_workspace__" in m: _flujo(m["__function_workspace__"].tobytes(), "ws", out)
    return out
if __name__ == "__main__":
    import sys
    for c, a in leer(sys.argv[1]): print(f"{c[-60:]:60s}", a.shape if isinstance(a, np.ndarray) else repr(a[:60]), (np.round(a.ravel()[:4], 3).tolist() if isinstance(a, np.ndarray) else ""))
