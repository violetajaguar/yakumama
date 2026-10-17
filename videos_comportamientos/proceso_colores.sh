#!/bin/zsh
# proceso_colores.sh - ~75 s del proyecto: la ballena en el salar, los diez animos (cada clip del taller tintado con el
# color del animo y la ballena encima, sin el recuadro de la cara), el cuerpo fisico, la memoria. Con palabras (tarjetas
# PNG hechas con Pillow en proceso/texto/; la del cuerpo dice 'we are building her body' y 'she will live in Barcelona first'). 1920x1080, 24 fps, sin audio.
set -e
Y=~/Desktop/Yakumama; D=~/Downloads; F=~/Desktop/Yakumama_Paqarina_koa/Yakumama/fotos/ballena_fisica; R=~/Desktop/"yakumama robot"
OUT=$Y/videos_comportamientos/proceso; T=$OUT/texto; mkdir -p $OUT; cd $OUT; rm -f lista.txt
typeset -A COL; COL=(calm ebeffa singing 9b4dff playful ff7300 curious ffd900 feeding 33c04d sad 5a6080 angry f21410 alert ff4da6 diving 2a4fb0 surfacing 19d6e8)
typeset -A SRC SS
SRC=(calm "$D/IMG_8289.MOV" singing "$D/copy_FC05E757-86B6-4283-810E-318E4EAEEA9A.MOV" playful "$D/7f4d7e03-667d-4516-a0aa-7d7afbecc386.MP4" curious "$D/0ff7f1d8-a066-43a0-9360-3e80b9a35ebf.JPG" feeding "$D/0b0b2b9d-f881-41d8-8332-6724952e98b8.MP4" sad "$D/50395326-0bfe-41a4-a865-888908685a2b.MP4" angry "$D/d3464339-7750-4327-8b71-578c06408dc0.MP4" alert "$D/e62980a0-f5c6-4133-a585-d4e1de784d91.MP4" diving "$D/IMG_7954.MOV" surfacing "$D/IMG_7954.MOV")
SS=(calm 0 singing 3 playful 0 curious 0 feeding 0 sad 0 angry 0 alert 1 diving 2 surfacing 12)
ENC=(-c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -an -r 24)
FOTO="scale=2112:1188:force_original_aspect_ratio=increase,crop=2112:1188,zoompan=z='1+0.0012*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24,setsar=1"
tarjeta() {
  local n=$1 img=$2 dur=$3 txt=$4 osc=${5:-0.55}
  ffmpeg -v error -y -loop 1 -framerate 24 -t $dur -i "$img" -loop 1 -framerate 24 -t $dur -i "$txt" \
    -filter_complex "[0:v]${FOTO},eq=brightness=-${osc}:saturation=0.8[b];[1:v]format=rgba,fade=t=in:st=0.6:d=0.9:alpha=1,fade=t=out:st=$((dur-1.2)):d=0.9:alpha=1[t];[b][t]overlay=0:0,fade=t=in:st=0:d=0.6,fade=t=out:st=$((dur-0.6)):d=0.6[v]" \
    -map "[v]" -t $dur "${ENC[@]}" seg_$n.mp4; echo "file 'seg_$n.mp4'" >> lista.txt; echo "  $n"
}
tarjeta 00_abre "$D/YakuMama .png" 6 $T/t_abre.png 0.25
ffmpeg -v error -y -ss 4 -t 4.5 -i "$D/IMG_8365.MOV" -loop 1 -framerate 24 -t 4.5 -i $T/t_animos.png \
  -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,setsar=1,eq=brightness=-0.22:saturation=0.9[b];[1:v]format=rgba,fade=t=in:st=0.4:d=0.8:alpha=1,fade=t=out:st=3.5:d=0.8:alpha=1[t];[b][t]overlay=0:0,fade=t=in:st=0:d=0.5,fade=t=out:st=4:d=0.5[v]" \
  -map "[v]" -t 4.5 "${ENC[@]}" seg_01_pantalla.mp4; echo "file 'seg_01_pantalla.mp4'" >> lista.txt; echo "  pantalla"
DUR=4.5
for a in calm singing playful curious feeding sad angry alert diving surfacing; do
  src=$SRC[$a]; c=$COL[$a]; ss=$SS[$a]
  if [[ $src == *.JPG ]]; then IN=(-loop 1 -framerate 24 -t $DUR -i "$src"); PROC="[0:v]${FOTO}"
  else IN=(-stream_loop -1 -ss $ss -t $DUR -i "$src"); PROC="[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,setsar=1"; fi
  ffmpeg -v error -y "${IN[@]}" -t $DUR -i $Y/videos_comportamientos/16x9/$a.mp4 -f lavfi -t $DUR -i "color=color=0x${c}:size=1920x1080:rate=24" -loop 1 -framerate 24 -t $DUR -i $T/p_$a.png \
    -filter_complex "$PROC,hue=s=0.25,eq=contrast=1.1:brightness=0.05[p];[2:v]scale=1920:1080,setsar=1[c];[p][c]blend=all_mode=multiply:shortest=1[t];[1:v]crop=1440:810:0:135,scale=1920:1080,fps=24,setsar=1[w];[t][w]blend=all_mode=screen:shortest=1[m];[3:v]format=rgba,fade=t=in:st=0.5:d=0.6:alpha=1,fade=t=out:st=3.6:d=0.6:alpha=1[x];[m][x]overlay=0:0,fade=t=in:st=0:d=0.5,fade=t=out:st=4:d=0.5[v]" \
    -map "[v]" -t $DUR "${ENC[@]}" seg_10_$a.mp4
  echo "file 'seg_10_$a.mp4'" >> lista.txt; echo "  $a"
done
tarjeta 20_cuerpo "$F/serpiente_detalle.png" 4.5 $T/t_cuerpo.png 0.3
for f in nazca_lado trazos_arriba; do
  ffmpeg -v error -y -loop 1 -framerate 24 -t 3 -i "$F/$f.png" -filter_complex "[0:v]${FOTO},fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5[v]" -map "[v]" -t 3 "${ENC[@]}" seg_21_$f.mp4
  echo "file 'seg_21_$f.mp4'" >> lista.txt; echo "  $f"
done
ffmpeg -v error -y -loop 1 -framerate 24 -t 3 -i "$D/IMG_7146.JPG" -filter_complex "[0:v]${FOTO},fade=t=in:st=0:d=0.5,fade=t=out:st=2.5:d=0.5[v]" -map "[v]" -t 3 "${ENC[@]}" seg_21_piezas.mp4
echo "file 'seg_21_piezas.mp4'" >> lista.txt; echo "  piezas"
ffmpeg -v error -y -i "$R/yakumama_led.mp4" -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,setsar=1,fade=t=in:st=0:d=0.5,fade=t=out:st=3.5:d=0.5[v]" -map "[v]" -t 4 "${ENC[@]}" seg_22_led.mp4
echo "file 'seg_22_led.mp4'" >> lista.txt; echo "  led"
tarjeta 30_memoria "$F/boceto_tres_cuartos.png" 4.5 $T/t_memoria.png 0.45
tarjeta 40_cierra "$Y/docs/yakumama.jpg" 5 $T/t_cierra.png 0.3
ffmpeg -v error -y -f concat -safe 0 -i lista.txt -c copy proceso_colores_animos.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 proceso_colores_animos.mp4
