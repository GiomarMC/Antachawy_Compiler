"""
Abre Antachawi Yachay:

    python -m antachawi.ide [programa.awi]
    antachawi-ide [programa.awi]          (si se instaló con [ide])
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from antachawi.ide.iconos import icono_de_la_aplicacion
from antachawi.ide.ventana import TITULO, VentanaPrincipal


def main(argumentos=None) -> int:
    argumentos = sys.argv if argumentos is None else argumentos
    aplicacion = QApplication(argumentos)
    aplicacion.setApplicationName(TITULO)
    aplicacion.setDesktopFileName("antachawi-yachay")
    aplicacion.setWindowIcon(icono_de_la_aplicacion())
    ventana = VentanaPrincipal()
    if len(argumentos) > 1 and Path(argumentos[1]).is_file():
        ventana.abrir_archivo(Path(argumentos[1]))
    ventana.show()
    return aplicacion.exec()


if __name__ == "__main__":
    sys.exit(main())
