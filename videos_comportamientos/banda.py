#!/usr/bin/env python3
"""banda.py <segundos> <salida.wav> - la banda sonora del video: Tidal Echoes (la base de Blender) entera y, debajo de
cada animo (empiezan en 10.5 s, 4.5 s cada uno), su sonido de Huk/whale sound/."""
import os, sys, subprocess
W = os.path.expanduser("~/Desktop/Huk/whale sound"); tot = float(sys.argv[1]); salida = sys.argv[2]
animos = ["calm", "singing", "playful", "curious", "feeding", "sad", "angry", "alert", "diving", "surfacing"]
ins = ["-i", os.path.join(W, "Tidal Echoes.mp3")]; fc = [f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{tot:.2f},afade=t=in:d=2,afade=t=out:st={tot - 5:.2f}:d=5,volume=0.7[m]"]; mix = "[m]"
for i, a in enumerate(animos, 1):
    ins += ["-i", os.path.join(W, a + ".wav")]; ms = int(10500 + (i - 1) * 4500)
    fc.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:4.5,afade=t=in:d=0.4,afade=t=out:st=3.3:d=1.2,adelay={ms}|{ms},volume=0.8[s{i}]"); mix += f"[s{i}]"
fc.append(f"{mix}amix=inputs={len(animos) + 1}:normalize=0:dropout_transition=0,alimiter=limit=0.9[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[a]", "-t", f"{tot:.2f}", salida], check=True); print("banda", salida, f"{tot:.1f} s")
