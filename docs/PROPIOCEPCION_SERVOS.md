# Propiocepción: los servos de las aletas le cuentan a ella lo que hicieron

21 oct 2026. Violeta: "the servos are clones of the Feetech and they report back their position and temperature".

## Lo que ya está hecho (software, en la Mac)

La cadena entera espera una línea nueva de la placa de la ballena:

```
SERVO:fl_pos,fl_temp,fl_load,fr_pos,fr_temp,fr_load[,tail]
```

`pos` en la misma escala que se le manda (−1..1), `temp` en °C, `load` −1..1 (signo = sentido del esfuerzo). Una línea cada 100 ms basta.

- `ballena_joy.py` (el puente USB) la lee y la manda al cerebro de Dan (UDP 5006) como `servos`.
- `ballena_td.py` la pone en `cuerpo_fisico.medido` del paquete 9995 (junto a lo que se le **mandó**: `aleta_i`, `aleta_d`, `cola`, `parpado`, y `viva`).
- `grabar_ballena.py` la pasa a su cerebro; `cerebro_ballena.py` la escribe en su paquete y la dice en el log (`[body] fins told … measured …`).
- Desde ahí entra en sus decisiones cuando se quiera (temperatura alta → cansancio; posición medida ≠ mandada → algo la frena: alguien la sujeta).

## Lo que falta (firmware, placa de la ballena: Dan / Brian)

Primero confirmar **qué servos son**:

- **Bus serie Feetech (STS/SCS, 3 hilos, en cadena, TTL half-duplex)**: reportan posición, temperatura, carga y voltaje. El firmware actual (`ballena_joy_esp32.ino` v29) mueve las aletas por **PWM (LEDC, 50 Hz)**: a un servo de bus eso no le llega. Hay que moverlos por el bus y leerlos por el bus.
- **Servo PWM con hilo de realimentación (FS90-FB y parecidos)**: solo posición, analógica, sin temperatura. Entonces la línea SERVO lleva posición y `temp` = −1.

Para el caso de bus (el que reporta temperatura), el esqueleto en Arduino (librería **SCServo** de Feetech, clase `SMS_STS`):

```cpp
#include <SCServo.h>
SMS_STS st;                       // Serial1 a 1 000 000 baud, TX al pin de datos por un conversor half-duplex (o TX y RX unidos con 1 kΩ)
const uint8_t ID_L = 1, ID_R = 2; // ids de las aletas (se ponen con la herramienta de Feetech)
void setup() { Serial1.begin(1000000, SERIAL_8N1, RX_PIN, TX_PIN); st.pSerial = &Serial1; }
void moverAleta(uint8_t id, float s) {          // s −1..1 -> ticks (STS: 0..4095, 4096 = una vuelta)
  st.WritePosEx(id, (int16_t)(2048 + s * 1024), 1500, 50);   // posición, velocidad, aceleración
}
void reportar() {                                 // cada 100 ms
  float pl = (st.ReadPos(ID_L) - 2048) / 1024.0f, pr = (st.ReadPos(ID_R) - 2048) / 1024.0f;
  int   tl = st.ReadTemper(ID_L),  tr = st.ReadTemper(ID_R);
  float ll = st.ReadLoad(ID_L) / 1000.0f, lr = st.ReadLoad(ID_R) / 1000.0f;   // ±1000 -> ±1
  Serial.printf("SERVO:%.3f,%d,%.3f,%.3f,%d,%.3f\n", pl, tl, ll, pr, tr, lr);
}
```

La placa de la ballena habla con el puente por ESP-NOW; la línea SERVO viaja igual que las de tacto/palanca (el puente ya la reconoce).

## Por qué importa

Es la mitad que faltaba del cuerpo: hasta hoy ella sabía qué le mandaba a sus aletas, no qué hicieron. Con la medida puede notar que la sujetan (posición mandada ≠ medida), cuánto se calienta (temperatura → descansar), y el esfuerzo (carga). Todo eso entra en el mismo registro de decisiones y recompensa, así que lo aprende como todo lo demás.

## Lo que ella hace con la medida (21 oct, noche · Violeta: "the told-measured gap as a hand on her fin, temperature as tiredness and also excitement")

`cerebro_ballena.cuerpo_leer` (cada 0,2 s, con lo que la placa reporta):

- **Se calibra sola.** La placa manda grados (p. ej. L +25,7°), ella manda −1..1. No hay tabla de unidades: un ajuste lineal con olvido por aleta (`medido = a·mandado + b`) aprende la relación en un par de minutos y vuelve a aprenderla si Dan reflashea. Solo aprende de lecturas que parecen su propio movimiento.
- **Una mano en la aleta** = residuo muy por encima de lo habitual durante ~1 s → `aleta_sujeta` 0..1 (sube en 1 s, baja en ~5 s al soltar). Cuenta como tacto: ánimo *alert* (el mapa: aleta → alerta), palabra "aleta" en la recompensa, y en `decisiones.puntajes` la inclina a quedarse, invitar, mirar; nada de show mientras la sujetan.
- **Temperatura como excitación**: grados por encima de una línea base lenta (sigue en ~20 min) → `excitada` 0..1: más baile de vuelta, show, canto, imitar.
- **Temperatura como cansancio**: por encima de `YAKUMAMA_CANSADA_C` (60 °C; en reposo aquí rondan 47–52, los STS se protegen cerca de 70) → `cansada` 0..1: observar, quedarse, silencio, menos baile y show. Cansada apaga a excitada.

Todo entra en la situación que registra (`aleta_sujeta`, `cansada`, `excitada`, `calor`), así que lo aprende como lo demás. Log cada minuto: `[body] fins told … measured … | held … tired … excited … (baseline …)`; y `[body] a hand on her fin` cuando pasa. El paquete 9994 lleva `propio: {sujeta, cansada, excitada}` por si el render quiere mostrarlo.
