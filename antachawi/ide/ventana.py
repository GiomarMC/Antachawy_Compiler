"""
Ventana principal de Antachawi Yachay.

El programa se analiza solo mientras se escribe (con una pequeña pausa
para no molestar), y Tunki vuela hasta el primer error. "Ejecutar" usa el
intérprete (antachawi/interprete.py), así que no hace falta tener gcc.

Los colores y la hoja de estilo están en tema.py; los íconos, en
iconos.py.
"""
import html
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from antachawi import api, mensajes
from antachawi.errores import texto_de
from antachawi.ide import iconos, sprite, tema
from antachawi.ide.editor import EditorDeCodigo
from antachawi.ide.tunki import ERROR, EXITO, INFO, Tunki
from antachawi.mensajes import ADVERTENCIA, AMBOS, ES, QU
from antachawi.traduccion import EJEMPLOS_QUECHUA, numero_de_ejemplo

TITULO = "Antachawi Yachay"
EJEMPLOS = Path(__file__).parent / "ejemplos"
PAUSA_ANTES_DE_ANALIZAR = 700       # milisegundos sin escribir
MAXIMO_DE_PASOS = 100_000
PLANTILLA = 'qhapaq()\n{\n    rikuchiy("¡Hola!")\n}\n'
PLANTILLAS = {ES: PLANTILLA,
              QU: 'qhapaq()\n{\n    rikuchiy("¡Napaykullayki!")\n}\n'}
NOMBRES_DE_IDIOMA = {ES: "Español", QU: "Quechua", AMBOS: "Español + Quechua"}
ESCALA_DE_LA_MARCA = 2              # Tunki pequeño junto al nombre
TAMANO_ICONOS = QSize(iconos.LADO * iconos.ESCALA,
                      iconos.LADO * iconos.ESCALA)


def nombre_de_ejemplo(ruta: Path) -> str:
    """01_encuentra_el_error.awi -> Encuentra el error"""
    nombre = ruta.stem.split("_", 1)[-1].replace("_", " ")
    return nombre[:1].upper() + nombre[1:]


def ejemplos_en(idioma: str) -> List[Path]:
    """Los ejemplos en ese idioma; los que aún no están traducidos al
    quechua (ejemplos/qu/) se muestran en español."""
    espanol = sorted(EJEMPLOS.glob("*.awi"))
    if idioma == ES:
        return espanol
    quechua = {numero_de_ejemplo(r): r
               for r in EJEMPLOS_QUECHUA.glob("*.awi")}
    return [quechua.get(numero_de_ejemplo(r), r) for r in espanol]


def _punto(color: str, lado: int = 12) -> QIcon:
    """Circulito de color para la lista de problemas."""
    imagen = QPixmap(lado, lado)
    imagen.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(QColor(color))
    pintor.drawEllipse(1, 1, lado - 2, lado - 2)
    pintor.end()
    return QIcon(imagen)


def _estilo_de_insignia(fondo: str, letra: str) -> str:
    return (f"background: {fondo}; color: {letra}; border-radius: 9px; "
            "padding: 1px 9px; font-weight: bold;")


class HiloDeEjecucion(QThread):
    """Ejecuta el programa sin congelar la ventana."""

    terminado = Signal(object)

    def __init__(self, resultado, parent=None):
        super().__init__(parent)
        self.resultado = resultado

    def run(self):
        self.terminado.emit(self.resultado.ejecutar(MAXIMO_DE_PASOS))


class FranjaDeAguayo(QWidget):
    """Una franja de colores como la de un aguayo andino."""

    ALTO = 6
    ANCHO_DE_BANDA = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.ALTO)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        x, i = 0, 0
        while x < self.width():
            pintor.fillRect(x, 0, self.ANCHO_DE_BANDA, self.ALTO,
                            QColor(tema.AGUAYO[i % len(tema.AGUAYO)]))
            # Rombitos claros, como el tejido
            centro = x + self.ANCHO_DE_BANDA // 2
            pintor.fillRect(centro - 1, 1, 2, self.ALTO - 2,
                            QColor(255, 255, 255, 120))
            pintor.fillRect(centro - 3, 2, 6, self.ALTO - 4,
                            QColor(255, 255, 255, 70))
            x += self.ANCHO_DE_BANDA
            i += 1
        pintor.end()


