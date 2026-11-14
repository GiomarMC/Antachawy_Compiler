"""Reglas del sistema de tipos (antachawi/tipos.py)."""
import pytest

from antachawi.tipos import (
    BOOL,
    CHUNKAYUQ,
    ERROR,
    QAYTU,
    SANANPA,
    YUPAY,
    es_asignable,
    tipo_binario,
    tipo_unario,
)


@pytest.mark.parametrize("operador, izquierdo, derecho, esperado", [
    # Aritméticos: conversión implícita de entero a decimal
    ("+", YUPAY, YUPAY, YUPAY),
    ("-", YUPAY, CHUNKAYUQ, CHUNKAYUQ),
    ("*", CHUNKAYUQ, YUPAY, CHUNKAYUQ),
    ("/", CHUNKAYUQ, CHUNKAYUQ, CHUNKAYUQ),
    ("/", YUPAY, YUPAY, YUPAY),
    # Concatenación solo con '+' entre textos
    ("+", QAYTU, QAYTU, QAYTU),
    ("*", QAYTU, QAYTU, None),
    ("+", QAYTU, YUPAY, None),
    ("+", BOOL, BOOL, None),
    ("+", SANANPA, SANANPA, None),
    # De orden: números o caracteres
    ("<", YUPAY, CHUNKAYUQ, BOOL),
    (">=", SANANPA, SANANPA, BOOL),
    ("<", QAYTU, QAYTU, None),
    (">", BOOL, BOOL, None),
    ("<", YUPAY, QAYTU, None),
    # De igualdad: mismo tipo o ambos numéricos
    ("==", YUPAY, CHUNKAYUQ, BOOL),
    ("!=", QAYTU, QAYTU, BOOL),
    ("==", BOOL, BOOL, BOOL),
    ("==", YUPAY, QAYTU, None),
    ("!=", SANANPA, QAYTU, None),
    # Lógicos: solo bool
    ("&&", BOOL, BOOL, BOOL),
    ("||", BOOL, YUPAY, None),
    ("&&", YUPAY, YUPAY, None),
])
def test_tipo_binario(operador, izquierdo, derecho, esperado):
    assert tipo_binario(operador, izquierdo, derecho) == esperado


@pytest.mark.parametrize("operador", ["+", "<", "==", "&&"])
def test_el_tipo_error_se_propaga_sin_nuevos_errores(operador):
    assert tipo_binario(operador, ERROR, YUPAY) == ERROR
    assert tipo_binario(operador, QAYTU, ERROR) == ERROR


@pytest.mark.parametrize("tipo, esperado", [
    (YUPAY, YUPAY), (CHUNKAYUQ, CHUNKAYUQ), (QAYTU, None), (BOOL, None),
    (SANANPA, None), (ERROR, ERROR),
])
def test_menos_unario(tipo, esperado):
    assert tipo_unario("-", tipo) == esperado


@pytest.mark.parametrize("destino, origen, esperado", [
    (YUPAY, YUPAY, True),
    (CHUNKAYUQ, YUPAY, True),       # se convierte a decimal
    (YUPAY, CHUNKAYUQ, False),      # se perderían los decimales
    (QAYTU, SANANPA, False),
    (BOOL, YUPAY, False),
    (YUPAY, ERROR, True),           # ya se reportó el error
])
def test_es_asignable(destino, origen, esperado):
    assert es_asignable(destino, origen) is esperado
