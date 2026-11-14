"""Análisis semántico: ámbitos, tipos y advertencias."""
import pytest

from antachawi import mensajes
from antachawi.ast_nodos import formatear
from conftest import INPUTS, RAIZ
from test_parser import programa


@pytest.fixture
def semantico(analizar):
    def _semantico(*lineas):
        r = analizar(programa(*lineas), semantico=True)
        assert r.errores_sintacticos == []
        return r
    return _semantico


def mensajes_de(lista):
    return [e["mensaje"] for e in lista]


def lineas_de(lista):
    return [e["linea"] for e in lista]


def bloque(*lineas, cabecera="ari (chiqaq)"):
    """Líneas de un ari con el cuerpo indentado."""
    return [cabecera, "{", *(f"    {linea}" for linea in lineas), "}"]


# ----------------------------------------------------------------------
# Ámbitos
# ----------------------------------------------------------------------
def test_variable_de_un_bloque_no_existe_afuera(semantico):
    r = semantico(*bloque("yupay z = 1", "rikuchiy (z)"), "rikuchiy (z)")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.USAR_NO_DECLARADA.texto(nombre="z")]
    assert lineas_de(r.errores_semanticos) == [8]


def test_bloque_interno_ve_las_variables_externas(semantico):
    r = semantico("yupay a = 1",
                  *bloque(*bloque("a = a + 1", cabecera="ari (a > 0)")),
                  "rikuchiy (a)")
    assert r.errores_semanticos == []


def test_bloques_hermanos_pueden_reusar_un_nombre(semantico):
    r = semantico(
        "ari (chiqaq) {", "    yupay z = 1", "    rikuchiy (z)",
        "} mana_chayqa {", "    qaytu z = \"x\"", "    rikuchiy (z)", "}")
    assert r.errores_semanticos == []


def test_redeclaracion_en_el_mismo_bloque(semantico):
    r = semantico("yupay a = 1", "chunkayuq a = 2.0", "rikuchiy (a)")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.VARIABLE_REDECLARADA.texto(nombre="a", linea=3)]


def test_no_se_permite_ocultar_una_variable_externa(semantico):
    r = semantico("yupay a = 1", *bloque("yupay a = 2", "rikuchiy (a)"))
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.VARIABLE_OCULTA.texto(nombre="a", linea=3)]


def test_la_tabla_registra_los_ambitos(semantico):
    r = semantico("yupay a = 1", *bloque("yupay b = a", "rikuchiy (b)"),
                  "rikuchiy (a)")
    assert [(s.nombre, s.ambito, s.nivel) for s in r.tabla.historial] == [
        ("a", "qhapaq", 0), ("b", "ari (línea 4)", 1)]


# ----------------------------------------------------------------------
# Declaraciones y asignaciones
# ----------------------------------------------------------------------
@pytest.mark.parametrize("lineas", [
    ("chunkayuq c = 3",),
    ("chunkayuq c", "c = 3"),
    ("yupay a = 1", "chunkayuq c = a * 2.5"),
    ("qaytu s = \"hola \"", "qaytu t = s + \"mundo\""),
    ("sananpa l = 'x'", *bloque("rikuchiy (l)", cabecera="ari (l < 'y')")),
    ("bool b = chiqaq",
     *bloque("rikuchiy (b)", cabecera="ari (1 < 2.5 && b || yanqa)")),
], ids=["entero-en-decimal", "asignar-entero-a-decimal", "mezcla-numerica",
        "concatenar-textos", "comparar-caracteres", "logica"])
def test_programas_validos(semantico, lineas):
    r = semantico(*lineas)
    assert r.errores_semanticos == []


@pytest.mark.parametrize("lineas, tipo, tipo_expresion", [
    (("yupay x = \"hola\"",), "yupay", "qaytu"),
    (("yupay x = 2.5",), "yupay", "chunkayuq"),
    (("bool b = 1",), "bool", "yupay"),
    (("yupay x = 1", "x = x / 2.0"), "yupay", "chunkayuq"),
    (("qaytu s = 'a'",), "qaytu", "sananpa"),
])
def test_asignaciones_incompatibles(semantico, lineas, tipo, tipo_expresion):
    r = semantico(*lineas)
    assert len(r.errores_semanticos) == 1
    mensaje = r.errores_semanticos[0]["mensaje"]
    assert f"'{tipo}'" in mensaje and f"'{tipo_expresion}'" in mensaje


def test_asignar_a_variable_no_declarada(semantico):
    r = semantico("x = 1")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.ASIGNAR_NO_DECLARADA.texto(nombre="x")]


def test_variable_en_su_propia_inicializacion(semantico):
    r = semantico("yupay a = a + 1")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.USAR_NO_DECLARADA.texto(nombre="a")]


