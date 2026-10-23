# Yakumama en TouchDesigner, en esta Mac (desde el 20 oct 2026)

El proyecto de TD vino del PC de Dan (`Yaku_PC_2026-10-20.zip`, 3.6 GB, sha256 verificado) y vive en
`fuentes/Yaku_PC_2026-10-20/Paqarina_TD/` (esa carpeta NO va al git: es de Dan y pesa).
TouchDesigner instalado: 2025.33230 (el proyecto pide > 2025.30280). El `.toe` vigente es `Paqarina.toe` (19 oct 23:12);
`Paqarina_safe.toe` es la copia del 4 oct.

## Correr
    bash ~/Desktop/Yakumama/correr_td.sh            # cerebro en --idle (viva sin publico) + abre TD
    bash ~/Desktop/Yakumama/correr_td.sh --run      # con comportamientos; --run --brain si Ollama esta arriba

El cerebro es `ballena_td.py` con su propio entorno `venv_td/` (python-osc, numpy, opencv, depthai, sounddevice).
NO usa `venv/` (ese es el de Huk y no se toca). Manda OSC a 127.0.0.1:7000 a 30 fps; control en UDP 5006.
Probado el 20 oct: arranca en la Mac, 26.7 fps, rig de 30 huesos y 4 shape keys cargado.

## La primera vez en TD (una sola vez por maquina)
1. Con el cerebro ya corriendo, TD abre `Paqarina.toe`.
2. En TD: Text DAT -> cargar `td/relocate_paths.py` -> Run Script. Repunta las rutas absolutas del PC
   (`C:/Users/Daniel/Documents/Paqarina_TD/...`: el FBX de la ballena, la sal, las montanas, los cactus) a esta carpeta.
   Imprime que cambio y que falta. Re-correrlo no hace dano.
3. Si queda una cruz roja o parametros en error: `td/td_bind_osc.py` (Text DAT -> Run Script).
4. Guardar el .toe (queda con rutas de esta Mac).

## Lo que no esta en esta Mac
- Camara OAK-D (`ballena_crowd.py`): solo si esta enchufada.
- La escultura (ESP32, `ballena_joy.py --port`): el puerto en Mac es `/dev/tty.usbserial-*`, no COM3.
- Ollama con `qwen35-local` (12 GB): el PC lo tomaba del Mac Mini (192.168.50.104). Sin Ollama ella nada por reflejos.
- `Neural_Net/para_Violeta_salar_2026-10-18.zip` llego corrupto dentro del zip (CRC); el resto se extrajo bien.
- Los `td/setup_*.py` traen rutas de Windows (SHADER_DIR, OBJ_PATH): solo hacen falta para reconstruir la escena, no para arrancar.

Detalle de todo: `Paqarina_TD/docs/RUNNING.md` (PC) y `docs/touchdesigner_setup.md`.

## 20 oct, tarde — dos cambios para que corra sin tocar TD
- **Rutas del PC sin relocate:** dentro de `Paqarina_TD/` hay una carpeta `C:/Users/Daniel/Documents/` con un enlace
  `Paqarina_TD -> (esta carpeta)`. Como en Mac `C:/...` es una ruta relativa al proyecto, las rutas absolutas del PC que
  guarda el `.toe` (FBX, salt.obj, montañas, cactus) resuelven solas. `td/relocate_paths.py` sigue siendo la forma limpia
  (y deja el .toe con rutas Mac); el enlace es para arrancar ya.
- **La red de movimiento es la de la Mac, entrenada con Sanam** (`modelos/movimiento_pesos.npz` del 17 oct: entrada 28 =
  24 + 4 actores violeta/sanam/suri/dan, con el `yakumama_modelo.py` que sabe de actores). El paquete del PC traía la del
  14 oct (24 entradas, sin actores). Copiadas a `Paqarina_TD/Neural_Net/Yakumama/` (la vieja en `_viejo_14oct/`). El cerebro
  de TD la carga con `actor=None` = estilo promedio de los cuatro; el log dice `Net: her motion net loaded (5 layers)` y
  los sesgos de ceja cambian (0.44/0.13 contra 0.17/0.38 de la vieja), señal de que es la nueva. Cuando se reentrene en la
  Mac (`entrenar_movimiento.py`), volver a copiar esos dos archivos.

## 20 oct, 16:00 — revisión del traslado y lo que falta enchufar

