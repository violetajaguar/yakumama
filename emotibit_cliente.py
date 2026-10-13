#!/usr/bin/env python3
"""emotibit_cliente.py - habla DIRECTO con el EmotiBit por WiFi, sin el Oscilloscope ni OSC.

Protocolo (EmotiBit_FeatherWing/EmotiBitWiFi.cpp y ofxEmotiBit/EmotiBitWiFiHost.cpp):
  host -> UDP 3131 "HE"                       (hello)            dispositivo -> "HH,DP,<p>,DI,<id>"
  host -> UDP 3131 "EC,CP,<ctrl>,DP,<data>"  (conectar)         dispositivo abre TCP a host:<ctrl> y manda datos UDP a host:<data>
  host -> UDP 3131 "PN,DP,<data>" cada 1 s   (ping)             dispositivo -> "PO" ; si no hay ping o cae el TCP, se desconecta
  dispositivo -> datos: lineas CSV "timestamp,n,largo,TAG,version,fiabilidad,v1,v2,...\\n"  (varias por datagrama)
  dispositivo -> datos "RD,TL,TU" cada tanto (pide la hora): host responde "TL,<hora>" y "AK,<n>,RD"
HR se calcula aqui a partir del PPG infrarrojo (picos), como hace el Oscilloscope.

    venv/bin/python emotibit_cliente.py            # prueba: 15 s de datos, tasa por senal
"""
import socket, time, threading, sys, select
ADV = 3131
TAGS = {"EA": "eda", "EL": "edl", "ER": "edr", "PI": "ppg_ir", "PR": "ppg_red", "PG": "ppg_grn", "T0": "temp", "T1": "temp1", "TH": "therm", "H0": "humidity",
        "AX": "acc_x", "AY": "acc_y", "AZ": "acc_z", "GX": "gyro_x", "GY": "gyro_y", "GZ": "gyro_z", "MX": "mag_x", "MY": "mag_y", "MZ": "mag_z",
        "BV": "batt_v", "B%": "batt", "HR": "hr", "BI": "ibi", "SA": "scr_amp", "SF": "scr_freq", "SR": "scr_ris"}

def paquete(tag, n, payload=""):
    datos = payload.split(",") if payload else []
    return f"{int(time.time() * 1000) % 4294967296},{n % 65536},{len(datos)},{tag},1,100" + ("," + payload if payload else "") + "\n"

