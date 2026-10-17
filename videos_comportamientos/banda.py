#!/usr/bin/env python3
"""banda.py <segundos> <salida.wav> - la banda sonora del video, hecha solo con lo suyo (sin musica ajena):
  - un bordon grave sintetizado (55 / 82 / 110 Hz, respira despacio),
  - un latido a 65 por minuto, grave, como el EmotiBit en la muneca,
  - su canto (singing.wav) en bucle, muy bajo, filtrado, como textura,
  - y debajo de cada animo (empiezan en 10.5 s, 4.5 s cada uno) el sonido de ese animo (Huk/whale sound/),
  - al abrir, el agua (calm) y al cerrar, el soplo (surfacing)."""
import os, sys, subprocess
W = os.path.expanduser("~/Desktop/Huk/whale sound"); tot = float(sys.argv[1]); salida = sys.argv[2]
animos = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
fmt = "aformat=sample_rates=44100:channel_layouts=stereo"
ins = ["-f", "lavfi", "-t", f"{tot:.2f}", "-i", f"aevalsrc=exprs='(0.5*sin(2*PI*55*t)+0.3*sin(2*PI*82.41*t)+0.15*sin(2*PI*110*t))*(0.7+0.3*sin(2*PI*0.06*t))|(0.5*sin(2*PI*55*t+0.3)+0.3*sin(2*PI*82.41*t)+0.15*sin(2*PI*110*t+0.5))*(0.7+0.3*sin(2*PI*0.06*t+1))':s=44100",
       "-f", "lavfi", "-t", f"{tot:.2f}", "-i", "aevalsrc=exprs='(exp(-30*mod(t,0.923))*sin(2*PI*52*t)+0.55*exp(-30*mod(t-0.18,0.923))*sin(2*PI*48*t))|(exp(-30*mod(t,0.923))*sin(2*PI*52*t)+0.55*exp(-30*mod(t-0.18,0.923))*sin(2*PI*48*t))':s=44100",
       "-stream_loop", "-1", "-i", os.path.join(W, "singing.wav")]
fc = [f"[0:a]{fmt},lowpass=f=220,volume=0.16,afade=t=in:d=4,afade=t=out:st={tot - 6:.2f}:d=6[dron]",
      f"[1:a]{fmt},lowpass=f=140,volume=0.42,afade=t=in:st=6:d=4,afade=t=out:st={tot - 6:.2f}:d=5[latido]",
      f"[2:a]{fmt},atrim=0:{tot:.2f},lowpass=f=1800,highpass=f=120,volume=0.10,afade=t=in:d=8,afade=t=out:st={tot - 8:.2f}:d=8[canto]"]
mix = "[dron][latido][canto]"; n = 3
def suena(nombre, inicio, dur, vol, fin_fade=1.2):
    global n, mix
    ins.extend(["-i", os.path.join(W, nombre + ".wav")]); ms = int(inicio * 1000)
    fc.append(f"[{n}:a]{fmt},atrim=0:{dur:.2f},dynaudnorm=p=0.6:m=6:s=8,afade=t=in:d=0.5,afade=t=out:st={dur - fin_fade:.2f}:d={fin_fade},adelay={ms}|{ms},volume={vol}[s{n}]"); mix += f"[s{n}]"; n += 1
suena("calm", 0.5, 7.5, 0.5, 2.5)                                  # el agua al abrir
for i, a in enumerate(animos): suena(a, 10.5 + i * 4.5, 4.5, 0.9)   # cada animo bajo su tramo
suena("diving", tot - 24, 16, 0.35, 5)                               # hondo bajo el final
suena("surfacing", tot - 7, 6, 0.6, 2.5)                             # el soplo al cerrar
fc.append(f"{mix}amix=inputs={n}:normalize=0:dropout_transition=0,alimiter=limit=0.89,aformat=sample_fmts=s16[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[a]", "-t", f"{tot:.2f}", salida], check=True); print("banda", salida, f"{tot:.1f} s")