**Nada llegó corrupto.** El paquete trae su propio git (commit `44fdee5`, el proyecto tal como salió del PC): `git fsck` limpio y
`git status` solo muestra lo que cambiamos aquí (la red de Sanam, `Paqarina_mac.toe`, la carpeta `C:/`). Los archivos que ese git
no cubre se revisaron a mano: `whale.fbx/glb/blend`, `cactus7.blend` y el blob de la OAK-D tienen cabecera buena; los dos
`kokoro-v1.0.onnx`, `jepa_datos.npz` y los pesos de Laya (`model.safetensors`, 843 MB) tienen el mismo sha256 que las copias de esta
Mac. `Violeta_Code/YakuMama.zip` pasa `unzip -t`. Dos cosas que parecían daño y no lo son:
- `Neural_Net/para_Violeta_salar_2026-10-18.zip` llegó de 0 bytes: se restauró desde el git del paquete (`git checkout`, 951 KB, 39 archivos,
  `unzip -t` sin errores).
- El wav de Björk aparece como "borrado + nuevo" en `git status`: el git del PC guardó el nombre con la ö rota; el archivo es el mismo y está sano.

**TD renderiza.** `Paqarina_mac.toe` (guardado 15:44 por `relocate_paths.py`) está abierto en el monitor Samsung: ella sobre el salar con
el Tunupa detrás, 60 fps. El `.toe` tiene cambios sin guardar (asterisco en el título): guardar antes de cerrar TD.

**La mente en la Mac mini, probada.** La mini es `violetas-mini`, **192.168.50.104** por cable (MAC d0:11:e5:03:a1:cb), con Ollama
sirviendo `qwen35-local` (12 GB, el de Dan) y `qwen3.5:9b-q8_0`. Esta Mac tiene que estar en la red **UNF (192.168.50.x)**: en otra red
(192.168.1.x) la mini no responde. `correr_td.sh` ya exporta `BALLENA_OLLAMA=192.168.50.104:11434`; con `--run --brain` el log dice
`Cognition: ollama reachable @ http://192.168.50.104:11434/api/chat` y luego `Brain tick #1: calm=0.92 ...` (probado 16:00, 2.9 s por
respuesta). Ojo: con `--brain` el alma escribe en `Violeta_Code/YakuMama/Huk/yakumama_{lexico,poemas,memoria}.json`; lo que escribió en la
prueba (sala vacía) se revirtió con git. Sin público, dejarla en `--idle`. En la mini los puertos 22/5900 están cerrados: lo que haya que
instalar allí (Laya, su ojo, `cerebro_ballena.py`, ver `docs/DOS_MAQUINAS_DAN.md` §A) se hace sentado en la mini.

**Lo que aún no está enchufado (20 oct 16:00) y qué hacer cuando esté:**
1. **Proyector (Epson, HDMI/USB-C).** Conectarlo, en TD: Text DAT → `td/setup_projector.py` → Run Script. Imprime los monitores como TD
   los numera y abre `window1` sin bordes en el Epson (por nombre; si no, en el monitor no principal de 1920x1080 — añadido hoy para la Mac).
   Ahora mismo hay dos monitores externos (Samsung 1680x1050, MSI 1920x1080): si el MSI sigue puesto, decir en el script cuál es el proyector.
2. **Dos OAK-D.** Ambas por USB3. Una es de la sala (`ballena_crowd.py`, cuenta personas → cerebro 5005), la otra es su ojo
   (`grabar_ballena.py` con `venv/`). Primero `venv_td/bin/python ballena_crowd.py --check` (lista los seriales); luego
   `BALLENA_OAK_MXID=<serial> venv_td/bin/python ballena_crowd.py` para que la sala tome ESA cámara y el ojo la otra. Un proceso por
   cámara. `venv_td` quedó con `depthai 2.32.0.0` (el 3.11 que tenía no sirve: el script usa la API 2.x) y `pyserial`.
3. **Puente ESP32 (la tabla con palanca y tiras de cobre, USB).** En Mac el puerto es `/dev/cu.usbserial-*` (CP2102), no COM3:
   `venv_td/bin/python ballena_joy.py --port /dev/cu.usbserial-XXXX --color`. El autodetectar solo toma un CP210x y rechaza un CH340 (el
   cable de la ballena impresa: abrirlo la resetea). La pantalla de la mesa: `ballena_vista.py --serial /dev/cu.usbserial-YYYY --prueba`.
   Los ESP32 de la hermana (siente / mueve / brilla) van por WiFi a 9995 de la Mac que corra `grabar_ballena.py` (`docs/HERMANA_ESP32_PAQUETES.md`).