class Tarjeta(QFrame):
    """Panel blanco con bordes redondeados, un título y una insignia."""

    def __init__(self, contenido: QWidget, con_titulo: bool = True,
                 margen: int = 10):
        super().__init__(objectName="tarjeta")
        diseno = QVBoxLayout(self)
        diseno.setContentsMargins(margen, margen, margen, margen)
        diseno.setSpacing(8)
        self.titulo = QLabel(objectName="titulo_tarjeta")
        self.insignia = QLabel(objectName="insignia")
        self.insignia.hide()
        if con_titulo:
            cabecera = QHBoxLayout()
            cabecera.setContentsMargins(4, 0, 4, 0)
            cabecera.addWidget(self.titulo)
            cabecera.addStretch()
            cabecera.addWidget(self.insignia)
            diseno.addLayout(cabecera)
        diseno.addWidget(contenido)


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        aplicacion = QApplication.instance()
        if aplicacion is not None:
            tema.aplicar_tema(aplicacion)
        self.idioma = AMBOS
        self.ruta: Optional[Path] = None
        self.resultado = None
        self.errores: List[dict] = []
        self.error_actual = 0
        self.hilo: Optional[HiloDeEjecucion] = None
        self._puntos = {ERROR: _punto(tema.ROJO),
                        ADVERTENCIA: _punto(tema.AMARILLO)}

        self.resize(1180, 800)
        self._crear_editor_y_paneles()
        self._crear_barra()
        self._crear_barra_de_estado()

        self.temporizador = QTimer(self, singleShot=True,
                                   interval=PAUSA_ANTES_DE_ANALIZAR)
        self.temporizador.timeout.connect(self.analizar_ahora)
        self.editor.textChanged.connect(self._al_cambiar_texto)
        self.editor.cursorPositionChanged.connect(self._mostrar_posicion)

        self.cargar_texto(PLANTILLA)
        self.tunki.humor = sprite.FELIZ
        self._decir(mensajes.TUNKI_SALUDO, INFO)
        self._actualizar_textos()

    # ------------------------------------------------------------------
    # Construcción de la ventana
    # ------------------------------------------------------------------
    def _crear_editor_y_paneles(self):
        self.editor = EditorDeCodigo()
        self.tunki = Tunki(self.editor)
        self.tunki.clicado.connect(self.siguiente_error)
        self.editor.tamano_cambiado.connect(self._al_cambiar_tamano)

        self.salida = QPlainTextEdit(readOnly=True, objectName="salida")
        self.salida.setFont(tema.fuente_de_codigo(tema.TAMANO_CODIGO - 2))
        colores = self.salida.palette()
        colores.setColor(colores.ColorRole.PlaceholderText,
                         QColor(tema.CONSOLA_TENUE))
        self.salida.setPalette(colores)
        self.problemas = QListWidget(objectName="problemas")
        self.problemas.setIconSize(QSize(12, 12))
        self.problemas.setWordWrap(True)
        self.problemas.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.problemas.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.problemas.itemClicked.connect(self._al_elegir_problema)

        self.tarjeta_salida = Tarjeta(self.salida)
        self.tarjeta_problemas = Tarjeta(self.problemas)
        self.titulo_salida = self.tarjeta_salida.titulo
        self.titulo_problemas = self.tarjeta_problemas.titulo
        self.insignia_problemas = self.tarjeta_problemas.insignia

        abajo = QSplitter(Qt.Orientation.Horizontal, handleWidth=12)
        abajo.addWidget(self.tarjeta_salida)
        abajo.addWidget(self.tarjeta_problemas)
        abajo.setSizes([620, 520])

        division = QSplitter(Qt.Orientation.Vertical, handleWidth=12)
        division.addWidget(Tarjeta(self.editor, con_titulo=False, margen=3))
        division.addWidget(abajo)
        division.setStretchFactor(0, 3)
        division.setStretchFactor(1, 1)
        division.setSizes([540, 220])

        contenido = QWidget()
        diseno_contenido = QVBoxLayout(contenido)
        diseno_contenido.setContentsMargins(14, 12, 14, 12)
        diseno_contenido.addWidget(division)

        central = QWidget(objectName="central")
        diseno = QVBoxLayout(central)
        diseno.setContentsMargins(0, 0, 0, 0)
        diseno.setSpacing(0)
        diseno.addWidget(FranjaDeAguayo())
        diseno.addWidget(contenido)
        self.setCentralWidget(central)

    def _accion(self, barra, atajo, funcion, icono=None) -> QAction:
        accion = QAction(self)
        if icono is not None:
            accion.setIcon(iconos.icono(icono))
        if atajo:
            accion.setShortcut(QKeySequence(atajo))
        accion.triggered.connect(funcion)
        barra.addAction(accion)
        return accion

    def _crear_marca(self) -> QWidget:
        """Tunki pequeño, el nombre del entorno y el subtítulo."""
        marca = QWidget()
        diseno = QHBoxLayout(marca)
        diseno.setContentsMargins(0, 0, 6, 0)
        diseno.setSpacing(8)
        dibujo = QLabel()
        dibujo.setPixmap(iconos.imagen_de_cuadricula(
            sprite.filas(sprite.FELIZ), sprite.PALETA, ESCALA_DE_LA_MARCA))
        diseno.addWidget(dibujo)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        nombre = QLabel(TITULO, objectName="marca")
        fuente = nombre.font()
        fuente.setPointSize(tema.TAMANO_INTERFAZ + 4)
        nombre.setFont(fuente)
        self.subtitulo = QLabel(objectName="submarca")
        fuente = self.subtitulo.font()
        fuente.setPointSize(tema.TAMANO_INTERFAZ - 2)
        self.subtitulo.setFont(fuente)
        textos.addStretch()
        textos.addWidget(nombre)
        textos.addWidget(self.subtitulo)
        textos.addStretch()
        diseno.addLayout(textos)
        return marca

    def _crear_barra(self):
        barra = QToolBar(movable=False, objectName="barra")
        barra.setIconSize(TAMANO_ICONOS)
        barra.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        barra.toggleViewAction().setVisible(False)
        self.addToolBar(barra)
        barra.addWidget(self._crear_marca())
        barra.addSeparator()

        self.accion_nuevo = self._accion(
            barra, QKeySequence.StandardKey.New, self.nuevo, "nuevo")
        self.accion_abrir = self._accion(
            barra, QKeySequence.StandardKey.Open, self.abrir, "abrir")
        self.accion_guardar = self._accion(
            barra, QKeySequence.StandardKey.Save, self.guardar, "guardar")

        self.boton_ejemplos = QToolButton(
            popupMode=QToolButton.ToolButtonPopupMode.InstantPopup,
            toolButtonStyle=Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
            icon=iconos.icono("ejemplos"))
        self.boton_ejemplos.setIconSize(TAMANO_ICONOS)
        self.boton_ejemplos.setMenu(QMenu(self.boton_ejemplos))
        barra.addWidget(self.boton_ejemplos)

        self.accion_ejecutar = self._accion(barra, "F5", self.ejecutar,
                                            "ejecutar")
        boton = barra.widgetForAction(self.accion_ejecutar)
        boton.setObjectName("ejecutar")
        boton.setCursor(Qt.CursorShape.PointingHandCursor)

    def _crear_barra_de_estado(self):
        barra = self.statusBar()
        barra.setSizeGripEnabled(False)
        self.estado = QLabel()
        self.posicion = QLabel()
        barra.addWidget(self.estado)
        barra.addPermanentWidget(self.posicion)
        self.selector_idioma = QComboBox()
        for codigo, nombre in NOMBRES_DE_IDIOMA.items():
            self.selector_idioma.addItem(nombre, codigo)
        self.selector_idioma.setCurrentIndex(
            self.selector_idioma.findData(self.idioma))
        self.selector_idioma.currentIndexChanged.connect(
            self._al_cambiar_idioma)
        barra.addPermanentWidget(self.selector_idioma)
        self.accion_achicar = self._boton_de_letra(
            barra, "A−", -1, QKeySequence.StandardKey.ZoomOut)
        self.accion_agrandar = self._boton_de_letra(
            barra, "A+", +1, QKeySequence.StandardKey.ZoomIn,
            QKeySequence("Ctrl+="))

    def _boton_de_letra(self, barra, texto, paso, *atajos) -> QAction:
        accion = QAction(texto, self)
        accion.setShortcuts(list(atajos))
        accion.triggered.connect(
            lambda: self.editor.cambiar_tamano(self.editor.tamano + paso))
        self.addAction(accion)
        boton = QToolButton(objectName="zoom")
        boton.setDefaultAction(accion)
        barra.addPermanentWidget(boton)
        return accion

    # ------------------------------------------------------------------
    # Textos según el idioma
    # ------------------------------------------------------------------
    @property
    def idioma_principal(self) -> str:
        return QU if self.idioma == QU else ES

    def t(self, mensaje, **parametros) -> str:
        """Texto de la interfaz en el idioma elegido."""
        return mensaje.texto(self.idioma_principal, **parametros)

    def texto_de_error(self, error) -> str:
        """HTML del mensaje de un error; con AMBOS, el quechua debajo."""
        texto = html.escape(texto_de(error, self.idioma_principal))
        quechua = error["textos"].get(QU)
        if self.idioma == AMBOS and quechua:
            texto += ("<br><i style='color:#7a5c3e'>"
                      f"{html.escape(quechua)}</i>")
        return texto

    def _actualizar_textos(self):
        self.accion_nuevo.setText(self.t(mensajes.IDE_NUEVO))
        self.accion_abrir.setText(self.t(mensajes.IDE_ABRIR))
        self.accion_guardar.setText(self.t(mensajes.IDE_GUARDAR))
        self.boton_ejemplos.setText(self.t(mensajes.IDE_EJEMPLOS) + "  ▾")
        self.boton_ejemplos.setToolTip(self.t(mensajes.IDE_PISTA_EJEMPLOS))
        self.accion_ejecutar.setText(self.t(mensajes.IDE_EJECUTAR))
        self.accion_ejecutar.setToolTip(
            self.t(mensajes.IDE_PISTA_EJECUTAR))
        self.accion_achicar.setToolTip(
            self.t(mensajes.IDE_LETRA_MAS_PEQUENA) + "  (Ctrl −)")
        self.accion_agrandar.setToolTip(
            self.t(mensajes.IDE_LETRA_MAS_GRANDE) + "  (Ctrl +)")
        total = len(mensajes.catalogo())
        self.selector_idioma.setToolTip(
            self.t(mensajes.IDE_IDIOMA) + "\n" + self.t(
                mensajes.IDE_AVANCE_QUECHUA, total=total,
                listos=total - len(mensajes.pendientes_de_traduccion())))
        self._llenar_ejemplos()
        self.subtitulo.setText(self.t(mensajes.IDE_SUBTITULO))
        self.titulo_salida.setText(self.t(mensajes.IDE_SALIDA))
        self.salida.setPlaceholderText(self.t(mensajes.IDE_PISTA_SALIDA))
        self.titulo_problemas.setText(self.t(mensajes.IDE_PROBLEMAS))
        self._llenar_problemas()
        self._mostrar_estado()
        self._mostrar_posicion()

    def _llenar_ejemplos(self):
        menu = self.boton_ejemplos.menu()
        menu.clear()
        for numero, ruta in enumerate(ejemplos_en(self.idioma_principal),
                                      1):
            accion = menu.addAction(
                f"{numero}.  {nombre_de_ejemplo(ruta)}")
            accion.triggered.connect(
                lambda _=False, r=ruta: self.abrir_ejemplo(r))

    def _al_cambiar_idioma(self):
        self.idioma = self.selector_idioma.currentData()
        self._actualizar_textos()
        if self.errores and self.tunki.globo.isVisible():
            self.mostrar_error(self.error_actual)

    def _decir(self, mensaje, tipo, **parametros):
        self.tunki.decir(html.escape(self.t(mensaje, **parametros)), tipo)

    # ------------------------------------------------------------------
    # Barra de estado y tamaño de letra
    # ------------------------------------------------------------------
    def _mostrar_posicion(self):
        cursor = self.editor.textCursor()
        self.posicion.setText(self.t(
            mensajes.IDE_POSICION, linea=cursor.blockNumber() + 1,
            columna=cursor.positionInBlock() + 1))

    def _mostrar_estado(self):
        if self.hilo is not None and self.hilo.isRunning():
            texto = "⏳  " + self.t(mensajes.IDE_ESTADO_EJECUTANDO)
            fondo, letra = tema.AMARILLO_SUAVE, tema.TEXTO
        elif self.resultado is None:
            return
        elif self.errores:
            texto = "✖  " + self.t(mensajes.IDE_ESTADO_ERRORES,
                                   total=len(self.errores))
            fondo, letra = tema.ROJO_SUAVE, tema.ROJO
        else:
            texto = "✔  " + self.t(mensajes.IDE_ESTADO_SIN_ERRORES)
            fondo, letra = "#e6f6e9", tema.VERDE_OSCURO
            avisos = len(self.resultado.advertencias)
            if avisos:
                texto += "   ·   ⚠  " + self.t(
                    mensajes.IDE_ESTADO_ADVERTENCIAS, total=avisos)
        self.estado.setText(texto)
        self.estado.setStyleSheet(
            f"background: {fondo}; color: {letra}; font-weight: bold; "
            "border-radius: 9px; padding: 3px 12px; margin: 4px 6px;")

    def _al_cambiar_tamano(self, tamano: int):
        self.salida.setFont(tema.fuente_de_codigo(
            max(tema.TAMANO_MINIMO, tamano - 2)))
        self.tunki.seguir()

    # ------------------------------------------------------------------
    # Análisis mientras se escribe
    # ------------------------------------------------------------------
    def _al_cambiar_texto(self):
        self.setWindowModified(True)
        self.tunki.callar()
        self.tunki.humor = sprite.PENSANDO
        self.editor.marcar_ejecucion(None)
        self.temporizador.start()

    def analizar_ahora(self):
        self.temporizador.stop()
        habia_errores = bool(self.errores)
        self.resultado = api.analizar(self.editor.toPlainText(),
                                      optimizar_codigo=False)
        self.errores = self.resultado.errores
        self.editor.marcar(self.errores + self.resultado.advertencias)
        self._llenar_problemas()
        self._mostrar_estado()
        if self.errores:
            self.mostrar_error(0)
            return
        self.tunki.humor = sprite.NORMAL
        self.tunki.volar_a_casa()
        if habia_errores:
            self.tunki.humor = sprite.FELIZ
            self._decir(mensajes.TUNKI_TODO_BIEN, EXITO)

    def _llenar_problemas(self):
        self.problemas.clear()
        if self.resultado is None:
            return
        marcas = self.resultado.errores + self.resultado.advertencias
        for marca in marcas:
            linea = self.t(mensajes.IDE_LINEA, linea=marca["linea"])
            texto = texto_de(marca, self.idioma_principal)
            elemento = QListWidgetItem(f"{linea}:  {texto}")
            elemento.setIcon(self._puntos[
                ADVERTENCIA if marca["gravedad"] == ADVERTENCIA else ERROR])
            elemento.setData(Qt.ItemDataRole.UserRole, marca)
            elemento.setToolTip(marca["codigo"])
            self.problemas.addItem(elemento)
        if not marcas:
            elemento = QListWidgetItem(self.t(mensajes.IDE_SIN_PROBLEMAS))
            elemento.setForeground(QColor(tema.TEXTO_TENUE))
            elemento.setFlags(Qt.ItemFlag.NoItemFlags)
            self.problemas.addItem(elemento)
        self._mostrar_insignia(len(self.resultado.errores), len(marcas))

    def _mostrar_insignia(self, errores: int, total: int):
        if errores:
            estilo = _estilo_de_insignia(tema.ROJO, "white")
        elif total:
            estilo = _estilo_de_insignia(tema.AMARILLO, "white")
        else:
            estilo = _estilo_de_insignia("#e6f6e9", tema.VERDE_OSCURO)
        self.insignia_problemas.setStyleSheet(estilo)
        self.insignia_problemas.setText(str(total) if total else "✔")
        self.insignia_problemas.show()

    # ------------------------------------------------------------------
    # Tunki explica los errores
    # ------------------------------------------------------------------
    def mostrar_error(self, indice: int, introduccion=None):
        self.error_actual = indice % len(self.errores)
        error = self.errores[self.error_actual]
        self.explicar(error, mensajes.TUNKI_ERROR, introduccion)

    def explicar(self, error, titulo, introduccion=None):
        """Tunki vuela a la línea del error y lo explica."""
        self.tunki.humor = (sprite.NORMAL
                            if error["gravedad"] == ADVERTENCIA
                            else sprite.SORPRENDIDO)
        self.tunki.volar_a_linea(error["linea"])
        partes = []
        if introduccion is not None:
            partes.append(html.escape(self.t(introduccion)) + "<br>")
        partes.append(
            f"<b>{html.escape(self.t(titulo, linea=error['linea']))}</b>")
        partes.append(self.texto_de_error(error))
        if len(self.errores) > 1 and error in self.errores:
            partes.append("<small style='color:#8a7f70'>" + html.escape(
                self.t(mensajes.TUNKI_VARIOS_ERRORES,
                       total=len(self.errores),
                       numero=self.error_actual + 1)) + "</small>")
        partes.append(
            f"<small style='color:#b0a593'>{error['codigo']}</small>")
        tipo = INFO if error["gravedad"] == ADVERTENCIA else ERROR
        self.tunki.decir("<br>".join(partes), tipo)

    def siguiente_error(self):
        if self.errores:
            self.mostrar_error(self.error_actual + 1)

    def _al_elegir_problema(self, elemento):
        marca = elemento.data(Qt.ItemDataRole.UserRole)
        if marca is None:
            return
        self.editor.ir_a_linea(marca["linea"], marca.get("columna") or 1)
        self.editor.setFocus()
        if marca in self.errores:
            self.mostrar_error(self.errores.index(marca))
        else:
            self.explicar(marca, mensajes.IDE_LINEA)

    # ------------------------------------------------------------------
    # Ejecutar
    # ------------------------------------------------------------------
    def ejecutar(self):
        self.analizar_ahora()
        if self.errores:
            self.mostrar_error(0, mensajes.TUNKI_ARREGLA_PRIMERO)
            return
        self.salida.clear()
        self.accion_ejecutar.setEnabled(False)
        self.tunki.humor = sprite.PENSANDO
        self._decir(mensajes.TUNKI_EJECUTANDO, INFO)
        self.hilo = HiloDeEjecucion(self.resultado, self)
        self.hilo.terminado.connect(self.al_terminar_ejecucion)
        self.hilo.finished.connect(self._mostrar_estado)
        self.hilo.start()
        self._mostrar_estado()

    def al_terminar_ejecucion(self, traza):
        self.accion_ejecutar.setEnabled(True)
        if traza.salida:
            self.salida.setPlainText(traza.salida)
        else:
            self.salida.setPlainText(self.t(mensajes.IDE_SIN_SALIDA))
        if traza.error is not None:
            self.editor.marcar(self.resultado.advertencias + [traza.error])
            self.explicar(traza.error, mensajes.TUNKI_ERROR_EJECUCION)
            return
        self.tunki.humor = sprite.FELIZ
        self.tunki.volar_a_casa()
        self.tunki.celebrar()
        self._decir(mensajes.TUNKI_EXITO, EXITO)

    # ------------------------------------------------------------------
    # Archivos
    # ------------------------------------------------------------------
    def cargar_texto(self, texto: str, ruta: Optional[Path] = None):
        self.ruta = ruta
        self.editor.setPlainText(texto)
        self.salida.clear()
        self.analizar_ahora()
        self.setWindowModified(False)
        nombre = ruta.name if ruta else "sin nombre"
        self.setWindowTitle(f"{TITULO} — {nombre}[*]")

    def abrir_archivo(self, ruta: Path):
        self.cargar_texto(ruta.read_text(encoding="utf-8"), ruta)

    def abrir_ejemplo(self, ruta: Path):
        if self.puede_descartar_cambios():
            # Los ejemplos se abren sin ruta: al guardar se pide un nombre
            # nuevo y el ejemplo original no se modifica.
            self.cargar_texto(ruta.read_text(encoding="utf-8"))

    def nuevo(self):
        if self.puede_descartar_cambios():
            self.cargar_texto(PLANTILLAS[self.idioma_principal])

    def abrir(self):
        if not self.puede_descartar_cambios():
            return
        nombre, _ = QFileDialog.getOpenFileName(
            self, self.t(mensajes.IDE_ABRIR), "",
            "Antachawi (*.awi);;* (*)")
        if nombre:
            self.abrir_archivo(Path(nombre))

    def guardar(self) -> bool:
        if self.ruta is None:
            nombre, _ = QFileDialog.getSaveFileName(
                self, self.t(mensajes.IDE_GUARDAR), "programa.awi",
                "Antachawi (*.awi)")
            if not nombre:
                return False
            self.ruta = Path(nombre)
        self.ruta.write_text(self.editor.toPlainText(), encoding="utf-8")
        self.setWindowModified(False)
        self.setWindowTitle(f"{TITULO} — {self.ruta.name}[*]")
        return True

    def puede_descartar_cambios(self) -> bool:
        if not self.isWindowModified():
            return True
        Boton = QMessageBox.StandardButton
        respuesta = QMessageBox.question(
            self, TITULO, self.t(mensajes.IDE_GUARDAR_CAMBIOS),
            Boton.Save | Boton.Discard | Boton.Cancel)
        if respuesta == Boton.Save:
            return self.guardar()
        return respuesta == Boton.Discard

    def closeEvent(self, evento):
        if self.hilo is not None:
            self.hilo.wait()
        if self.puede_descartar_cambios():
            evento.accept()
        else:
            evento.ignore()
