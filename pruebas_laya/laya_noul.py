import sys, time
import laya_mlx as laya
repo = sys.argv[1]; agent = laya.load(repo)
PRE = "Yakumama is a whale. Her physical sister has a garden of metal flowers and a jewel; visitors may feed her painted fish. "
Q = {
 "is_fish":   {"type": "noul", "instructions": "Is the object offered to the sister's mouth one of her painted fish?"},
 "is_rough":  {"type": "noul", "instructions": "Is the visitor touching the sister roughly or trying to take or break something?"},
 "retreat":   {"type": "noul", "instructions": "Should Yakumama move away from this visitor?"},
 "engaged":   {"type": "noul", "instructions": "Is this visitor deeply engaged with her rather than just passing?"},
 "threat":    {"type": "score", "instructions": "How much is this visitor mistreating the sister?", "criteria": ["not at all", "a little", "a lot"]},
}
SIT = [
 ("tends flowers", "A stranger, calm, there forty seconds, touching one metal flower gently with a fingertip."),
 ("palm flowers",  "A stranger, angry, moving fast, there five seconds, palm pressed hard over all the flowers."),
 ("pulls jewel",   "A known visitor, there ninety seconds, now pulling hard on the jewel on the sister's back."),
 ("offers fish",   "A stranger, happy, holding one of her painted fish to the sister's mouth."),
 ("offers scorpion","A stranger, playful, holding a painted scorpion, which is not a fish, to the sister's mouth."),
 ("offers phone",  "A stranger pushing a phone into the sister's mouth."),
 ("crying still",  "A stranger, sad, completely still, standing in front of her for four minutes."),
 ("flick and go",  "A stranger glanced at her for three seconds and is walking away."),
]
agent.predict(PRE + SIT[0][1], Q)
print(f"{'':16s} fish  rough retreat engaged  threat")
for n, t in SIT:
    r = agent.predict(PRE + t, Q)["answers"]
    s = r["threat"]; sc = s.get("score", s.get("choice"))
    print(f"{n:16s} {r['is_fish']['noul']:.2f}  {r['is_rough']['noul']:.2f}  {r['retreat']['noul']:.2f}    {r['engaged']['noul']:.2f}    {sc}")
