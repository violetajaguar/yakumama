#!/bin/zsh
# proceso_colores.sh - un minuto del proceso mezclado con los animos: cada tramo tinta un clip del taller con el color de
# un animo y le superpone (screen) a la ballena en ese animo. 10 animos x 6 s = 60 s, 1920x1080, sin audio.
set -e
Y=~/Desktop/Yakumama; D=~/Downloads; OUT=$Y/videos_comportamientos/proceso; mkdir -p $OUT; cd $OUT
typeset -A COL; COL=(calm ebeffa singing 9b4dff playful ff7300 curious ffd900 feeding 33c04d sad 5a6080 angry f21410 alert ff4da6 diving 2a4fb0 surfacing 19d6e8)
# animo -> clip del taller (los 8 ultimos de Descargas; dos se usan dos veces, desde otro segundo)
typeset -A SRC SS
SRC=(calm "$D/IMG_8289.MOV" singing "$D/copy_FC05E757-86B6-4283-810E-318E4EAEEA9A.MOV" playful "$D/7f4d7e03-667d-4516-a0aa-7d7afbecc386.MP4" curious "$D/0ff7f1d8-a066-43a0-9360-3e80b9a35ebf.JPG" feeding "$D/0b0b2b9d-f881-41d8-8332-6724952e98b8.MP4" sad "$D/50395326-0bfe-41a4-a865-888908685a2b.MP4" angry "$D/d3464339-7750-4327-8b71-578c06408dc0.MP4" alert "$D/e62980a0-f5c6-4133-a585-d4e1de784d91.MP4" diving "$D/copy_FC05E757-86B6-4283-810E-318E4EAEEA9A.MOV" surfacing "$D/0b0b2b9d-f881-41d8-8332-6724952e98b8.MP4")
SS=(calm 0 singing 3 playful 0 curious 0 feeding 0 sad 0 angry 0 alert 1 diving 22 surfacing 8)
rm -f lista.txt
for a in calm singing playful curious feeding sad angry alert diving surfacing; do
  src=$SRC[$a]; c=$COL[$a]; ss=$SS[$a]
  if [[ $src == *.JPG ]]; then
    IN=(-loop 1 -framerate 24 -t 6 -i "$src")
    PROC="[0:v]scale=2112:1188:force_original_aspect_ratio=increase,crop=2112:1188,zoompan=z='1+0.0015*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24,setsar=1"
  else
    IN=(-stream_loop -1 -ss $ss -t 6 -i "$src")
    PROC="[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,setsar=1"
  fi
  ffmpeg -v error -y "${IN[@]}" -t 6 -i $Y/videos_comportamientos/16x9/$a.mp4 -f lavfi -t 6 -i "color=color=0x${c}:size=1920x1080:rate=24" \
    -filter_complex "$PROC,hue=s=0.25,eq=contrast=1.1:brightness=0.05[p];[2:v]scale=1920:1080,setsar=1[c];[p][c]blend=all_mode=multiply:shortest=1[t];[1:v]scale=1920:1080,fps=24,setsar=1[w];[t][w]blend=all_mode=screen:shortest=1,fade=t=in:st=0:d=0.6,fade=t=out:st=5.4:d=0.6,format=yuv420p[v]" \
    -map "[v]" -t 6 -c:v libx264 -crf 18 -preset medium -an seg_$a.mp4
  echo "file 'seg_$a.mp4'" >> lista.txt; echo "  $a listo"
done
ffmpeg -v error -y -f concat -safe 0 -i lista.txt -c copy proceso_colores_animos.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 proceso_colores_animos.mp4
