"""
Colores y estilo de Antachawi Yachay.

El entorno usa SIEMPRE su propio tema claro, sin importar el del sistema:
si el escritorio usa un tema oscuro (KDE Breeze Dark, GNOME oscuro...),
Qt pondría letras blancas sobre nuestros fondos claros y no se leería
nada. Por eso `aplicar_tema` fija el estilo Fusion y una paleta completa.

Todos los colores están aquí; los demás archivos los toman de este.
"""
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

# ----------------------------------------------------------------------
# Paleta
# ----------------------------------------------------------------------
FONDO = "#f3ece0"           # fondo de la ventana (crema)
SUPERFICIE = "#ffffff"      # tarjetas, barra, editor
BORDE = "#e0d3bd"
BORDE_FUERTE = "#cbb89a"
TEXTO = "#2b2118"           # casi negro, cálido
TEXTO_SUAVE = "#76664f"
TEXTO_TENUE = "#a8977d"
ACENTO = "#c4561b"          # naranja de Tunki
ACENTO_SUAVE = "#fde3cf"
PASAR_ENCIMA = "#f8eedf"
PRESIONADO = "#efdcc0"
SELECCION = "#ffd8a8"

VERDE = "#2f9e44"
VERDE_CLARO = "#37b24d"
VERDE_OSCURO = "#237a35"
VERDE_APAGADO = "#9fd3ab"
ROJO = "#e03131"
ROJO_SUAVE = "#ffe3e3"
AMARILLO = "#e8a317"
AMARILLO_SUAVE = "#fff3d6"

# Editor
EDITOR_FONDO = SUPERFICIE
EDITOR_MARGEN = "#faf5ec"
EDITOR_NUMERO = "#b3a48c"
EDITOR_LINEA_ACTUAL = "#fbf3e6"
EDITOR_EJECUCION = "#d3f9d8"

# Consola (lo que muestra el programa)
CONSOLA_FONDO = "#1f2a30"
CONSOLA_TEXTO = "#dff7e3"
CONSOLA_TENUE = "#8fa9b1"

# Franja de aguayo (tejido andino) debajo de la barra
AGUAYO = ("#c92a2a", "#f08c00", "#fcc419", "#2f9e44", "#1971c2",
          "#862e9c")

# ----------------------------------------------------------------------
# Letras
# ----------------------------------------------------------------------
TAMANO_INTERFAZ = 11        # puntos
TAMANO_CODIGO = 15
TAMANO_MINIMO = 10
TAMANO_MAXIMO = 32


def fuente_de_codigo(tamano: int = TAMANO_CODIGO) -> QFont:
    fuente = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    fuente.setPointSize(tamano)
    return fuente


