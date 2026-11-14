"""
Optimización independiente de la máquina sobre el código de tres
direcciones (Libro del Dragón, secciones 8.5, 8.7, 9.1 y 9.2).

Las pasadas se repiten hasta que el código ya no cambia, porque cada una
abre oportunidades para las otras:

1. Optimización local de cada bloque básico (8.5):
   * propagación de constantes y de copias (9.1.5): después de `a = 5`,
     `t1 = a + 1` pasa a ser `t1 = 5 + 1`;
   * plegado de constantes (9.1.4): `t1 = 5 + 1` pasa a ser `t1 = 6`;
   * identidades algebraicas (8.5.4): `x + 0`, `x * 1`, `x * 0`...;
   * subexpresiones comunes (8.5.1, 9.1.3): si `a * b` ya se calculó en
     el bloque y no cambió, se reutiliza;
   * saltos con condición constante: `if 6 > 1 goto L` pasa a `goto L`.
2. Eliminación de código inalcanzable: bloques a los que no llega ninguna
   arista del grafo de flujo.
3. Eliminación de código muerto con el análisis de variables vivas
   (9.2.5): se borra `x = ...` si ese valor de x nunca se vuelve a leer.
4. Optimización de mirilla (8.7): saltos a saltos, saltos a la siguiente
   instrucción, `if c goto L1 / goto L2 / L1:` -> `ifFalse c goto L2`,
   etiquetas sin uso, y `t = a + b / x = t` -> `x = a + b`.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional, Set

from antachawi.bloques_basicos import (
    BloqueBasico,
    alcanzables,
    aplanar,
    particionar,
)
from antachawi.intermedio import (
    A_CHUNKAYUQ,
    BINARIOS,
    COPIA,
    ETIQUETA,
    MENOS,
    NEGACION,
    SALTO,
    SALTOS_CONDICIONALES,
    SALTOS_RELACIONALES,
    SI,
    SI_NO,
    Constante,
    Cuadrupla,
    Temporal,
    es_variable,
    formatear_codigo,
    relacion,
)
from antachawi.tipos import CHUNKAYUQ, QAYTU, SANANPA, YUPAY

MAXIMO_DE_PASADAS = 50
_BITS = 64


# ----------------------------------------------------------------------
# Evaluación en tiempo de compilación (plegado de constantes)
# ----------------------------------------------------------------------
def _entero_de_64_bits(n: int) -> int:
    """Desborda igual que un entero de 64 bits del procesador."""
    return (n + 2 ** (_BITS - 1)) % 2 ** _BITS - 2 ** (_BITS - 1)


def _division_entera(a: int, b: int) -> int:
    # Como idiv: trunca hacia cero (en Python // redondea hacia abajo)
    cociente = abs(a) // abs(b)
    return cociente if (a < 0) == (b < 0) else -cociente


_ARITMETICA = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
}

_COMPARACIONES = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def comparar(operador: str, a: Constante, b: Constante) -> bool:
    valor_a, valor_b = a.valor, b.valor
    if a.tipo == SANANPA:
        valor_a, valor_b = ord(valor_a), ord(valor_b)
    return _COMPARACIONES[operador](valor_a, valor_b)


def _aritmetica(operador: str, a: Constante, b: Constante):
    if operador == "/" and b.valor == 0:
        return None         # se deja para la ejecución
    if a.tipo != YUPAY:
        return _ARITMETICA[operador](a.valor, b.valor)
    if operador == "/":
        return _entero_de_64_bits(_division_entera(a.valor, b.valor))
    return _entero_de_64_bits(_ARITMETICA[operador](a.valor, b.valor))


def plegar(instruccion: Cuadrupla) -> Optional[Constante]:
    """Valor de la instrucción si todos sus operandos son constantes."""
    op, a, b = instruccion.op, instruccion.arg1, instruccion.arg2
    tipo = instruccion.resultado.tipo
    if not isinstance(a, Constante):
        return None
    if op == COPIA:
        return a
    if op == MENOS:
        valor = -a.valor
        return Constante(_entero_de_64_bits(valor) if tipo == YUPAY
                         else valor, tipo)
    if op == A_CHUNKAYUQ:
        return Constante(float(a.valor), tipo)
    if not isinstance(b, Constante):
        return None
    if op in _COMPARACIONES:
        return Constante(comparar(op, a, b), tipo)
    valor = _aritmetica(op, a, b)
    return None if valor is None else Constante(valor, tipo)


def _es_entero(direccion, valor: int) -> bool:
    return (isinstance(direccion, Constante) and direccion.tipo == YUPAY
            and direccion.valor == valor)


def simplificar(instruccion: Cuadrupla) -> Cuadrupla:
    """Identidades algebraicas (solo con enteros: con decimales x + 0.0
    no es igual a x cuando x es -0.0)."""
    op, a, b = instruccion.op, instruccion.arg1, instruccion.arg2
    destino = instruccion.resultado
    if destino.tipo != YUPAY or op not in ("+", "-", "*", "/"):
        return instruccion
    copia = None
    if op in ("+", "-") and _es_entero(b, 0) \
            or op in ("*", "/") and _es_entero(b, 1):
        copia = a                                   # x+0, x-0, x*1, x/1
    elif op == "+" and _es_entero(a, 0) or op == "*" and _es_entero(a, 1):
        copia = b                                   # 0+x, 1*x
    elif op == "*" and (_es_entero(a, 0) or _es_entero(b, 0)):
        copia = Constante(0, YUPAY)                 # x*0, 0*x
    if copia is None:
        return instruccion
    return Cuadrupla(COPIA, copia, resultado=destino, pos=instruccion.pos)


# ----------------------------------------------------------------------
# 1. Optimización local de un bloque básico
# ----------------------------------------------------------------------
_CONMUTATIVOS = ("*", "==", "!=")


def _clave_expresion(instruccion: Cuadrupla):
    op, a, b = instruccion.op, instruccion.arg1, instruccion.arg2
    conmutativo = op in _CONMUTATIVOS or (
        op == "+" and instruccion.resultado.tipo != QAYTU)
    if conmutativo and str(b) < str(a):
        a, b = b, a
    return (op, a, b, instruccion.resultado.tipo)


class ValoresConocidos:
    """Lo que se sabe en un punto de un bloque básico (es la información
    que guarda el GDA de la sección 8.5.1):

    * copias: variable -> constante o variable con el mismo valor;
    * expresiones: (op, arg1, arg2) -> variable que ya tiene ese valor.
    """

    def __init__(self):
        self.copias: Dict[object, object] = {}
        self.expresiones: Dict[tuple, object] = {}

    def sustituir(self, direccion):
        if es_variable(direccion):
            return self.copias.get(direccion, direccion)
        return direccion

    def reutilizar(self, instruccion: Cuadrupla) -> Cuadrupla:
        if instruccion.op not in BINARIOS + (MENOS, A_CHUNKAYUQ):
            return instruccion
        previa = self.expresiones.get(_clave_expresion(instruccion))
        if previa is None:
            return instruccion
        return Cuadrupla(COPIA, previa, resultado=instruccion.resultado,
                         pos=instruccion.pos)

    def redefinir(self, instruccion: Cuadrupla):
        """La instrucción le da un valor nuevo a su destino: se olvida
        todo lo que dependía del valor anterior."""
        destino = instruccion.resultado
        self.copias = {v: c for v, c in self.copias.items()
                       if destino not in (v, c)}
        self.expresiones = {
            clave: v for clave, v in self.expresiones.items()
            if v != destino and destino not in clave[1:3]}
        argumentos = (instruccion.arg1, instruccion.arg2)
        if instruccion.op == COPIA:
            if instruccion.arg1 != destino:
                self.copias[destino] = instruccion.arg1
        elif destino not in argumentos:
            self.expresiones[_clave_expresion(instruccion)] = destino


def resolver_salto(instruccion: Cuadrupla) -> Optional[Cuadrupla]:
    """Un salto condicional con condición constante se vuelve un goto
    (si se cumple) o desaparece (si no)."""
    a, b = instruccion.arg1, instruccion.arg2
    if instruccion.op in (SI, SI_NO):
        if not isinstance(a, Constante):
            return instruccion
        salta = bool(a.valor) == (instruccion.op == SI)
    elif isinstance(a, Constante) and isinstance(b, Constante):
        salta = comparar(relacion(instruccion.op), a, b)
    else:
        return instruccion
    if not salta:
        return None
    return Cuadrupla(SALTO, resultado=instruccion.resultado,
                     pos=instruccion.pos)


def _optimizar_instruccion(instruccion: Cuadrupla,
                           valores: ValoresConocidos):
    instruccion = replace(instruccion,
                          arg1=valores.sustituir(instruccion.arg1),
                          arg2=valores.sustituir(instruccion.arg2))
    if instruccion.op in SALTOS_CONDICIONALES:
        return resolver_salto(instruccion)
    if instruccion.definicion() is None:
        return instruccion
    constante = plegar(instruccion)
    if constante is not None:
        instruccion = Cuadrupla(COPIA, constante,
                                resultado=instruccion.resultado,
                                pos=instruccion.pos)
    else:
        instruccion = valores.reutilizar(simplificar(instruccion))
    valores.redefinir(instruccion)
    return instruccion


def optimizar_bloque(instrucciones: List[Cuadrupla]) -> List[Cuadrupla]:
    valores = ValoresConocidos()
    resultado = []
    for instruccion in instrucciones:
        nueva = _optimizar_instruccion(instruccion, valores)
        if nueva is not None:
            resultado.append(nueva)
    return resultado


# ----------------------------------------------------------------------
# 3. Variables vivas y código muerto (sección 9.2.5)
# ----------------------------------------------------------------------
def _uso_y_definicion(bloque: BloqueBasico):
    """use_B: variables que se leen antes de definirse en el bloque.
    def_B: variables que se definen en el bloque."""
    usadas, definidas = set(), set()
    for instruccion in bloque.instrucciones:
        usadas.update(u for u in instruccion.usos() if u not in definidas)
        if instruccion.definicion() is not None:
            definidas.add(instruccion.definicion())
    return usadas, definidas


def variables_vivas(bloques: List[BloqueBasico]) -> Dict[BloqueBasico, Set]:
    """OUT[B] de cada bloque (algoritmo 9.14). Al final del programa no
    hay ninguna variable viva."""
    uso_def = {b: _uso_y_definicion(b) for b in bloques}
    entrada = {b: set() for b in bloques}
    salida = {b: set() for b in bloques}
    cambio = True
    while cambio:
        cambio = False
        for bloque in reversed(bloques):
            salida[bloque] = set().union(
                *(entrada[s] for s in bloque.sucesores))
            usadas, definidas = uso_def[bloque]
            nueva = usadas | (salida[bloque] - definidas)
            if nueva != entrada[bloque]:
                entrada[bloque], cambio = nueva, True
    return salida


def eliminar_codigo_muerto(bloques: List[BloqueBasico]):
    """Recorre cada bloque de abajo hacia arriba sabiendo qué variables
    están vivas; una definición de una variable muerta se borra (ninguna
    instrucción con destino tiene efectos laterales)."""
    salida = variables_vivas(bloques)
    for bloque in bloques:
        vivas = set(salida[bloque])
        conservadas = []
        for instruccion in reversed(bloque.instrucciones):
            destino = instruccion.definicion()
            if destino is not None and destino not in vivas:
                continue
            vivas.discard(destino)
            vivas.update(instruccion.usos())
            conservadas.append(instruccion)
        bloque.instrucciones = conservadas[::-1]


# ----------------------------------------------------------------------
# 4. Optimización de mirilla (sección 8.7)
# ----------------------------------------------------------------------
def _destino_final(etiqueta: str, codigo: List[Cuadrupla]) -> str:
    """Saltos a saltos (8.7.3): si en L solo hay `goto M`, saltar a L
    es lo mismo que saltar a M."""
    posicion = {c.resultado: i for i, c in enumerate(codigo)
                if c.op == ETIQUETA}
    vistas = set()
    while etiqueta not in vistas:
        vistas.add(etiqueta)
        i = posicion[etiqueta] + 1
        while i < len(codigo) and codigo[i].op == ETIQUETA:
            i += 1
        if i == len(codigo) or codigo[i].op != SALTO:
            break
        etiqueta = codigo[i].resultado
    return etiqueta


def saltos_a_saltos(codigo: List[Cuadrupla]) -> List[Cuadrupla]:
    return [replace(c, resultado=_destino_final(c.resultado, codigo))
            if c.es_salto() else c for c in codigo]


def _etiquetas_siguientes(codigo: List[Cuadrupla], i: int) -> Set[str]:
    """Etiquetas que están justo después de la instrucción i."""
    etiquetas = set()
    for siguiente in codigo[i + 1:]:
        if siguiente.op != ETIQUETA:
            break
        etiquetas.add(siguiente.resultado)
    return etiquetas


def _se_puede_invertir(instruccion: Cuadrupla) -> bool:
    if instruccion.op in (SI, SI_NO):
        return True
    # Con decimales la negación no vale si hay NaN (ver intermedio.py)
    return (instruccion.op in SALTOS_RELACIONALES
            and instruccion.arg1.tipo != CHUNKAYUQ)


def _invertir(instruccion: Cuadrupla, destino: str) -> Cuadrupla:
    if instruccion.op in (SI, SI_NO):
        op = SI_NO if instruccion.op == SI else SI
    else:
        op = SI + NEGACION[relacion(instruccion.op)]
    return replace(instruccion, op=op, resultado=destino)


def _invertir_salto_sobre_goto(codigo, i) -> Optional[Cuadrupla]:
    """if c goto L1      =>    ifFalse c goto L2
       goto L2                 L1:
       L1:                                         (ejemplo de 8.7.2)"""
    actual = codigo[i]
    if (i + 1 < len(codigo) and codigo[i + 1].op == SALTO
            and actual.op in SALTOS_CONDICIONALES
            and _se_puede_invertir(actual)
            and actual.resultado in _etiquetas_siguientes(codigo, i + 1)):
        return _invertir(actual, codigo[i + 1].resultado)
    return None


def saltos_innecesarios(codigo: List[Cuadrupla]) -> List[Cuadrupla]:
    resultado, i = [], 0
    while i < len(codigo):
        actual = codigo[i]
        invertido = _invertir_salto_sobre_goto(codigo, i)
        if invertido is not None:
            resultado.append(invertido)
            i += 2
            continue
        # Un salto a la instrucción siguiente no hace nada
        if not (actual.es_salto()
                and actual.resultado in _etiquetas_siguientes(codigo, i)):
            resultado.append(actual)
        i += 1
    return resultado


def etiquetas_sin_uso(codigo: List[Cuadrupla]) -> List[Cuadrupla]:
    usadas = {c.resultado for c in codigo if c.es_salto()}
    return [c for c in codigo
            if c.op != ETIQUETA or c.resultado in usadas]


def fusionar_temporales(codigo: List[Cuadrupla]) -> List[Cuadrupla]:
    """t = a + b       =>    x = a + b
       x = t                (si t no se usa en ningún otro lugar)"""
    usos: Dict[object, int] = {}
    for instruccion in codigo:
        for uso in instruccion.usos():
            usos[uso] = usos.get(uso, 0) + 1
    resultado = []
    for instruccion in codigo:
        anterior = resultado[-1] if resultado else None
        if (anterior is not None and instruccion.op == COPIA
                and isinstance(instruccion.arg1, Temporal)
                and anterior.definicion() == instruccion.arg1
                and usos[instruccion.arg1] == 1
                and instruccion.arg1.tipo == instruccion.resultado.tipo):
            resultado[-1] = replace(anterior,
                                    resultado=instruccion.resultado)
            continue
        resultado.append(instruccion)
    return resultado


# ----------------------------------------------------------------------
# Optimizador completo
# ----------------------------------------------------------------------
def pasada(codigo: List[Cuadrupla]) -> List[Cuadrupla]:
    bloques = particionar(codigo)
    for bloque in bloques:
        bloque.instrucciones = optimizar_bloque(bloque.instrucciones)
    # Los saltos pudieron cambiar: se vuelve a armar el grafo de flujo
    bloques = alcanzables(particionar(aplanar(bloques)))
    bloques = particionar(aplanar(bloques))
    eliminar_codigo_muerto(bloques)
    codigo = aplanar(bloques)
    for mirilla in (saltos_a_saltos, saltos_innecesarios,
                    etiquetas_sin_uso, fusionar_temporales):
        codigo = mirilla(codigo)
    return codigo


def optimizar(codigo: List[Cuadrupla]) -> List[Cuadrupla]:
    for _ in range(MAXIMO_DE_PASADAS):
        nuevo = pasada(codigo)
        if formatear_codigo(nuevo) == formatear_codigo(codigo):
            return nuevo
        codigo = nuevo
    return codigo
