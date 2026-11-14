"""
Punto de entrada del compilador para otros programas (un IDE, una
extensión de editor, las pruebas).

`analizar(texto)` pasa el programa por todas las fases sin imprimir nada
ni escribir archivos, y devuelve un `Resultado` con lo que produjo cada
una. La consola (antachawi/compiler.py) usa esta misma función y solo se
encarga de mostrar y guardar.

    resultado = analizar('qhapaq() {\\n    rikuchiy(1)\\n}')
    resultado.exito          -> True
    resultado.errores        -> []  (ver antachawi/errores.py)
    resultado.intermedio     -> código de tres direcciones
    resultado.ejecutar()     -> Traza para el depurador
    a_json(resultado)        -> diccionario listo para json.dumps

Como en el compilador, el análisis se detiene en la primera fase que
encuentra errores (`fase_fallida`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from antachawi.ast_nodos import Programa
from antachawi.bloques_basicos import particionar
from antachawi.constructor_ast import construir_ast
from antachawi.generador_x86 import generar_ensamblador
from antachawi.intermedio import (
    Cuadrupla,
    Nombre,
    generar_codigo_intermedio,
)
from antachawi.interprete import MAXIMO_DE_PASOS, Traza, trazar
from antachawi.optimizador import optimizar
from antachawi.parser import RecursiveDescentParser
from antachawi.plataformas import plataforma_actual
from antachawi.scanner import Scanner
from antachawi.semantic import SemanticAnalyzer
from antachawi.sourcecode import SourceCode
from antachawi.symboltable import TablaSimbolos
from antachawi.token import Token

LEXICO = "lexico"
SINTACTICO = "sintactico"
SEMANTICO = "semantico"


@dataclass
class Resultado:
    fuente: SourceCode
    tokens: List[Token] = field(default_factory=list)
    arbol: Optional[object] = None          # árbol de derivación (anytree)
    ast: Optional[Programa] = None          # con tipos y símbolos
    tabla: Optional[TablaSimbolos] = None
    errores: List[dict] = field(default_factory=list)
    advertencias: List[dict] = field(default_factory=list)
    intermedio: Optional[List[Cuadrupla]] = None
    optimizado: Optional[List[Cuadrupla]] = None
    fase_fallida: Optional[str] = None

    @property
    def exito(self) -> bool:
        return self.fase_fallida is None

    def codigo_final(self) -> Optional[List[Cuadrupla]]:
        """El código que se traduce a ensamblador."""
        return self.optimizado if self.optimizado is not None \
            else self.intermedio

    def bloques(self, optimizado: bool = True):
        codigo = self.codigo_final() if optimizado else self.intermedio
        return particionar(codigo) if codigo is not None else None

    def ensamblador(self, plataforma=None) -> Optional[str]:
        """Ensamblador x86-64 para `plataforma` (por defecto la actual).
        None si hubo errores o la plataforma no es compatible."""
        plataforma = plataforma or plataforma_actual()
        if not self.exito or plataforma is None:
            return None
        return generar_ensamblador(self.codigo_final(), plataforma)

    def ejecutar(self, maximo_de_pasos=MAXIMO_DE_PASOS) -> Optional[Traza]:
        """Ejecuta el código sin optimizar con el intérprete y devuelve la
        traza paso a paso (ver antachawi/interprete.py)."""
        if not self.exito:
            return None
        return trazar(self.intermedio, self.fuente, maximo_de_pasos)


def _fallar(resultado: Resultado, fase: str, errores: List[dict]):
    resultado.errores = errores
    resultado.fase_fallida = fase
    return resultado


def analizar_fuente(fuente: SourceCode,
                    optimizar_codigo: bool = True) -> Resultado:
    resultado = Resultado(fuente)

    scanner = Scanner(fuente)
    resultado.tokens = scanner.tokenize()
    if scanner.errors:
        return _fallar(resultado, LEXICO, scanner.errors)

    parser = RecursiveDescentParser(scanner, fuente)
    resultado.arbol = parser.parse()
    if parser.errors:
        return _fallar(resultado, SINTACTICO, parser.errors)

    analizador = SemanticAnalyzer(fuente)
    resultado.ast = analizador.analyze(construir_ast(resultado.arbol))
    resultado.tabla = analizador.tabla
    resultado.advertencias = analizador.advertencias
    if analizador.errors:
        return _fallar(resultado, SEMANTICO, analizador.errors)

    resultado.intermedio = generar_codigo_intermedio(resultado.ast)
    if optimizar_codigo:
        resultado.optimizado = optimizar(resultado.intermedio)
    return resultado


def analizar(texto: str, nombre: str = "<texto>",
             optimizar_codigo: bool = True) -> Resultado:
    """Analiza un programa dado como texto (no necesita estar en disco)."""
    return analizar_fuente(SourceCode.desde_texto(texto, nombre),
                           optimizar_codigo)


def analizar_archivo(ruta: str, optimizar_codigo: bool = True) -> Resultado:
    return analizar_fuente(SourceCode(str(ruta)), optimizar_codigo)


# ----------------------------------------------------------------------
# Conversión a JSON (para comunicarse con un IDE o un editor)
# ----------------------------------------------------------------------
def _posicion_json(pos):
    if pos is None:
        return None
    return {"linea": pos.linea, "columna": pos.columna,
            "longitud": pos.longitud}


def _codigo_json(codigo):
    if codigo is None:
        return None
    return [{"texto": str(c), "op": c.op, "pos": _posicion_json(c.pos)}
            for c in codigo]


def _simbolos_json(tabla):
    if tabla is None:
        return None
    return [{"nombre": s.nombre, "tipo": s.tipo, "ambito": s.ambito,
             "nivel": s.nivel, "pos": _posicion_json(s.pos),
             "usado": s.usado} for s in tabla.historial]


def _nombre_visible(variable) -> str:
    # Dos bloques hermanos con una variable `x` -> x y x.2 (intermedio.py)
    return variable.nombre.split(".")[0]


def traza_json(traza: Traza) -> dict:
    return {
        "pasos": [{
            "indice": p.indice,
            "instruccion": str(p.instruccion),
            "pos": _posicion_json(p.pos),
            "variable": (_nombre_visible(p.variable)
                         if isinstance(p.variable, Nombre) else None),
            "valor": (str(p.valor)
                      if isinstance(p.variable, Nombre) else None),
            "salida": p.salida,
        } for p in traza.pasos],
        "salida": traza.salida,
        "error": traza.error,
    }


def a_json(resultado: Resultado, con_traza: bool = False) -> dict:
    """Todo el resultado en tipos simples (dict, list, str...)."""
    datos = {
        "archivo": resultado.fuente.filename,
        "exito": resultado.exito,
        "fase_fallida": resultado.fase_fallida,
        "errores": resultado.errores,
        "advertencias": resultado.advertencias,
        "tokens": [{"lexema": t.lexema, "etiqueta": t.etiqueta,
                    "linea": t.linea, "columna": t.columna}
                   for t in resultado.tokens],
        "simbolos": _simbolos_json(resultado.tabla),
        "intermedio": _codigo_json(resultado.intermedio),
        "optimizado": _codigo_json(resultado.optimizado),
    }
    if con_traza:
        traza = resultado.ejecutar()
        datos["ejecucion"] = traza_json(traza) if traza else None
    return datos
