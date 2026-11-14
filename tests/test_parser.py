import pytest
from anytree import PreOrderIter

from conftest import INPUTS, RAIZ


def programa(*lineas):
    """Envuelve sentencias dentro de qhapaq () { ... }."""
    cuerpo = "\n".join(f"    {linea}" for linea in lineas)
    return f"qhapaq ()\n{{\n{cuerpo}\n}}\n"


def nodos(arbol, nombre):
    return [n for n in PreOrderIter(arbol) if n.name == nombre]


def hojas(nodo):
    """Lexemas de las hojas (sin los nodos de número de línea)."""
    return [n.name for n in PreOrderIter(nodo)
            if n.children and isinstance(n.children[0].name, int)]


def assert_valido(r):
    assert r.errores_lexicos == []
    assert r.errores_sintacticos == []
    assert not nodos(r.arbol, "ERROR")


# ----------------------------------------------------------------------
# Programas válidos
# ----------------------------------------------------------------------
ARCHIVOS_VALIDOS = sorted(INPUTS.glob("prueba*.awi")) + [
    RAIZ / "example.awi", INPUTS / "main.awi"]


@pytest.mark.parametrize("archivo", ARCHIVOS_VALIDOS, ids=lambda p: p.name)
def test_ejemplos_del_repositorio(analizar_archivo, archivo):
    assert_valido(analizar_archivo(archivo))


@pytest.mark.parametrize("codigo", [
    # Salto de línea al final del archivo (lo agregan casi todos los editores).
    "qhapaq ()\n{\n    yupay a = 1\n}\n",
    "qhapaq ()\n{\n    yupay a = 1\n}\n\n\n",
    # Sin salto de línea al final.
    "qhapaq ()\n{\n    yupay a = 1\n}",
    # Llave en la misma línea.
    "qhapaq () {\n    yupay a = 1\n}\n",
    # Líneas en blanco y comentarios en cualquier parte.
    ":: inicio\n\nqhapaq ()\n\n{\n\n    yupay a = 1  :: x\n\n}\n:: fin\n",
    # Bloque vacío.
    "qhapaq ()\n{\n}\n",
], ids=["salto-final", "varios-saltos-finales", "sin-salto-final",
        "llave-misma-linea", "lineas-en-blanco", "bloque-vacio"])
def test_formatos_de_programa(analizar, codigo):
    assert_valido(analizar(codigo))


def test_condicional_seguido_de_otra_sentencia(analizar):
    r = analizar(programa(
        "yupay a = 1",
        "ari (a > 0)",
        "{",
        "    rikuchiy (a)",
        "}",
        "rikuchiy (\"despues\")",
    ))
    assert_valido(r)
    assert len(nodos(r.arbol, "Sentencias")) == 4


def test_condicionales_anidadas(analizar):
    r = analizar(programa(
        "yupay a = 5",
        "ari (a > 1)",
        "{",
        "    ari (a > 3)",
        "    {",
        "        ari (a > 4)",
        "        {",
        "            rikuchiy (\"tres niveles\")",
        "        }",
        "    }",
        "    mana_chayqa",
        "    {",
        "        rikuchiy (\"no\")",
        "    }",
        "}",
    ))
    assert_valido(r)
    assert len(nodos(r.arbol, "Condicional")) == 3


def test_cadena_completa_de_mana_chayqa_ari(analizar):
    r = analizar(programa(
        "yupay a = 5",
        "ari (a > 10) {",
        "    rikuchiy (1)",
        "} mana_chayqa_ari (a > 5) {",
        "    rikuchiy (2)",
        "}",
        "mana_chayqa_ari (a > 1)",
        "{",
        "    rikuchiy (3)",
        "}",
        "",
        "mana_chayqa {",
        "    rikuchiy (4)",
        "}",
    ))
    assert_valido(r)
    primas = [n for n in nodos(r.arbol, "CondicionalPrime") if n.children]
    assert [p.children[0].name for p in primas] == [
        "mana_chayqa_ari", "mana_chayqa_ari", "mana_chayqa"]


@pytest.mark.parametrize("condicion", [
    "a > 1",
    "a + 1 > 2 * b",
    "(a + 1) * 2 >= b - 3",
    "a > 1 && b < 2",
    "a > 1 || b < 2 && a != b",
    "v",
    "chiqaq",
    "-a < 0",
])
def test_condiciones(analizar, condicion):
    r = analizar(programa(
        "yupay a = 1", "yupay b = 2", "bool v = yanqa",
        f"ari ({condicion})", "{", "    rikuchiy (a)", "}"))
    assert_valido(r)


@pytest.mark.parametrize("expresion", [
    "-3",
    "- -3",
    "-(a + 1)",
    "a * -2",
    "(a - 1) * (a + 1) / 2",
    "((((a))))",
    "a - b - 3",
])
def test_expresiones_aritmeticas(analizar, expresion):
    r = analizar(programa("yupay a = 1", "yupay b = 2",
                          f"yupay c = {expresion}"))
    assert_valido(r)


# ----------------------------------------------------------------------
# Forma del árbol: precedencia y asociatividad
# ----------------------------------------------------------------------
def test_multiplicacion_tiene_mayor_precedencia(analizar):
    r = analizar(programa("c = a + 2 * b"))
    assert_valido(r)
    expresion = nodos(r.arbol, "ExpresionAditiva")[0]
    # ExpresionAditiva -> ExpresionMultiplicativa(a)
    #                     ExpresionAditivaPrime(+ 2*b)
    izquierda, resto = expresion.children
    assert hojas(izquierda) == ["a"]
    assert resto.children[0].name == "OperadorAditivo"
    assert hojas(resto.children[1]) == ["2", "*", "b"]


