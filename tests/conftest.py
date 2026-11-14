from pathlib import Path

import pytest

from antachawi.constructor_ast import construir_ast
from antachawi.parser import RecursiveDescentParser
from antachawi.scanner import Scanner
from antachawi.semantic import SemanticAnalyzer
from antachawi.sourcecode import SourceCode

RAIZ = Path(__file__).resolve().parent.parent
INPUTS = RAIZ / "inputs"


class Resultado:
    """Resultado de pasar un programa por scanner, parser y (opcional)
    análisis semántico."""

    def __init__(self, ruta: Path, semantico: bool):
        self.fuente = SourceCode(str(ruta))
        self.scanner = Scanner(self.fuente)
        self.tokens = self.scanner.tokenize(str(ruta))
        self.parser = RecursiveDescentParser(self.scanner, self.fuente)
        self.arbol = self.parser.parse()
        self.ast = None
        self.errores_semanticos = None
        self.advertencias = None
        self.tabla = None
        if semantico and not self.errores_lexicos \
                and not self.errores_sintacticos:
            analizador = SemanticAnalyzer(self.fuente)
            self.ast = analizador.analyze(construir_ast(self.arbol))
            self.errores_semanticos = analizador.errors
            self.advertencias = analizador.advertencias
            self.tabla = analizador.tabla

    @property
    def errores_lexicos(self):
        return self.scanner.errors

    @property
    def errores_sintacticos(self):
        return self.parser.errors

    @property
    def etiquetas(self):
        return [t.etiqueta for t in self.tokens]


@pytest.fixture
def analizar(tmp_path):
    """analizar(codigo) -> Resultado. Escribe el código en un .awi
    temporal y lo analiza."""
    contador = {"n": 0}

    def _analizar(codigo: str, semantico: bool = False) -> Resultado:
        contador["n"] += 1
        ruta = tmp_path / f"programa{contador['n']}.awi"
        ruta.write_text(codigo, encoding="utf-8")
        return Resultado(ruta, semantico)

    return _analizar


@pytest.fixture
def analizar_archivo():
    def _analizar(ruta: Path, semantico: bool = False) -> Resultado:
        return Resultado(ruta, semantico)

    return _analizar