4. **Orden del día completo:** `bash correr_td.sh --run --brain` (cerebro con la mini + TD) → `ballena_crowd.py` → `ballena_joy.py --port ...`
   → en TD `setup_projector.py`. Panel de operador: `venv_td/bin/python ballena_panel.py` (tkinter: hoy se instaló `brew install python-tk@3.11`, ya importa desde venv_td).

## 20 oct, 16:20 — las dos OAK-D leídas
- **OAK-D Pro = `14442C10214FDBD600`** (tiene proyector láser: mejor profundidad en sala oscura → la sala, `ballena_crowd.py`).
- **OAK-D Lite = `18443010319BC90F00`** (base estéreo 7.5 cm, sin láser → su ojo en el trípode, `grabar_ballena.py`, que es sobre todo RGB).
- Las dos dieron color a 15 fps y profundidad a 10 fps desde `venv_td` (depthai 2.32). Pero estaban colgadas de un **hub USB 2** (GenesysLogic,
  480 Mbps compartidos): el pipeline completo (color + estéreo + red) en la Pro se cayó al primer intento y después la Pro **desapareció del
  bus** (la Lite siguió). La Pro consume más al arrancar (láser): enchufarla **directa a un puerto de la Mac o a un hub USB 3 con fuente**,
  nunca las dos en el mismo hub USB 2. Si desaparece: desenchufar y volver a enchufar.
- Orden: primero `BALLENA_OAK_MXID=14442C10214FDBD600 venv_td/bin/python ballena_crowd.py` (toma la Pro); después `venv/bin/python
  grabar_ballena.py` (ballena3 abre la primera cámara libre: la Lite). Al revés, el ojo se queda con la Pro.

## 20 oct, 16:40 — puente ESP32 y sala probados
- **Puente ESP32 (CP2102) = `/dev/cu.usbserial-0001`** (VID:PID 10C4:EA60). `ballena_joy.py --port /dev/cu.usbserial-0001 --raw` lee la tabla:
  palanca + 3 tiras de cobre a 29 Hz, centro medido 1802,1830, líneas base de las tiras 46/85/88; la tabla anuncia `BRAIN: driving fins +
  propeller`. Arranque normal: `venv_td/bin/python ballena_joy.py --port /dev/cu.usbserial-0001 --color` (con el cerebro ya en `--run`).
- **La sala** (`BALLENA_OAK_MXID=14442C10214FDBD600 venv_td/bin/python ballena_crowd.py`) manda la percepción a UDP 5005 a ~10/s
  (`user_present, user_count, user_distance, user_lateral, user_motion, scene_color ...`) mientras la Lite entrega 15 fps al mismo tiempo.
  Sigue avisando `USB HIGH (USB2)`: las dos cámaras y el puente cuelgan del mismo hub USB 2. Funciona. La Pro desaparece del bus unos 10 s si se la
  mata de golpe (`kill -9`) y vuelve sola; con poca corriente al arrancar puede no volver (16:05): pasar la Pro a un puerto directo o a un hub USB 3 con fuente.
- Una sola instancia de `ballena_crowd.py`: si una vieja sigue viva reintentando, la nueva dice `ALREADY RUNNING` y sale (`pkill -f ballena_crowd.py`).

## 20 oct, 17:40 — Laya en la mini: el puente ya existe
Dan escribió `laya_puente.py` (19 oct; copiado del paquete a esta carpeta). Lleva los dos archivos de /tmp por la red, sin tocar
`cerebro_ballena.py`, `laya_sentidos.py` ni `decisiones.py`: UDP 9981 (situación → mini) y 9982 (respuesta ← mini); solo librería estándar.
- **Aquí (el cerebro):** `venv/bin/python laya_puente.py pc 192.168.50.104`
- **En la mini:** `python laya_puente.py mac <IP de esta Mac>` — arranca `laya_sentidos.py` solo y reenvía su respuesta cada 2 s. Dan lo dejó en
  `~/DAN/Ballena/laya` y **no se relanza al reiniciar**. Probado 17:50: la mini YA está corriendo ese extremo apuntando a esta Mac
  (192.168.50.172): una situación de prueba a 9981 volvió por 9982 en 157 ms (`engaged 0.61, maltrato 0.48, retirarse 0.14, regalo 0.30`
  para un desconocido tocando una flor). La IP de esta Mac es DHCP: reservarla en el router como la de la mini, o relanzar el extremo
  de la mini con la IP nueva (sentado en ella: no tiene Remote Login).
- Sin el puente (o sin la mini) ella decide igual: `decisiones.py` trata a Laya como ausente pasados 12 s.

