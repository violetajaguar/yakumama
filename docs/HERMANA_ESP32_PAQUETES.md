# The sister in Barcelona: three ESP32s, two cameras, the packets · for Dan · 18 October 2026

What Violeta and I settled last night, so your side and hers fit. Her brain stays on the Mac and makes every decision as a fixed
choice with a probability, never a sentence. Your side feels, moves and glows. Nothing of a visitor's face ever reaches your machine.

## The room

- The digital whale on the screen; **her eye on a tripod beside the screen**, looking down the table. It runs on the Mac. It sees
  faces, bodies, distance, clothes, who is known, and what is held over the table (the fish). The mirror under the table is in its
  frame and is ignored.
- **The sister on the table**, over the white base, among the cactuses. Translucent body, lights inside. Two touch points only:
  the **garden** (Jicara's metal flowers on wire stems, the hand-made triangle) and the **jewel** on her back. Tail and fins move
  but are never touched. The mouth takes her painted fish.
- **The joystick** moves the camera in TouchDesigner. The visitor leads the eye; she leads the body.
- Headphones: her poem, for the one who puts them on.

## Her six questions (every 4 s, from `decisiones.py`)

| question | answers |
|---|---|
| distance | approach · stay · retreat |
| body | dance back · invite · watch |
| voice | poem · song · silence |
| memory | remember · forget |
| colour | her own · the visitor's clothes |
| mouth | eat · refuse · wait |

Her objective is to keep people **engaged, not entertained**: the nightly learning rewards time weighted late (minute four counts,
second ten does not), distance that shrinks, her touch words used, stillness of a known face, time on the joystick, a return on
another day. Crowd, noise and speed count for nothing.

**Three refusals never learn away**: something in the mouth that is not one of her fish; a pull on the jewel; a palm pressed over
the flowers. Each one: tail stops, fins fold, colour out, head turned, silence, and she remembers who. A later gentle touch on the
flowers by the same person is forgiveness. A visitor who presses *forget* is forgotten absolutely.

## The three ESP32s

None of them talk to each other. Feeling goes up to her; moving and glowing come down from her. The sister needs no computer.

**1. Feels** (keep it away from the motors: a servo twitch on the same board ruins a capacitive reading).
- Flowers and jewel on the ESP32's native touch pads, read as **analog** values (approach before contact, fingertip vs palm).
  Usable pads: T0 GPIO4, T2 GPIO2, T3 GPIO15, T4 GPIO13, T5 GPIO12, T6 GPIO14, T7 GPIO27, T8 GPIO33, T9 GPIO32 (T1/GPIO0 is the
  boot pin, skip it). Suggested: **jewel on T0**, **flowers on T2…T9**, one stem per pad; with more than eight flowers, two stems
  per pad. Calibrate each pad's idle value at boot; send `(idle − raw) / (idle − full_touch)` clamped 0..1.
- Sends to the Mac, **UDP 9995**, about 20 times a second, one JSON:

```
{"flores": [0.0, 0.42, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],   one value per stem, 0..1
 "joya": 0.05, "joya_tiron": 0,                        jewel 0..1; joya_tiron 1 if the jewel is pulled (if it can give, or from a strain pad)
 "presencia": 1}                                       someone near 0..1 (optional)
```

**2. Moves.** Servos for the fins (link by link if you have them) and the fan that spins the tail. Listens to her stream (below).

**3. Glows.** The LED strips inside the body: colour per mood, the heartbeat, the ~1 s fade. Own power. Listens to the same stream.

## What she sends: UDP 9994, 30/s (unchanged, plus her decisions)

Everything in `PROTOCOLO.md` still holds: `animo color turbina latido pulso pitch roll yaw x y z jaw flap fluke aleta_l aleta_r blink …`.
Two fields matter for the sister now:

- `decision`: `{"distancia": "alejarse", "con_cuerpo": "observar", "voz": "silencio", "memoria": "recordar", "color": "propio", "boca": "rehusar"}`
- `decision_prob`: the probability of every answer.

For the body you need not read `decision` at all: the packet already carries the result. `come = 1` while she eats (jaw at its
maximum, `turbina` ×1.5); `rehusa = 1` while she refuses (`jaw 0`, `turbina 0`, `flap 0`, `color` almost black, `latido 0.1`, and she
turns away through `yaw`). Both are 0 otherwise. The refusals also arrive as mood: a pull on the jewel
is `angry`, trampled flowers are `sad`, a fish is `feeding`, a non-fish is `alert`.

## From TouchDesigner back to her (same port 9995)

She needs to know when she is being looked at and from where, so the digital whale can face the visitor's eye or hide her face:

```
{"camara": {"cerca": 0.8, "mira": 1},   cerca: how close the TD camera is to her (0 far .. 1 on her face); mira: 1 if she is in the view
 "palanca": 1}                           1 while the joystick is being moved, 0 when idle (she accumulates seconds on it)
```
Send it ~10/s, or only on change. If the stick has a button, keep it for one thing: the visitor asking her for a poem. She may say no.

## Temporary: the mouth, until her eye recognises the fish

The fish recogniser (fish / not a fish / nothing, from her eye) is next on my side. Until then you can test the mouth by hand with
the same port: `{"ofrenda": "pez", "ofrenda_p": 0.9}` or `{"ofrenda": "no_pez"}` or `{"ofrenda": "nada"}`. She eats a fish she is sure of
(her appetite: picky right after eating, hungry after ten minutes), refuses anything else, and a third non-fish in a row marks the
person as rough.

## A crowd (MozFest premiere)

Her eye now runs the jaguar's camera with the cloud removed (`ojo_multitud.py`): OpenPose on the OAK-D for everyone in view and a
stereo depth per person, so she counts the room and knows each person's distance and whether a hand is on the table. She attends
ONE person at a time, chosen in this order: whoever is feeding her, whoever is touching her jewel crown, a face she knows, whoever
tends the flowers, whoever holds the joystick, the closest still face, the closest. She stays with her chosen one until they leave;
only feeding, the crown or a known face take her away. The packet carries `personas_n`, `foco_razon` (why she chose) and
`distancia_m` (her chosen one's distance). The crowd is never a reward: she learns from the one she chose, not from the room.
In a crowd her poem goes to the headphones; the song may be in the room.

## What she keeps about people

Only numbers in `modelos/decisiones_personas.json`: a face id from her memory, visits, fish given, whether and when they were rough.
Never an image. The forget button removes the id.
