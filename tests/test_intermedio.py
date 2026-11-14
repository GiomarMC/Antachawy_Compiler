"""Código de tres direcciones generado a partir del AST."""
from antachawi.intermedio import (
    Constante,
    decodificar_escapes,
    formatear_codigo,
    generar_codigo_intermedio,
)
from antachawi.tipos import CHUNKAYUQ, QAYTU, SANANPA
from test_parser import programa


def tres_direcciones(analizar, *lineas):
    r = analizar(programa(*lineas), semantico=True)
    assert not r.errores_semanticos
    return formatear_codigo(generar_codigo_intermedio(r.ast)).split("\n")


def test_expresion_aritmetica_usa_temporales(analizar):
    assert tres_direcciones(analizar,
                            "yupay a = 2",
                            "yupay b = a * 3 + -a",
                            "rikuchiy (b)") == [
        "    a = 2",
        "    t1 = a * 3",
        "    t2 = minus a",
        "    t3 = t1 + t2",
        "    b = t3",
        "    param b",
        "    call rikuchiy, 1",
    ]


def test_conversion_de_entero_a_decimal(analizar):
    assert tres_direcciones(analizar,
                            "yupay a = 2",
                            "chunkayuq b = a",
                            "b = b + a",
                            "rikuchiy (b)")[1:5] == [
        "    t1 = (chunkayuq) a",
        "    b = t1",
        "    t2 = (chunkayuq) a",
        "    t3 = b + t2",
    ]


def test_declaracion_sin_valor_recibe_valor_por_defecto(analizar):
    assert tres_direcciones(analizar,
                            "qaytu s",
                            "chunkayuq d",
                            "rikuchiy (s, d)")[:2] == [
        '    s = ""',
        "    d = 0.0",
    ]


def test_si_con_mana_chayqa_ari_y_mana_chayqa(analizar):
    assert tres_direcciones(analizar,
                            "yupay a = 1",
                            "ari (a > 1) {",
                            "    rikuchiy (1)",
                            "} mana_chayqa_ari (a == 1) {",
                            "    rikuchiy (2)",
                            "} mana_chayqa {",
                            "    rikuchiy (3)",
                            "}") == [
        "    a = 1",
        "    if a <= 1 goto L2",
        "    param 1",
        "    call rikuchiy, 1",
        "    goto L1",
        "L2:",
        "    if a != 1 goto L3",
        "    param 2",
        "    call rikuchiy, 1",
        "    goto L1",
        "L3:",
        "    param 3",
        "    call rikuchiy, 1",
        "L1:",
    ]


def test_cortocircuito(analizar):
    # a > 0 || (b && a < 5)
    assert tres_direcciones(analizar,
                            "yupay a = 1",
                            "bool b = chiqaq",
                            "ari (a > 0 || b && a < 5) {",
                            "    rikuchiy (a)",
                            "}")[2:6] == [
        "    if a > 0 goto L2",
        "    ifFalse b goto L1",
        "    if a >= 5 goto L1",
        "L2:",
    ]


def test_valor_de_una_expresion_logica(analizar):
    assert tres_direcciones(analizar,
                            "yupay a = 1",
                            "bool b = a > 0 && a < 5",
                            "rikuchiy (b)")[1:9] == [
        "    if a <= 0 goto L1",
        "    if a >= 5 goto L1",
        "    t1 = chiqaq",
        "    goto L2",
        "L1:",
        "    t1 = yanqa",
        "L2:",
        "    b = t1",
    ]


def test_comparacion_de_decimales_no_se_niega(analizar):
    # Con NaN, "no (a < b)" no es lo mismo que "a >= b"
    assert tres_direcciones(analizar,
                            "chunkayuq d = 1.5",
                            "ari (d < 2.0) {",
                            "    rikuchiy (d)",
                            "}")[1:3] == [
        "    t1 = d < 2.0",
        "    ifFalse t1 goto L1",
    ]


def test_variables_hermanas_reciben_nombres_distintos(analizar):
    codigo = tres_direcciones(analizar,
                              "ari (chiqaq) {",
                              "    yupay x = 1",
                              "    rikuchiy (x)",
                              "} mana_chayqa {",
                              "    yupay x = 2",
                              "    rikuchiy (x)",
                              "}")
    assert "    x = 1" in codigo
    assert "    x.2 = 2" in codigo


def test_literales():
    assert decodificar_escapes(r"a\n\"b\"\\") == 'a\n"b"\\'
    assert str(Constante("dijo \"hola\"\n", QAYTU)) == r'"dijo \"hola\"\n"'
    assert str(Constante("'", SANANPA)) == r"'\''"
    assert Constante(0.0, CHUNKAYUQ) != Constante(-0.0, CHUNKAYUQ)


def test_chaykama(analizar):
    assert tres_direcciones(analizar,
                            "yupay n = 3",
                            "chaykama (n > 0) {",
                            "    n = n - 1",
                            "}",
                            "rikuchiy (n)")[1:7] == [
        "L1:",
        "    if n <= 0 goto L2",
        "    t1 = n - 1",
        "    n = t1",
        "    goto L1",
        "L2:",
    ]


def test_imapaq(analizar):
    assert tres_direcciones(analizar,
                            "imapaq (yupay i = 0; i < 3; i = i + 1) {",
                            "    rikuchiy (i)",
                            "}") == [
        "    i = 0",
        "L1:",
        "    if i >= 3 goto L2",
        "    param i",
        "    call rikuchiy, 1",
        "    t1 = i + 1",
        "    i = t1",
        "    goto L1",
        "L2:",
    ]
