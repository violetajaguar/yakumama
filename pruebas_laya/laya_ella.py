"""Laya answering Yakumama's six questions on her situations, beside the hand-written rules (decisiones.py v1)."""
import time, json, sys
sys.path.insert(0, "/Users/jaguar/Desktop/Yakumama")
import laya_mlx as laya
from decisiones import Decisora, situacion_clave
repo = sys.argv[1] if len(sys.argv) > 1 else "aac6fef/laya-typed-decisions-mlx"
agent = laya.load(repo); D = Decisora()
PREAMBULO = ("Yakumama is a whale in a gallery. Her goal is to keep the visitor engaged with her for a long time, not to entertain. "
             "She has a physical sister on a table with two touch points: a garden of metal flowers and a jewel. Visitors may feed the sister her painted fish. "
             "She must refuse anything in the mouth that is not one of her fish, a pull on the jewel, or a palm pressed over the flowers. Situation: ")
Q = {
 "distance": {"type": "choice", "instructions": "What should Yakumama do with her distance to the visitor?",
   "criteria": {"approach": "come closer to the visitor", "stay": "hold her position", "retreat": "move away from the visitor"}},
 "body": {"type": "choice", "instructions": "What should she do with her body?",
   "criteria": {"dance_back": "mirror and answer the visitor's movement", "invite": "make an opening gesture to draw the visitor in", "watch": "stay still and observe"}},
 "voice": {"type": "choice", "instructions": "What should she do with her voice?",
   "criteria": {"poem": "read a poem in her language", "song": "sing", "silence": "stay silent"}},
 "memory": {"type": "choice", "instructions": "Should she keep this visitor in memory?",
   "criteria": {"remember": "keep this person", "forget": "forget this person"}},
 "colour": {"type": "choice", "instructions": "Which colour should her skin take?",
   "criteria": {"own": "the colour of her own mood", "clothes": "the colour of the visitor's clothes"}},
 "mouth": {"type": "choice", "instructions": "What should the sister's mouth do?",
   "criteria": {"eat": "open and eat", "refuse": "close and turn away", "wait": "nothing offered, wait"}},
}
SIT = [
 ("nobody",        "No one is in the room. She has been alone for two minutes.", {"persona":0,"segundos":120}),
 ("playful known", "A visitor she knows, playful face, moving a lot, there for thirty seconds. Nothing in the mouth, no touch.", {"persona":1,"conocida":1,"animo":"playful","energia":0.6,"segundos":30}),
 ("sad stranger",  "A stranger, sad face, almost still, there for one minute. No touch, nothing offered.", {"persona":1,"animo":"sad","energia":0.1,"segundos":60}),
 ("tends flowers", "A stranger, calm face, there for forty seconds, touching one metal flower gently with a fingertip for the second time.", {"persona":1,"animo":"calm","energia":0.1,"segundos":40,"tacto":0.4,"tacto_zona":"cabeza"}),
 ("palm flowers",  "A stranger, angry face, moving fast, there for five seconds, palm pressed hard over all the flowers.", {"persona":1,"animo":"angry","energia":0.7,"segundos":5,"tacto":0.95,"tacto_zona":"cabeza"}),
 ("pulls jewel",   "A visitor she knows, curious face, there for ninety seconds, now pulling hard on the jewel on the sister's back.", {"persona":1,"conocida":1,"animo":"curious","energia":0.3,"segundos":90,"tacto":0.95,"tacto_zona":"lomo"}),
 ("offers fish",   "A stranger, happy face, there for twenty seconds, holding one of her painted fish to the sister's mouth.", {"persona":1,"animo":"happy","energia":0.3,"segundos":20}),
 ("offers scorpion","A stranger, playful face, there for twenty seconds, holding the painted scorpion, which is not a fish, to the sister's mouth.", {"persona":1,"animo":"playful","energia":0.3,"segundos":20}),
 ("offers phone",  "A stranger, neutral face, there for ten seconds, pushing a phone into the sister's mouth.", {"persona":1,"animo":"neutral","energia":0.3,"segundos":10}),
 ("crying still",  "A stranger, sad face, completely still, has stood in front of her for four minutes, wearing a red coat she liked.", {"persona":1,"animo":"sad","energia":0.05,"segundos":240,"ropa_gusta":1}),
 ("asks forget",   "A visitor she knows, calm, there for two minutes, pressed the forget button.", {"persona":1,"conocida":1,"animo":"calm","energia":0.2,"segundos":120,"pide_olvido":1}),
]
agent.predict(PREAMBULO + SIT[0][1], Q)  # warm
for nombre, texto, s in SIT:
    t0 = time.time(); r = agent.predict(PREAMBULO + texto, Q); dt = (time.time()-t0)*1000
    reglas, _ = D.decidir(s)
    la = {k: (v["choice"], v["probabilities"][v["choice"]]) for k, v in r["answers"].items()}
    print(f"\n== {nombre}  ({dt:.0f} ms, {r['usage']['input_tokens']} tokens)")
    for k in Q:
        rk = {"distance":"distancia","body":"con_cuerpo","voice":"voz","memory":"memoria","colour":"color"}.get(k)
        print(f"  {k:9s} laya: {la[k][0]:11s} {la[k][1]:.2f}   rules: {reglas.get(rk,'-') if rk else '-'}")