class EmotiBit:
    def __init__(self, ip=None, data_port=3140, ctrl_port=3141, al_recibir=None):
        self.ip = ip; self.data_port = data_port; self.ctrl_port = ctrl_port; self.al_recibir = al_recibir
        self.valores = {}; self.ultimo = 0.0; self.n = 0; self.estado = "buscando"; self.id = None; self._ctr = 0; self._stop = False
        self._ppg = []; self._picos = []; self._ppg_t0 = None
    def start(self): threading.Thread(target=self._run, daemon=True).start(); return self
    def stop(self): self._stop = True
    def _run(self):
        while not self._stop:
            try: self._sesion()
            except Exception as e: self.estado = f"error: {e}"
            time.sleep(1.0)
    def _ips_broadcast(self):
        ips = {"255.255.255.255"}
        try:
            import subprocess
            for l in subprocess.run(["ifconfig"], capture_output=True, text=True).stdout.splitlines():
                if "broadcast" in l: ips.add(l.split("broadcast")[1].split()[0])
        except Exception: pass
        return ips
    def _sesion(self):
        adv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); adv.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1); adv.bind(("0.0.0.0", 0)); adv.settimeout(0.5)
        # 1) hello hasta que conteste
        self.estado = "buscando"; dev = None
        while not self._stop and dev is None:
            destinos = [self.ip] if self.ip else list(self._ips_broadcast())
            for d in destinos:
                try: adv.sendto(paquete("HE", self._ctr).encode(), (d, ADV)); self._ctr += 1
                except OSError: pass
            t0 = time.time()
            while time.time() - t0 < 1.0:
                try: msg, src = adv.recvfrom(4096)
                except socket.timeout: continue
                f = msg.decode(errors="ignore").strip().split(",")
                if len(f) > 3 and f[3] == "HH":
                    dev = src[0]; self.id = f[f.index("DI") + 1] if "DI" in f else None; break
        if dev is None: adv.close(); return
        # 2) servidores: control TCP + datos UDP
        ctrl = socket.socket(socket.AF_INET, socket.SOCK_STREAM); ctrl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); ctrl.bind(("0.0.0.0", self.ctrl_port)); ctrl.listen(1); ctrl.settimeout(0.5)
        datos = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); datos.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); datos.bind(("0.0.0.0", self.data_port)); datos.settimeout(0.2)
        self.estado = f"conectando a {dev}"; conn = None; t_ec = 0
        while not self._stop and conn is None:
            if time.time() - t_ec > 1.0:
                adv.sendto(paquete("EC", self._ctr, f"CP,{self.ctrl_port},DP,{self.data_port}").encode(), (dev, ADV)); self._ctr += 1; t_ec = time.time()
            try: conn, _ = ctrl.accept()
            except socket.timeout: pass
            if time.time() - t_ec > 15: break
        if conn is None: adv.close(); ctrl.close(); datos.close(); return
        conn.setblocking(False); self.estado = f"conectado {dev} ({self.id})"; self.ultimo = time.time(); t_ping = 0; dn = 0
        # 3) datos + ping
        while not self._stop:
            if time.time() - t_ping > 0.5:
                adv.sendto(paquete("PN", self._ctr, f"DP,{self.data_port}").encode(), (dev, ADV)); self._ctr += 1; t_ping = time.time()
            try: adv.recvfrom(4096)   # PO etc.
            except socket.timeout: pass
            try: msg, src = datos.recvfrom(65535)
            except socket.timeout: msg = None
            if msg:
                for linea in msg.decode(errors="ignore").split("\n"):
                    f = linea.strip().split(",")
                    if len(f) < 6: continue
                    tag = f[3]
                    if tag == "RD":   # pide la hora
                        hora = time.strftime("%Y-%m-%d_%H-%M-%S") + "-" + f"{int(time.time() * 1000) % 1000:03d}"
                        datos.sendto(paquete("TL", dn, hora).encode(), (dev, self.data_port)); dn += 1
                        datos.sendto(paquete("AK", dn, f"{f[1]},RD").encode(), (dev, self.data_port)); dn += 1; continue
                    if tag in TAGS and len(f) > 6:
                        try: vals = [float(x) for x in f[6:] if x != ""]
                        except ValueError: continue
                        if not vals: continue
                        self.valores["emotibit_" + TAGS[tag]] = round(vals[-1], 5); self.ultimo = time.time(); self.n += 1
                        if tag == "PI": self._latidos(vals, float(f[0]))
                        if self.al_recibir: self.al_recibir(TAGS[tag], vals)
            try:
                r, _, _ = select.select([conn], [], [], 0)
                if r and not conn.recv(4096): raise ConnectionError("control cerrado")
            except (BlockingIOError, InterruptedError): pass
            except Exception: self.estado = "desconectado"; break
            if time.time() - self.ultimo > 5: self.estado = "sin datos 5 s"; break
        try: adv.sendto(paquete("ED", self._ctr).encode(), (dev, ADV))
        except Exception: pass
        for s in (conn, ctrl, datos, adv):
            try: s.close()
            except Exception: pass
    def _latidos(self, vals, ts_ms):
        """HR por picos del PPG infrarrojo (25 Hz): media movil de 1 s, pico = maximo local sobre la media, >0.33 s entre picos."""
        for v in vals:
            self._ppg.append(v)
        self._ppg = self._ppg[-250:]
        if len(self._ppg) < 50: return
        fs = 25.0; w = self._ppg[-50:]; med = sum(w) / len(w); x = [a - med for a in w]
        i = len(x) - 2
        if x[i] > x[i - 1] and x[i] >= x[i + 1] and x[i] > 0.3 * max(abs(a) for a in x):
            t = time.time() - 2 / fs
            if not self._picos or t - self._picos[-1] > 0.33: self._picos.append(t)
        self._picos = [p for p in self._picos if time.time() - p < 8]
        if len(self._picos) >= 3:
            ibi = [b - a for a, b in zip(self._picos, self._picos[1:])]; ibi = sorted(ibi)[len(ibi) // 4: len(ibi) - len(ibi) // 4] or ibi
            bpm = 60.0 / (sum(ibi) / len(ibi))
            if 35 < bpm < 200: self.valores["emotibit_hr"] = round(bpm, 1); self.valores["emotibit_ibi"] = round(sum(ibi) / len(ibi), 3)

def osc_msg(addr, v):
    """un mensaje OSC con un float (lo que manda el Oscilloscope)."""
    import struct
    def pad(b): return b + b"\0" * ((4 - len(b) % 4) % 4)
    return pad(addr.encode() + b"\0") + pad(b",f\0") + struct.pack(">f", float(v))
OSC_ADDR = {"eda": "EDA", "edl": "EDL", "edr": "EDR", "ppg_ir": "PPG:IR", "ppg_red": "PPG:RED", "ppg_grn": "PPG:GRN", "temp": "TEMP", "temp1": "TEMP1", "therm": "THERM", "humidity": "HUMIDITY",
            "acc_x": "ACC:X", "acc_y": "ACC:Y", "acc_z": "ACC:Z", "gyro_x": "GYRO:X", "gyro_y": "GYRO:Y", "gyro_z": "GYRO:Z", "mag_x": "MAG:X", "mag_y": "MAG:Y", "mag_z": "MAG:Z",
            "batt_v": "BATT:V", "batt": "BATT", "hr": "HR", "ibi": "IBI", "scr_amp": "SCR:AMP", "scr_freq": "SCR:FREQ", "scr_ris": "SCR:RIS"}

if __name__ == "__main__":
    import argparse
    from collections import Counter
    ap = argparse.ArgumentParser(); ap.add_argument("ip", nargs="?", default=None); ap.add_argument("--osc", type=int, default=0, help="reenviar como OSC a 127.0.0.1:PUERTO (como el Oscilloscope), sin parar")
    ap.add_argument("--segundos", type=float, default=15); a = ap.parse_args()
    c = Counter(); u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    def recibir(k, v):
        c.update({k: len(v)})
        if a.osc:
            for x in v: u.sendto(osc_msg("/EmotiBit/0/" + OSC_ADDR.get(k, k.upper()), x), ("127.0.0.1", a.osc))
    e = EmotiBit(ip=a.ip, al_recibir=recibir).start(); t0 = time.time(); ultimo_hr = None
    while a.osc or time.time() - t0 < a.segundos:
        time.sleep(3)
        if a.osc and e.valores.get("emotibit_hr") is not None and e.valores.get("emotibit_hr") != ultimo_hr:
            ultimo_hr = e.valores["emotibit_hr"]; u.sendto(osc_msg("/EmotiBit/0/HR", ultimo_hr), ("127.0.0.1", a.osc))
        print(f"  [{time.time()-t0:5.0f} s] {e.estado} | hr {e.valores.get('emotibit_hr')} eda {e.valores.get('emotibit_eda')} therm {e.valores.get('emotibit_therm')} | paquetes {sum(c.values())}", flush=True)
    e.stop()