def test_y_tiene_mayor_precedencia_que_o(analizar):
    r = analizar(programa(
        "ari (a > 1 && b > 2 || c > 3)", "{", "    rikuchiy (a)", "}"))
    assert_valido(r)
    condicion = nodos(r.arbol, "Expresion")[0]
    # (a > 1 && b > 2) || (c > 3)
    grupo_y, resto_o = condicion.children
    assert hojas(grupo_y) == ["a", ">", "1", "&&", "b", ">", "2"]
    assert hojas(resto_o) == ["||", "c", ">", "3"]


def test_parentesis_agrupan(analizar):
    r = analizar(programa("c = (a + 2) * b"))
    termino = nodos(r.arbol, "Termino")[0]
    assert hojas(termino) == ["(", "a", "+", "2", ")"]


# ----------------------------------------------------------------------
# Errores sintácticos
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "archivo", sorted((INPUTS / "errores_sintacticos").glob("*.awi")),
    ids=lambda p: p.name)
def test_archivos_con_errores_sintacticos(analizar_archivo, archivo):
    r = analizar_archivo(archivo)
    assert r.errores_sintacticos


@pytest.mark.parametrize("codigo, linea", [
    (programa("yupay a = 1 +"), 3),
    (programa("rikuchiy (a"), 3),
    (programa("ari (a > ) {", "}"), 3),
    (programa("yupay 43 = 32"), 3),
    (programa("yupay x = 5 yupay y = 10"), 3),
    (programa("chiqaq"), 3),
    (programa("ari (a > 1) { rikuchiy (a) }"), 3),
    ("qhapaq ()\n{\n    yupay a = 1\n", 3),        # falta '}'
    ("qhapaq ()\n{\n}\nyupay a = 1\n", 4),       # código después de '}'
], ids=["operador-sin-operando", "falta-parentesis", "condicion-incompleta",
        "id-invalido", "dos-sentencias-misma-linea", "valor-suelto",
        "bloque-en-una-linea", "falta-llave", "codigo-fuera-de-qhapaq"])
def test_error_sintactico_en_la_linea_correcta(analizar, codigo, linea):
    r = analizar(codigo)
    assert r.errores_sintacticos
    assert r.errores_sintacticos[0]["linea"] == linea


def test_un_error_por_linea_sin_cascada(analizar):
    r = analizar(programa(
        "yupay a = 1 +",
        "rikuchiy (a",
        "ari (a > ) {",
        "    a = 2",
        "}",
        "+ 3",
        "rikuchiy (\"esta linea esta bien\")",
    ))
    assert [e["linea"] for e in r.errores_sintacticos] == [3, 4, 5, 8]


def test_el_parser_nunca_se_cae(analizar):
    """Ningún prefijo de un programa válido debe provocar una excepción."""
    codigo = programa(
        "yupay a = (1 + 2) * -3",
        "ari (a > 1 && a < 10)",
        "{",
        "    rikuchiy (\"a\", a)",
        "}",
        "mana_chayqa_ari (a == 0) {",
        "    a = a / 2",
        "} mana_chayqa {",
        "    rikuchiy (a)",
        "}",
    )
    for fin in range(len(codigo)):
        r = analizar(codigo[:fin])
        if fin < len(codigo) - 2:
            assert r.errores_lexicos or r.errores_sintacticos, codigo[:fin]


def test_el_parser_nunca_se_cae_quitando_un_token(analizar):
    lineas = ["yupay a = 1", "ari (a > 1) {", "    rikuchiy (a, 2)",
              "} mana_chayqa {", "    a = -a", "}"]
    palabras = programa(*lineas).split(" ")
    for i in range(len(palabras)):
        analizar(" ".join(palabras[:i] + palabras[i + 1:]))


# ----------------------------------------------------------------------
# Expresiones lógicas y relacionales en cualquier lugar
# ----------------------------------------------------------------------
@pytest.mark.parametrize("lineas", [
    ("bool b = a > 1",),
    ("bool b = a > 1 && a < 10 || chiqaq",),
    ("rikuchiy (a > 1, \" \", a == 2 && b)",),
    ("b = (a + 1) * 2 >= 3",),
    ("ari ((a > 1))", "{", "    rikuchiy (a)", "}"),
    ("ari ((a > 1 || b) && a != 2)", "{", "    rikuchiy (a)", "}"),
    ("b = (a > 1) == b",),
], ids=["declaracion", "logica-en-declaracion", "en-rikuchiy",
        "aritmetica-y-comparacion", "condicion-entre-parentesis",
        "agrupar-logicos", "comparar-resultados"])
def test_expresiones_booleanas(analizar, lineas):
    assert_valido(analizar(programa(*lineas)))


def test_comparaciones_no_se_encadenan(analizar):
    # "a < b < c" no tiene sentido entre tipos: se debe escribir
    # "a < b && b < c"
    r = analizar(programa("bool x = a < b < c"))
    assert len(r.errores_sintacticos) == 1
    assert r.errores_sintacticos[0]["columna"] == 20
