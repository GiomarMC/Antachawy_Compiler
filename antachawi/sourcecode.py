# Autor: Giomar Muñoz
# Fecha: 2023-09-26
# Descripción: Clase que representa un archivo de código fuente
from typing import Optional


def normalizar_texto(texto: str) -> str:
    """Saltos de línea de Windows (\\r\\n) o de Mac antiguo (\\r) -> \\n,
    igual que al leer un archivo en modo texto."""
    return texto.replace("\r\n", "\n").replace("\r", "\n")


class SourceCode:
    """
    Código fuente de un programa. Se crea desde un archivo,
    SourceCode("programa.awi"), o desde un texto que no está en disco
    (por ejemplo, lo que hay en el editor de un IDE):
    SourceCode.desde_texto("qhapaq() {...}").
    """

    def __init__(self, filename: str, texto: Optional[str] = None):
        self.filename = filename
        if texto is None:
            with open(filename, "r", encoding='utf-8') as file:
                texto = file.read()
        self.texto = normalizar_texto(texto)
        # Se conserva la indentación para poder señalar la columna exacta
        # de un error.
        lineas = self.texto.split("\n")
        if lineas and lineas[-1] == "":
            lineas.pop()        # el salto de línea final no abre una línea
        self.lines = dict(enumerate(lineas, start=1))

    @classmethod
    def desde_texto(cls, texto: str, nombre: str = "<texto>"):
        return cls(nombre, texto)

    def get_line(self, lineno: int) -> str:
        # Devuelve la línea de código en la posición indicada
        return self.lines.get(lineno, None)

    def get_all_lines(self) -> dict:
        # Devuelve todo el contenido del archivo en un diccionario
        return self.lines
