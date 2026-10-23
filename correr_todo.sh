#!/usr/bin/env bash
# Yakumama, la instalacion completa en ESTA Mac (20 oct 2026), en el orden que manda docs/RUNNING.md de Dan ("Running with Violeta's brain"):
#   1 sala (OAK-D Pro)  2 su ojo (OAK-D Lite) + su cerebro + puente Laya  3 puente ESP32 + cerebro de Dan (--violeta --brain)  4 TouchDesigner
# Qwen: sus poemas en ESTA Mac (qwen3.6, el modelo para el que fue hecha; ELLA_OLLAMA/ELLA_MODEL), el cerebro de Dan en la mini
# (qwen35-local; DAN_OLLAMA/DAN_MODEL): probado 20 oct, el qwen3.6 local con TD en la misma GPU le vence el tiempo a la cognicion de Dan.
# Laya: en la mini por el puente (LAYA=mini) o aqui (LAYA=aqui). Un log por proceso en logs/.  Uso:
#   bash correr_todo.sh            arranca todo        bash correr_todo.sh --parar      para todo (el cerebro de Dan primero: deja el rig en reposo)
#   SILENCIO=1 bash correr_todo.sh prueba sin voz ni sonidos        bash correr_todo.sh --estado   que corre y que no
Y=~/Desktop/Yakumama; D=$Y/fuentes/Yaku_PC_2026-10-20/Paqarina_TD; L=$Y/logs; mkdir -p $L
MINI=${MINI:-192.168.50.104}; ELLA_OLLAMA=${ELLA_OLLAMA:-$MINI:11434}; ELLA_MODEL=${ELLA_MODEL:-qwen35-local}   # local qwen3.6 only when TD is not on this GPU (20 Oct)
DAN_OLLAMA=${DAN_OLLAMA:-$MINI:11434}; DAN_MODEL=${DAN_MODEL:-qwen35-local}; LAYA=${LAYA:-mini}; PRO=${PRO:-14442C10214FDBD600}; PUENTE=${PUENTE:-$(ls /dev/cu.usbserial-* 2>/dev/null | head -1)}
VISTA=${VISTA:-$(ls /dev/cu.usbserial-* 2>/dev/null | sed -n 2p)}      # la placa de la pantalla 2.4", si hay un segundo puerto
if [ "$1" = "--parar" ]; then
  pkill -f "dormir_ballena.p[y]" 2>/dev/null     # la despierta (dormir_ballena.py le cierra los ojos de noche por el puente)
  pkill -INT -f "ballena_td.p[y]"; sleep 2      # el cerebro de Dan primero: deja el rig en reposo
  P="carrusel_ofrendas.py carrusel_animos.py simular_jerarquia.py ojo_webcam.py puente_blender.py ballena_td.py ballena_joy.py ballena_vista.py laya_puente.py cerebro_ballena.py grabar_ballena.py ballena3.py ballena_crowd.py"
  for p in $P laya_sentidos.py; do pkill -TERM -f "$p" 2>/dev/null; done; sleep 3
  for p in $P laya_sentidos.py; do pkill -KILL -f "$p" 2>/dev/null; done; sleep 1     # el grabador y el puente ignoran INT/TERM a veces (20 oct)
  echo "parado (TD sigue abierto: guardar y cerrar a mano)"; bash $Y/correr_todo.sh --estado; exit 0
fi
if [ "$1" = "--estado" ]; then
  for p in ballena_crowd.py grabar_ballena.py cerebro_ballena.py laya_puente.py laya_sentidos.py ballena_joy.py ballena_vista.py ballena_td.py TouchDesigner; do printf "  %-20s %s\n" $p "$(pgrep -f "$p" >/dev/null && echo corre || echo -)"; done; exit 0
