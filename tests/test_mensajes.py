"""
Integridad del catálogo de mensajes (antachawi/mensajes.py). Estas pruebas
protegen a quien traduzca: si una traducción usa una llave que no existe
({nombr} en vez de {nombre}), la prueba lo dice antes de que falle el
compilador.
"""
import re

import pytest

from antachawi import mensajes
from antachawi.errores import nuevo_error, texto_de
from antachawi.mensajes import ES, QU, Mensaje, campos

CATALOGO = mensajes.catalogo()


def test_los_codigos_son_unicos():
    codigos = [m.codigo for m in CATALOGO]
    assert len(codigos) == len(set(codigos))


@pytest.mark.parametrize("mensaje", CATALOGO, ids=lambda m: m.codigo)
def test_formato_del_codigo(mensaje):
    prefijos = "LEX|SIN|SEM|ADV|EJE|CON|IDE"
    assert re.fullmatch(rf"({prefijos})\d{{3}}", mensaje.codigo)


@pytest.mark.parametrize("mensaje", [m for m in CATALOGO if m.traducido],
                         ids=lambda m: m.codigo)
def test_la_traduccion_solo_usa_llaves_del_espanol(mensaje):
    # Una traducción puede omitir un dato, pero no inventar uno
    assert campos(mensaje.qu) <= campos(mensaje.es)


def test_sin_traduccion_se_usa_el_espanol():
    mensaje = Mensaje("SEM999", "hola {nombre}")
    assert mensaje.texto(QU, nombre="x") == "hola x"
    assert mensaje.textos(nombre="x") == {ES: "hola x", QU: None}


def test_pendientes_de_traduccion():
    pendientes = mensajes.pendientes_de_traduccion()
    assert all(m.qu is None for m in pendientes)
    assert mensajes.TOKEN_INESPERADO not in pendientes


def test_buscar_por_codigo():
    assert mensajes.por_codigo("SEM004") is mensajes.USAR_NO_DECLARADA
    with pytest.raises(KeyError):
        mensajes.por_codigo("XXX000")


@pytest.mark.parametrize("mensaje, fase, gravedad", [
    (mensajes.SIMBOLO_DESCONOCIDO, "lexico", "error"),
    (mensajes.TOKEN_INESPERADO, "sintactico", "error"),
    (mensajes.USAR_NO_DECLARADA, "semantico", "error"),
    (mensajes.VARIABLE_NO_USADA, "semantico", "advertencia"),
    (mensajes.EJECUCION_SIN_FIN, "ejecucion", "error"),
])
def test_fase_y_gravedad(mensaje, fase, gravedad):
    assert (mensaje.fase, mensaje.gravedad) == (fase, gravedad)


def test_un_error_guarda_ambos_idiomas():
    error = nuevo_error(mensajes.USAR_NO_DECLARADA, 4, "a = b", 5,
                        parametros={"nombre": "b"})
    assert error["codigo"] == "SEM004"
    assert error["parametros"] == {"nombre": "b"}
    assert error["mensaje"] == "la variable 'b' no fue declarada."
    assert texto_de(error, QU) == "variable 'b' mana churakusqa."


def test_un_parametro_puede_llamarse_linea():
    # VARIABLE_REDECLARADA tiene {linea}, igual que el argumento linea
    error = nuevo_error(mensajes.VARIABLE_REDECLARADA, 7, "yupay a", 7,
                        parametros={"nombre": "a", "linea": 3})
    assert error["linea"] == 7
    assert "(línea 3)" in error["mensaje"]