# ----------------------------------------------------------------------
# Expresiones y condiciones
# ----------------------------------------------------------------------
@pytest.mark.parametrize("prefijo, expresion, operador", [
    ("rikuchiy (", "\"a\" * \"b\"", "*"),
    ("rikuchiy (", "chiqaq + yanqa", "+"),
    ("rikuchiy (", "1 + \"x\"", "+"),
    ("ari (", "1 < \"x\"", "<"),
    ("ari (", "chiqaq > yanqa", ">"),
    ("ari (", "1 == \"1\"", "=="),
])
def test_operaciones_invalidas(semantico, prefijo, expresion, operador):
    lineas = bloque("rikuchiy (1)", cabecera=f"{prefijo}{expresion})") \
        if prefijo == "ari (" else [f"{prefijo}{expresion})"]
    r = semantico(*lineas)
    assert len(r.errores_semanticos) == 1
    # Se señala el operador (las sentencias están indentadas 4 espacios)
    columna = 5 + len(prefijo) + expresion.index(operador)
    assert r.errores_semanticos[0]["columna"] == columna


def test_menos_unario_a_texto(semantico):
    r = semantico("qaytu s = -\"hola\"", "rikuchiy (s)")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.OPERADOR_UNARIO_INVALIDO.texto(operador="-", tipo="qaytu")]


@pytest.mark.parametrize("condicion, tipo", [
    ("a", "yupay"), ("a + 1", "yupay"), ("\"si\"", "qaytu"),
])
def test_la_condicion_debe_ser_bool(semantico, condicion, tipo):
    r = semantico("yupay a = 1",
                  *bloque("rikuchiy (a)", cabecera=f"ari ({condicion})"))
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.CONDICION_NO_BOOL.texto(tipo=tipo)]
    # Se subraya toda la condición
    assert r.errores_semanticos[0]["columna"] == 10
    assert r.errores_semanticos[0]["longitud"] == len(condicion)


def test_condicion_en_mana_chayqa_ari(semantico):
    r = semantico("yupay a = 1",
                  "ari (a > 1) {", "    rikuchiy (a)",
                  "} mana_chayqa_ari (a) {", "    rikuchiy (a)", "}")
    assert lineas_de(r.errores_semanticos) == [6]


def test_operador_logico_con_enteros(semantico):
    r = semantico("yupay a = 1",
                  *bloque("rikuchiy (a)", cabecera="ari (a > 0 && a)"))
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.OPERADOR_LOGICO_NO_BOOL.texto(
            operador="&&", izquierdo="bool", derecho="yupay")]


def test_un_solo_error_por_variable_no_declarada(semantico):
    # x no existe: no se reporta además la suma, el producto ni la
    # asignación. La 'a' del final tampoco existe todavía.
    r = semantico("yupay a = (x + 1) * 2 - a", "rikuchiy (a)")
    assert [e["mensaje"] for e in r.errores_semanticos] == [
        mensajes.USAR_NO_DECLARADA.texto(nombre="x"),
        mensajes.USAR_NO_DECLARADA.texto(nombre="a"),
    ]


def test_el_ast_queda_con_tipos(semantico):
    r = semantico("yupay a = 1", "chunkayuq r = a + 2.5 * a",
                  *bloque("rikuchiy (r)", cabecera="ari (r > 1)"))
    assert formatear(r.ast) == (
        "Programa\n"
        "└── Bloque\n"
        "    ├── Declaracion yupay a\n"
        "    │   └── Literal 1 : yupay\n"
        "    ├── Declaracion chunkayuq r\n"
        "    │   └── Binaria + : chunkayuq\n"
        "    │       ├── Variable a : yupay\n"
        "    │       └── Binaria * : chunkayuq\n"
        "    │           ├── Literal 2.5 : chunkayuq\n"
        "    │           └── Variable a : yupay\n"
        "    └── Si\n"
        "        ├── Binaria > : bool\n"
        "        │   ├── Variable r : chunkayuq\n"
        "        │   └── Literal 1 : yupay\n"
        "        └── Bloque\n"
        "            └── Imprimir\n"
        "                └── Variable r : chunkayuq")


# ----------------------------------------------------------------------
# Advertencias
# ----------------------------------------------------------------------
def test_variable_no_usada(semantico):
    r = semantico("yupay a = 1", "yupay b = 2", "b = 3", "rikuchiy (a)")
    assert r.errores_semanticos == []
    # b solo se asigna, nunca se lee
    assert mensajes_de(r.advertencias) == [
        mensajes.VARIABLE_NO_USADA.texto(nombre="b")]
    assert lineas_de(r.advertencias) == [4]


def test_variable_usada_sin_valor(semantico):
    r = semantico("yupay a", "rikuchiy (a)", "rikuchiy (a)")
    # Una sola advertencia aunque se use dos veces
    assert mensajes_de(r.advertencias) == [
        mensajes.VARIABLE_SIN_VALOR.texto(nombre="a")]