## 20 oct, 18:40 — los cambios de Dan a SU código, fusionados e instalados
`cerebro_ballena.py`, `grabar_ballena.py`, `difusion_ballena.py` y tres líneas en `Huk/` (ballena3 `YAKUMAMA_SIN_SERIAL=1`, voz_ella ruta de
voces, alma `YAKUMAMA_OLLAMA`) traen lo que Dan hizo en el PC del 17 al 19 oct (inventa todo el tiempo en un hilo; QUIÉN ESTÁ AQUÍ AHORA:
campos que no llegan en 2 s caducan, cara congelada = cara perdida; los rechazos frenan la cola inventada; LA VISTA; `YAKUMAMA_DIBUJO_PRUEBA`;
`gente` para la pantalla; Ollama por `YAKUMAMA_OLLAMA`/`OLLAMA_MODEL`). Lo de ella del 20 oct (29 ofrendas) se conserva. Qué hay en el paquete:
`docs/PAQUETE_DAN_20oct.md`. Respaldo de lo reemplazado: `entregas/respaldo_pre_merge_20oct/`. Probado: `decisiones.py` (autotest igual),
`cerebro_ballena.py --prueba` 45 s sin errores (H-JEPA + difusión cargan, línea `[sees]`), semillas 19c copiadas a `Huk/palabras/semillas`.
Variables nuevas para el cerebro de ella: `YAKUMAMA_OLLAMA=192.168.50.104:11434 OLLAMA_MODEL=qwen35-local` (poemas e inglés en la mini),
`YAKUMAMA_VISTA=127.0.0.1:4210` (la pantalla), `YAKUMAMA_DIBUJO_PRUEBA=espiral` (dibujo de prueba cada 120 s).

## 20 oct, 19:10 — dispositivos y cadena completa
- **Epson**: conectado por HDMI (`EPSON PJ`, 1920x1080); `window1` de TD ya está a pantalla completa en él (ella sobre el salar, verificado con
  captura 19:05). Si alguna vez vuelve al escritorio: en TD, Text DAT → `td/setup_projector.py` → Run Script.
- **Proyector de mesa D013D (Android, 192.168.50.15)**: responde ping; en su navegador abrir `http://192.168.50.172:8765/ventana` (la
  ventana de ella: poema en su lengua, castellano, inglés, lo que ve y decide). Probado 19:00: `/ventana` responde desde la IP de red (http 200)
  con el grabador corriendo (`--panel-red 1` por defecto; firewall de la Mac apagado). Un mouse USB en el proyector pasa el login de Google.
- **Cadena real probada 18:55**: sala en la Pro (`BALLENA_OAK_MXID=14442C10214FDBD600 ballena_crowd.py`) + grabador en la Lite
  (`YAKUMAMA_SIN_SERIAL=1 venv/bin/python grabar_ballena.py --panel 8765 --espejo 127.0.0.1:9997 ...`): las dos cámaras corren a la vez,
  `OAK-D: running` en las dos. Cerebro fusionado en vivo 40 s: 30 paquetes/s, cuerpo inventado en el 98 %, `she invents calm` 0.9 s tras el ánimo.
- **Difusión: CPU, no MPS.** Medido en esta Mac: 32 s inventados tardan 2.1 s en CPU y 12.6 s en MPS. `difusion_ballena.py` elige
  cuda → cpu (MPS solo con `YAKUMAMA_DIFUSION_DEV=mps`). El orden de Dan (cuda → mps → cpu) era 6x más lento aquí.
- **Pantalla 2.4"**: la placa aún no está enchufada. Cuando esté: `YAKUMAMA_VISTA=127.0.0.1:4210` antes del cerebro de ella y
  `venv_td/bin/python fuentes/.../Paqarina_TD/ballena_vista.py --serial /dev/cu.usbserial-XXXX` (`--prueba` para ver la figura sin cerebro).
- **Pendiente de verificar con gente**: moondream en las manos (ollama local tiene `moondream`), un poema disparado por una visita, la vista en vivo.
- **La palanca llega a ella (20 oct 19:20).** `ballena_td.py --violeta` ya le mandaba a 9995 tacto/zona/presencia cada 0.1 s; ahora también
  `{"camara": {"cerca": 0..1, "mira": 0/1}, "palanca": 0/1}` como pide `docs/DOS_MAQUINAS_DAN.md` §C (cerca: 12 m = 1, 60 m = 0 de la lente a
  ella; mira: ella dentro del FOV horizontal; palanca: la palanca se movió en el último 0.5 s). Probado: 127 paquetes en 15 s, `cerca 0.4` en el
  plano por defecto. Respaldo del ballena_td.py anterior en `entregas/respaldo_pre_merge_20oct/`.
