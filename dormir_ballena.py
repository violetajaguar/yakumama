#!/usr/bin/env python3
"""dormir_ballena.py - bedtime for the printed whale (21 Oct 2026, Violeta: "turn her eyes black and time to sleep").
The board draws whatever eye state the bridge (ballena_joy.py) last received on UDP 5007; with nothing arriving it IDLES (eyes
wander, fins breathe). So this keeps sending, 15 times a second: lids shut (blink 1), strip black (r g b 0, amt 1), fins and tail
at rest, mood calm. Run it after stopping Dan's brain, with the bridge still up; stop it to let the board idle or when the brain returns.
    nohup venv/bin/python -u dormir_ballena.py > logs/dormir.log 2>&1 &"""
import json, socket, time
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); n = 0
m = {"blink": 1.0, "lx": 0.0, "ly": 0.0, "mood": 0, "ang": 0.0, "sad": 0.0, "aso": 0.0, "fl": 0.0, "fr": 0.0, "tail": 0.0, "r": 0, "g": 0, "b": 0, "amt": 1.0, "bpm": 0}
print("she sleeps: eyes shut and black, strip black, fins at rest (ctrl-C or pkill to stop)", flush=True)
while True:
    m["t"] = time.time(); s.sendto(json.dumps(m).encode(), ("127.0.0.1", 5007)); n += 1
    if n % 900 == 0: print(f"  asleep {n // 15} s", flush=True)
    time.sleep(1.0 / 15)
