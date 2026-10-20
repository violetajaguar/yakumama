#!/usr/bin/env bash
# Yakumama en TouchDesigner (paquete del PC de Dan, 20 oct 2026): arranca el cerebro y despues abre el .toe.
# Orden obligatorio: PRIMERO el cerebro (OSC 7000), DESPUES TouchDesigner; si TD abre antes, sus parametros ligados
# a OSC dan error (cruz roja) hasta que el cerebro envie.  Uso:  bash ~/Desktop/Yakumama/correr_td.sh [--run|--idle]
Y=~/Desktop/Yakumama; D=$Y/fuentes/Yaku_PC_2026-10-20/Paqarina_TD; MODO=${1:---idle}
cd "$D"
pkill -f "ballena_td.p[y]" 2>/dev/null; sleep 1
mkdir -p "$Y/logs"; nohup "$Y/venv_td/bin/python" -u ballena_td.py "$MODO" > "$Y/logs/ballena_td.log" 2>&1 &
echo "cerebro: pid $!  (log: $Y/logs/ballena_td.log)"; sleep 4; tail -3 "$Y/logs/ballena_td.log"
TOE="$D/Paqarina.toe"; [ -f "$D/Paqarina_mac.toe" ] && TOE="$D/Paqarina_mac.toe"   # la copia con rutas Mac (relocate_paths.py, 20 oct)
open -a TouchDesigner "$TOE"; echo "abriendo $(basename "$TOE")"
echo "TouchDesigner abriendo Paqarina.toe. La primera vez en esta Mac: en TD, abrir td/relocate_paths.py en un Text DAT y Run Script"
echo "(repunta las rutas del PC de Dan a esta carpeta). Si la ballena no aparece o hay cruz roja: td/td_bind_osc.py igual."
echo "Para parar: Ctrl-C / pkill del cerebro primero (deja el rig en pose de reposo), despues cerrar TD."
