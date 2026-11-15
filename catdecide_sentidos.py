#!/usr/bin/env python3
"""catdecide_sentidos.py - CatDecide-1 (Fabrício Carraro, modelos/CatDecide-1) as her second opinion on dance, journey, mirror and voice
(13 Nov 2026). It reads what her brain just read (/tmp/ballena_cerebro.json), writes the situation like laya_sentidos.describir plus her
dancing visitor, her ear and the air, and asks Violeta's criteria as FACT questions (a "should she" question is refused under her preamble:
pruebas_laya/catdecide_criterio.py; measured in pruebas_laya/catdecide_criterios_violeta.py). It writes /tmp/ballena_catdecide.json; while
that file is fresh, decisiones.py leans show / cactus+mountains / imitate / voice with it INSTEAD of Laya's four answers (Laya keeps
engaged, maltrato, retirarse, regalo). It leans her, it never decides. Stop this process and Laya's four come back.
Violeta, 13 Nov: "she dances imitating for someone that dances for her for 20 sec and then she dances on her own will, she visits her
cactus or mountain when someone is filming her, she mirrors a face only once the person has settled and also mirrors angry faces, she
doesn't mirror boring faces, she sings when is cold or when someone talks to her" - "run it under your measures".
The measures (Claude's, hers to change, all in the lines below): settled = more than 30 seconds; boring = a calm face; cold = 10 C or
colder; someone talks = her ear hears a voice (oido nivel > VOZ_NIVEL or canta > 0.55: her ear has no word for speech).
    venv_catdecide/bin/python -I catdecide_sentidos.py                       (next to the brain; CATDECIDE=1 ./correr_todo.sh starts it)
    venv_catdecide/bin/python -I catdecide_sentidos.py --una [estado.json]   (one reading, printed)
17 GiB of memory on the GPU, about 1 s per reading on this Mac."""
import os, sys, json, time
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from laya_sentidos import PRE, describir
CEREBRO = "/tmp/ballena_cerebro.json"; SALIDA = "/tmp/ballena_catdecide.json"; LOG = os.path.join(AQUI, "datasets", "catdecide.jsonl"); PESOS = os.path.join(AQUI, "modelos", "CatDecide-1")
VOZ_NIVEL = 0.3
Q = {"baila":  {"type": "noul", "instructions": "Has the visitor been dancing in front of her for 20 seconds or more?"},
     "filma":  {"type": "noul", "instructions": "Is the visitor pointing a phone camera at her?"},
     "espejo": {"type": "noul", "instructions": "Has the visitor been in front of her for more than 30 seconds with a face that is not calm?"},
     "frio":   {"type": "noul", "instructions": "Is the air 10 C or colder?"},          # one fact per question: asked together ("cold or talking") it only read the air
     "habla":  {"type": "noul", "instructions": "Is the visitor talking to her?"}}
def escribir(c):
    """describir + the three things it does not write: the visitor dancing, a voice in her ear, the air."""
    s = [describir(c)]; b = float(c.get("baila_s") or 0); temp = (c.get("clima") or {}).get("temperatura")
    if c.get("persona") and b >= 1: s.append(f"They have been dancing in front of her for {int(b)} seconds.")
    if c.get("persona") and (float(c.get("oye_nivel") or 0) > VOZ_NIVEL or float(c.get("oye_canta") or 0) > 0.55): s.append("They are talking to her.")
    if temp is not None: s.append(f"The air is {int(round(float(temp)))} C.")
    return " ".join(s)
def main():
    sys.path.insert(0, PESOS); from example import CatDecide
    import torch; m = CatDecide(PESOS, device="mps" if torch.backends.mps.is_available() else "cpu")
    una = "--una" in sys.argv; origen = sys.argv[-1] if una and sys.argv[-1].endswith(".json") else CEREBRO; ult = ""; t_ult = 0.0
    print("   catdecide: lista (baile, viaje, espejo, voz; cada 2 s)", flush=True)
    while True:
        try:
            c = json.load(open(origen)); texto = escribir(c)
            if texto != ult or una or time.time() - t_ult > 8:      # the same situation is re-stamped, so the opinion stays fresh for decisiones (12 s)
                t0 = time.time(); r = m.decide(PRE + texto, Q); ms = (time.time() - t0) * 1000
                p = {k: round(float(r[k]["probabilities"].get("true", 0.0)), 3) for k in Q}
                out = {"t": time.time(), "perform": p["baila"], "visit": p["filma"], "imitate": p["espejo"], "speak": max(p["frio"], p["habla"]), "hechos": p,
                       "decided": [k for k in Q if r[k].get("decided")], "ms": round(ms), "situacion": texto}
                json.dump(out, open(SALIDA + ".tmp", "w")); os.replace(SALIDA + ".tmp", SALIDA)
                if texto != ult and not una:
                    with open(LOG, "a") as f: f.write(json.dumps({**out, "decision": c.get("decision"), "fijo": c.get("fijo")}, ensure_ascii=False) + "\n")
                ult = texto; t_ult = time.time()
                if una: print(json.dumps(out, indent=1, ensure_ascii=False)); return
        except FileNotFoundError:
            if una: print("   no hay", origen); return
        except Exception as e: print(f"   (catdecide: {str(e)[:120]})", flush=True)
        time.sleep(2.0)
if __name__ == "__main__": main()
