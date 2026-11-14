"""
Árbol sintáctico abstracto (AST) de Antachawi.

A diferencia del árbol de derivación que arma el parser, el AST solo guarda
lo que significa el programa: no tiene saltos de línea, paréntesis ni nodos
"Prime". Ver Libro del Dragón, sección 5.3.1 (construcción de árboles
sintácticos).

Cada nodo guarda su posición en el código fuente. Las expresiones tienen
además el atributo `tipo`, que completa el análisis semántico (es el
atributo sintetizado de la sección 6.5). Los nodos que nombran una variable
guardan también el `simbolo` de la tabla de símbolos al que se refieren,
así la generación de código no tiene que volver a resolver los nombres.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Union

if TYPE_CHECKING:
    from antachawi.symboltable import Simbolo


@dataclass(frozen=True)
class Posicion:
    """Rango de una línea del código fuente (columnas empiezan en 1)."""

    linea: int
    columna: int
    longitud: int = 1

    @property
    def columna_final(self) -> int:
        return self.columna + self.longitud

    def hasta(self, otra: Posicion) -> Posicion:
        """Rango desde esta posición hasta el final de `otra`. Si están en
        líneas distintas, se queda con esta posición."""
        if otra.linea != self.linea or otra.columna_final <= self.columna:
            return self
        return Posicion(self.linea, self.columna,
                        otra.columna_final - self.columna)


# ----------------------------------------------------------------------
# Expresiones
# ----------------------------------------------------------------------
@dataclass(eq=False)
class Literal:
    tipo_literal: str           # yupay, chunkayuq, sananpa, qaytu o bool
    valor: str                  # lexema tal como está en el código
    pos: Posicion
    tipo: Optional[str] = None


@dataclass(eq=False)
class Variable:
    nombre: str
    pos: Posicion
    tipo: Optional[str] = None
    simbolo: Optional[Simbolo] = None


@dataclass(eq=False)
class Unaria:
    operador: str
    operando: Expresion
    pos: Posicion               # toda la expresión
    pos_operador: Posicion
    tipo: Optional[str] = None


@dataclass(eq=False)
class Binaria:
    operador: str
    izquierda: Expresion
    derecha: Expresion
    pos: Posicion               # toda la expresión
    pos_operador: Posicion
    tipo: Optional[str] = None


Expresion = Union[Literal, Variable, Unaria, Binaria]


# ----------------------------------------------------------------------
# Sentencias
# ----------------------------------------------------------------------
@dataclass(eq=False)
class Declaracion:
    tipo: str                   # tipo declarado
    nombre: str
    valor: Optional[Expresion]  # None si no se inicializa
    pos: Posicion               # posición del nombre
    simbolo: Optional[Simbolo] = None


@dataclass(eq=False)
class Asignacion:
    nombre: str
    valor: Expresion
    pos: Posicion               # posición del nombre
    simbolo: Optional[Simbolo] = None


@dataclass(eq=False)
class Imprimir:
    argumentos: List[Expresion]
    pos: Posicion               # posición de rikuchiy


@dataclass(eq=False)
class Bloque:
    sentencias: List[Sentencia]
    pos: Posicion               # posición de '{'


@dataclass(eq=False)
class Si:
    """ari (condicion) entonces [mana_chayqa si_no]. Un mana_chayqa_ari se
    representa como un Si dentro de `si_no`."""

    condicion: Expresion
    entonces: Bloque
    si_no: Optional[Union[Bloque, Si]]
    pos: Posicion               # posición de ari / mana_chayqa_ari


@dataclass(eq=False)
class Mientras:
    """chaykama (condicion) cuerpo"""

    condicion: Expresion
    cuerpo: Bloque
    pos: Posicion               # posición de chaykama


@dataclass(eq=False)
class Para:
    """imapaq (inicio; condicion; paso) cuerpo. La variable que declara
    `inicio` solo existe dentro del bucle."""

    inicio: Union[Declaracion, Asignacion]
    condicion: Expresion
    paso: Asignacion
    cuerpo: Bloque
    pos: Posicion               # posición de imapaq


Sentencia = Union[Declaracion, Asignacion, Imprimir, Si, Mientras, Para]


@dataclass(eq=False)
class Programa:
    cuerpo: Bloque
    pos: Posicion = field(default_factory=lambda: Posicion(1, 1))


# ----------------------------------------------------------------------
# Representación en texto (archivos de depuración y tests)
# ----------------------------------------------------------------------
def _sufijo_tipo(nodo) -> str:
    tipo = getattr(nodo, "tipo", None)
    if isinstance(nodo, (Declaracion,)) or tipo is None:
        return ""
    return f" : {tipo}"


def _descripcion(nodo) -> str:
    descripciones = {
        Programa: lambda n: "Programa",
        Bloque: lambda n: "Bloque",
        Declaracion: lambda n: f"Declaracion {n.tipo} {n.nombre}",
        Asignacion: lambda n: f"Asignacion {n.nombre}",
        Imprimir: lambda n: "Imprimir",
        Si: lambda n: "Si",
        Mientras: lambda n: "Mientras",
        Para: lambda n: "Para",
        Binaria: lambda n: f"Binaria {n.operador}",
        Unaria: lambda n: f"Unaria {n.operador}",
        Literal: lambda n: f"Literal {n.valor}",
        Variable: lambda n: f"Variable {n.nombre}",
    }
    return descripciones[type(nodo)](nodo) + _sufijo_tipo(nodo)


def hijos(nodo) -> list:
    """Hijos de un nodo, en orden."""
    if isinstance(nodo, Programa):
        return [nodo.cuerpo]
    if isinstance(nodo, Bloque):
        return list(nodo.sentencias)
    if isinstance(nodo, (Declaracion, Asignacion)):
        return [nodo.valor] if nodo.valor is not None else []
    if isinstance(nodo, Imprimir):
        return list(nodo.argumentos)
    if isinstance(nodo, Si):
        resto = [nodo.si_no] if nodo.si_no is not None else []
        return [nodo.condicion, nodo.entonces] + resto
    if isinstance(nodo, Mientras):
        return [nodo.condicion, nodo.cuerpo]
    if isinstance(nodo, Para):
        return [nodo.inicio, nodo.condicion, nodo.paso, nodo.cuerpo]
    if isinstance(nodo, Binaria):
        return [nodo.izquierda, nodo.derecha]
    if isinstance(nodo, Unaria):
        return [nodo.operando]
    return []


def formatear(nodo, prefijo: str = "") -> str:
    """Dibuja el AST como texto, con el tipo de cada expresión:

        Programa
        └── Bloque
            └── Declaracion yupay x
                └── Literal 5 : yupay
    """
    lineas = [_descripcion(nodo)]
    hijos_nodo = hijos(nodo)
    for i, hijo in enumerate(hijos_nodo):
        ultimo = i == len(hijos_nodo) - 1
        rama, continuacion = ("└── ", "    ") if ultimo else ("├── ", "│   ")
        sub = formatear(hijo, prefijo + continuacion).split("\n")
        lineas.append(prefijo + rama + sub[0])
        lineas.extend(sub[1:])
    return "\n".join(lineas)