- **`correr_todo.sh`**: arranca TODO en el orden de Dan (sala Pro → ojo Lite + cerebro de ella + puente Laya → puente ESP32 + pantalla + cerebro
  de Dan `--violeta --brain` → TD si no está abierto). `--parar`, `--estado`, `SILENCIO=1` para probar sin voz. `correr_td.sh` queda para TD solo.
- **TODO JUNTO, probado 19:35** (`SILENCIO=1 VISITAS=0 bash correr_todo.sh`): sala en la Pro, su ojo en la Lite (vio una cara: ánimo curious, cuerpo),
  su cerebro inventando y dibujando un zigzag, Laya contestando por la mini (75 respuestas en 2 min), puente ESP32 calibrado, cerebro de Dan
  `--violeta --brain` con Qwen en la mini y `her brain is driving`, ánimos de ella pasando a TD (calm → singing → feeding → curious). Para el show:
  `bash correr_todo.sh` (con voz y visitas). Si el puente dice `Address already in use` en 5007, quedó un `ballena_joy.py` viejo: `--parar` y de nuevo.

## 20 oct, 19:15 — prueba real completa: tres cosas que salieron y se arreglaron
1. **El cerebro de ella se cayó** al primer teléfono alzado mientras cantaba: en singing la cola es la palabra `pulso` y las ramas `comer`/`lente`
   hacían `float()` de eso (bug suyo de antes del merge). Arreglado (`_turb()` en `cerebro_ballena.py`).
2. **TD a tirones.** Causa: `Huk/ballena3.py` (el cerebro viejo dentro del grabador) tiene su propia cognición Qwen cada 5 s, clavada a
   `localhost` + `qwen3.6` (26 GB en la GPU que TD usa para renderizar; en el PC estaba muda porque no había Ollama local). Ahora
   `YAKUMAMA_SIN_QWEN=1` la apaga (el launcher lo pone) y respeta `YAKUMAMA_OLLAMA`/`OLLAMA_MODEL`. Con eso y los modelos locales descargados
   (`curl .../api/generate -d '{"model":"qwen3.6","keep_alive":0}'`) la memoria libre pasó de 23 % a 79 %.
3. **Reparto de Qwen** (launcher): la cognición de Dan en la mini (`qwen35-local`: con el qwen3.6 local y TD en la misma GPU le vencía el
   tiempo 10 de 13 veces); sus poemas también en la mini mientras TD comparta GPU (`ELLA_OLLAMA`, por defecto local qwen3.6: cambiar a
   `ELLA_OLLAMA=192.168.50.104:11434 ELLA_MODEL=qwen35-local` si TD se frena). Laya aquí (`LAYA=aqui`) o por el puente (`LAYA=mini`).
   Audio: todo sale por la salida por defecto del sistema (hoy el JBL Charge 4). Su primer poema con voz en vivo: 19:01 (25 s, Kokoro).
- **Líneas de Nazca una encima de otra (19:40).** `ballena_td.py` guardaba las figuras vivas y el reloj del lienzo solo en memoria: cada
  reinicio del cerebro de Dan (hubo dos esta noche) olvidaba dónde había dibujado y volvía al primer sitio (su casa, (-4,+13) m) mientras TD
  conservaba la línea. Ahora las guarda en `logs/nazca_vivas.json` (`BALLENA_DIB_VIVAS` para otra ruta) y al arrancar las recupera si siguen
  dentro de 20+40 min: no borra el salar y la figura siguiente va a un sitio vecino (62 m). El borrado manual (`dib_clear` del panel) vacía el archivo.
- **moondream local.** El grabador manda los poemas a `YAKUMAMA_OLLAMA` pero moondream (lente apuntando, respaldo del pez) a
  `YAKUMAMA_MOONDREAM` (por defecto `localhost:11434`): la mini no lo tiene (daba 404). El ojo de las manos (`ojo_ofrendas`, 32 clases)
  es local y no usa Ollama.

## 20 oct, 19:50 — las 29 ofrendas, probadas en vivo
- **Reconocimiento**: funciona de punta a punta (ojo → cerebro de ella → ventana → cerebro de Dan): 29 (pez azul cola rosada, reacción 13),
  01 (ciempiés, 1), 24 (pez amarillo púas, 17) vistos con las criaturas reales. Dos cosas que lo tapaban, arregladas: el ojo de las manos solo
  miraba con una cara vista (la cámara estaba por debajo de la cara → ahora también con un cuerpo reciente), y la camiseta amarilla pasaba por
  "hermana dorada" (el detector de color del prototipo dorado del 18 oct: **apagado por defecto**, `YAKUMAMA_HERMANA_ORO=1` lo vuelve; la hermana
  de la mesa no es dorada, cambia de color con ella). El grabador imprime cada mirada: `[ojo manos] clase p=… -> voto`.
