"""
Código intermedio de tres direcciones (Libro del Dragón, capítulo 6).

El programa se traduce a una lista de cuádruplas (op, arg1, arg2,
resultado) (sección 6.2.2). Las direcciones pueden ser:

* Constante: un valor conocido al compilar (5, 2.5, 'a', "hola", chiqaq).
* Nombre:    una variable del programa.
* Temporal:  un valor intermedio creado por el compilador (t1, t2...).

Todas las direcciones llevan su tipo, porque la generación de código
necesita saber si una suma es de enteros, de decimales o de textos.

Instrucciones (sección 6.2.1):

    x = y op z          op aritmético o relacional
    x = minus y         negación
    x = (chunkayuq) y   conversión de entero a decimal (sección 6.5.2)
    x = y               copia
    goto L
    if x goto L
    ifFalse x goto L
    if x relop y goto L
    L:                  etiqueta
    param x             argumento de rikuchiy
    call rikuchiy, n    imprime los últimos n param y un salto de línea

Las condiciones se traducen con código de saltos y evaluación en
cortocircuito (secciones 6.6.3 a 6.6.6): en `a > 0 && b > 0`, si `a > 0`
es falso no se evalúa `b > 0`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from antachawi.ast_nodos import (
    Asignacion,
    Binaria,
    Bloque,
    Declaracion,
    Imprimir,
    Literal,
    Mientras,
    Para,
    Posicion,
    Programa,
    Si,
    Unaria,
    Variable,
)
from antachawi.tipos import (
    BOOL,
    CHUNKAYUQ,
    NUMERICOS,
    QAYTU,
    SANANPA,
    YUPAY,
    tipo_numerico,
)

# ----------------------------------------------------------------------
# Direcciones
# ----------------------------------------------------------------------
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\",
            "'": "'", '"': '"'}
_ESCAPES_INVERSOS = {v: "\\" + k for k, v in _ESCAPES.items()}


def decodificar_escapes(texto: str) -> str:
    """'a\\\\nb' (con una barra invertida) -> 'a', salto de línea, 'b'."""
    resultado, i = [], 0
    while i < len(texto):
        if texto[i] == "\\" and i + 1 < len(texto):
            resultado.append(_ESCAPES[texto[i + 1]])
            i += 2
        else:
            resultado.append(texto[i])
            i += 1
    return "".join(resultado)


def _escapar(texto: str, comilla: str) -> str:
    return "".join(_ESCAPES_INVERSOS.get(c, c) if c in (comilla, "\\")
                   or c in "\n\t\r\0" else c for c in texto)


@dataclass(frozen=True, eq=False)
class Constante:
    valor: object       # int, float, str (sananpa y qaytu) o bool
    tipo: str

    def _clave(self):
        # repr distingue 0.0 de -0.0 (que en Python son iguales con ==)
        return (self.tipo, repr(self.valor))

    def __eq__(self, otra):
        return isinstance(otra, Constante) and self._clave() == otra._clave()

    def __hash__(self):
        return hash(self._clave())

    def __str__(self):
        if self.tipo == BOOL:
            return "chiqaq" if self.valor else "yanqa"
        if self.tipo == SANANPA:
            return f"'{_escapar(self.valor, chr(39))}'"
        if self.tipo == QAYTU:
            return f'"{_escapar(self.valor, chr(34))}"'
        return repr(self.valor)


@dataclass(frozen=True)
class Nombre:
    nombre: str
    tipo: str

    def __str__(self):
        return self.nombre


@dataclass(frozen=True)
class Temporal:
    numero: int
    tipo: str

    def __str__(self):
        return f"t{self.numero}"


Direccion = Union[Constante, Nombre, Temporal]


def es_variable(direccion) -> bool:
    """Nombres y temporales: direcciones que guardan un valor que cambia."""
    return isinstance(direccion, (Nombre, Temporal))


def valor_de_literal(tipo: str, lexema: str):
    """Valor de un literal del código fuente."""
    if tipo == YUPAY:
        return int(lexema)
    if tipo == CHUNKAYUQ:
        return float(lexema)
    if tipo == BOOL:
        return lexema == "chiqaq"
    return decodificar_escapes(lexema[1:-1])     # sin las comillas


VALOR_POR_DEFECTO = {
    YUPAY: 0,
    CHUNKAYUQ: 0.0,
    SANANPA: "\0",
    QAYTU: "",
    BOOL: False,
}

CHIQAQ = Constante(True, BOOL)
YANQA = Constante(False, BOOL)

# ----------------------------------------------------------------------
# Instrucciones
# ----------------------------------------------------------------------
COPIA = "="
MENOS = "minus"
A_CHUNKAYUQ = "(chunkayuq)"
SALTO = "goto"
SI = "if"
SI_NO = "ifFalse"
ETIQUETA = "label"
PARAMETRO = "param"
LLAMADA = "call"
RIKUCHIY = "rikuchiy"

ARITMETICOS = ("+", "-", "*", "/")
RELACIONALES = ("<", ">", "<=", ">=", "==", "!=")
BINARIOS = ARITMETICOS + RELACIONALES
NEGACION = {"<": ">=", ">=": "<", ">": "<=", "<=": ">", "==": "!=",
            "!=": "=="}

# Saltos relacionales: "if<", "if==", ...
SALTOS_RELACIONALES = tuple(SI + r for r in RELACIONALES)
SALTOS_CONDICIONALES = (SI, SI_NO) + SALTOS_RELACIONALES
SALTOS = (SALTO,) + SALTOS_CONDICIONALES

# Instrucciones que calculan un valor en `resultado` sin efectos laterales
DEFINICIONES = BINARIOS + (MENOS, A_CHUNKAYUQ, COPIA)


def relacion(op: str) -> str:
    """"if<" -> "<"."""
    return op[len(SI):]


@dataclass
class Cuadrupla:
    op: str
    arg1: Optional[object] = None
    arg2: Optional[object] = None
    resultado: Optional[object] = None   # Direccion o etiqueta
    # Sentencia del código fuente de la que salió la instrucción (para el
    # depurador y los mensajes de error). No cuenta al comparar.
    pos: Optional[Posicion] = field(default=None, compare=False)

    def definicion(self) -> Optional[Direccion]:
        """Variable a la que esta instrucción da un valor, si hay una."""
        return self.resultado if self.op in DEFINICIONES else None

    def usos(self) -> List[Direccion]:
        """Variables cuyo valor lee esta instrucción."""
        return [a for a in (self.arg1, self.arg2) if es_variable(a)]

    def es_salto(self) -> bool:
        return self.op in SALTOS

    def __str__(self):
        if self.op in BINARIOS:
            return f"{self.resultado} = {self.arg1} {self.op} {self.arg2}"
        if self.op in SALTOS_RELACIONALES:
            return (f"if {self.arg1} {relacion(self.op)} {self.arg2} "
                    f"goto {self.resultado}")
        formatos = {
            COPIA: "{r} = {a}",
            MENOS: "{r} = minus {a}",
            A_CHUNKAYUQ: "{r} = (chunkayuq) {a}",
            SALTO: "goto {r}",
            SI: "if {a} goto {r}",
            SI_NO: "ifFalse {a} goto {r}",
            ETIQUETA: "{r}:",
            PARAMETRO: "param {a}",
            LLAMADA: "call {a}, {b}",
        }
        return formatos[self.op].format(a=self.arg1, b=self.arg2,
                                        r=self.resultado)


def formatear_codigo(codigo: List[Cuadrupla]) -> str:
    """Una instrucción por línea; las etiquetas sin sangría."""
    return "\n".join(str(c) if c.op == ETIQUETA else f"    {c}"
                     for c in codigo)


# ----------------------------------------------------------------------
# Generación (esquemas de traducción de las secciones 6.4 y 6.6)
# ----------------------------------------------------------------------
def _tipo_comun(izquierdo: str, derecho: str) -> str:
    if izquierdo in NUMERICOS and derecho in NUMERICOS:
        return tipo_numerico(izquierdo, derecho)
    return izquierdo


class GeneradorIntermedio:
    """Recorre el AST ya analizado (con tipos y símbolos) y produce el
    código de tres direcciones."""

    def __init__(self):
        self.codigo: List[Cuadrupla] = []
        self._temporales = 0
        self._etiquetas = 0
        self._nombres = {}          # Simbolo -> Nombre
        self._nombres_usados = set()
        self._pos: Optional[Posicion] = None    # sentencia actual
        self._sentencias = {
            Declaracion: self._declaracion,
            Asignacion: self._asignacion,
            Imprimir: self._imprimir,
            Si: self._si,
            Mientras: self._mientras,
            Para: self._para,
        }

    def generar(self, programa: Programa) -> List[Cuadrupla]:
        self._bloque(programa.cuerpo)
        return self.codigo

    # ------------------------------------------------------------------
    # Utilidades: newtemp, newlabel y gen del libro
    # ------------------------------------------------------------------
    def nuevo_temporal(self, tipo: str) -> Temporal:
        self._temporales += 1
        return Temporal(self._temporales, tipo)

    def nueva_etiqueta(self) -> str:
        self._etiquetas += 1
        return f"L{self._etiquetas}"

    def emitir(self, op, arg1=None, arg2=None, resultado=None):
        self.codigo.append(Cuadrupla(op, arg1, arg2, resultado,
                                     self._pos))

    def _nombre(self, simbolo) -> Nombre:
        """Nombre único para cada símbolo. Dos bloques hermanos pueden
        declarar una variable con el mismo nombre; la segunda se llama
        x.2 (el punto no puede aparecer en un nombre de Antachawi)."""
        if simbolo not in self._nombres:
            nombre, n = simbolo.nombre, 1
            while nombre in self._nombres_usados:
                n += 1
                nombre = f"{simbolo.nombre}.{n}"
            self._nombres_usados.add(nombre)
            self._nombres[simbolo] = Nombre(nombre, simbolo.tipo)
        return self._nombres[simbolo]

    # ------------------------------------------------------------------
    # Sentencias
    # ------------------------------------------------------------------
    def _bloque(self, bloque: Bloque):
        for sentencia in bloque.sentencias:
            self._sentencia(sentencia)

    def _sentencia(self, sentencia, traducir=None):
        """Traduce la sentencia; sus instrucciones llevan su posición. Al
        terminar se vuelve a la de la sentencia que la contiene (así el
        `goto` del final de un bucle es de la línea del bucle)."""
        traducir = traducir or self._sentencias[type(sentencia)]
        anterior, self._pos = self._pos, sentencia.pos
        traducir(sentencia)
        self._pos = anterior

    def _declaracion(self, declaracion: Declaracion):
        destino = self._nombre(declaracion.simbolo)
        if declaracion.valor is None:
            # Toda variable empieza con un valor conocido
            valor = Constante(VALOR_POR_DEFECTO[destino.tipo], destino.tipo)
            self.emitir(COPIA, valor, resultado=destino)
        else:
            self._asignar(destino, declaracion.valor)

    def _asignacion(self, asignacion: Asignacion):
        self._asignar(self._nombre(asignacion.simbolo), asignacion.valor)

    def _asignar(self, destino: Nombre, expresion):
        valor = self.ampliar(self.expresion(expresion), destino.tipo)
        self.emitir(COPIA, valor, resultado=destino)

    def _imprimir(self, imprimir: Imprimir):
        # Primero se evalúan todos los argumentos y luego se pasan
        # (sección 6.4.4, llamadas a procedimientos).
        direcciones = [self.expresion(a) for a in imprimir.argumentos]
        for direccion in direcciones:
            self.emitir(PARAMETRO, direccion)
        self.emitir(LLAMADA, RIKUCHIY, len(direcciones))

    def _si(self, si: Si, fin: Optional[str] = None):
        """
        S -> ari (B) S1 mana_chayqa S2   (figura 6.36):

                ifFalse B goto falso
                S1
                goto fin
            falso:
                S2
            fin:

        Una cadena de mana_chayqa_ari comparte la misma etiqueta `fin`.
        """
        exterior = fin is None
        fin = fin or self.nueva_etiqueta()
        falso = fin if si.si_no is None else self.nueva_etiqueta()

        self.saltar(si.condicion, None, falso)
        self._bloque(si.entonces)
        if si.si_no is not None:
            self.emitir(SALTO, resultado=fin)
            self.emitir(ETIQUETA, resultado=falso)
            if isinstance(si.si_no, Si):
                self._sentencia(si.si_no, lambda s: self._si(s, fin))
            else:
                self._bloque(si.si_no)
        if exterior:
            self.emitir(ETIQUETA, resultado=fin)

    def _mientras(self, mientras: Mientras):
        """
        S -> chaykama (B) S1   (figura 6.36):

            inicio:
                ifFalse B goto fin
                S1
                goto inicio
            fin:
        """
        self._bucle(mientras.condicion, mientras.cuerpo, None)

    def _para(self, para: Para):
        """
        S -> imapaq (I; B; P) S1 es igual a
             I  y luego  chaykama (B) { S1  P }
        """
        self._sentencia(para.inicio)
        self._bucle(para.condicion, para.cuerpo, para.paso)

    def _bucle(self, condicion, cuerpo: Bloque, paso):
        inicio, fin = self.nueva_etiqueta(), self.nueva_etiqueta()
        self.emitir(ETIQUETA, resultado=inicio)
        self.saltar(condicion, None, fin)
        self._bloque(cuerpo)
        if paso is not None:
            self._sentencia(paso)
        self.emitir(SALTO, resultado=inicio)
        self.emitir(ETIQUETA, resultado=fin)

    # ------------------------------------------------------------------
    # Expresiones: devuelven la dirección que guarda su valor (E.addr)
    # ------------------------------------------------------------------
    def expresion(self, expresion) -> Direccion:
        if isinstance(expresion, Literal):
            return Constante(valor_de_literal(expresion.tipo_literal,
                                              expresion.valor),
                             expresion.tipo)
        if isinstance(expresion, Variable):
            return self._nombre(expresion.simbolo)
        if isinstance(expresion, Unaria):
            operando = self.expresion(expresion.operando)
            temporal = self.nuevo_temporal(expresion.tipo)
            self.emitir(MENOS, operando, resultado=temporal)
            return temporal
        if expresion.operador in ("&&", "||"):
            return self._valor_logico(expresion)
        izquierda, derecha = self._operandos(expresion)
        temporal = self.nuevo_temporal(expresion.tipo)
        self.emitir(expresion.operador, izquierda, derecha, temporal)
        return temporal

    def ampliar(self, direccion: Direccion, tipo: str) -> Direccion:
        """widen(a, t, w) de la sección 6.5.2: convierte un entero a
        decimal cuando el contexto lo pide."""
        if tipo == CHUNKAYUQ and direccion.tipo == YUPAY:
            temporal = self.nuevo_temporal(CHUNKAYUQ)
            self.emitir(A_CHUNKAYUQ, direccion, resultado=temporal)
            return temporal
        return direccion

    def _operandos(self, binaria: Binaria):
        """Evalúa ambos lados y los lleva al mismo tipo (en 2 + 0.5 el 2
        se convierte a chunkayuq antes de sumar)."""
        izquierda = self.expresion(binaria.izquierda)
        derecha = self.expresion(binaria.derecha)
        tipo = _tipo_comun(izquierda.tipo, derecha.tipo)
        return self.ampliar(izquierda, tipo), self.ampliar(derecha, tipo)

    def _valor_logico(self, expresion: Binaria) -> Temporal:
        """Valor de && o || fuera de una condición, por ejemplo en
        `bool b = x > 0 && y > 0`:

                <código de saltos para la expresión, falso -> Lf>
                t = chiqaq
                goto Lfin
            Lf: t = yanqa
            Lfin:
        """
        temporal = self.nuevo_temporal(BOOL)
        falso, fin = self.nueva_etiqueta(), self.nueva_etiqueta()
        self.saltar(expresion, None, falso)
        self.emitir(COPIA, CHIQAQ, resultado=temporal)
        self.emitir(SALTO, resultado=fin)
        self.emitir(ETIQUETA, resultado=falso)
        self.emitir(COPIA, YANQA, resultado=temporal)
        self.emitir(ETIQUETA, resultado=fin)
        return temporal

    # ------------------------------------------------------------------
    # Código de saltos (sección 6.6.5: verdadero/falso = None significa
    # "seguir con la siguiente instrucción", la etiqueta fall del libro)
    # ------------------------------------------------------------------
    def saltar(self, expresion, verdadero: Optional[str],
               falso: Optional[str]):
        if isinstance(expresion, Binaria) and expresion.operador == "&&":
            self._saltar_y(expresion, verdadero, falso)
        elif isinstance(expresion, Binaria) and expresion.operador == "||":
            self._saltar_o(expresion, verdadero, falso)
        elif (isinstance(expresion, Binaria)
              and expresion.operador in RELACIONALES):
            self._saltar_relacional(expresion, verdadero, falso)
        elif isinstance(expresion, Literal):
            destino = verdadero if expresion.valor == "chiqaq" else falso
            if destino is not None:
                self.emitir(SALTO, resultado=destino)
        else:
            self._emitir_saltos(SI, SI_NO, self.expresion(expresion), None,
                                verdadero, falso)

    def _saltar_y(self, expresion, verdadero, falso):
        # B -> B1 && B2: si B1 es falso, B es falso sin evaluar B2
        falso_izquierda = falso or self.nueva_etiqueta()
        self.saltar(expresion.izquierda, None, falso_izquierda)
        self.saltar(expresion.derecha, verdadero, falso)
        if falso is None:
            self.emitir(ETIQUETA, resultado=falso_izquierda)

    def _saltar_o(self, expresion, verdadero, falso):
        # B -> B1 || B2: si B1 es verdadero, B es verdadero sin evaluar B2
        verdadero_izquierda = verdadero or self.nueva_etiqueta()
        self.saltar(expresion.izquierda, verdadero_izquierda, None)
        self.saltar(expresion.derecha, verdadero, falso)
        if verdadero is None:
            self.emitir(ETIQUETA, resultado=verdadero_izquierda)

    def _saltar_relacional(self, expresion, verdadero, falso):
        izquierda, derecha = self._operandos(expresion)
        operador = expresion.operador
        if izquierda.tipo == CHUNKAYUQ and verdadero is None:
            # Con decimales no se puede negar la comparación: si un valor
            # es NaN, tanto a < b como a >= b son falsos.
            temporal = self.nuevo_temporal(BOOL)
            self.emitir(operador, izquierda, derecha, temporal)
            self._emitir_saltos(SI, SI_NO, temporal, None, None, falso)
            return
        self._emitir_saltos(SI + operador, SI + NEGACION[operador],
                            izquierda, derecha, verdadero, falso)

    def _emitir_saltos(self, op_verdadero, op_falso, arg1, arg2,
                       verdadero, falso):
        if verdadero is not None:
            self.emitir(op_verdadero, arg1, arg2, verdadero)
            if falso is not None:
                self.emitir(SALTO, resultado=falso)
        elif falso is not None:
            self.emitir(op_falso, arg1, arg2, falso)


def generar_codigo_intermedio(programa: Programa) -> List[Cuadrupla]:
    return GeneradorIntermedio().generar(programa)
