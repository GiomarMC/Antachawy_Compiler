"""
Intérprete del código de tres direcciones.

Tiene dos usos:

* En las pruebas es la referencia: lo que imprime debe ser idéntico a lo
  que imprime el ejecutable generado (tests/test_diferencial.py).
* Es la base del depurador: `trazar` ejecuta el programa guardando cada
  paso (qué instrucción, de qué línea del código fuente, qué variable
  cambió y qué se imprimió). Con esa traza un IDE puede avanzar y
  retroceder paso a paso y mostrar el valor de las variables en cualquier
  momento (`Traza.variables_en`).

Conviene trazar el código SIN optimizar: cada instrucción corresponde a
una sentencia del programa tal como se escribió.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from antachawi import mensajes
from antachawi.errores import nuevo_error
from antachawi.intermedio import (
    DEFINICIONES,
    ETIQUETA,
    LLAMADA,
    PARAMETRO,
    SALTO,
    SALTOS_RELACIONALES,
    SI,
    SI_NO,
    Constante,
    Cuadrupla,
    Nombre,
    relacion,
)
from antachawi.optimizador import comparar, plegar
from antachawi.tipos import BOOL, CHUNKAYUQ

MAXIMO_DE_PASOS = 200_000


class LimiteDePasos(Exception):
    """El programa no terminó (probablemente un bucle infinito)."""


class DivisionEntreCero(ZeroDivisionError):
    def __init__(self, instruccion: Cuadrupla):
        super().__init__(str(instruccion))
        self.instruccion = instruccion


def texto_de_valor(constante: Constante) -> str:
    """Como lo imprime rikuchiy."""
    if constante.tipo == BOOL:
        return "1" if constante.valor else "0"
    if constante.tipo == CHUNKAYUQ:
        return "%g" % constante.valor
    return str(constante.valor)


class Interprete:
    def __init__(self, codigo: List[Cuadrupla]):
        self.codigo = codigo
        self.etiquetas = {c.resultado: i for i, c in enumerate(codigo)
                          if c.op == ETIQUETA}
        self.memoria = {}
        self.parametros = []
        self.salida = []
        self.pc = 0

    @property
    def terminado(self) -> bool:
        return self.pc >= len(self.codigo)

    def valor(self, direccion) -> Constante:
        if isinstance(direccion, Constante):
            return direccion
        return self.memoria[direccion]

    def _definir(self, c: Cuadrupla):
        # El plegado de constantes ya imita al procesador (enteros de 64
        # bits, división que trunca hacia cero...)
        argumentos = [self.valor(a) if a is not None else None
                      for a in (c.arg1, c.arg2)]
        resultado = plegar(Cuadrupla(c.op, *argumentos, c.resultado))
        if resultado is None:
            raise DivisionEntreCero(c)
        self.memoria[c.resultado] = resultado

    def _salta(self, c: Cuadrupla) -> bool:
        if c.op == SALTO:
            return True
        if c.op in (SI, SI_NO):
            return bool(self.valor(c.arg1).valor) == (c.op == SI)
        return comparar(relacion(c.op), self.valor(c.arg1),
                        self.valor(c.arg2))

    def _llamar(self, c: Cuadrupla):
        argumentos = self.parametros[len(self.parametros) - c.arg2:]
        del self.parametros[len(self.parametros) - c.arg2:]
        self.salida.append("".join(texto_de_valor(a)
                                   for a in argumentos) + "\n")

    def paso(self):
        c = self.codigo[self.pc]
        self.pc += 1
        if c.op in DEFINICIONES:
            self._definir(c)
        elif c.op in (SALTO, SI, SI_NO) + SALTOS_RELACIONALES:
            if self._salta(c):
                self.pc = self.etiquetas[c.resultado]
        elif c.op == PARAMETRO:
            self.parametros.append(self.valor(c.arg1))
        elif c.op == LLAMADA:
            self._llamar(c)


def ejecutar(codigo, maximo_de_pasos=MAXIMO_DE_PASOS) -> str:
    """Ejecuta el código y devuelve lo que imprime."""
    interprete = Interprete(codigo)
    for _ in range(maximo_de_pasos):
        if interprete.terminado:
            return "".join(interprete.salida)
        interprete.paso()
    raise LimiteDePasos()


# ----------------------------------------------------------------------
# Traza para el depurador
# ----------------------------------------------------------------------
@dataclass
class Paso:
    indice: int                 # posición de la instrucción en el código
    instruccion: Cuadrupla
    variable: Optional[object] = None    # Nombre o Temporal que cambió
    valor: Optional[Constante] = None    # su nuevo valor
    salida: str = ""            # lo que imprimió este paso

    @property
    def pos(self):
        return self.instruccion.pos

    @property
    def linea(self) -> Optional[int]:
        return self.pos.linea if self.pos else None


@dataclass
class Traza:
    pasos: List[Paso] = field(default_factory=list)
    salida: str = ""
    error: Optional[dict] = None    # error de ejecución (ver errores.py)

    @property
    def termino(self) -> bool:
        return self.error is None

    def variables_en(self, paso: int) -> Dict[Nombre, Constante]:
        """Valor de las variables del programa (sin temporales) después
        de ejecutar los pasos 0..paso."""
        variables = {}
        for p in self.pasos[:paso + 1]:
            if isinstance(p.variable, Nombre):
                variables[p.variable] = p.valor
        return variables

    def salida_hasta(self, paso: int) -> str:
        return "".join(p.salida for p in self.pasos[:paso + 1])


def _error_de_ejecucion(mensaje, instruccion, fuente, **parametros):
    pos = instruccion.pos
    if pos is None:
        return nuevo_error(mensaje, 0, None, parametros=parametros)
    contenido = fuente.get_line(pos.linea) if fuente else None
    return nuevo_error(mensaje, pos.linea, contenido, pos.columna,
                       pos.longitud, parametros)


def _dar_paso(interprete: Interprete) -> Paso:
    indice = interprete.pc
    instruccion = interprete.codigo[indice]
    impreso = len(interprete.salida)
    interprete.paso()
    paso = Paso(indice, instruccion)
    destino = instruccion.definicion()
    if destino is not None:
        paso.variable, paso.valor = destino, interprete.memoria[destino]
    if len(interprete.salida) > impreso:
        paso.salida = interprete.salida[-1]
    return paso


def trazar(codigo: List[Cuadrupla], fuente=None,
           maximo_de_pasos=MAXIMO_DE_PASOS) -> Traza:
    """
    Ejecuta el código guardando cada paso. Nunca lanza excepciones: si el
    programa divide entre cero o no termina, la traza llega hasta ahí y
    `error` dice qué pasó y en qué línea. `fuente` (un SourceCode) se usa
    para mostrar la línea del error.
    """
    interprete = Interprete(codigo)
    traza = Traza()
    while not interprete.terminado:
        if len(traza.pasos) >= maximo_de_pasos:
            traza.error = _error_de_ejecucion(
                mensajes.EJECUCION_SIN_FIN, codigo[interprete.pc], fuente,
                pasos=maximo_de_pasos)
            break
        try:
            traza.pasos.append(_dar_paso(interprete))
        except DivisionEntreCero as division:
            traza.error = _error_de_ejecucion(
                mensajes.EJECUCION_DIVISION_ENTRE_CERO,
                division.instruccion, fuente)
            break
    traza.salida = "".join(interprete.salida)
    return traza