- **Pantalla de las 29**: `python3 ventana_ofrendas.py` → http://localhost:8766 (también desde el proyector de mesa en la IP de esta Mac:8766):
  miradas, ofrenda en la boca y su reacción, ánimo, seis respuestas, lo que escribe, lo que renderiza Dan, y las 29 tarjetas (la actual
  encendida, las probadas con ✓ en `logs/ofrendas_probadas.json`).
- **Carrusel sin criaturas**: `venv/bin/python carrusel_ofrendas.py [ids] [--pausa 8]` manda cada ofrenda por 9995 lo que dura su reacción
  y dice si el cerebro la tomó y qué ánimos pasó. Registro de la noche: `logs/carrusel.log`.
- **Movimiento en conflicto**: mientras dura una reacción, la coreografía del ánimo y la decisión acercarse/alejarse ya no tiran de su posición
  (`cerebro_ballena.py`, 19:50): la reacción es dueña de dónde va. Lo que queda del lado de Dan: su render promedia el rumbo 10 s y limita el giro
  a 15°/s (VIOLETA_HEADING_S / VIOLETA_TURN_DPS en ballena_td.py), lo que aplana un susto o un giro rápido.

## 20 oct, 20:05 — por qué se trababa y saltaba, y el carrusel completo
- **Clavada al piso.** En su escenario el salar está ~2.5 unidades bajo z=0 (dibuja "bajo" en z=-1.4); Dan mapeaba su z 1:1 sobre home_y=0 con
  el salar a solo 1.44 m (FLOOR_PY_LEVEL). Cada inmersión o ladeo metía las aletas bajo la sal y el guardián del piso la empujaba (114
  correcciones en 300 líneas, media 0.7 m, máx 3.5 m): traba + salto. `VIOLETA_Z_OFFSET_M` existe en `ballena_td.py` pero queda en **0** (el mapeo de Dan): Violeta vio su movimiento
  fluido en el PC con ese mapeo y no hay registro del PC para comparar cuántas correcciones hacía allá. Es una inferencia mía, no un hecho.
- **El cuarto la aleteaba.** 653 cambios de ánimo en un carrusel: el color de la escena en un borde (feeding ↔ calm ↔ surfacing cada segundo;
  Dan lo vio el 17 oct). En `cerebro_ballena.py` el ánimo del cuarto ahora debe liderar 3 s y dura al menos 8 s (`ESC_CAND_S`, `ESC_HOLD_S`).
- **Se congeló en el carrusel (20:00):** `ZeroDivisionError` en `violeta_world` (dd = 0) mató al cerebro de Dan; TD se quedó en la última pose.
  Guardado con `max(dd, 1e-9)`.
- **Carrusel 29/29:** su cerebro tomó todas las reacciones en 1-2 s (`logs/carrusel.log`). Figuras de Nazca ya se reparten (3 vivas en parches
  distintos). Sigue del lado de Dan: promedio de rumbo 10 s y giro máx 15°/s (aplana un susto).

## 20 oct, 21:10 — el árbitro (mapa de Violeta: tres capas compiten, dos paralelas)
`cerebro_ballena.py`: repertorio (cuerpo base + color aditivo: espejo, osciladores, canto) < ofrenda (receta sobre su propia copia) <
cosquillas (toque vivo en flores/tiras, dura lo que dura el toque). Cada capa con peso en rampa de 0.5 s, el color se apaga bajo una capa
superior, y UN suavizado por canal al final (`ARB_TAU`). Medido con el mismo carrusel (14, 8, 4) escuchando sus paquetes en 9996:

| canal | saltos antes | saltos después | máx paso antes | máx paso después |
|---|---|---|---|---|
| fluke | 183 | 0 | 0.30 | 0.07 |
| depth | 15 | 0 | 0.36 | 0.02 |
| jaw | 9 | 6→0 (boca al comer pasa por el suavizado) | 0.50 | — |
| head | 5 | 0 | 0.32 | 0.05 |
| pitch | 3 | 0 | 0.30 | 0.03 |

