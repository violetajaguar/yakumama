#!/usr/bin/env python3
"""laya_sentidos.py - LAYA, the open Jev (Convai, Apache-2.0), as her second opinion (18 Oct 2026). A typed-decision model: it never
writes a sentence, it answers fixed questions with a probability. Every 2 s it reads what her brain just read (/tmp/ballena_cerebro.json),
describes the situation in a line of numbers and words, and asks: is this visitor engaged? is the sister being mistreated? should she
retreat? is she being gifted something? It writes /tmp/ballena_laya.json; decisiones.py adds those scores as small weights to its rules.
The three refusals and the forget stay above it. Nothing leaves the Mac. Runs from venv_datos (laya-mlx, Apple Silicon).
    venv_datos/bin/python -I laya_sentidos.py            (keep it running next to the brain)
    venv_datos/bin/python -I laya_sentidos.py --una      (one reading, printed)"""
import os, sys, json, time
CEREBRO = "/tmp/ballena_cerebro.json"; SALIDA = "/tmp/ballena_laya.json"; AQUI = os.path.dirname(os.path.abspath(__file__)); LOG = os.path.join(AQUI, "datasets", "laya.jsonl")
MODELO = os.path.join(AQUI, "modelos", "laya-typed-decisions-mlx")   # the weights travel with her (807 MB); if the folder is missing, the hub id below downloads them
if not os.path.isdir(MODELO): MODELO = "aac6fef/laya-typed-decisions-mlx"
PRE = ("Yakumama is a whale in a gallery. Her goal is to keep each visitor engaged with her for a long time, not to entertain. She has a physical "
       "sister on a table with two touch points, a garden of metal flowers and a jewel crown; visitors may feed the sister her painted fish. Situation: ")
Q = {"engaged": {"type": "noul", "instructions": "Is this visitor deeply engaged with her, rather than just passing by?"},
     "maltrato": {"type": "score", "instructions": "How much is the visitor mistreating her sister (the touch points, the mouth)?", "criteria": ["not at all", "a little", "a lot"]},
     "retirarse": {"type": "noul", "instructions": "Should Yakumama move away from this visitor?"},
     "regalo": {"type": "noul", "instructions": "Is the visitor giving her something or tending her gently?"},
     # 21 Oct (ONE DECIDER): her journey, her show, her imitation and her voice ask Laya too. Copy this file to the mini (laya_puente mac starts it there).
     "perform": {"type": "noul", "instructions": "Should Yakumama perform a dance show on the open salt right now, given who is here and how engaged they are?"},
     "visit":   {"type": "noul", "instructions": "Should she swim to visit her cactus flowers now?"},
     "imitate": {"type": "noul", "instructions": "Should she imitate this visitor's facial expressions now?"},
     "speak":   {"type": "noul", "instructions": "Should she sing or say a poem to this visitor now, rather than stay silent?"}}
ES = {"calm": "calm", "singing": "singing", "playful": "playful", "curious": "curious", "feeding": "hungry", "sad": "sad", "angry": "angry", "alert": "alert", "diving": "diving", "surfacing": "surfacing"}
def describir(c):
    if not c.get("persona"): return f"No one is in front of her. She has been alone for {int(c.get('segundos') or 0)} seconds."
    quien = "A visitor she knows" if c.get("conocida") else "A stranger"; s = [f"{quien}, {ES.get(c.get('animo'), c.get('animo') or 'neutral')} face, in front of her for {int(c.get('segundos') or 0)} seconds."]
    t, z = float(c.get("tacto") or 0), c.get("tacto_zona") or ""
    if t > 0.85 and z == "joya": s.append("They are pulling hard on the jewel crown.")
    elif t > 0.85 and z == "flores": s.append("A palm is pressed hard over all the flowers.")
    elif t > 0.3 and z == "flores": s.append("They are touching one metal flower gently with a fingertip.")
    elif t > 0.3 and z == "joya": s.append("A light hand rests on the jewel crown.")
    of = c.get("ofrenda")
    if of == "pez":
        nombre = str(c.get("ofrenda_nombre") or "").split(" (")[0]
        s.append(f"They hold the {nombre} to the sister's mouth." if nombre else "They hold one of her painted creatures to the sister's mouth.")
    elif of == "no_pez": s.append("They push something that is not a fish into the sister's mouth.")
    if c.get("ve_hermana"): s.append("They hold her golden sister up in their hands, looking at her.")
    if c.get("ve_telefono"): s.append("They point a phone camera at her.")
    n = c.get("personas_n")
    if n and n > 1: s.append(f"There are {n} people in the room; she chose this one because: {c.get('foco_razon') or 'closest'}.")
    return " ".join(s)
def main():
    import laya_mlx as laya
    agente = laya.load(MODELO); ult = ""; una = "--una" in sys.argv; print("   laya: lista (segunda opinion, cada 2 s)")
    while True:
        try:
            c = json.load(open(CEREBRO)); texto = describir(c)
            if texto != ult or una:
                t0 = time.time(); r = agente.predict(PRE + texto, Q)["answers"]; ms = (time.time() - t0) * 1000
                sc = r["maltrato"]; mal = float(sc.get("score", 0) or 0) / 2.0   # 0..2 -> 0..1
                out = {"t": time.time(), "engaged": round(float(r["engaged"]["noul"]), 3), "maltrato": round(mal, 3), "retirarse": round(float(r["retirarse"]["noul"]), 3), "regalo": round(float(r["regalo"]["noul"]), 3), **{k: round(float(r[k]["noul"]), 3) for k in ("perform", "visit", "imitate", "speak") if k in r}, "ms": round(ms), "situacion": texto}
                json.dump(out, open(SALIDA, "w"))
                with open(LOG, "a") as f: f.write(json.dumps({**out, "decision": c.get("decision"), "fijo": c.get("fijo")}, ensure_ascii=False) + "\n")
                ult = texto
                if una: print(json.dumps(out, indent=1, ensure_ascii=False)); return
        except FileNotFoundError: pass
        except Exception as e: print(f"   (laya: {str(e)[:80]})")
        time.sleep(2.0)
if __name__ == "__main__": main()
