#!/usr/bin/env bash
# vigilante_td.sh - keeps TouchDesigner alive for a whole day (21 Oct 2026, Violeta: "we want to run the entire experience for longer").
# TD on this Mac grows ~70 MB/min (1.8 GB at open, 15.4 GB after 4.5 h; a node inside the project, see docs/td_memoria.py) and
# slows as it grows. Every minute this checks its memory and, when it passes TD_SUAVE_GB with nobody in the room for 2 minutes,
# or TD_DURO_GB regardless, it does the restart by hand's recipe: Cmd+S (TD saves an incremented Paqarina_mac.N.toe), Cmd+Q,
# reopen the newest file. About a minute of black on the projector; everything else keeps running (Dan's brain reconnects alone).
#   bash vigilante_td.sh &            TD_SUAVE_GB=9 TD_DURO_GB=14 by default; logs/vigilante_td.log
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin
Y=~/Desktop/Yakumama; D=$Y/fuentes/Yaku_PC_2026-10-20/Paqarina_TD; L=$Y/logs/vigilante_td.log
SUAVE=${TD_SUAVE_GB:-9}; DURO=${TD_DURO_GB:-14}; vacio_desde=0
say_() { echo "$(date '+%H:%M:%S') $*" >> "$L"; }
say_ "vigilante: soft ${SUAVE} GB (room empty 2 min), hard ${DURO} GB"
while true; do
  sleep 60
  P=$(pgrep -x TouchDesigner | head -1); [ -z "$P" ] && continue
  GB=$(ps -o rss= -p "$P" | awk '{printf "%.1f", $1/1048576}')
  N=$(python3 -c "import json; d=json.load(open('/tmp/ballena_cerebro.json')); print(int(d.get('personas_n') or 0) + int(d.get('persona') or 0))" 2>/dev/null || echo 1)
  now=$(date +%s)
  if [ "$N" = "0" ]; then [ "$vacio_desde" = "0" ] && vacio_desde=$now; else vacio_desde=0; fi
  vacio=$(( vacio_desde > 0 ? now - vacio_desde : 0 ))
  suave=$(python3 -c "print(1 if $GB >= $SUAVE and $vacio >= 120 else 0)"); duro=$(python3 -c "print(1 if $GB >= $DURO else 0)")
  if [ "$suave" = "1" ] || [ "$duro" = "1" ]; then
    say_ "TD at ${GB} GB (room empty ${vacio} s): saving and relaunching"
    osascript -e 'tell application "TouchDesigner" to activate' -e 'delay 0.8' -e 'tell application "System Events" to keystroke "s" using command down' >/dev/null 2>&1; sleep 8
    TOE=$(ls -t "$D"/Paqarina_mac*.toe | head -1); say_ "saved: $(basename "$TOE")"
    osascript -e 'tell application "System Events" to keystroke "q" using command down' >/dev/null 2>&1
    n=0; until ! pgrep -x TouchDesigner >/dev/null || [ $n -ge 40 ]; do sleep 1; n=$((n+1)); done
    if pgrep -x TouchDesigner >/dev/null; then say_ "TD did not quit (a dialog?): leaving it"; continue; fi
    open -a TouchDesigner "$TOE"; sleep 45
    P=$(pgrep -x TouchDesigner | head -1); say_ "relaunched: $(ps -o rss= -p "$P" 2>/dev/null | awk '{printf "%.1f", $1/1048576}') GB"
    vacio_desde=0
  fi
done
