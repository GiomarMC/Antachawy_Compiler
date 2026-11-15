"""
Íconos de la barra en pixel art, con el mismo estilo que Tunki.

Igual que en sprite.py, cada dibujo es una cuadrícula de texto: cada
letra es un color de PALETA y '.' es transparente. Todos miden LADO x LADO
(lo verifica tests/test_ide.py) y se muestran a ESCALA sin suavizar.
"""
from typing import Dict, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap

LADO = 16
ESCALA = 2

PALETA = {
    "K": "#3b2a1e",     # contorno
    "W": "#ffffff",     # papel
    "L": "#c9b8a0",     # renglones
    "G": "#2f9e44",     # verde
    "Y": "#ffc53d",     # carpeta
    "P": "#f59f00",     # carpeta, frente
    "B": "#1c7ed6",     # disquete
    "S": "#d0ebff",     # etiqueta del disquete
    "M": "#74c0fc",     # brillo azul
    "R": "#c92a2a",     # tapa del libro
}

DIBUJOS: Dict[str, List[str]] = {
    "nuevo": """
................
..KKKKKKKK......
..KWWWWWWKK.....
..KWWWWWWKWK....
..KWWWWWWKKKK...
..KWLLLLLLWWK...
..KWWWWWWWWWK...
..KWLLLLLLWWK...
..KWWWWWWWKKKK..
..KWLLLLWWKGGK..
..KWWWWWKKKGGKKK
..KWLLLLKGGGGGGK
..KWWWWWKGGGGGGK
..KWWWWWKKKGGKKK
..KKKKKKKKKGGK..
..........KKKK..
""",
    "abrir": """
................
................
.KKKKK..........
KYYYYYK.........
KYYYYYYKKKKKKK..
KYYYYYYYYYYYYK..
KYYKKKKKKKKKKKKK
KYKPPPPPPPPPPPPK
KYKPPPPPPPPPPPK.
KKPPPPPPPPPPPPK.
KKPPPPPPPPPPPK..
KPPPPPPPPPPPPK..
KPPPPPPPPPPPPK..
KKKKKKKKKKKKKK..
................
................
""",
    "guardar": """
................
.KKKKKKKKKKKKK..
.KBBWWWWWWWBBBK.
.KBBWWWWWWKKBBBK
.KBBWWWWWWKKBBBK
.KBBWWWWWWWWBBBK
.KBBBBBBBBBBBBBK
.KBBBBBBBBBBBBBK
.KBBSSSSSSSSSBBK
.KBBSLLLLLLLSBBK
.KBBSSSSSSSSSBBK
.KBBSLLLLLLLSBBK
.KBBSSSSSSSSSBBK
.KMBSSSSSSSSSBBK
.KKKKKKKKKKKKKKK
................
""",
    "ejemplos": """
................
................
.KKKK......KKKK.
KWWWWKK..KKWWWWK
KWLLWWWKKWWWLLWK
KWWWWWWKKWWWWWWK
KWLLLWWKKWWLLLWK
KWWWWWWKKWWWWWWK
KWLLWWWKKWWWLLWK
KWWWWWWKKWWWWWWK
KWWWWKKKKKKWWWWK
KRKKKRRKKRRKKKRK
.KRRRRRKKRRRRRK.
..KKKKK..KKKKK..
................
................
""",
    "ejecutar": """
................
................
................
....WW..........
....WWWW........
....WWWWWW......
....WWWWWWWW....
....WWWWWWWWWW..
....WWWWWWWWWW..
....WWWWWWWW....
....WWWWWW......
....WWWW........
....WW..........
................
................
................
""",
}

NOMBRES = tuple(DIBUJOS)


def filas(nombre: str) -> List[str]:
    return DIBUJOS[nombre].split()


def imagen_de_cuadricula(cuadricula: List[str], paleta: Dict[str, str],
                         escala: int = 1) -> QPixmap:
    """Convierte una cuadrícula de letras en una imagen pixelada."""
    img = QImage(len(cuadricula[0]), len(cuadricula),
                 QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    for y, fila in enumerate(cuadricula):
        for x, letra in enumerate(fila):
            if letra in paleta:
                img.setPixelColor(x, y, QColor(paleta[letra]))
    return QPixmap.fromImage(img.scaled(
        img.width() * escala, img.height() * escala,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation))


def icono(nombre: str) -> QIcon:
    pixeles = imagen_de_cuadricula(filas(nombre), PALETA, ESCALA)
    resultado = QIcon(pixeles)
    # Desactivado: el mismo dibujo, más transparente (en vez del gris
    # que Qt genera por su cuenta).
    apagado = QPixmap(pixeles.size())
    apagado.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(apagado)
    pintor.setOpacity(0.55)
    pintor.drawPixmap(0, 0, pixeles)
    pintor.end()
    resultado.addPixmap(apagado, QIcon.Mode.Disabled)
    return resultado


TAMANOS_DEL_ICONO = (16, 24, 32, 48, 64, 128, 256, 512)


def imagen_de_la_aplicacion(lado: int) -> QImage:
    """Tunki feliz centrado en un cuadrado de lado x lado, pixelado (sin
    suavizar). Es el ícono de la ventana y de los instaladores."""
    from antachawi.ide import sprite

    dibujo = sprite.imagen(sprite.FELIZ)
    escala = max(1, lado // max(dibujo.width(), dibujo.height()))
    dibujo = dibujo.scaled(
        dibujo.width() * escala, dibujo.height() * escala,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation)
    if dibujo.width() > lado or dibujo.height() > lado:
        dibujo = dibujo.scaled(
            lado, lado, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
    resultado = QImage(lado, lado, QImage.Format.Format_ARGB32)
    resultado.fill(QColor(0, 0, 0, 0))
    pintor = QPainter(resultado)
    pintor.drawImage((lado - dibujo.width()) // 2,
                     (lado - dibujo.height()) // 2, dibujo)
    pintor.end()
    return resultado


def icono_de_la_aplicacion() -> QIcon:
    resultado = QIcon()
    for lado in TAMANOS_DEL_ICONO:
        resultado.addPixmap(QPixmap.fromImage(imagen_de_la_aplicacion(lado)))
    return resultado
