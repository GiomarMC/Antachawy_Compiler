import pytest

from antachawi.definitions import EtiquetasAntachawy as E
from conftest import INPUTS

NL = E.SALTO_LINEA


def test_booleanos_quechua(analizar):
    r = analizar("chiqaq yanqa")
    assert r.etiquetas == [E.TRUE, E.FALSE]


def test_operadores_y_simbolos_compuestos(analizar):
    r = analizar("+ - * / = == != < <= > >= && ||")
    assert r.etiquetas == [
        E.MAS, E.MENOS, E.MULTIPLICA, E.DIVIDE, E.ASIGNACION, E.IGUAL,
        E.DIFERENTE, E.MENOR, E.MENOR_IGUAL, E.MAYOR, E.MAYOR_IGUAL,
        E.Y_LOGICO, E.O_LOGICO,
    ]


def test_literales(analizar):
    r = analizar("12 3.5 'a' \"hola mundo\" nombre_1")
    assert r.etiquetas == [E.NUMEROENTERO, E.NUMEROFLOTANTE, E.CARACTER,
                           E.CADENA, E.ID]
    assert r.errores_lexicos == []


def test_comentarios(analizar):
    r = analizar("a :: comentario\n:* bloque\nde varias líneas *:\nb")
    assert [t.lexema for t in r.tokens] == ["a", "\n", "b"]
    assert r.tokens[-1].linea == 4


class TestNormalizacionSaltosDeLinea:
    def test_lineas_en_blanco_cuentan_como_un_salto(self, analizar):
        r = analizar("a\n\n\n\nb")
        assert r.etiquetas == [E.ID, NL, E.ID]

    def test_sin_saltos_al_inicio_ni_al_final(self, analizar):
        r = analizar("\n\n:: comentario\na\n\n\n")
        assert r.etiquetas == [E.ID]

    def test_salto_antes_de_llave_se_ignora(self, analizar):
        r = analizar("ari (a)\n\n{")
        assert NL not in r.etiquetas

    def test_salto_antes_de_mana_chayqa_se_ignora(self, analizar):
        r = analizar("}\nmana_chayqa_ari\n}\n\nmana_chayqa")
        assert r.etiquetas == [E.LLAVE_DER, E.CONDICION_MANA_CHAYQA_ARI, NL,
                               E.LLAVE_DER, E.CONDICION_MANA_CHAYQA]

    def test_salto_antes_de_llave_derecha_se_mantiene(self, analizar):
        # Es el fin de la última sentencia del bloque.
        r = analizar("a\n}")
        assert r.etiquetas == [E.ID, NL, E.LLAVE_DER]


def test_numero_al_final_del_archivo_no_rompe(analizar):
    r = analizar("a = 5")
    assert r.errores_lexicos == []
    assert r.tokens[-1].lexema == "5"


@pytest.mark.parametrize("codigo", [
    "5a",          # número seguido de letras
    "1.2.3",       # más de un punto decimal
    "'ab'",        # carácter con más de un símbolo
    "'a",          # carácter sin cerrar
    "\"hola",      # cadena sin cerrar
    "@",           # símbolo desconocido
])
def test_errores_lexicos(analizar, codigo):
    assert analizar(codigo).errores_lexicos


def test_lineas_correctas_despues_de_literales_sin_cerrar(analizar):
    # Antes, una cadena o un número inválido "se comían" el salto de línea
    # y todos los errores siguientes se reportaban en la línea equivocada.
    r = analizar("x = \"hola\ny = 5a\nz = 'b\nw = @")
    assert [e["linea"] for e in r.errores_lexicos] == [1, 2, 3, 4]


@pytest.mark.parametrize(
    "archivo", sorted((INPUTS / "inputs_errors_lexicos").glob("*.awi")),
    ids=lambda p: p.name)
def test_archivos_con_errores_lexicos(analizar_archivo, archivo):
    assert analizar_archivo(archivo).errores_lexicos


# ----------------------------------------------------------------------
# Secuencias de escape, carácter vacío y números que empiezan con '.'
# ----------------------------------------------------------------------
@pytest.mark.parametrize("codigo, etiqueta", [
    (r'"dijo \"hola\""', E.CADENA),
    (r'"linea\nnueva\ttab \\ fin"', E.CADENA),
    (r"'\n'", E.CARACTER),
    (r"'\''", E.CARACTER),
    (r"'\\'", E.CARACTER),
    (r"'\0'", E.CARACTER),
])
def test_secuencias_de_escape_validas(analizar, codigo, etiqueta):
    r = analizar(codigo)
    assert r.errores_lexicos == []
    assert [(t.lexema, t.etiqueta) for t in r.tokens] == [(codigo, etiqueta)]


@pytest.mark.parametrize("codigo, columna", [
    (r'x = "hola\q"', 10),
    (r"x = '\z'", 6),
])
def test_secuencia_de_escape_invalida(analizar, codigo, columna):
    r = analizar(codigo)
    assert len(r.errores_lexicos) == 1
    error = r.errores_lexicos[0]
    assert (error["columna"], error["longitud"]) == (columna, 2)


def test_barra_al_final_deja_el_texto_sin_cerrar(analizar):
    # \" es una comilla escapada, así que el texto nunca se cierra
    r = analizar(r'"hola\"')
    assert len(r.errores_lexicos) == 1


def test_caracter_vacio(analizar):
    r = analizar("x = ''")
    assert len(r.errores_lexicos) == 1
    assert (r.errores_lexicos[0]["columna"],
            r.errores_lexicos[0]["longitud"]) == (5, 2)


@pytest.mark.parametrize("codigo, lexema", [
    (".5", ".5"), ("0.25", "0.25"), ("x = .75 * 2", ".75"),
])
def test_decimal_que_empieza_con_punto(analizar, codigo, lexema):
    r = analizar(codigo)
    assert r.errores_lexicos == []
    flotantes = [t.lexema for t in r.tokens
                 if t.etiqueta == E.NUMEROFLOTANTE]
    assert flotantes == [lexema]


def test_punto_solo_sigue_siendo_error(analizar):
    assert analizar("x = . 5").errores_lexicos