Las 3 reacciones se tomaron igual en 1 s. `medir_saltos.py` (scratchpad) escucha un `--salida 127.0.0.1:9996` extra del cerebro.
También del mapa: la ofrenda dura 30 s (`YAKUMAMA_OFRENDA_S`) y otra criatura reemplaza a la que está; la misma no reinicia.
Lo que sigue de TD (Dan): el cruce de 1.5 s y el promedio de rumbo de 10 s se quitan solo con una comparación lado a lado.

## 20 oct, 22:35 — carrusel completo con el árbitro: 29/29
Cada escena de 30 s tomada en 1 s, un solo ánimo por escena (antes: 653 cambios en un carrusel; ahora 03 y 15 tuvieron un parpadeo
playful→calm→playful a mitad, a mirar). Sin errores en ningún cerebro. Además esta noche: una ofrenda interrumpe un dibujo de Nazca y no
empieza uno mientras dura una escena (la 21, la abeja, sí dibuja porque su receta lo pide); la descripción de cada reacción se presenta en
**su ventana** (`/ventana`, el proyector de mesa) como un poema (línea dorada con número y nombre, texto en itálica) mientras dura, y en la
pantalla de ofrendas (`:8766` banner y `:8766/lista`); también va a la superposición de Dan por OSC 7002 (`/ballena/alma/linea` y
`/expresion`), que aparece en el salar cuando se corra `td/setup_alma_text.py` una vez dentro de TD.

## 20 oct, 23:40 — desde cero, con la jerarquía, y un bug que habría callado a la hermana
Todo parado y arrancado con `correr_todo.sh` (TD limpio: 1.8 GB en vez de 22; `dib_clear` por 5006 para que el lienzo y el cerebro arranquen
iguales). Falta en TD: `td/setup_projector.py` desde un Text DAT (el .toe de las 15:44 no guarda la ventana del Epson).
**`simular_jerarquia.py`** actúa la jerarquía por 9995 (sola → ofrenda 29 → cosquillas durante la escena → 14 reemplaza → palma → perdón →
tirón de la joya → no-pez → palanca → sola) e imprime cada 2 s lo que decide. Primera corrida: **ningún toque llegaba al cerebro**: el cerebro de
Dan manda `{"tacto": 0, "zona": "lomo"}` 10 veces por segundo a 9995 (las tiras de la escultura) y el grabador reseteaba flores y joya con
cada paquete que traía `tacto`. En Barcelona los ESP32 de la hermana habrían quedado mudos. Arreglado en `grabar_ballena.py`
(`_leer_retorno`: tres fuentes — tiras, flores, joya — cada paquete actualiza solo la suya; ella siente la más fuerte y fresca, 1.2 s).
Segunda corrida: cosquillas 0.60 en flores durante la escena, palma → rechazo `palma` + rehusar, toque suave → calma y se acerca, tirón →
`tiron` angry rehusar, suelta → calm. Y una palma o un tirón ahora cortan la escena como el no-pez. Durante la prueba apareció un rechazo
`lente` (moondream vio un teléfono): mirar si era real.

## 21 oct, 08:30 — las reacciones como combinaciones de sus 10 movimientos, y vuelos
Violeta: "cuando digo espiral tiene que hacer una espiral en el espacio; movimientos repetitivos, no usa sus 10 movimientos con sus posiciones".
Causa: cada receta era UN ánimo + una oscilación escrita a mano sobre el cuerpo, sin camino en el espacio, y el árbitro apagaba la coreografía
durante la reacción. Ahora (`reacciones_ofrendas.py` FASES/VUELO + `cerebro_ballena.py`):
- cada reacción recorre **fases (movimiento, segundos)** de su repertorio que suman la escena de 30 s; en cada fase manda ese ánimo, con su
  cuerpo inventado y **su coreografía en el espacio encendida**; la receta se dibuja encima.
- **vuelos** con la pluma arriba (figuras_nazca, radio 0.6, rápidos, terminan con la reacción, no gastan el enfriado del dibujo): 8 espiral,
  19 zigzag, 21 espiral, 27 laberinto. Medido (reacción 8): curious 0–12 s volando la espiral (radio 0.39 → 0.88), playful 12–20, feeding
  20–30 con `come 1`.
- una escena **no se repite** mientras la misma criatura siga en la mano (`RO.soltar()` al no haber pez en la boca).
- **Blender** recibe también x, y, z y rumbo por `puente_blender.py` (canales del receptor): los vuelos y la coreografía se ven en Blender.
- **ojo_webcam.py**: el ojo de las manos en la cámara de la Mac (--foto N: `s` guarda una foto en ofrendas_fotos/<carpeta>/, `a` ráfaga);
  reconoció 6/6 criaturas mostradas (flores > 0.9; peces con dientes 0.5–0.8); el escorpión y el 04 SÍ se enviaron (08:11:54 y 08:12:38),
  sus reacciones no se leían. Apagarlo durante un carrusel: lo que vea en cuadro reemplaza la escena.
