"""
Construcción del AST a partir del árbol de derivación del parser.

La gramática es LL(1), así que no tiene recursión por la izquierda: una
expresión como a - b - c se deriva como

    ExpresionAditiva -> ExpresionMultiplicativa(a) ExpresionAditivaPrime(- b
                        ...)

Para recuperar la asociatividad por la izquierda, (a - b) - c, se recorre
la cadena de nodos "Prime" pasando el árbol construido hasta el momento
como atributo heredado (Libro del Dragón, sección 5.4 y figura 5.13).

Solo se debe llamar con árboles sin errores sintácticos.
"""
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
from antachawi.definitions import EtiquetasAntachawy as E

# Etiqueta del token literal -> tipo del lenguaje
TIPO_DE_LITERAL = {
    E.NUMEROENTERO: "yupay",
    E.NUMEROFLOTANTE: "chunkayuq",
    E.CARACTER: "sananpa",
    E.CADENA: "qaytu",
    E.TRUE: "bool",
    E.FALSE: "bool",
}


def posicion_de(hoja) -> Posicion:
    """Posición del token guardado en una hoja del árbol de derivación."""
    token = hoja.token
    return Posicion(token.linea, token.columna, len(token.lexema))


def _hoja(nodo):
    """Primera hoja (token) dentro de un nodo envoltorio como ID u
    OperadorAditivo."""
    return nodo.children[0]


def construir_ast(arbol) -> Programa:
    """Árbol de derivación (nodo "Programa") -> AST."""
    definicion = arbol.children[0]
    bloque = next(h for h in definicion.children if h.name == "Bloque")
    return Programa(_bloque(bloque))


# ----------------------------------------------------------------------
# Sentencias
# ----------------------------------------------------------------------
def _bloque(nodo) -> Bloque:
    # Bloque -> { NL ListaSentencias }
    llave, _, lista, _ = nodo.children
    sentencias = []
    while lista.children:
        # ListaSentencias -> Sentencias ListaSentencias
        sentencia, lista = lista.children
        sentencias.append(_sentencia(sentencia.children[0]))
    return Bloque(sentencias, posicion_de(llave))


def _sentencia(nodo):
    constructores = {
        "Declaraciones": _declaracion,
        "Asignaciones": _asignacion,
        "Impresiones": _impresion,
        "Condicional": _condicional,
        "Mientras": _mientras,
        "Para": _para,
    }
    return constructores[nodo.name](nodo)


def _declaracion(nodo) -> Declaracion:
    # Declaraciones -> Tipo ID DeclaracionesPrime
    tipo, envoltorio_id, prima = nodo.children
    hoja_id = _hoja(envoltorio_id)
    valor = _expresion(prima.children[1]) if prima.children else None
    return Declaracion(_hoja(tipo).name, hoja_id.name, valor,
                       posicion_de(hoja_id))


def _asignacion(nodo) -> Asignacion:
    # Asignaciones -> ID = Expresion
    envoltorio_id, _, expresion = nodo.children
    hoja_id = _hoja(envoltorio_id)
    return Asignacion(hoja_id.name, _expresion(expresion),
                      posicion_de(hoja_id))


def _impresion(nodo) -> Imprimir:
    # Impresiones -> rikuchiy ( ExpresionImpresion )
    rikuchiy, _, lista, _ = nodo.children
    argumentos = []
    while lista is not None:
        # ExpresionImpresion -> Expresion ExpresionImpresionPrime
        expresion, prima = lista.children
        argumentos.append(_expresion(expresion))
        lista = prima.children[1] if prima.children else None
    return Imprimir(argumentos, posicion_de(rikuchiy))


def _condicional(nodo) -> Si:
    # Condicional -> ari ( Expresion ) Bloque CondicionalPrime
    ari, _, condicion, _, bloque, prima = nodo.children
    return Si(_expresion(condicion), _bloque(bloque), _si_no(prima),
              posicion_de(ari))


def _si_no(prima):
    # CondicionalPrime -> mana_chayqa_ari ( Expresion ) Bloque
    #                     CondicionalPrime
    #                   | mana_chayqa Bloque
    #                   | ε
    if not prima.children:
        return None
    if len(prima.children) == 2:
        return _bloque(prima.children[1])
    return _condicional(prima)


def _mientras(nodo) -> Mientras:
    # Mientras -> chaykama ( Expresion ) Bloque
    chaykama, _, condicion, _, bloque = nodo.children
    return Mientras(_expresion(condicion), _bloque(bloque),
                    posicion_de(chaykama))


def _para(nodo) -> Para:
    # Para -> imapaq ( ParaInicio ; Expresion ; Asignaciones ) Bloque
    imapaq, _, inicio, _, condicion, _, paso, _, bloque = nodo.children
    return Para(_sentencia(inicio.children[0]), _expresion(condicion),
                _asignacion(paso), _bloque(bloque), posicion_de(imapaq))


# ----------------------------------------------------------------------
# Expresiones
# ----------------------------------------------------------------------
def _expresion(nodo):
    constructores = {
        "Expresion": _cadena_izquierda,
        "ExpresionY": _cadena_izquierda,
        "ExpresionAditiva": _cadena_izquierda,
        "ExpresionMultiplicativa": _cadena_izquierda,
        "ExpresionRelacional": _relacional,
        "Termino": _termino,
    }
    return constructores[nodo.name](nodo)


def _binaria(envoltorio_operador, izquierda, derecha) -> Binaria:
    hoja = _hoja(envoltorio_operador)
    return Binaria(hoja.name, izquierda, derecha,
                   izquierda.pos.hasta(derecha.pos), posicion_de(hoja))


def _cadena_izquierda(nodo):
    """
    X -> Operando XPrime
    XPrime -> Operador Operando XPrime | ε

    El árbol acumulado se pasa a cada XPrime (atributo heredado) para
    formar (((a op b) op c) op d).
    """
    primero, prima = nodo.children
    acumulado = _expresion(primero)
    while prima.children:
        operador, operando, prima = prima.children
        acumulado = _binaria(operador, acumulado, _expresion(operando))
    return acumulado


def _relacional(nodo):
    # ExpresionRelacional -> ExpresionAditiva ExpresionRelacionalPrime
    # ExpresionRelacionalPrime -> OperadorRelacional ExpresionAditiva | ε
    # (no es asociativa: a < b < c no es válido)
    izquierda, prima = nodo.children
    resultado = _expresion(izquierda)
    if prima.children:
        operador, derecha = prima.children
        resultado = _binaria(operador, resultado, _expresion(derecha))
    return resultado


def _termino(nodo):
    # Termino -> - Termino | ( Expresion ) | id | literal
    primero = nodo.children[0]
    if primero.name == "-":
        operando = _termino(nodo.children[1])
        pos_menos = posicion_de(primero)
        return Unaria("-", operando, pos_menos.hasta(operando.pos),
                      pos_menos)
    if primero.name == "(":
        interna = _expresion(nodo.children[1])
        # Se amplía la posición para incluir los paréntesis.
        interna.pos = posicion_de(primero).hasta(
            posicion_de(nodo.children[2]))
        return interna
    hoja = _hoja(primero)
    if hoja.token.etiqueta == E.ID:
        return Variable(hoja.name, posicion_de(hoja))
    return Literal(TIPO_DE_LITERAL[hoja.token.etiqueta], hoja.token.lexema,
                   posicion_de(hoja))
