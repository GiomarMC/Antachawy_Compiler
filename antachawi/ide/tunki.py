"""
Tunki, la mascota del entorno: vive encima del editor, vuela hasta la
línea donde hay un error y lo explica con un globo de diálogo.

    tunki.volar_a_linea(4)            vuela junto a la línea 4
    tunki.volar_a_casa()              vuelve a la esquina
    tunki.decir("texto", ERROR)       muestra el globo (texto con HTML)
    tunki.humor = sprite.FELIZ        cambia la cara
    tunki.celebrar()                  salta de alegría
"""
import random
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from antachawi.ide import sprite

ESCALA = 4                      # cada píxel del dibujo mide 4x4
MARGEN_ARRIBA = 7               # espacio (en píxeles del dibujo) para el "!"
SEPARACION = 14                 # distancia al borde del editor
DURACION_VUELO = 650            # milisegundos

# Tipos de globo
INFO = "info"
ERROR = "error"
EXITO = "exito"
COLORES_GLOBO = {
    INFO: ("#fff8e7", "#e8a33a"),
    ERROR: ("#fff1f1", "#e03131"),
    EXITO: ("#ebfbee", "#2f9e44"),
}
COLA = 10                       # tamaño de la colita del globo
ANCHO_GLOBO = 300


class Globo(QWidget):
    """Globo de diálogo con una colita que apunta a Tunki."""

    clicado = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.tipo = INFO
        self.cola_arriba = True
        self.etiqueta = QLabel(self)
        self.etiqueta.setWordWrap(True)
        self.etiqueta.setTextFormat(Qt.TextFormat.RichText)
        self.etiqueta.setStyleSheet("color: #2b2118; font-size: 14px;")
        self._diseno = QVBoxLayout(self)
        self._ajustar_margenes()
        self._diseno.addWidget(self.etiqueta)
        self.setFixedWidth(ANCHO_GLOBO)
        self.hide()

    def _ajustar_margenes(self):
        arriba, abajo = (COLA + 10, 10) if self.cola_arriba \
            else (10, COLA + 10)
        self._diseno.setContentsMargins(14, arriba, 14, abajo)

    def mostrar(self, texto: str, tipo: str):
        self.tipo = tipo
        self.etiqueta.setText(texto)
        self._diseno.activate()
        self.adjustSize()
        self.show()
        self.raise_()
        self.update()

    def poner_cola(self, arriba: bool):
        if arriba != self.cola_arriba:
            self.cola_arriba = arriba
            self._ajustar_margenes()
            self._diseno.activate()
            self.adjustSize()
        self.update()

    def mousePressEvent(self, evento):
        self.clicado.emit()

    def paintEvent(self, evento):
        fondo, borde = COLORES_GLOBO[self.tipo]
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        caja = QRect(1, COLA if self.cola_arriba else 1,
                     self.width() - 2, self.height() - COLA - 2)
        camino = QPainterPath()
        camino.addRoundedRect(caja, 12, 12)
        # La colita sale cerca del borde derecho, hacia donde está Tunki
        x = self.width() - 40
        if self.cola_arriba:
            punta, base = caja.top() - COLA + 1, caja.top() + 1
        else:
            punta, base = caja.bottom() + COLA - 1, caja.bottom() - 1
        cola = QPainterPath()
        cola.moveTo(x - COLA, base)
        cola.lineTo(x + 4, punta)
        cola.lineTo(x + COLA, base)
        cola.closeSubpath()
        camino = camino.united(cola)
        pintor.setPen(QPen(QColor(borde), 2))
        pintor.setBrush(QColor(fondo))
        pintor.drawPath(camino)
        pintor.end()