- Bug de anoche corregido: el puente escribía el ánimo en `/tmp/ballena_animo_prueba.json`, el mismo archivo que el cerebro lee como prueba
  → bucle, ánimo clavado, sin invención. Ahora `/tmp/ballena_animo_blender.json`.
- Para la lista: el receptor de Blender también emite su paquete por 9994 (el puerto del cerebro de Dan): con Blender y TD juntos, Dan
  recibiría dos flujos.

## 21 oct, 09:15 — "que nada pelee con su animación": tres causas y cuatro candados
Violeta vio glitch al cambiar de ánimo dentro de una escena. Medido en sus paquetes: 0 saltos en el cuerpo; 13 saltos en la posición (bordes de
escena, el susto empujándola 0.24/cuadro) → **la posición pasa por el suavizado** (`ARB_TAU_POS` 0.6 s). Después: el ánimo alternaba cada
segundo entre dos escenas → **dos carruseles míos peleaban por su boca** (uno viejo seguía vivo: un proceso en segundo plano ignora SIGINT;
matar con TERM/KILL). Con una sola fuente: escorpión = alert 6 s → sad 10 → calm 14 → feeding, 0 saltos. Candados:
1. `grabar_ballena.py`: **una fuente de ofrendas a la vez** — otra criatura dentro de 3 s del último cambio (`PINGPONG_S`) se rechaza y lo dice.
2. carruseles, simulación y ojo_webcam: **una instancia** (`/tmp/ballena_prueba.lock`) y al parar (TERM/INT) vacían su boca y borran el archivo de ánimo de prueba.
3. `receptor_ballena.py`: **no emite su propio paquete por 9994** mientras su cerebro la mueve por el puente (Dan recibiría dos flujos).
4. `correr_todo.sh --parar` también para carruseles, simulación, ojo_webcam y puente.
Regla: con un carrusel andando, ningún otro ojo (Lite con alguien delante, cámara de la Mac) ni otro carrusel; `--estado` + `pgrep -fl carrusel`.

## 21 oct, 09:40 — "no rueda como antes": la firma de cada movimiento sobrevive a la invención
Medido: la difusión (mismo checkpoint que el de Dan, 17 oct) inventa playful con spin ±0.02 y sin salto, en todos los ánimos; la curva de
comportamiento de Violeta para playful ES el breach (spin hasta 12.6 = dos vueltas, depth +0.9), diving baja a −1.8, surfacing sube +1.2.
El cerebro reemplazaba spin y depth por los de la invención → sin breach. Ahora, para spin y depth, **gana el más fuerte**: la invención mueve
el cuerpo y la vuelta/el buceo/la subida de la curva atraviesan cuando ocurren. Playful 40 s: 6 breaches (spin máx 12.57, depth +0.83).

## 21 oct, 09:55 — tenencia de 30 s
Violeta: "el ánimo, movimiento u ofrenda que gana se queda 30 s". `TENENCIA_S` (env `YAKUMAMA_TENENCIA_S`, 30) en `cerebro_ballena.py`: dentro
del repertorio (cuarto, cara del visitante, su iniciativa) el ánimo que ganó la tiene 30 s antes de que otro del mismo nivel la tome; toque,
ofrenda, rechazo y prueba siguen por encima; al soltar, el ánimo al que vuelve empieza su tenencia. Sola 75 s: calm 0–23, curious 23–53,
singing 53–75, 0 saltos. (La ofrenda ya duraba 30 s como escena.)

## 21 oct · el viaje (cámara que la sigue)
Con `--violeta` el cerebro de Dan arranca en `nav_mode = viaje`: ella vive en metros absolutos del salar y la cámara la sigue (15–80 m según se acerque o se aleje). Perillas (entorno de `ballena_td.py`): `VIOLETA_VIAJE=0` (toma fija de antes), `VIAJE_M` (metros por unidad, 12), `VIAJE_MPS` (3 m/s de crucero entre destinos), `VIAJE_DEST_R` (destinos dentro de 200 m), `VIAJE_NEAR_M`/`VIAJE_FAR_M` (8/60 m de cámara), `BALLENA_EYE_DEG` (25°, cuánto giran sus ojos). Palanca: x orbita, y acerca/aleja. El panel puede volver a `walk`/`orbit`. Respaldo del archivo de Dan antes del cambio: `entregas/ballena_td_antes_viaje_21oct.py`.