# ----------------------------------------------------------------------
# Hoja de estilo
# ----------------------------------------------------------------------
ESTILO = f"""
QMainWindow, QWidget#central {{ background: {FONDO}; }}
QWidget {{ color: {TEXTO}; }}

/* Barra superior */
QToolBar#barra {{
    background: {SUPERFICIE}; border: none;
    padding: 8px 12px; spacing: 4px;
}}
QToolBar#barra::separator {{
    background: {BORDE}; width: 1px; margin: 8px 10px;
}}
QToolBar QToolButton {{
    color: {TEXTO}; background: transparent;
    border: 1px solid transparent; border-radius: 10px;
    padding: 5px 10px 5px 6px; font-weight: 600;
}}
QToolBar QToolButton:hover {{
    background: {PASAR_ENCIMA}; border-color: {BORDE};
}}
QToolBar QToolButton:pressed, QToolBar QToolButton:open {{
    background: {PRESIONADO}; border-color: {BORDE_FUERTE};
}}
QToolBar QToolButton::menu-indicator {{ image: none; width: 0; }}
QToolBar QToolButton#ejecutar {{
    color: white; background: {VERDE};
    border: 1px solid {VERDE_OSCURO}; border-bottom-width: 3px;
    padding: 6px 22px 4px 14px; font-weight: bold; margin-left: 6px;
}}
QToolBar QToolButton#ejecutar:hover {{ background: {VERDE_CLARO}; }}
QToolBar QToolButton#ejecutar:pressed {{
    background: {VERDE_OSCURO}; border-bottom-width: 1px;
    padding-top: 8px; padding-bottom: 4px;
}}
QToolBar QToolButton#ejecutar:disabled {{
    background: {VERDE_APAGADO}; border-color: {VERDE_APAGADO};
}}
QToolButton#zoom {{
    color: {TEXTO}; background: {SUPERFICIE}; font-weight: bold;
    border: 1px solid {BORDE}; border-radius: 8px;
    padding: 1px 8px; margin: 3px 2px;
}}
QToolButton#zoom:hover {{ background: {PASAR_ENCIMA}; }}
QToolButton#zoom:pressed {{ background: {PRESIONADO}; }}
QLabel#marca {{ color: {ACENTO}; font-weight: 800; }}
QLabel#submarca {{ color: {TEXTO_SUAVE}; }}

/* Menús y listas desplegables */
QMenu {{
    background: {SUPERFICIE}; color: {TEXTO};
    border: 1px solid {BORDE_FUERTE}; border-radius: 10px; padding: 6px;
}}
QMenu::item {{ padding: 8px 22px 8px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {ACENTO_SUAVE}; color: {TEXTO}; }}
QMenu::separator {{ height: 1px; background: {BORDE}; margin: 4px 8px; }}
QComboBox {{
    background: {SUPERFICIE}; color: {TEXTO};
    border: 1px solid {BORDE_FUERTE}; border-radius: 8px;
    padding: 2px 10px; margin: 3px 6px;
}}
QComboBox:hover {{ background: {PASAR_ENCIMA}; }}
QComboBox QAbstractItemView {{
    background: {SUPERFICIE}; color: {TEXTO};
    border: 1px solid {BORDE_FUERTE}; outline: none; padding: 4px;
    selection-background-color: {ACENTO_SUAVE}; selection-color: {TEXTO};
}}

/* Tarjetas */
QFrame#tarjeta {{
    background: {SUPERFICIE}; border: 1px solid {BORDE};
    border-radius: 14px;
}}
QLabel#titulo_tarjeta {{ color: {TEXTO_SUAVE}; font-weight: bold; }}
QLabel#insignia {{
    border-radius: 9px; padding: 1px 8px; font-weight: bold;
}}

/* Editor, consola y problemas */
QPlainTextEdit#editor {{
    background: {EDITOR_FONDO}; color: {TEXTO}; border: none;
    selection-background-color: {SELECCION}; selection-color: {TEXTO};
}}
QPlainTextEdit#salida {{
    background: {CONSOLA_FONDO}; color: {CONSOLA_TEXTO};
    border: none; border-radius: 10px; padding: 8px;
    selection-background-color: #3d5560;
}}
QListWidget#problemas {{
    background: {SUPERFICIE}; color: {TEXTO}; border: none;
    outline: none;
}}
QListWidget#problemas::item {{
    padding: 7px 6px; border-radius: 8px; margin: 1px 0;
}}
QListWidget#problemas::item:hover {{ background: {PASAR_ENCIMA}; }}
QListWidget#problemas::item:selected {{
    background: {ACENTO_SUAVE}; color: {TEXTO};
}}

/* Barra de estado */
QStatusBar {{
    background: {SUPERFICIE}; color: {TEXTO_SUAVE};
    border-top: 1px solid {BORDE};
}}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {TEXTO_SUAVE}; padding: 2px 10px; }}

/* Separadores que se pueden arrastrar */
QSplitter::handle {{ background: {FONDO}; }}
QSplitter::handle:hover {{ background: {BORDE}; }}

/* Barras de desplazamiento */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar:horizontal {{
    background: transparent; height: 12px; margin: 2px;
}}
QScrollBar::handle {{ background: {BORDE_FUERTE}; border-radius: 4px; }}
QScrollBar::handle:vertical {{ min-height: 30px; }}
QScrollBar::handle:horizontal {{ min-width: 30px; }}
QScrollBar::handle:hover {{ background: {TEXTO_TENUE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QPlainTextEdit#salida QScrollBar::handle {{ background: #4b6069; }}
QPlainTextEdit#salida QScrollBar::handle:hover {{ background: #627a84; }}

QToolTip {{
    background: {AMARILLO_SUAVE}; color: {TEXTO};
    border: 1px solid {AMARILLO}; padding: 4px 6px;
}}
"""


def paleta() -> QPalette:
    """Paleta clara completa (para diálogos, menús y todo lo que no
    cubre la hoja de estilo)."""
    p = QPalette()
    R = QPalette.ColorRole
    colores = {
        R.Window: FONDO, R.WindowText: TEXTO,
        R.Base: SUPERFICIE, R.AlternateBase: EDITOR_MARGEN,
        R.Text: TEXTO, R.PlaceholderText: TEXTO_TENUE,
        R.Button: SUPERFICIE, R.ButtonText: TEXTO, R.BrightText: "white",
        R.Highlight: SELECCION, R.HighlightedText: TEXTO,
        R.ToolTipBase: AMARILLO_SUAVE, R.ToolTipText: TEXTO,
        R.Link: ACENTO, R.LinkVisited: ACENTO,
        R.Light: SUPERFICIE, R.Midlight: PASAR_ENCIMA, R.Mid: BORDE,
        R.Dark: BORDE_FUERTE, R.Shadow: TEXTO_TENUE,
    }
    for rol, color in colores.items():
        p.setColor(rol, QColor(color))
    desactivado = QPalette.ColorGroup.Disabled
    for rol in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(desactivado, rol, QColor(TEXTO_TENUE))
    return p


def aplicar_tema(aplicacion: QApplication):
    """Fija el estilo, la paleta, la letra y la hoja de estilo."""
    aplicacion.setStyle("Fusion")
    aplicacion.setPalette(paleta())
    fuente = aplicacion.font()
    fuente.setPointSize(TAMANO_INTERFAZ)
    aplicacion.setFont(fuente)
    aplicacion.setStyleSheet(ESTILO)