fi
cd $Y
curl -s -m 3 http://$DAN_OLLAMA/api/tags >/dev/null && echo "cerebro de Dan: ollama en $DAN_OLLAMA ($DAN_MODEL)" || echo "cerebro de Dan: SIN ollama en $DAN_OLLAMA (reflejos)"
curl -s -m 3 http://$ELLA_OLLAMA/api/tags >/dev/null && echo "sus poemas: ollama en $ELLA_OLLAMA ($ELLA_MODEL)" || echo "sus poemas: SIN ollama en $ELLA_OLLAMA (sin poemas)"
# 1. la sala, en la Pro, PRIMERO (fija su camara por serial; el ojo toma la otra)
pkill -f "dormir_ballena.p[y]" 2>/dev/null   # la despierta: de noche dormir_ballena.py le manda ojos cerrados y negros por el puente
pkill -f "ballena_crowd.p[y]" 2>/dev/null; sleep 1
(cd $D && BALLENA_OAK_MXID=$PRO nohup $Y/venv_td/bin/python -u ballena_crowd.py > $L/crowd.log 2>&1 </dev/null &); echo "1 sala (Pro $PRO) -> logs/crowd.log"; sleep 8
# 2. su ojo en la Lite, su cerebro, Laya por el puente
V=1; S=1; [ "${SILENCIO:-0}" = "1" ] && V=0 && S=0
YAKUMAMA_SIN_SERIAL=1 YAKUMAMA_SIN_QWEN=1 YAKUMAMA_OLLAMA=$ELLA_OLLAMA OLLAMA_MODEL=$ELLA_MODEL nohup venv/bin/python -u grabar_ballena.py --panel 8765 --visitas ${VISITAS:-1} --voz $V --sonido 0 --musica 0 --ojo-objeto 1 --emotibit 0 --emotibit-directo 0 --espejo 127.0.0.1:9997 > $L/ojo.log 2>&1 </dev/null &
echo "2a su ojo (Lite) -> logs/ojo.log   ventana: http://$(ipconfig getifaddr en0 2>/dev/null || echo localhost):8765/ventana"; sleep 6
YAKUMAMA_EVALUAR=${EVALUAR:-0} YAKUMAMA_VISTA=${YAKUMAMA_VISTA:-127.0.0.1:4210} nohup venv/bin/python -u cerebro_ballena.py --entrada 9997 --salida 127.0.0.1:9994 --salida 127.0.0.1:9993 --callado > $L/cerebro.log 2>&1 </dev/null &
echo "2b su cerebro -> 9994 (TD de Dan) y la vista 4210 -> logs/cerebro.log"; sleep 3
pkill -f "laya_puente.py pc" 2>/dev/null; pkill -f "laya_sentidos.py" 2>/dev/null; sleep 1
if [ "$LAYA" = "aqui" ]; then
  nohup venv_datos/bin/python -I laya_sentidos.py > $L/laya.log 2>&1 </dev/null &
  echo "2c Laya AQUI (laya_sentidos.py, venv_datos) -> logs/laya.log"
else
  nohup venv/bin/python -u laya_puente.py pc $MINI > $L/laya_puente.log 2>&1 </dev/null &
  echo "2c puente Laya <-> mini $MINI -> logs/laya_puente.log"
fi
# 3. el puente ESP32 (palanca, tiras, ojos, aletas, cola), la pantalla de la mesa, y el cerebro de Dan como render
cd $D
if [ -n "$PUENTE" ]; then nohup $Y/venv_td/bin/python -u ballena_joy.py --port $PUENTE --color > $L/joy.log 2>&1 </dev/null & echo "3a puente ESP32 en $PUENTE -> logs/joy.log"; else echo "3a SIN puente ESP32 (no hay /dev/cu.usbserial-*)"; fi
if [ -n "$VISTA" ]; then nohup $Y/venv_td/bin/python -u ballena_vista.py --serial $VISTA > $L/vista.log 2>&1 </dev/null & echo "3b pantalla 2.4\" en $VISTA -> logs/vista.log"; else echo "3b pantalla 2.4\": sin placa (segundo usbserial)"; fi
pkill -f "ballena_td.p[y]" 2>/dev/null; sleep 1
A="canto memoria"; [ "$S" = "0" ] && export SONIDO=0
# la medida (21 oct): EVALUAR=1 ./correr_todo.sh = un dia con moneda por encuentro (ella / azar); luego venv/bin/python calibracion.py --dias 1
# la banda sonora (21 oct): Bjork de cama (BALLENA_AMBIENT_FILE), viento/lluvia de la biblioteca (ambiente/), salida por nombre (BALLENA_AUDIO_OUT: JBL, MSI, MacBook)
BALLENA_AUDIO_OUT="${AUDIO:-JBL}" BALLENA_AMBIENT=${MUSICA_ON:-0} BALLENA_AMBIENT_FILE="${MUSICA:-$HOME/Desktop/Huk/whale sound/musica}" BALLENA_AMBIENT_VOL=${MUSICA_VOL:-0.6} BALLENA_VIENTO_VOL=${VIENTO_VOL:-0.9} BALLENA_LLUVIA_VOL=${LLUVIA_VOL:-0.9} \
BALLENA_OLLAMA=$DAN_OLLAMA OLLAMA_MODEL=$DAN_MODEL ALMA="$A" nohup $Y/venv_td/bin/python -u ballena_td.py --violeta --brain > $L/ballena_td.log 2>&1 </dev/null &
echo "3c cerebro de Dan --violeta --brain (ALMA=\"$A\") -> logs/ballena_td.log"; sleep 5
# 4. TouchDesigner, solo si no esta abierto
TOE="$D/Paqarina.toe"; [ -f "$D/Paqarina_mac.toe" ] && TOE="$D/Paqarina_mac.toe"; N=$(ls -t "$D"/Paqarina_mac*.toe 2>/dev/null | head -1); [ -n "$N" ] && TOE="$N"   # the newest Mac save (TD saves incrementally: Paqarina_mac.4.toe, 21 Oct)
pgrep -x TouchDesigner >/dev/null && echo "4 TouchDesigner ya abierto" || { open -a TouchDesigner "$TOE"; echo "4 abriendo $(basename "$TOE")"; }
pkill -f vigilante_td.sh 2>/dev/null; nohup bash $Y/vigilante_td.sh > /dev/null 2>&1 </dev/null & echo "5 vigilante de TD (guarda y relanza a 9 GB con la sala vacia, o a 14 GB) -> logs/vigilante_td.log"
echo; echo "estado:"; bash $Y/correr_todo.sh --estado
