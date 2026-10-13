# Yakumama: la lógica entera (13 oct 2026)

Dos programas y un modelo. **El grabador** (`grabar_ballena.py`) mira al actor y manda paquetes. **El receptor**
(`receptor_ballena.py`, dentro de Blender) los convierte en la ballena. **El reconocedor** (`modelos/animo_rf.pkl`)
va dentro del grabador y le pone nombre al ánimo que ve. Todo viaja por UDP 9998 a 30 paquetes por segundo.

```
 OAK-D ──► ballena3.py (Huk) ──► grabador ──► paquete ──► receptor (Blender) ──► ballena
 EmotiBit ─────────────────────► grabador        │              │
 (WiFi directo)                      │           │              ├─ cuerpo: COMPORTAMIENTO del ánimo (fotos NOAA)
                                 reconocedor     │              ├─ cara: expresión del ánimo + cara del actor encima
                                 de ánimo ───────┘              ├─ aletas: manos del actor + aleteo del ánimo
                                                                ├─ pulso: latido, tempo, energía, tensión
 tomas grabadas ──► reproducir.py ──► paquete (igual) ───────────┴─ piel: color del ánimo
```

## 1. Sentidos (lo que entra en cada paquete)

| sentido | de dónde | campos | para qué |
|---|---|---|---|
| cara del actor | OAK-D → FaceMesh + Face Landmarker | `head_yaw/pitch`, `jaw_open`, `blink`, `brow_up/down`, `mouth_sad/smile`, `eye_yaw/pitch`, 51 `face_*` | cabeza, boca, párpados, cejas, mirada |
| manos | OAK-D → MediaPipe Hands | `l_palm_x/y`, `r_palm_x/y`, `l_depth` | aletas (altura = aleteo, diferencia = ladeo) |
| pulso y piel | EmotiBit por WiFi (`emotibit_cliente.py`) | `emotibit_hr`, `emotibit_eda`, `emotibit_therm`, ppg, acc/gyro | latido, tempo, energía, tensión |
| ánimo del actor | reconocedor (ventanas de 2 s) | `actor_animo` + `actor_<ánimo>` | qué comportamiento hace el cuerpo |
| entorno | ballena3 | `scene_color`, `water`, `temp`, `humidity`, joystick | ánimo por color, nado (cuando no hay actor) |
| cerebro | Qwen vía ollama (ballena3 / yakumama_alma) | `whale_<ánimo>` ×10 | ánimo cuando no hay actor y el panel tiene Brain activo; poemas y memorias |
| modo | teclas / panel web | `solo_cara` (1 cuerpo quieto, 2 + cabeza fija), `anclada` | qué parte del cuerpo se mueve |

El grabador **calibra** la cara respecto al neutral (`n`), suaviza, y solo manda EmotiBit si llegó un dato hace < 2 s.
Si no hay cara (OAK sin ver al actor), los campos de cara no cambian y el receptor lo nota (`cara_actor`).

## 2. De dónde sale el ánimo (prioridad, de arriba abajo)

1. **Menú Comportamiento del panel** (si no está en Automático): manda sobre todo. Un `Reproducir` lo devuelve a Automático.
2. **`actor_animo`** del paquete: el reconocedor en vivo, o la etiqueta de la toma al reproducir. Un solo ánimo, entero.
3. **Cerebro Qwen** (`whale_*`), solo si Brain está activado en el panel: mezcla 30 %.
4. **Color de la escena y agua** (el mapa de Brian: rojo angry, naranja playful, amarillo curious, verde feeding,
   cian surfacing, azul calm, violeta singing, rosa alert, blanco diving, negro sad) + pistas de la cara (sonrisa → playful…).

El ánimo elegido se llama `dominant`. El panel, en **Sentidos**, muestra cuál es y de cuál de estas cuatro fuentes salió.

## 3. Cuerpo: comportamientos (referencias/noaa_comportamientos)

Cada ánimo es una función del tiempo, no una pose. Devuelve: cabeceo y rolido del root, giro, cabeza, curva de los
6 huesos de la columna, inclinación de la cola, aleteo y ladeo de las aletas, boca, **cara** (párpados, angry, sad,
asombrado), **mirada**, **spin** (vueltas) y **depth** (sube/baja).

