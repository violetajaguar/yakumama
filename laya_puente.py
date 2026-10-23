#!/usr/bin/env python3
"""laya_puente.py - Laya on the Mac Mini, her brain on the PC (Dan's setup, 19 Oct 2026).

Violeta's laya_sentidos.py reads her brain's situation from /tmp/ballena_cerebro.json and writes its opinion to
/tmp/ballena_laya.json, on ONE machine. Here her brain runs on the PC and Laya (MLX: Apple Silicon only) on the Mac
Mini, so this carries the two files across the network. The same file runs on both ends:

    PC:   python laya_puente.py pc  <mac-ip>    her situation -> Mac UDP 9981; Laya's answers <- UDP 9982, written to
                                                /tmp/ballena_laya.json stamped with the PC's own clock (decisiones.py
                                                ignores an opinion older than 12 s, measured on THIS machine)
    Mac:  python laya_puente.py mac <pc-ip>     UDP 9981 -> /tmp/ballena_cerebro.json; starts laya_sentidos.py itself
                                                and sends its answer back - again every 2 s while Laya is alive, because
                                                Laya only writes when the situation CHANGES and a still visitor must not
                                                make her opinion go stale

The paths are her code's own ("/tmp/..."; on Windows that is C:\\tmp on drive C). Standard library only. If either end
is missing, her brain runs exactly as before: decisiones.py treats Laya as absent."""
import json
import os
import socket
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
CEREBRO, LAYA = "/tmp/ballena_cerebro.json", "/tmp/ballena_laya.json"
A_MAC, A_PC = 9981, 9982
REENVIO_S = 2.0
VIVO_S = 10.0     # the chain is alive only while her brain is: it writes a situation every 4 s. A situation older than
                  # this is not sent (PC), and Laya's answer is not sent once situations stop arriving (Mac) - otherwise
                  # a leftover file would reach decisiones.py looking fresh (caught by the Mac session, 19 Oct)


def _leer_json(ruta):
    """The file's bytes if they are a whole JSON object (her brain writes in place, so a read can catch half a file)."""
    b = open(ruta, "rb").read()
    json.loads(b)
    return b


def _escribir(ruta, b):
    tmp = ruta + ".tmp"
    with open(tmp, "wb") as f:
        f.write(b)
    os.replace(tmp, ruta)                         # whole or not at all, for whoever reads it


def pc(mac):
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     # separate sockets: on Windows a send to a closed port
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)     # makes the NEXT recv on the same socket raise
    rx.bind(("0.0.0.0", A_PC)); rx.settimeout(0.5)
    m_ant, t_env, n_out, n_in, t_dicho, t_resp = 0.0, 0.0, 0, 0, time.time(), 0.0
    print(f"   laya puente (PC): situation {CEREBRO} -> {mac}:{A_MAC}   answers :{A_PC} -> {LAYA}", flush=True)
    while True:
        try:
            m = os.path.getmtime(CEREBRO)
            if time.time() - m < VIVO_S and (m != m_ant or time.time() - t_env > 4.0):   # new, or a resend if one was lost
                tx.sendto(_leer_json(CEREBRO), (mac, A_MAC)); m_ant, t_env = m, time.time(); n_out += 1
        except (OSError, ValueError):
            pass
        try:
            b, _ = rx.recvfrom(65535)
            v = json.loads(b); v["t"] = time.time()             # fresh by the PC's clock
            _escribir(LAYA, json.dumps(v).encode()); n_in += 1; t_resp = time.time()
        except socket.timeout:
            pass
        except (OSError, ValueError) as e:
            print(f"   (laya puente: {str(e)[:80]})", flush=True)
        if time.time() - t_dicho > 30.0:
            t_dicho = time.time()
            vivo = "Laya answering" if time.time() - t_resp < 10 else "no answer from the Mac"
            print(f"   laya puente: {n_out} situations sent, {n_in} answers received - {vivo}", flush=True)


def mac(pc_ip):
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rx.bind(("0.0.0.0", A_MAC)); rx.settimeout(0.5)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    os.makedirs(os.path.join(AQUI, "datasets"), exist_ok=True)   # laya_sentidos.py logs to datasets/laya.jsonl
    for viejo in (LAYA, CEREBRO):                                 # nothing from a previous run may pass as live
        try:
            os.remove(viejo)
        except OSError:
            pass
    laya, t_ini, t_sit = None, 0.0, 0.0
    m_ant, ultima, t_env, n_in, n_out, t_dicho = 0.0, None, 0.0, 0, 0, time.time()
    print(f"   laya puente (Mac): situations :{A_MAC} -> {CEREBRO}   Laya's answers {LAYA} -> {pc_ip}:{A_PC}", flush=True)
    while True:
        if laya is None or (laya.poll() is not None and time.time() - t_ini > 5.0):
            if laya is not None:
                print(f"   (laya_sentidos.py stopped with code {laya.returncode}; starting it again)", flush=True)
            laya, t_ini = subprocess.Popen([sys.executable, "-I", os.path.join(AQUI, "laya_sentidos.py")], cwd=AQUI), time.time()
        try:
            b, _ = rx.recvfrom(65535); json.loads(b); _escribir(CEREBRO, b); n_in += 1; t_sit = time.time()
        except socket.timeout:
            pass
        except (OSError, ValueError) as e:
            print(f"   (laya puente: {str(e)[:80]})", flush=True)
        try:
            m = os.path.getmtime(LAYA)
            if m != m_ant:
                ultima, m_ant, t_env = _leer_json(LAYA), m, 0.0
        except (OSError, ValueError):
            pass
        if (ultima is not None and laya.poll() is None and time.time() - t_sit < VIVO_S
                and time.time() - t_env >= REENVIO_S):
            tx.sendto(ultima, (pc_ip, A_PC)); t_env = time.time(); n_out += 1
        if time.time() - t_dicho > 30.0:
            t_dicho = time.time()
            print(f"   laya puente: {n_in} situations received, {n_out} answers sent - "
                  f"Laya {'running' if laya.poll() is None else 'stopped'}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("pc", "mac"):
        sys.exit(__doc__)
    (pc if sys.argv[1] == "pc" else mac)(sys.argv[2])
