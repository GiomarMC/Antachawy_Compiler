"""Bloques básicos y optimización del código de tres direcciones."""
from antachawi.bloques_basicos import particionar
from antachawi.intermedio import (
    COPIA,
    PARAMETRO,
    Constante,
    Cuadrupla,
    Nombre,
    formatear_codigo,
    generar_codigo_intermedio,
)
from antachawi.optimizador import (
    optimizar,
    optimizar_bloque,
    plegar,
    saltos_innecesarios,
)
from antachawi.tipos import BOOL, CHUNKAYUQ, YUPAY
from test_parser import programa


def intermedio(analizar, *lineas):
    r = analizar(programa(*lineas), semantico=True)
    assert not r.errores_semanticos
    return generar_codigo_intermedio(r.ast)


def optimizado(analizar, *lineas):
    codigo = optimizar(intermedio(analizar, *lineas))
    return formatear_codigo(codigo).split("\n")


# ----------------------------------------------------------------------
# Bloques básicos
# ----------------------------------------------------------------------
def test_lideres_y_grafo_de_flujo(analizar):
    bloques = particionar(intermedio(analizar,
                                     "yupay a = 1",
                                     "ari (a > 1) {",
                                     "    a = 2",
                                     "} mana_chayqa {",
                                     "    a = 3",
                                     "}",
                                     "rikuchiy (a)"))
    # B1: a = 1; if   B2: a = 2; goto   B3: L2: a = 3   B4: L1: ...
    assert [len(b.instrucciones) for b in bloques] == [2, 2, 2, 3]
    sucesores = {b.nombre: [s.nombre for s in b.sucesores] for b in bloques}
    assert sucesores == {"B1": ["B3", "B2"], "B2": ["B4"], "B3": ["B4"],
                         "B4": []}


# ----------------------------------------------------------------------
# Optimización local
# ----------------------------------------------------------------------
def test_plegado_y_propagacion_de_constantes(analizar):
    assert optimizado(analizar,
                      "yupay a = 2",
                      "yupay b = a * 3 + 1",
                      "chunkayuq c = b / 2",
                      "rikuchiy (b, c)") == [
        "    param 7",
        "    param 3.0",
        "    call rikuchiy, 2",
    ]


def test_plegado_imita_al_procesador():
    def valor(op, a, b, tipo=YUPAY):
        return plegar(Cuadrupla(op, Constante(a, tipo), Constante(b, tipo),
                                Nombre("x", tipo))).valor

    assert valor("/", -7, 2) == -3                     # trunca hacia cero
    assert valor("*", 2 ** 62, 4) == 0                 # 64 bits
    assert valor("+", 2 ** 63 - 1, 1) == -2 ** 63
    assert valor("/", 1.0, 4.0, CHUNKAYUQ) == 0.25
    # La división entre cero se deja para la ejecución
    assert plegar(Cuadrupla("/", Constante(1, YUPAY), Constante(0, YUPAY),
                            Nombre("x", YUPAY))) is None


def test_subexpresion_comun_e_identidades():
    a, b = Nombre("a", YUPAY), Nombre("b", YUPAY)
    t1, t2, t3 = (Nombre(f"t{i}", YUPAY) for i in (1, 2, 3))
    bloque = [
        Cuadrupla("*", a, b, t1),
        Cuadrupla("*", b, a, t2),                 # igual a t1
        Cuadrupla("+", t2, Constante(0, YUPAY), t3),
        Cuadrupla(PARAMETRO, t3),
    ]
    assert [str(c) for c in optimizar_bloque(bloque)] == [
        "t1 = a * b",
        "t2 = t1",
        "t3 = t1",
        "param t1",
    ]


def test_subexpresion_comun_se_invalida_al_redefinir():
    a, b = Nombre("a", YUPAY), Nombre("b", YUPAY)
    t1, t2 = Nombre("t1", YUPAY), Nombre("t2", YUPAY)
    bloque = [
        Cuadrupla("*", a, b, t1),
        Cuadrupla(COPIA, t1, resultado=a),
        Cuadrupla("*", a, b, t2),
    ]
    assert str(optimizar_bloque(bloque)[-1]) == "t2 = t1 * b"


def test_condicion_constante_elimina_la_rama_que_no_se_ejecuta(analizar):
    assert optimizado(analizar,
                      "yupay a = 5",
                      "ari (a > 10) {",
                      "    rikuchiy (\"grande\")",
                      "} mana_chayqa {",
                      "    rikuchiy (\"chico\")",
                      "}") == [
        '    param "chico"',
        "    call rikuchiy, 1",
    ]


def test_si_eliminado_une_los_bloques_y_sigue_propagando(analizar):
    # Al quitar el salto, el ari y lo que sigue quedan en un solo bloque
    # y la propagación local llega hasta rikuchiy.
    assert optimizado(analizar,
                      "bool c = chiqaq",
                      "yupay b = 1",
                      "ari (c) {",
                      "    b = b + 1",
                      "}",
                      "rikuchiy (b)") == [
        "    param 2",
        "    call rikuchiy, 1",
    ]


# ----------------------------------------------------------------------
# Código muerto y mirilla
# ----------------------------------------------------------------------
def test_asignaciones_muertas_se_eliminan(analizar):
    assert optimizado(analizar,
                      "yupay a = 1",
                      "a = 2",
                      "yupay b = a",
                      "rikuchiy (\"fin\")") == [
        '    param "fin"',
        "    call rikuchiy, 1",
    ]


def test_mirilla_invierte_el_salto_sobre_un_goto():
    c = Nombre("c", BOOL)
    codigo = [
        Cuadrupla("if", c, resultado="L1"),
        Cuadrupla("goto", resultado="L2"),
        Cuadrupla("label", resultado="L1"),
        Cuadrupla(PARAMETRO, c),
        Cuadrupla("label", resultado="L2"),
    ]
    assert [str(x) for x in saltos_innecesarios(codigo)] == [
        "ifFalse c goto L2", "L1:", "param c", "L2:"]


def test_optimizar_no_cambia_un_codigo_ya_optimo():
    codigo = [Cuadrupla(PARAMETRO, Constante(1, YUPAY))]
    assert formatear_codigo(optimizar(codigo)) == formatear_codigo(codigo)