| ánimo | cuerpo | cara | extra |
|---|---|---|---|
| calm | logging: quieta, respira | párpados a medias | — |
| singing | cabeza abajo, casi inmóvil | ojos casi cerrados, boca al ritmo | baja un poco |
| playful | golpes de aleta, rolido | ojos muy abiertos, mirada arriba | breach cada 12 s con 2 vueltas, sube |
| curious | spyhop: vertical, gira | ojos muy abiertos, mirada que busca | sube |
| feeding | embestida boca abierta, filtra ondulando | mirada abajo | — |
| sad | cabeza y cola caídas | triste, párpados caídos, mirada al fondo | baja |
| angry | lobtail: cola arriba y golpe | furiosa, mirada fija | boca al golpe |
| alert | lomo arqueado, cabeza escanea | ojos abiertos, mirada que barre | — |
| diving | nariz abajo, cola vertical | ojos entornados, mirada abajo | **baja 1.3 y vuelve** |
| surfacing | sube, sopla, se nivela | ojos abiertos al soplar | **sube 0.7** |

Límites fijos para que nunca se arquee hacia atrás ni meta las aletas en el cuerpo (`LIMITES`).
El reloj del comportamiento va a la velocidad del pulso del actor (50 lpm = 0.7×, 130 lpm = 1.6×).

## 4. Capas sobre el cuerpo

- **Cara del actor encima de la del ánimo**: párpados, angry, sad, asombrado = `max(actor, ánimo)`; boca = la del
  actor con la del ánimo por debajo; mirada = la del actor + 60 % de la del ánimo; cabeza = la del actor (hasta ~14°).
- **Manos → aletas**: altura de cada mano = aleteo de su aleta; una más alta que la otra = ladeo; se suma al aleteo del ánimo.
- **Pulso**: latido que recorre la columna (4 %), tempo del comportamiento, energía en aletas y nado, tensión (eda) en la cabeza.
- **Piel**: vira en ~2 s al color del ánimo (mismo mapa de Brian, aclarado).
- **Modos**: `solo_cara` deja el cuerpo en reposo (solo cara y aletas); `cabeza fija` además no mueve la cabeza;
  `anclada` mueve el cuerpo pero no viaja (sí sube/baja por `depth`).

## 5. Controles

| dónde | qué |
|---|---|
| Panel web `localhost:8765` (grabador) | ánimo a grabar, grabar/guardar, neutral, modo, anclada, lo que la ballena ve, pulso/piel en vivo |
| Panel Ballena en Blender (N) | **Tomas grabadas** (elegir y reproducir), **Sentidos** (qué le llega y de dónde sale el ánimo), **Comportamiento** (forzar uno), sliders viejos (Mouth, Tongue, Brain, Color Follow, joystick virtual, volúmenes) |
| Teclas en la terminal del grabador | lo mismo que el panel web (`1-0 g f n c a t r q`) |

Los ajustes del panel de Blender **se conservan** al volver a ejecutar el script (antes se perdían: re-registrar la
clase los ponía en sus valores por defecto; ahora se guardan y restauran). El receptor se carga solo al abrir
`whale.blend` (add-on `yakumama_receptor`) y se recarga solo cuando cambia el archivo.

## 6. Datos y aprendizaje

- Cada toma: `datasets/cara/<ánimo>_NNN.jsonl` + `datasets/cuerpo/<ánimo>_NNN.jsonl`, 30 líneas/s, mismo `t`.
- `entrenar_animo.py` → `modelos/animo_rf.pkl`: ventanas de 2 s de 51 blendshapes + cabeza + manos. Dentro de sesión
  ~75 % de acierto; entre sesiones ~5 %: **hace falta una tercera sesión** (cámara de frente, neutral, misma silla)
  antes de grabar a otros actores, y con otro actor habrá que grabar sus tomas y reentrenar con todos.
- Lo que la ballena todavía no aprende de los datos: la columna y la cola. Eso viene de los comportamientos NOAA.

## 7. Qwen (pendiente de decidir)

Hoy Qwen adivina el ánimo por sensores y escribe memorias/poemas (Huk). Propuesta: cuando el actor está, el actor
manda y Qwen recibe su ánimo y su pulso para que los poemas respondan; cuando no está, Qwen elige el ánimo y el
receptor lo interpreta. Requiere tocar el prompt en `ballena3.py` / `yakumama_alma.py` (Huk).
