"""
Editor de código: números de línea, colores (resaltador.py), subrayado de
errores y advertencias, la línea que se está ejecutando, sangría
automática y tamaño de letra ajustable (Ctrl + rueda del ratón).
"""
from typing import List, Optional

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QPainter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from antachawi.ide import tema
from antachawi.ide.resaltador import ResaltadorAntachawi
from antachawi.mensajes import ADVERTENCIA

SANGRIA = "    "

COLOR_ERROR = QColor(tema.ROJO)
FONDO_ERROR = QColor(tema.ROJO_SUAVE)
COLOR_ADVERTENCIA = QColor(tema.AMARILLO)
FONDO_EJECUCION = QColor(tema.EDITOR_EJECUCION)
FONDO_LINEA_ACTUAL = QColor(tema.EDITOR_LINEA_ACTUAL)
FONDO_MARGEN = QColor(tema.EDITOR_MARGEN)
COLOR_NUMERO = QColor(tema.EDITOR_NUMERO)
COLOR_NUMERO_ACTUAL = QColor(tema.TEXTO)
COLOR_BORDE_MARGEN = QColor(tema.BORDE)


class MargenDeLineas(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.ancho_del_margen(), 0)

    def paintEvent(self, evento):
        self.editor.pintar_margen(evento)


def _sangria_de(linea: str) -> str:
    return linea[:len(linea) - len(linea.lstrip(" \t"))]


