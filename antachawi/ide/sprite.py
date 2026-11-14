"""
Tunki en pixel art. "Tunki" es el nombre en quechua del gallito de las
rocas (Rupicola peruvianus).

El dibujo es una cuadrícula de texto: cada letra es un color de PALETA y
'.' es transparente. Los estados de ánimo solo cambian el ojo, que se
dibuja encima del cuerpo con OJOS.

Para editar el dibujo basta con cambiar las letras: todas las filas deben
tener el mismo ancho (lo verifica tests/test_ide.py).
"""
from typing import Dict, List, Tuple

from PySide6.QtGui import QColor, QImage

PALETA = {
    "K": "#2a0e08",     # contorno
    "O": "#ff5a1f",     # naranja del cuerpo
    "Y": "#ff9a3c",     # brillo de la cresta
    "R": "#c8380f",     # sombra
    "B": "#1c1c22",     # alas y cola negras
    "G": "#a9b0b8",     # mancha gris del ala
    "W": "#ffffff",     # brillo del ojo
    "E": "#120806",     # pupila
    "I": "#ffd34d",     # anillo amarillo del ojo
    "P": "#f2c14e",     # pico
    "L": "#e8a33a",     # patas
    "C": "#ff8fa3",     # mejillas (cuando está feliz)
}

CUERPO = """
.......KKKKK..........
.....KKYOYOYKK........
....KYOYOOOOOOK.......
...KYOOOOOOOOOOK......
..KYOOOOOOOOOOOOK.....
.KYOOOOOOOOOOOOOK.....
.KOOOOOOOOOOOOOOOK....
KYOOOOOOOOOOOOOOOK....
KOOOORRRRROOOOOOOK....
KPPRROOOROOOOOOOOK....
.KPPOOOOOOOOOOOORK....
..KKOOOOOOOOOOOORK....
....KOOOOOOOOOOORKK...
....KRROOOOOOOBBBBK...
....KROOOOOOOBBGGGBBK.
...KROOOOOOOBBGGGBBBBK
...KROOOOOOBBBBBBBBBBK
...KRROOOOOBBBBBBBBBK.
....KRROOOOOBBBBBBKBBK
.....KKRRRRRKKKKKKBBBK
.......KLK.KLK...KBBK.
.......KLK.KLK....KK..
......KLLKKLLK........
""".split()

NORMAL = "normal"
FELIZ = "feliz"
SORPRENDIDO = "sorprendido"
PENSANDO = "pensando"
PARPADEO = "parpadeo"

# Ojo de cada estado: fila -> (columna inicial, píxeles)
OJOS: Dict[str, Dict[int, Tuple[int, str]]] = {
    NORMAL: {9: (5, "III"), 10: (4, "IWEEI"), 11: (4, "IEEEI"),
             12: (5, "III")},
    FELIZ: {9: (5, "KKK"), 10: (4, "KOOOK"), 12: (6, "CC")},
    SORPRENDIDO: {9: (5, "III"), 10: (4, "IWWWI"), 11: (4, "IWEWI"),
                  12: (5, "III")},
    PENSANDO: {9: (5, "III"), 10: (4, "IEEWI"), 11: (4, "IEEII"),
               12: (5, "III")},
    PARPADEO: {11: (4, "OKKKO")},
}
HUMORES = tuple(OJOS)

ANCHO = len(CUERPO[0])
ALTO = len(CUERPO)


def filas(humor: str = NORMAL) -> List[str]:
    """La cuadrícula con el ojo del estado de ánimo dibujado."""
    resultado = list(CUERPO)
    for fila, (columna, pixeles) in OJOS[humor].items():
        texto = resultado[fila]
        resultado[fila] = (texto[:columna] + pixeles
                           + texto[columna + len(pixeles):])
    return resultado


def imagen(humor: str = NORMAL, mirando_a_la_derecha=False) -> QImage:
    """Imagen de ANCHO x ALTO píxeles. Para mostrarla grande hay que
    escalarla sin suavizar (Qt.FastTransformation) para que se vean los
    píxeles."""
    img = QImage(ANCHO, ALTO, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    for y, fila in enumerate(filas(humor)):
        for x, letra in enumerate(fila):
            if letra in PALETA:
                img.setPixelColor(x, y, QColor(PALETA[letra]))
    if mirando_a_la_derecha:
        img = img.mirrored(True, False)
    return img
