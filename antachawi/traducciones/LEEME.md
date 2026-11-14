# Traducir Antachawi al quechua (Collao)

Antachawi Yachay está pensado para niños quechuahablantes. Cuando eligen
**Quechua** en la parte de abajo de la ventana, cada texto que ya está
traducido aparece en quechua; lo que todavía no está traducido sigue
apareciendo en español.

No hace falta saber programar para traducir. Hay dos cosas para traducir:

1. Los **mensajes** (botones, lo que dice Tunki, los errores) → `quechua.csv`
2. Los **programas de ejemplo** → la carpeta `antachawi/ide/ejemplos/qu/`

---

## 1. Mensajes: `quechua.csv`

Abre `quechua.csv` con **LibreOffice Calc** o **Excel**. Si LibreOffice
pregunta cómo abrirlo, elige *Juego de caracteres: Unicode (UTF-8)* y
*Separado por: coma*.

| Columna   | Qué es                                            |
|-----------|---------------------------------------------------|
| `codigo`  | Identificador del mensaje. **No lo cambies.**     |
| `donde`   | Dónde aparece el texto en el programa.            |
| `espanol` | El texto original.                                |
| `quechua` | **Aquí escribes la traducción.**                  |
| `origen`  | `equipo`, `borrador` o `revisado` (ver abajo).    |
| `nota`    | Avisos para quien traduce.                        |

Solo hay que llenar la columna **quechua**. Las celdas vacías se muestran en
español.

### Borradores por revisar

Las traducciones con origen **`borrador`** se hicieron sin un hablante de
quechua collao que las revisara: se muestran en el entorno, pero pueden
tener errores (sobre todo las palabras de programación, que no tienen una
traducción establecida). Al revisar una fila, corrige el texto si hace
falta y cambia `borrador` por **`revisado`**. Los ejemplos de
`antachawi/ide/ejemplos/qu/` también son borradores.

Palabras usadas en el borrador (para que la revisión sea coherente):

| Español             | Borrador                         |
|---------------------|----------------------------------|
| error               | pantasqa                         |
| aviso               | willakuy                         |
| línea               | siq'i (como en la traducción del equipo) |
| programa, variable, condición, operador, bloque | se dejaron como préstamo |
| ejecutar            | purichiy                         |
| valor               | chanin                           |
| declarada           | willaykusqa (como el equipo)     |
| cero                | ch'usaq                          |

### Las palabras entre llaves `{ }` no se traducen

Algunos textos tienen palabras entre llaves, por ejemplo:

    Línea {linea}
    la variable '{nombre}' no fue declarada.

Al mostrarse, el programa cambia `{linea}` por un número y `{nombre}` por el
nombre de la variable. Por eso hay que **copiarlas tal cual**, con las
llaves y sin traducirlas. Sí se pueden mover de lugar dentro de la
oración, según lo pida el quechua:

    Español:   Línea {linea}
    Quechua:   ........ {linea} ........     ✔ {linea} quedó igual
    Quechua:   ........ {........} ...       ✖ se tradujo lo de las llaves

La columna `nota` dice cuáles hay que copiar.

### Guardar

Guarda el archivo **en formato CSV** (en LibreOffice: *Guardar como → Texto
CSV*, *Mantener el formato actual*). La próxima vez que se abra el entorno
ya aparecen las traducciones.

### Revisar

Desde la carpeta del proyecto:

    python -m antachawi.traduccion revisar

Dice cuántos textos faltan y avisa si alguna traducción tiene un problema
(por ejemplo, una palabra entre llaves mal copiada; esas traducciones no se
usan hasta corregirlas). También avisa si el texto en español cambió después
de traducirlo.

Cuando los programadores agregan mensajes nuevos, se añaden a la hoja con:

    python -m antachawi.traduccion actualizar

(Lo ya traducido no se borra.)

---

## 2. Programas de ejemplo: `antachawi/ide/ejemplos/qu/`

1. Copia un ejemplo de `antachawi/ide/ejemplos/` a la carpeta `qu/`.
2. **Conserva el número** del principio y cambia el resto del nombre al
   quechua. Ese nombre es el que aparece en el menú *Ejemplos*
   (los `_` se muestran como espacios):

       01_hola.awi   →   qu/01_<nombre_en_quechua>.awi

3. Traduce:
   - los **comentarios** (las líneas que empiezan con `::`),
   - los **textos entre comillas** (`rikuchiy("...")`),
   - si quieres, los **nombres de las variables**: pueden tener letras
     (también `ñ`), números y `_`, pero **no espacios ni apóstrofo (`'`)**.
     Las palabras con `ch'`, `k'`, `p'`, `q'`, `t'` no sirven como nombre
     de variable tal cual; dentro de comentarios y textos entre comillas
     sí se pueden escribir normalmente.
4. **No cambies** las palabras del lenguaje (`qhapaq`, `yupay`,
   `rikuchiy`, `ari`, `chaykama`...) ni los signos `( ) { } = + -`.

Al abrir el ejemplo en el entorno, Tunki avisa si algo quedó mal. Las
pruebas (`pytest`) también verifican que cada ejemplo traducido funcione.
