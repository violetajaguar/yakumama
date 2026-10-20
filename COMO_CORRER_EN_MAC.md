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
