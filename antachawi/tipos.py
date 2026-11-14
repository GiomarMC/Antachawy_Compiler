"""
Sistema de tipos de Antachawi (Libro del Dragón, sección 6.5).

Las reglas están en tablas y funciones pequeñas para poder leerlas de un
vistazo. Cada función devuelve el tipo del resultado, o None si la
operación no es válida para esos tipos.

ERROR es el "tipo error": lo recibe una expresión que ya tuvo un error.
Cualquier operación con ERROR da ERROR sin reportar nada nuevo, así un solo
error no produce una cascada de mensajes.
"""
YUPAY = "yupay"           # entero
CHUNKAYUQ = "chunkayuq"   # decimal
SANANPA = "sananpa"       # carácter
QAYTU = "qaytu"           # texto
BOOL = "bool"
ERROR = "<error>"

NUMERICOS = {YUPAY, CHUNKAYUQ}

ARITMETICOS = {"+", "-", "*", "/"}
DE_ORDEN = {"<", ">", "<=", ">="}
DE_IGUALDAD = {"==", "!="}
LOGICOS = {"&&", "||"}


def tipo_numerico(izquierdo, derecho):
    """Conversión implícita (sección 6.5.2): si uno de los dos es decimal,
    el resultado es decimal."""
    return CHUNKAYUQ if CHUNKAYUQ in (izquierdo, derecho) else YUPAY


def _aritmetico(operador, izquierdo, derecho):
    if izquierdo in NUMERICOS and derecho in NUMERICOS:
        return tipo_numerico(izquierdo, derecho)
    if operador == "+" and izquierdo == derecho == QAYTU:
        return QAYTU                    # concatenación de textos
    return None


def _de_orden(izquierdo, derecho):
    numericos = izquierdo in NUMERICOS and derecho in NUMERICOS
    caracteres = izquierdo == derecho == SANANPA
    return BOOL if numericos or caracteres else None


def _de_igualdad(izquierdo, derecho):
    numericos = izquierdo in NUMERICOS and derecho in NUMERICOS
    return BOOL if numericos or izquierdo == derecho else None


def _logico(izquierdo, derecho):
    return BOOL if izquierdo == derecho == BOOL else None


_REGLAS_BINARIAS = [
    (ARITMETICOS, _aritmetico),
    (DE_ORDEN, lambda _, izq, der: _de_orden(izq, der)),
    (DE_IGUALDAD, lambda _, izq, der: _de_igualdad(izq, der)),
    (LOGICOS, lambda _, izq, der: _logico(izq, der)),
]


def tipo_binario(operador, izquierdo, derecho):
    """Tipo de `izquierdo operador derecho`, o None si no es válido."""
    if ERROR in (izquierdo, derecho):
        return ERROR
    for operadores, regla in _REGLAS_BINARIAS:
        if operador in operadores:
            return regla(operador, izquierdo, derecho)
    raise ValueError(f"Operador desconocido: {operador}")


def tipo_unario(operador, tipo):
    """Tipo de `operador tipo` (solo existe el '-' unario)."""
    if tipo == ERROR:
        return ERROR
    if operador == "-" and tipo in NUMERICOS:
        return tipo
    return None


def es_asignable(destino, origen):
    """¿Se puede guardar un valor de tipo `origen` en una variable de tipo
    `destino`? Un entero se puede guardar en un decimal, pero no al revés
    (se perderían los decimales)."""
    if ERROR in (destino, origen):
        return True
    return destino == origen or (destino == CHUNKAYUQ and origen == YUPAY)