class Tunki(QWidget):
    """Se coloca como hijo del viewport del editor."""

    clicado = Signal()

    def __init__(self, editor):
        super().__init__(editor.viewport())
        self.editor = editor
        self._humor = sprite.NORMAL
        self._parpadeando = False
        self._arriba = False            # para flotar suavemente
        self.linea: Optional[int] = None
        self._imagenes = {humor: self._escalar(sprite.imagen(humor))
                          for humor in sprite.HUMORES}
        self.setFixedSize(sprite.ANCHO * ESCALA,
                          (sprite.ALTO + MARGEN_ARRIBA) * ESCALA)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.globo = Globo(editor.viewport())
        self.globo.clicado.connect(self.callar)

        self._vuelo = QPropertyAnimation(self, b"pos", self)
        self._vuelo.setDuration(DURACION_VUELO)
        self._vuelo.setEasingCurve(QEasingCurve.Type.OutBack)
        self._salto = None

        self._flotar = QTimer(self, interval=550)
        self._flotar.timeout.connect(self._al_flotar)
        self._flotar.start()
        self._parpadeo = QTimer(self, singleShot=True)
        self._parpadeo.timeout.connect(self._parpadear)
        self._programar_parpadeo()

        editor.verticalScrollBar().valueChanged.connect(self.seguir)
        editor.viewport().installEventFilter(self)
        self.move(self.posicion_de_casa())
        self.show()

    @staticmethod
    def _escalar(imagen) -> QPixmap:
        return QPixmap.fromImage(imagen.scaled(
            imagen.width() * ESCALA, imagen.height() * ESCALA,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation))

    # ------------------------------------------------------------------
    # Estado de ánimo
    # ------------------------------------------------------------------
    @property
    def humor(self) -> str:
        return self._humor

    @humor.setter
    def humor(self, humor: str):
        self._humor = humor
        self.update()

    def _programar_parpadeo(self):
        self._parpadeo.start(random.randint(2500, 5000))

    def _parpadear(self):
        if self._parpadeando:
            self._parpadeando = False
            self._programar_parpadeo()
        elif self._humor in (sprite.NORMAL, sprite.PENSANDO):
            self._parpadeando = True
            self._parpadeo.start(140)       # ojo cerrado un momento
        else:
            self._programar_parpadeo()
        self.update()

    def _al_flotar(self):
        self._arriba = not self._arriba
        self.update()

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def paintEvent(self, evento):
        pintor = QPainter(self)
        humor = sprite.PARPADEO if self._parpadeando else self._humor
        y = (MARGEN_ARRIBA - (1 if self._arriba else 0)) * ESCALA
        pintor.drawPixmap(0, y, self._imagenes[humor])
        if self._humor == sprite.SORPRENDIDO:
            self._pintar_exclamacion(pintor)
        pintor.end()

    @staticmethod
    def _pintar_exclamacion(pintor):
        # Un "!" en pixel art sobre la cresta
        x = 15 * ESCALA
        for fila in (0, 1, 2, 3, 5):
            pintor.fillRect(x, fila * ESCALA, ESCALA * 2, ESCALA,
                            QColor("#e03131"))

    def mousePressEvent(self, evento):
        self.clicado.emit()

    # ------------------------------------------------------------------
    # Movimiento
    # ------------------------------------------------------------------
    def posicion_de_casa(self) -> QPoint:
        area = self.parentWidget().rect()
        return QPoint(area.width() - self.width() - SEPARACION,
                      area.height() - self.height() - SEPARACION)

    def posicion_para_linea(self, linea: int) -> Optional[QPoint]:
        rect = self.editor.rect_de_linea(linea)
        if rect is None:
            return None
        area = self.parentWidget().rect()
        # El ojo de Tunki queda a la altura de la línea
        ojo = (MARGEN_ARRIBA + 11) * ESCALA
        y = rect.center().y() - ojo
        y = max(0, min(y, area.height() - self.height()))
        return QPoint(area.width() - self.width() - SEPARACION, y)

    def _ir(self, destino: QPoint, animado: bool):
        self._vuelo.stop()
        if not animado or destino == self.pos():
            self.move(destino)
            return
        self._vuelo.setStartValue(self.pos())
        self._vuelo.setEndValue(destino)
        self._vuelo.start()

    def volar_a_linea(self, linea: int, animado: bool = True):
        destino = self.posicion_para_linea(linea)
        if destino is None:
            self.volar_a_casa(animado)
            return
        self.linea = linea
        self._ir(destino, animado)

    def volar_a_casa(self, animado: bool = True):
        self.linea = None
        self._ir(self.posicion_de_casa(), animado)

    def seguir(self, *_):
        """Se recoloca sin animación (al desplazar o cambiar el tamaño
        del editor)."""
        if self._vuelo.state() == QPropertyAnimation.State.Running:
            self._vuelo.stop()
        if self.linea is None:
            self.move(self.posicion_de_casa())
        else:
            self.volar_a_linea(self.linea, animado=False)

    def celebrar(self):
        """Dos saltitos (al terminar el vuelo, si está volando)."""
        if self._vuelo.state() == QPropertyAnimation.State.Running:
            self._vuelo.stop()
            self.move(self._vuelo.endValue())
        base = self.pos()
        arriba = base - QPoint(0, 6 * ESCALA)
        self._salto = QSequentialAnimationGroup(self)
        for _ in range(2):
            for inicio, fin in ((base, arriba), (arriba, base)):
                tramo = QPropertyAnimation(self, b"pos")
                tramo.setDuration(160)
                tramo.setStartValue(inicio)
                tramo.setEndValue(fin)
                tramo.setEasingCurve(QEasingCurve.Type.OutQuad)
                self._salto.addAnimation(tramo)
        self._salto.start()

    def eventFilter(self, objeto, evento):
        if evento.type() == QEvent.Type.Resize:
            self.seguir()
        return False

    def moveEvent(self, evento):
        super().moveEvent(evento)
        self.colocar_globo()

    # ------------------------------------------------------------------
    # Globo de diálogo
    # ------------------------------------------------------------------
    def decir(self, texto: str, tipo: str = INFO):
        self.globo.mostrar(texto, tipo)
        self.colocar_globo()

    def callar(self):
        self.globo.hide()

    def colocar_globo(self):
        """Debajo de Tunki; si no cabe, encima."""
        if not self.globo.isVisible():
            return
        area = self.parentWidget().rect()
        cabe_abajo = (self.geometry().bottom() + self.globo.height()
                      <= area.height())
        self.globo.poner_cola(arriba=cabe_abajo)
        x = max(0, self.geometry().right() - self.globo.width() + 20)
        x = min(x, area.width() - self.globo.width())
        if cabe_abajo:
            y = self.geometry().bottom() - 4
        else:
            y = self.y() + MARGEN_ARRIBA * ESCALA - self.globo.height()
        self.globo.move(x, max(0, y))
        self.globo.raise_()
        self.raise_()