class EditorDeCodigo(QPlainTextEdit):
    tamano_cambiado = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editor")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.resaltador = ResaltadorAntachawi(self.document())
        self.marcas: List[dict] = []        # errores y advertencias
        self.linea_en_ejecucion: Optional[int] = None
        self.tamano = tema.TAMANO_CODIGO

        self.margen = MargenDeLineas(self)
        self.blockCountChanged.connect(self._actualizar_ancho_margen)
        self.updateRequest.connect(self._actualizar_margen)
        self.cursorPositionChanged.connect(self._redibujar_marcas)
        self.cambiar_tamano(self.tamano)

    # ------------------------------------------------------------------
    # Tamaño de letra
    # ------------------------------------------------------------------
    def cambiar_tamano(self, tamano: int):
        tamano = max(tema.TAMANO_MINIMO, min(tema.TAMANO_MAXIMO, tamano))
        self.tamano = tamano
        self.setFont(tema.fuente_de_codigo(tamano))
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * len(SANGRIA))
        self._actualizar_ancho_margen()
        self.resizeEvent(None)
        self.tamano_cambiado.emit(tamano)

    def wheelEvent(self, evento):
        if evento.modifiers() & Qt.KeyboardModifier.ControlModifier:
            paso = 1 if evento.angleDelta().y() > 0 else -1
            self.cambiar_tamano(self.tamano + paso)
            evento.accept()
            return
        super().wheelEvent(evento)

    # ------------------------------------------------------------------
    # Sangría automática
    # ------------------------------------------------------------------
    def keyPressEvent(self, evento):
        tecla = evento.key()
        sin_modificadores = not (evento.modifiers()
                                 & ~Qt.KeyboardModifier.KeypadModifier)
        if tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                sin_modificadores:
            self._nueva_linea_con_sangria()
        elif tecla == Qt.Key.Key_Tab and sin_modificadores:
            self.insertPlainText(SANGRIA)
        elif tecla == Qt.Key.Key_Backspace and sin_modificadores and \
                self._borrar_sangria():
            pass
        elif evento.text() == "}" and self._quitar_un_nivel():
            self.insertPlainText("}")
        else:
            super().keyPressEvent(evento)

    def _antes_del_cursor(self) -> str:
        cursor = self.textCursor()
        return cursor.block().text()[:cursor.positionInBlock()]

    def _nueva_linea_con_sangria(self):
        antes = self._antes_del_cursor()
        sangria = _sangria_de(antes)
        if antes.rstrip().endswith("{"):
            sangria += SANGRIA
        self.textCursor().insertText("\n" + sangria)
        self.ensureCursorVisible()

    def _borrar_espacios_antes(self, cuantos: int) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection() or cuantos <= 0:
            return False
        cursor.movePosition(QTextCursor.MoveOperation.Left,
                            QTextCursor.MoveMode.KeepAnchor, cuantos)
        cursor.removeSelectedText()
        return True

    def _borrar_sangria(self) -> bool:
        """Retroceso dentro de la sangría: borra un nivel completo."""
        antes = self._antes_del_cursor()
        if not antes or antes.strip(" "):
            return False
        sobrante = len(antes) % len(SANGRIA) or len(SANGRIA)
        return self._borrar_espacios_antes(sobrante)

    def _quitar_un_nivel(self) -> bool:
        """Al escribir '}' al comienzo de una línea, la alinea con su '{'."""
        antes = self._antes_del_cursor()
        if not antes or antes.strip(" "):
            return False
        return self._borrar_espacios_antes(min(len(SANGRIA), len(antes)))

    # ------------------------------------------------------------------
    # Margen con los números de línea
    # ------------------------------------------------------------------
    def ancho_del_margen(self) -> int:
        digitos = max(2, len(str(self.blockCount())))
        return 30 + self.fontMetrics().horizontalAdvance("9") * digitos

    def _actualizar_ancho_margen(self, *_):
        self.setViewportMargins(self.ancho_del_margen(), 0, 0, 0)

    def _actualizar_margen(self, rect, dy):
        if dy:
            self.margen.scroll(0, dy)
        else:
            self.margen.update(0, rect.y(), self.margen.width(),
                               rect.height())

    def resizeEvent(self, evento):
        if evento is not None:
            super().resizeEvent(evento)
        contenido = self.contentsRect()
        self.margen.setGeometry(QRect(contenido.left(), contenido.top(),
                                      self.ancho_del_margen(),
                                      contenido.height()))

    def _color_de_punto(self, numero: int) -> Optional[QColor]:
        gravedades = {m["gravedad"] for m in self.marcas
                      if m["linea"] == numero}
        if not gravedades:
            return None
        if gravedades == {ADVERTENCIA}:
            return COLOR_ADVERTENCIA
        return COLOR_ERROR

    def pintar_margen(self, evento):
        pintor = QPainter(self.margen)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.fillRect(evento.rect(), FONDO_MARGEN)
        pintor.setPen(COLOR_BORDE_MARGEN)
        borde = self.margen.width() - 1
        pintor.drawLine(borde, evento.rect().top(), borde,
                        evento.rect().bottom())
        actual = self.textCursor().blockNumber() + 1
        bloque = self.firstVisibleBlock()
        arriba = round(self.blockBoundingGeometry(bloque)
                       .translated(self.contentOffset()).top())
        while bloque.isValid() and arriba <= evento.rect().bottom():
            alto = round(self.blockBoundingRect(bloque).height())
            if bloque.isVisible():
                self._pintar_numero(pintor, bloque.blockNumber() + 1,
                                    arriba, alto, actual)
            arriba += alto
            bloque = bloque.next()
        pintor.end()

    def _pintar_numero(self, pintor, numero, arriba, alto, actual):
        punto = self._color_de_punto(numero)
        if punto is not None:
            radio = max(3, alto // 6)
            pintor.setPen(Qt.PenStyle.NoPen)
            pintor.setBrush(punto)
            pintor.drawEllipse(8, arriba + alto // 2 - radio,
                               radio * 2, radio * 2)
        if punto == COLOR_ERROR:
            color = COLOR_ERROR
        elif numero == actual:
            color = COLOR_NUMERO_ACTUAL
        else:
            color = COLOR_NUMERO
        fuente = self.font()
        fuente.setBold(punto == COLOR_ERROR or numero == actual)
        pintor.setFont(fuente)
        pintor.setPen(color)
        pintor.drawText(0, arriba, self.margen.width() - 10, alto,
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter, str(numero))

    # ------------------------------------------------------------------
    # Marcas: errores, advertencias y línea en ejecución
    # ------------------------------------------------------------------
    def marcar(self, marcas: List[dict]):
        """Subraya los errores y advertencias (formato de errores.py)."""
        self.marcas = list(marcas)
        self._redibujar_marcas()

    def marcar_ejecucion(self, linea: Optional[int]):
        self.linea_en_ejecucion = linea
        self._redibujar_marcas()

    def _redibujar_marcas(self):
        # El orden importa: lo que va después se pinta encima.
        selecciones = [self._fondo_de_linea(
            self.textCursor().blockNumber() + 1, FONDO_LINEA_ACTUAL)]
        selecciones += [self._fondo_de_linea(m["linea"], FONDO_ERROR)
                        for m in self.marcas
                        if m["gravedad"] != ADVERTENCIA
                        and self._bloque(m["linea"]).isValid()]
        if self.linea_en_ejecucion is not None:
            selecciones.append(self._fondo_de_linea(
                self.linea_en_ejecucion, FONDO_EJECUCION))
        selecciones += [self._seleccion(m) for m in self.marcas
                        if self._bloque(m["linea"]).isValid()]
        self.setExtraSelections(selecciones)
        self.margen.update()

    def _bloque(self, linea: int):
        return self.document().findBlockByNumber(linea - 1)

    def _fondo_de_linea(self, linea, color):
        seleccion = QTextEdit.ExtraSelection()
        seleccion.format.setBackground(color)
        seleccion.format.setProperty(
            QTextFormat.Property.FullWidthSelection, True)
        seleccion.cursor = QTextCursor(self._bloque(linea))
        return seleccion

    def _seleccion(self, marca):
        bloque = self._bloque(marca["linea"])
        cursor = QTextCursor(bloque)
        columna = marca.get("columna")
        if columna:
            inicio = min(columna - 1, max(0, bloque.length() - 1))
            cursor.setPosition(bloque.position() + inicio)
            cursor.movePosition(QTextCursor.MoveOperation.Right,
                                QTextCursor.MoveMode.KeepAnchor,
                                marca.get("longitud", 1))
        else:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        seleccion = QTextEdit.ExtraSelection()
        formato = QTextCharFormat()
        formato.setUnderlineStyle(
            QTextCharFormat.UnderlineStyle.WaveUnderline)
        formato.setUnderlineColor(COLOR_ADVERTENCIA
                                  if marca["gravedad"] == ADVERTENCIA
                                  else COLOR_ERROR)
        seleccion.format = formato
        seleccion.cursor = cursor
        return seleccion

    # ------------------------------------------------------------------
    # Posiciones en pantalla (para Tunki)
    # ------------------------------------------------------------------
    def rect_de_linea(self, linea: int) -> Optional[QRect]:
        """Rectángulo de la línea en coordenadas del viewport, o None si
        la línea no existe."""
        bloque = self._bloque(linea)
        if not bloque.isValid():
            return None
        geometria = self.blockBoundingGeometry(bloque).translated(
            self.contentOffset())
        return geometria.toRect()

    def ir_a_linea(self, linea: int, columna: int = 1):
        bloque = self._bloque(linea)
        if not bloque.isValid():
            return
        cursor = QTextCursor(bloque)
        cursor.setPosition(bloque.position()
                           + min(columna - 1, bloque.length() - 1))
        self.setTextCursor(cursor)
        self.centerCursor()
