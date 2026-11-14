from antachawi.definitions import EtiquetasAntachawy as E
from antachawi.grammar import (
    PRIMEROS,
    PRODUCCIONES,
    SIGUIENTES,
    conflictos_ll1,
    etiqueta_de,
    leer_gramatica,
)


def test_la_gramatica_es_ll1():
    assert not conflictos_ll1()


def test_todos_los_simbolos_estan_definidos():
    # Cada símbolo debe ser un no terminal definido o un terminal conocido.
    for alternativas in PRODUCCIONES.values():
        for alternativa in alternativas:
            for simbolo in alternativa:
                if simbolo not in PRODUCCIONES:
                    etiqueta_de(simbolo)  # lanza KeyError si no existe


def test_todos_los_no_terminales_son_alcanzables():
    alcanzables = {"Programa"}
    pendientes = ["Programa"]
    while pendientes:
        nt = pendientes.pop()
        for alternativa in PRODUCCIONES[nt]:
            for simbolo in alternativa:
                if simbolo in PRODUCCIONES and simbolo not in alcanzables:
                    alcanzables.add(simbolo)
                    pendientes.append(simbolo)
    assert alcanzables == set(PRODUCCIONES)


def test_primeros_y_siguientes_esperados():
    assert PRIMEROS["Condicional"] == {E.CONDICION_ARI}
    assert PRIMEROS["Termino"] >= {E.MENOS, E.PAREN_IZQ, E.ID, E.TRUE}
    # Una lista de sentencias solo puede terminar con '}'.
    assert SIGUIENTES["ListaSentencias"] == {E.LLAVE_DER}
    # Después de un if/else completo viene el salto de línea de la sentencia.
    assert SIGUIENTES["CondicionalPrime"] == {E.SALTO_LINEA}


def test_detecta_conflictos_en_una_gramatica_ambigua():
    # Recursión por la izquierda: no es LL(1).
    ambigua = leer_gramatica("""
Programa -> Expresion
Expresion -> Expresion + id | id
""")
    assert conflictos_ll1(ambigua)


def test_el_operador_o_no_se_confunde_con_el_separador():
    assert PRODUCCIONES["ExpresionOPrime"] == [
        ["||", "ExpresionY", "ExpresionOPrime"],
        [],
    ]
