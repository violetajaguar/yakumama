# Cómo enseñarle a Yakumama a reconocer cada ofrenda

*Texto para pedirle ayuda a alguien con las fotos. El catálogo de las 29 criaturas está en `docs/OFRENDAS.md`.*

## Qué significa "enseñarle"

Yakumama tiene un ojo (una cámara) que cada 3 segundos mira qué tiene en las manos la persona que está enfrente. Hoy ese ojo solo sabe decir "es un pez" o "no es un pez". Para que distinga el ciempiés de la abeja, o la flor amarilla de la naranja, hay que entrenarle un reconocedor propio, y eso se hace igual que con un niño: mostrándole cada criatura muchas veces, de muchas maneras, y diciéndole cómo se llama.

Esas "muchas veces" son fotos. Con las fotos yo entreno el modelo y lo pongo dentro de su ojo. Después, cuando alguien le acerque una criatura a la boca, ella sabrá cuál es y hará lo que Violeta decidió para esa (saltar con el saltamontes, oler la flor, saludar al pájaro).

## La forma buena: con su propio ojo (la OAK-D)

Hay dos OAK-D. Una se conecta a la M1 y con `fotos_ofrendas.py` (paquete `entregas/Yakumama_fotos_ofrendas_2026-10-20/`, con su `LEEME.md`) se hacen las fotos directamente con la cámara que ella usará: se elige la criatura, espacio, y guarda 40 cuadros en 20 segundos mientras se mueve en la mano. Es la sesión que hace Sanam. Lo que sigue es la versión con celular, por si no hay OAK-D a mano.

## Con el celular: una sesión de fotos

Son 29 criaturas. Por cada una, entre **30 y 40 fotos con el celular**, sosteniéndola en la mano como se la daríamos a la ballena. Unos 50 minutos en total.

Para cada criatura:

1. Tómala en la mano y haz fotos **desde donde estaría el ojo de la ballena**: de frente, a un metro más o menos.
2. Varía todo lo que puedas entre foto y foto:
   - el ángulo: de frente, de lado, girada, un poco de arriba, un poco de abajo, boca abajo;
   - la distancia: unas cerca (que llene la foto), otras lejos (que se vea la persona entera con la criatura en la mano);
   - cómo la agarras: con dos dedos, en la palma abierta, medio tapada por los dedos, con la otra mano;
   - la luz: cerca de la ventana, lejos de la ventana, con la luz prendida, a contraluz;
   - el fondo: pared, piso, mesa con cosas, con gente detrás.
3. Si puedes, que **dos o tres personas distintas** la sostengan (manos distintas, ropa distinta).
4. Sin filtros, sin zoom digital, sin recortar. Fotos normales. Si alguna sale movida no importa, también sirve.

Además de las 29 criaturas necesito tres grupos más, para que aprenda qué **no** es una ofrenda:

- **manos vacías**: 40 fotos de manos sin nada, en las mismas posiciones;
- **otras cosas en la mano**: 40 fotos con un celular, llaves, una taza, un lápiz, un papel, lo que haya;
- **la hermana dorada**: 20 fotos de la ballenita de oro en la mano, si la tienes a mano.

## Cómo guardarlas

Una carpeta por criatura, con el número y el nombre del catálogo, así:

```
ofrendas_fotos/
  01_ciempies/
  02_pez_verde_boca_grande/
  03_saltamontes_verde/
  ...
  23_pez_rosado_dientes/
  ...
  29_pez_azul_cola_rosada/
  manos_vacias/
  otras_cosas/
  hermana_dorada/
```

Los nombres de las 29 están en `docs/OFRENDAS.md` (y en `docs/ofrendas/` hay una foto de cada una para no confundirlas: las dos mariquitas, los dos saltamontes y los peces se parecen entre sí).

No hace falta renombrar las fotos, solo que cada una esté en su carpeta. Me las mandas por AirDrop o en un zip.

## Lo que hago yo después

1. Con las fotos entreno un reconocedor pequeño (29 criaturas + manos vacías + otras cosas + hermana) que corre en la Mac sin internet.
2. Lo meto en su ojo en lugar de la pregunta de hoy: cada 3 segundos dirá "veo el saltamontes verde" en vez de solo "veo un pez".
3. Conecto cada criatura con su reacción de la lista de Violeta en la capa de decisiones.
4. Lo probamos con las criaturas reales frente a su cámara, y lo que confunda lo volvemos a fotografiar.

Una segunda ronda de fotos, más adelante, la hacemos con **su propia cámara** (la que está en la instalación), porque ve distinto que un celular. Esa ronda es más corta: diez fotos por criatura.


## Lo que pasó el 20 de octubre (la sesión de Sanam)

Sanam hizo la sesión con la OAK-D en la M1: **2700 fotos** en `ofrendas_fotos/` (dos ráfagas por criatura, 76 fotos cada una; la mariposa tres; manos vacías 38; otras cosas 190; la hermana 228). En cada criatura la primera ráfaga fue **de cerca** (la mano llena el cuadro, unos 400 px) y la segunda **a un metro** (la mano mide unos 120 px y la criatura unos 40). Violeta rellenó la hoja impresa y las 29 reacciones quedaron emparejadas, una por criatura, sin repetir (`ofrendas/ofrendas.json`, campo `reaccion`).

Con eso entrené el ojo (`entrenar_ofrendas.py`): recorte ajustado alrededor de la mano (así de cerca y de lejos se ve igual), rasgos DINOv2 y una regresión logística. La prueba honesta, dejando fuera el último 40 % de cada ráfaga:

| | acierto |
|---|---|
| todas las fotos de prueba | 78 % |
| con la mano a un metro | 75 % |
| cuando responde con confianza (p ≥ 0.5, el 60 % de las veces) | 95 % |

Aprender solo de cerca y reconocer de lejos **no funciona** (36 %): hacen falta fotos a la distancia real. Las confusiones que quedan son entre parecidas: los dos saltamontes, las dos flores, el pez azul de cola rosada con el verde de cola naranja, el pez rosado de dientes con la araña.

En la instalación el ojo mira cada 3 segundos y vota entre las últimas tres miradas, así que una criatura sostenida unos segundos se reconoce casi siempre, y cuando duda no hace nada (mejor callar que reaccionar a la criatura equivocada).

### La segunda ronda de fotos

Para subir del 78 %, lo que más ayuda, en este orden:

1. **Otra persona** haciendo la sesión completa a un metro (otras manos, otra ropa, otro fondo). Todas las fotos de hoy son de Sanam con la misma camiseta.
2. **Solo a un metro**, que es como la verá: una ráfaga más por criatura, moviéndola mucho.
3. Las parejas que confunde, con especial cuidado de mostrar lo que las distingue: las antenas rosadas del saltamontes 13, el centro de cada flor, la cola de los peces 26 y 29.
4. **Luz de tarde o luz artificial**, si la instalación la tendrá.

Después: `venv/bin/python entrenar_ofrendas.py` (unos 4 minutos; reusa lo ya calculado, y vuelve a calcular solo si cambian las fotos).