@pytest.mark.parametrize("lineas, advierte", [
    # Asignada en todas las ramas: tiene valor seguro.
    (["ari (chiqaq) {", "    a = 1", "} mana_chayqa {", "    a = 2", "}"],
     False),
    (["ari (chiqaq) {", "    a = 1",
      "} mana_chayqa_ari (yanqa) {", "    a = 2",
      "} mana_chayqa {", "    a = 3", "}"], False),
    # Asignada antes del ari.
    (["a = 1", "ari (chiqaq) {", "    rikuchiy (1)", "}"], False),
    # Asignada solo en una rama, o sin mana_chayqa.
    (["ari (chiqaq) {", "    a = 1", "} mana_chayqa {",
      "    rikuchiy (1)", "}"], True),
    (["ari (chiqaq) {", "    a = 1", "}"], True),
    (["ari (chiqaq) {", "    a = 1",
      "} mana_chayqa_ari (yanqa) {", "    a = 2", "}"], True),
], ids=["si-y-sino", "cadena-completa", "antes-del-ari", "una-rama",
        "sin-sino", "cadena-sin-sino"])
def test_valor_seguro_despues_de_un_ari(semantico, lineas, advierte):
    r = semantico("yupay a", *lineas, "rikuchiy (a)")
    assert r.errores_semanticos == []
    esperado = [mensajes.VARIABLE_SIN_VALOR.texto(nombre="a")]
    assert mensajes_de(r.advertencias) == (esperado if advierte else [])


def test_division_entre_cero(semantico):
    r = semantico("yupay a = 10 / 0", "chunkayuq b = a / 0.0",
                  "rikuchiy (a, b)")
    assert r.errores_semanticos == []
    assert mensajes_de(r.advertencias) == [
        mensajes.DIVISION_ENTRE_CERO.texto()] * 2


# ----------------------------------------------------------------------
# Archivos del repositorio
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "archivo", sorted((INPUTS / "errores_semanticos").glob("*.awi")),
    ids=lambda p: p.name)
def test_archivos_con_errores_semanticos(analizar_archivo, archivo):
    r = analizar_archivo(archivo, semantico=True)
    assert r.errores_sintacticos == []
    assert r.errores_semanticos


@pytest.mark.parametrize(
    "archivo", sorted(INPUTS.glob("prueba*.awi")) + [RAIZ / "example.awi"],
    ids=lambda p: p.name)
def test_ejemplos_validos_sin_errores_semanticos(analizar_archivo, archivo):
    r = analizar_archivo(archivo, semantico=True)
    assert r.errores_semanticos == []


# ----------------------------------------------------------------------
# Expresiones booleanas fuera de un ari
# ----------------------------------------------------------------------
def test_guardar_una_comparacion_en_un_bool(semantico):
    r = semantico("yupay a = 5", "bool mayor = a > 3 && a != 4",
                  "rikuchiy (mayor, a <= 2)")
    assert r.errores_semanticos == []


def test_una_comparacion_no_es_un_entero(semantico):
    r = semantico("yupay a = 5", "yupay x = a > 3", "rikuchiy (x)")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.ASIGNACION_INCOMPATIBLE.texto(
            nombre="x", tipo="yupay", tipo_expresion="bool")]


def test_comparar_resultados_de_comparaciones(semantico):
    r = semantico("yupay a = 5", "bool b = (a > 1) == (a < 9)",
                  "bool c = (a > 1) < chiqaq", "rikuchiy (b, c)")
    # '==' entre bool es válido; '<' entre bool no
    assert lineas_de(r.errores_semanticos) == [5]


# ----------------------------------------------------------------------
# Bucles
# ----------------------------------------------------------------------
def test_la_variable_de_imapaq_solo_existe_en_el_bucle(semantico):
    r = semantico("imapaq (yupay i = 0; i < 3; i = i + 1) {",
                  "    rikuchiy (i)",
                  "}",
                  "rikuchiy (i)")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.USAR_NO_DECLARADA.texto(nombre="i")]


def test_imapaq_puede_usar_una_variable_existente(semantico):
    r = semantico("yupay i",
                  "imapaq (i = 0; i < 3; i = i + 1) {",
                  "    rikuchiy (i)",
                  "}")
    assert r.errores_semanticos == []


@pytest.mark.parametrize("cabecera", [
    "chaykama (5)",
    "imapaq (yupay i = 0; i + 1; i = i + 1)",
])
def test_la_condicion_de_un_bucle_debe_ser_bool(semantico, cabecera):
    r = semantico(cabecera + " {", "    rikuchiy (1)", "}")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.CONDICION_NO_BOOL.texto(tipo="yupay")]


def test_lo_asignado_en_un_bucle_no_es_un_valor_seguro(semantico):
    # El cuerpo puede no ejecutarse nunca
    r = semantico("yupay a",
                  "chaykama (yanqa) {",
                  "    a = 1",
                  "}",
                  "rikuchiy (a)")
    assert mensajes_de(r.advertencias) == [
        mensajes.VARIABLE_SIN_VALOR.texto(nombre="a")]


def test_el_paso_de_imapaq_se_verifica(semantico):
    r = semantico("imapaq (yupay i = 0; i < 3; i = \"x\") {",
                  "    rikuchiy (i)",
                  "}")
    assert mensajes_de(r.errores_semanticos) == [
        mensajes.ASIGNACION_INCOMPATIBLE.texto(
            nombre="i", tipo="yupay", tipo_expresion="qaytu")]
