#!/usr/bin/env python3
"""tarjetas.py - las tarjetas bilingues del video (proceso/texto_bi/): ingles a la izquierda, castellano a la derecha,
una linea fina entre los dos, sombra suave bajo la letra para que se lea sobre cualquier fondo. Georgia (itálica el
ingles, redonda el castellano)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
F = "/System/Library/Fonts/Supplemental/Georgia.ttf"; FI = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
C = (236, 230, 218, 255); CS = (236, 230, 218, 200); CARP = "proceso/texto_bi"; os.makedirs(CARP, exist_ok=True)
def envolver(d, texto, fuente, ancho):
    lineas, actual = [], ""
    for w in texto.split():
        prueba = (actual + " " + w).strip()
        if d.textlength(prueba, font=fuente) <= ancho: actual = prueba
        else: lineas.append(actual); actual = w
    if actual: lineas.append(actual)
    return lineas
def sombra(im):
    """una capa oscura difuminada debajo del texto (la alpha del texto, desplazada y borrosa)."""
    a = im.split()[3].filter(ImageFilter.GaussianBlur(6)); s = Image.new("RGBA", im.size, (0, 0, 0, 0)); s.putalpha(a.point(lambda v: int(v * 0.75)))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0)); base.alpha_composite(s, (3, 4)); base.alpha_composite(im); return base
def columnas(nombre, en, es, titulo=None, tam=50, y0=None, regla=True):
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fen, fes = ImageFont.truetype(FI, tam), ImageFont.truetype(F, tam - 2); ancho = 700; xl, xr = 160, 1060
    if titulo:
        ft = ImageFont.truetype(F, 140); w = d.textlength(titulo, font=ft); d.text(((1920 - w) / 2, 300), titulo, font=ft, fill=C)
    L = [l for p in en for l in (envolver(d, p, fen, ancho) if p else [""])]; R = [l for p in es for l in (envolver(d, p, fes, ancho) if p else [""])]
    alto = max(len(L), len(R)) * int(tam * 1.35); y = y0 if y0 is not None else (560 if titulo else (540 - alto // 2))
    for i, l in enumerate(L): d.text((xl + ancho - d.textlength(l, font=fen), y + i * int(tam * 1.35)), l, font=fen, fill=C)      # ingles alineado a la derecha, hacia la regla
    for i, l in enumerate(R): d.text((xr, y + i * int(tam * 1.35)), l, font=fes, fill=CS)                                        # castellano alineado a la izquierda
    if L or R:   # panel oscuro difuminado detras del texto, para que se lea sobre cualquier fondo
        panel = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); pd = ImageDraw.Draw(panel); pd.rounded_rectangle([110, y - 60, 1810, y + alto + 50], radius=40, fill=(0, 0, 0, 135)); panel = panel.filter(ImageFilter.GaussianBlur(28))
        fondo = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); fondo.alpha_composite(panel); fondo.alpha_composite(im); im = fondo; d = ImageDraw.Draw(im)
    if regla and (L or R): d.line([(960, y - 10), (960, y + alto + 4)], fill=(236, 230, 218, 120), width=2)
    sombra(im).save(f"{CARP}/{nombre}.png")
def pie(nombre, en, es):
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = ImageFont.truetype(FI, 34); g = ImageFont.truetype(F, 32)
    d.text((90, 960), en, font=f, fill=C); w = d.textlength(es, font=g); d.text((1830 - w, 962), es, font=g, fill=CS); sombra(im).save(f"{CARP}/{nombre}.png")
columnas("t_abre", ["a whale who lives in the Salar de Uyuni, the largest lithium reserve on earth"], ["una ballena que vive en el Salar de Uyuni, la mayor reserva de litio del mundo"], titulo="YAKUMAMA", tam=46)
columnas("t_animos", ["a human performer moves her: face, hands, body, heartbeat, skin", "", "ten moods, each one a real humpback behaviour"], ["una persona la mueve: cara, manos, cuerpo, latido, piel", "", "diez ánimos, cada uno un comportamiento real de yubarta"])
columnas("t_emotibit", ["an EmotiBit on the performer's wrist: heartbeat, skin conductance, temperature", "", "her pulse becomes the whale's rhythm"], ["un EmotiBit en la muñeca de quien la mueve: latido, conductancia de la piel, temperatura", "", "su pulso es el ritmo de la ballena"])
columnas("t_cuerpo", ["we are building her body, all of it in house: printed vertebrae, fins, a turbine tail, light under the skin", "", "she will live in Barcelona first"], ["su cuerpo lo hacemos nosotras, todo en casa: vértebras impresas, aletas, cola turbina, luz bajo la piel", "", "vivirá primero en Barcelona"])
columnas("t_local", ["all her AI runs on one laptop, locally. no cloud.", "", "she remembers faces without photos, learns who moves like whom, and writes."], ["toda su inteligencia corre en una laptop, local. sin nube.", "", "recuerda caras sin fotos, aprende quién se mueve como quién, y escribe."])
columnas("t_salvajes", ["the techbros can't deal with las salvajes"], ["los techbros no pueden con las salvajes"], tam=72)
def centrada(nombre, titulo, lineas, tam=46):
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im); ft = ImageFont.truetype(F, 140); f = ImageFont.truetype(FI, tam)
    w = d.textlength(titulo, font=ft); d.text(((1920 - w) / 2, 330), titulo, font=ft, fill=C); y = 560
    for l in lineas: w = d.textlength(l, font=f); d.text(((1920 - w) / 2, y), l, font=f, fill=CS); y += int(tam * 1.5)
    sombra(im).save(f"{CARP}/{nombre}.png")
centrada("t_cierra", "YAKUMAMA", ["Violeta Jaguar · Dan · Jícara · Paqarina", "MozFest Wilding · 2026"])
pie("p_flores", "the flowers · Jícara", "las flores · Jícara")
P = {"calm": ("calm · logging at the surface", "calma · descanso en superficie"), "singing": ("singing · head down, the song", "canto · cabeza abajo, el canto"), "playful": ("playful · the breach", "juego · el salto"),
     "curious": ("curious · spyhop", "curiosidad · asomarse"), "feeding": ("feeding · the lunge", "hambre · la embestida"), "sad": ("sad · sinking", "tristeza · hundirse"), "angry": ("angry · lobtail", "rabia · golpe de cola"),
     "alert": ("alert · scanning", "alerta · escaneo"), "diving": ("diving · flukes up", "hondo · colas arriba"), "surfacing": ("surfacing · the blow", "aire · el soplo")}
for k, (en, es) in P.items(): pie("p_" + k, en, es)
print("tarjetas bilingues:", len(os.listdir(CARP)))
