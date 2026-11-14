"""
Ubicación exacta de los errores: línea, columna y cuántos caracteres se
subrayan. Las columnas empiezan en 1.
"""
import pytest

from antachawi.consolehandler import formatear_error
from antachawi.errores import nuevo_error
from antachawi.mensajes import AMBOS, ES, QU, Mensaje
from test_parser import programa


def posicion(error):
    return error["linea"], error["columna"], error["longitud"]


# ----------------------------------------------------------------------
# Tokens
# ----------------------------------------------------------------------
def test_columnas_de_los_tokens(analizar):
    r = analizar("  yupay  x = 10\n\tari")
    assert [(t.lexema, t.linea, t.columna) for t in r.tokens] == [
        ("yupay", 1, 3), ("x", 1, 10), ("=", 1, 12), ("10", 1, 14),
        ("\n", 1, 16), ("ari", 2, 2),
    ]


def test_columnas_despues_de_un_comentario_de_bloque(analizar):
    r = analizar("a :* uno\ndos *: b\nc")
    assert [(t.lexema, t.linea, t.columna) for t in r.tokens] == [
        ("a", 1, 1), ("b", 2, 8), ("\n", 2, 9), ("c", 3, 1),
    ]


# ----------------------------------------------------------------------
# Errores léxicos
# ----------------------------------------------------------------------
@pytest.mark.parametrize("codigo, esperado", [
    ("x = \"hola", (1, 5, 5)),      # se subraya desde la comilla
    ("x = 5abc", (1, 5, 4)),        # todo el número inválido
    ("x = 1.2.3", (1, 5, 5)),
    ("x = 'ab'", (1, 5, 4)),
    ("x = 'b", (1, 5, 2)),
    ("x = 2 @ 1", (1, 7, 1)),
    ("\tx = @", (1, 6, 1)),         # el tab cuenta como una columna
    ("a\n  :* sin cerrar\nb", (2, 3, 2)),  # donde empieza el comentario
])
def test_posicion_de_errores_lexicos(analizar, codigo, esperado):
    r = analizar(codigo)
    assert posicion(r.errores_lexicos[0]) == esperado


def test_errores_lexicos_en_lineas_seguidas(analizar):
    r = analizar("x = \"hola\ny = 5a\nz = 'b\nw = @")
    assert [posicion(e) for e in r.errores_lexicos] == [
        (1, 5, 5), (2, 5, 2), (3, 5, 2), (4, 5, 1)]


# ----------------------------------------------------------------------
# Errores sintácticos
# ----------------------------------------------------------------------
@pytest.mark.parametrize("codigo, esperado", [
    # Falta algo al final de la línea: se señala después del último token.
    (programa("yupay a = 1 +"), (3, 18, 1)),
    (programa("rikuchiy (a"), (3, 16, 1)),
    ("qhapaq ()\n{\n    yupay a = 1\n", (3, 16, 1)),
    # Aunque la llave esté en la línea siguiente, falta el ')' del ari.
    (programa("ari (a > 1", "{", "}"), (3, 15, 1)),
    # Token inesperado: se subraya completo.
    (programa("a = 2 )"), (3, 11, 1)),
    (programa("yupay 43 = 32"), (3, 11, 2)),
    (programa("yupay a = 1 \"texto\""), (3, 17, 7)),
    (programa("+ 3"), (3, 5, 1)),
    (programa("ari (a > 1) { rikuchiy (a) }"), (3, 19, 8)),
    ("qhapaq ()\n{\n}\nyupay a = 1\n", (4, 1, 5)),
], ids=["operador-al-final", "falta-parentesis", "falta-llave",
        "falta-parentesis-llave-abajo", "parentesis-de-mas", "id-invalido",
        "cadena-inesperada", "sentencia-invalida", "bloque-en-una-linea",
        "codigo-fuera-de-qhapaq"])
def test_posicion_de_errores_sintacticos(analizar, codigo, esperado):
    r = analizar(codigo)
    assert posicion(r.errores_sintacticos[0]) == esperado


def test_contenido_conserva_la_indentacion(analizar):
    r = analizar(programa("rikuchiy (a"))
    assert r.errores_sintacticos[0]["contenido"] == "    rikuchiy (a"


# ----------------------------------------------------------------------
# Errores semánticos
# ----------------------------------------------------------------------
@pytest.mark.parametrize("lineas, esperado", [
    (("yupay a = b",), (3, 15, 1)),
    (("yupay a = 1", "yupay a = 2"), (4, 11, 1)),
    (("yupay a = 1", "a = a + \"x\""), (4, 11, 1)),
    (("noexiste = 1",), (3, 5, 8)),
])
def test_posicion_de_errores_semanticos(analizar, lineas, esperado):
    r = analizar(programa(*lineas), semantico=True)
    assert posicion(r.errores_semanticos[0]) == esperado


# ----------------------------------------------------------------------
# Formato en consola
# ----------------------------------------------------------------------
MENSAJE = Mensaje("SEM999", "mensaje", "willay")
SIN_TRADUCIR = Mensaje("SEM998", "solo en español")


def texto(error, idioma=AMBOS):
    return "\n".join(parte.plain for parte in formatear_error(
        error, idioma=idioma))


def test_formato_con_subrayado_en_ambos_idiomas():
    error = nuevo_error(MENSAJE, 12, "    ari (a > 1", 15, 1)
    assert texto(error) == (
        "Error SEM999 en 12:15: mensaje\n"
        "    qu: willay\n"
        "   12 |     ari (a > 1\n"
        "      |               ^"
    )


def test_formato_en_quechua():
    error = nuevo_error(MENSAJE, 12, "    ari (a > 1", 15, 1)
    assert texto(error, QU).splitlines()[0] == (
        "Pantachay SEM999 12:15 siq'isqapi: willay")


def test_formato_en_espanol():
    error = nuevo_error(MENSAJE, 12, "    ari (a > 1", 15, 1)
    assert texto(error, ES).splitlines()[:2] == [
        "Error SEM999 en 12:15: mensaje", "   12 |     ari (a > 1"]


def test_sin_traduccion_se_muestra_en_espanol():
    error = nuevo_error(SIN_TRADUCIR, 3, "yupay a")
    assert texto(error, QU).splitlines()[0].endswith("solo en español")
    assert "qu:" not in texto(error)


def test_formato_subraya_varios_caracteres_y_respeta_tabs():
    error = nuevo_error(MENSAJE, 3, "\tyupay 43 = 1", 8, 2)
    assert texto(error).splitlines()[-1] == "      | \t      ^^"


def test_formato_sin_columna():
    error = nuevo_error(MENSAJE, 3, "yupay a")
    assert texto(error, ES) == (
        "Error SEM999 en 3: mensaje\n    3 | yupay a")
