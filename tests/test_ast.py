"""Construcción del AST a partir del árbol de derivación."""
import pytest

from antachawi.ast_nodos import Bloque, Posicion, Si, formatear
from antachawi.constructor_ast import construir_ast
from test_parser import programa


@pytest.fixture
def ast_de(analizar):
    def _ast_de(*lineas):
        r = analizar(programa(*lineas))
        assert not r.errores_lexicos and not r.errores_sintacticos
        return construir_ast(r.arbol)
    return _ast_de


def expresion(ast_de, texto):
    """AST (como texto) de la expresión en 'c = <texto>'."""
    asignacion = ast_de(f"c = {texto}").cuerpo.sentencias[0]
    return formatear(asignacion.valor)


def test_resta_asocia_por_la_izquierda(ast_de):
    # (a - b) - c
    assert expresion(ast_de, "a - b - c") == (
        "Binaria -\n"
        "├── Binaria -\n"
        "│   ├── Variable a\n"
        "│   └── Variable b\n"
        "└── Variable c")


def test_division_asocia_por_la_izquierda(ast_de):
    # (a / b) * c
    assert expresion(ast_de, "a / b * c") == (
        "Binaria *\n"
        "├── Binaria /\n"
        "│   ├── Variable a\n"
        "│   └── Variable b\n"
        "└── Variable c")


def test_precedencia_y_parentesis(ast_de):
    assert expresion(ast_de, "a + b * c") == (
        "Binaria +\n"
        "├── Variable a\n"
        "└── Binaria *\n"
        "    ├── Variable b\n"
        "    └── Variable c")
    assert expresion(ast_de, "(a + b) * c") == (
        "Binaria *\n"
        "├── Binaria +\n"
        "│   ├── Variable a\n"
        "│   └── Variable b\n"
        "└── Variable c")


def test_menos_unario(ast_de):
    assert expresion(ast_de, "-a * 2") == (
        "Binaria *\n"
        "├── Unaria -\n"
        "│   └── Variable a\n"
        "└── Literal 2")


def test_y_tiene_mayor_precedencia_que_o(ast_de):
    # (a > 1 && b) || c
    assert expresion(ast_de, "a > 1 && b || c") == (
        "Binaria ||\n"
        "├── Binaria &&\n"
        "│   ├── Binaria >\n"
        "│   │   ├── Variable a\n"
        "│   │   └── Literal 1\n"
        "│   └── Variable b\n"
        "└── Variable c")


def test_literales_conservan_su_lexema(ast_de):
    assert expresion(ast_de, "\"hola\"") == "Literal \"hola\""
    assert expresion(ast_de, "'x'") == "Literal 'x'"
    assert expresion(ast_de, "chiqaq") == "Literal chiqaq"


def test_sentencias(ast_de):
    ast = ast_de("yupay a", "chunkayuq b = 1.5", "a = 2",
                 "rikuchiy (a, \" \", b)")
    assert formatear(ast) == (
        "Programa\n"
        "└── Bloque\n"
        "    ├── Declaracion yupay a\n"
        "    ├── Declaracion chunkayuq b\n"
        "    │   └── Literal 1.5\n"
        "    ├── Asignacion a\n"
        "    │   └── Literal 2\n"
        "    └── Imprimir\n"
        "        ├── Variable a\n"
        "        ├── Literal \" \"\n"
        "        └── Variable b")


def test_cadena_de_mana_chayqa_ari(ast_de):
    ast = ast_de(
        "ari (a) {", "    rikuchiy (1)",
        "} mana_chayqa_ari (b) {", "    rikuchiy (2)",
        "} mana_chayqa {", "    rikuchiy (3)", "}")
    si = ast.cuerpo.sentencias[0]
    assert isinstance(si, Si)
    assert isinstance(si.si_no, Si)              # mana_chayqa_ari
    assert isinstance(si.si_no.si_no, Bloque)    # mana_chayqa


def test_ari_sin_mana_chayqa(ast_de):
    si = ast_de("ari (a)", "{", "    rikuchiy (1)", "}").cuerpo.sentencias[0]
    assert si.si_no is None
    assert len(si.entonces.sentencias) == 1


def test_posiciones(ast_de):
    # Línea 3: "    c = (a + 10) * b"
    asignacion = ast_de("c = (a + 10) * b").cuerpo.sentencias[0]
    producto = asignacion.valor
    assert asignacion.pos == Posicion(3, 5, 1)
    assert producto.pos == Posicion(3, 9, 12)            # (a + 10) * b
    assert producto.pos_operador == Posicion(3, 18, 1)
    assert producto.izquierda.pos == Posicion(3, 9, 8)   # (a + 10)
    assert producto.izquierda.pos_operador == Posicion(3, 12, 1)
    assert producto.izquierda.derecha.pos == Posicion(3, 14, 2)


def test_posicion_de_menos_unario(ast_de):
    unaria = ast_de("c = -a").cuerpo.sentencias[0].valor
    assert unaria.pos == Posicion(3, 9, 2)
    assert unaria.pos_operador == Posicion(3, 9, 1)


def test_parentesis_agrupan_logicos(ast_de):
    # (a || b) && c
    assert expresion(ast_de, "(a || b) && c") == (
        "Binaria &&\n"
        "├── Binaria ||\n"
        "│   ├── Variable a\n"
        "│   └── Variable b\n"
        "└── Variable c")


def test_aritmetica_antes_que_comparacion(ast_de):
    # (a + 1) > (b * 2)
    assert expresion(ast_de, "a + 1 > b * 2") == (
        "Binaria >\n"
        "├── Binaria +\n"
        "│   ├── Variable a\n"
        "│   └── Literal 1\n"
        "└── Binaria *\n"
        "    ├── Variable b\n"
        "    └── Literal 2")
