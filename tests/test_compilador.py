"""Pruebas de punta a punta: .awi -> ensamblador x86-64 -> ejecutable.

Requieren Linux x86-64 y cc/gcc (para ensamblar y enlazar). Cada prueba se
ejecuta dos veces, con y sin optimización: ambos programas deben imprimir
lo mismo.
"""
import subprocess

import pytest

from antachawi.compiler import (
    Compiler,
    buscar_enlazador,
    plataforma_soportada,
)
from conftest import RAIZ
from test_parser import programa

pytestmark = pytest.mark.skipif(
    not plataforma_soportada() or buscar_enlazador() is None,
    reason="se necesita Linux x86-64 con cc o gcc")


@pytest.fixture(params=[True, False], ids=["optimizado", "sin_optimizar"])
def compilar(request, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _compilar(codigo):
        fuente = tmp_path / "programa.awi"
        fuente.write_text(codigo, encoding="utf-8")
        ejecutable = tmp_path / "run"
        ok = Compiler(str(fuente), str(ejecutable),
                      optimize=request.param).compile()
        if not ok:
            return ok, None
        salida = subprocess.run([str(ejecutable)], capture_output=True,
                                text=True, timeout=10,
                                check=True).stdout
        return ok, salida.splitlines()

    return _compilar


def test_operaciones_basicas(compilar):
    ok, salida = compilar(programa(
        "yupay a = 10",
        "yupay b = 2",
        "rikuchiy (a + b, \" \", a - b, \" \", a * b, \" \", a / b)",
        "rikuchiy ((a - b) * 3 - a / b)",
        "rikuchiy (a - b - 3, \" \", -a + 1)",
    ))
    assert ok
    assert salida == ["12 8 20 5", "19", "5 -9"]


def test_condicionales_anidadas(compilar):
    ok, salida = compilar(programa(
        "yupay a = 5",
        "ari (a > 1)",
        "{",
        "    ari (a > 7)",
        "    {",
        "        rikuchiy (\"mayor a 7\")",
        "    }",
        "    mana_chayqa_ari (a == 5) {",
        "        rikuchiy (\"igual a 5\")",
        "    } mana_chayqa {",
        "        rikuchiy (\"otro\")",
        "    }",
        "}",
        "rikuchiy (\"fin\")",
    ))
    assert ok
    assert salida == ["igual a 5", "fin"]


def test_rikuchiy_con_comas_y_parentesis(compilar):
    ok, salida = compilar(programa(
        "yupay a = 3",
        "rikuchiy (\"a, b = \", (a + 1) * 2, \" (fin)\")",
    ))
    assert ok
    assert salida == ["a, b = 8 (fin)"]


def test_comentarios_al_final_de_la_linea(compilar):
    ok, salida = compilar(programa(
        "yupay a = 5  :: comentario",
        "rikuchiy (\"a :: b\", a)  :: el :: del texto se mantiene",
    ))
    assert ok
    assert salida == ["a :: b5"]


def test_chiqaq_es_verdadero_y_yanqa_es_falso(compilar):
    ok, salida = compilar(programa(
        "bool v = chiqaq",
        "bool f = yanqa",
        "rikuchiy (v, f)",
    ))
    assert ok
    assert salida == ["10"]


def test_no_genera_ejecutable_con_errores(compilar, tmp_path):
    ok, _ = compilar(programa("yupay x = \"hola\""))
    assert ok is False
    assert not (tmp_path / "run").exists()


def test_mezcla_de_entero_y_decimal(compilar):
    ok, salida = compilar(programa(
        "yupay a = 3",
        "chunkayuq b = 1.5",
        "chunkayuq c = a * b",
        "chunkayuq d = 2",
        "rikuchiy (c, \" \", d / 4)",
    ))
    assert ok
    assert salida == ["4.5 0.5"]


def test_concatenar_texto_con_variable(compilar):
    ok, salida = compilar(programa(
        "qaytu nombre = \"Ana\"",
        "qaytu saludo = \"Hola \" + nombre",
        "rikuchiy (saludo)",
    ))
    assert ok
    assert salida == ["Hola Ana"]


def test_concatenar_dos_literales(compilar):
    ok, salida = compilar(programa("qaytu s = \"a\" + \"b\"",
                                   "rikuchiy (s + s)"))
    assert ok
    assert salida == ["abab"]


def test_las_advertencias_no_detienen_la_compilacion(compilar, capsys):
    ok, salida = compilar(programa(
        "yupay sin_usar = 1",
        "yupay a",
        "rikuchiy (\"ok\")",
        "a = 2",
    ))
    assert ok
    assert salida == ["ok"]
    assert "sin_usar" in capsys.readouterr().out


def test_expresiones_booleanas_e_impresion(compilar):
    ok, salida = compilar(programa(
        "yupay a = 5",
        "bool grande = a > 3 && a != 4",
        "rikuchiy (grande, \" \", a < 2, \" \", (a + 1) * 2 == 12)",
        "ari ((a > 1 || yanqa) && grande)",
        "{",
        "    rikuchiy (\"ok\")",
        "}",
    ))
    assert ok
    assert salida == ["1 0 1", "ok"]


def test_secuencias_de_escape_y_decimales(compilar):
    ok, salida = compilar(programa(
        "chunkayuq mitad = .5",
        "sananpa comilla = '\\''",
        "rikuchiy (\"dijo \\\"hola\\\"\\tfin\", comilla, mitad * 3)",
    ))
    assert ok
    assert salida == ["dijo \"hola\"\tfin'1.5"]


def test_division_entera_trunca_hacia_cero(compilar):
    ok, salida = compilar(programa(
        "yupay a = -7",
        "rikuchiy (a / 2, \" \", 7 / -2, \" \", -7 / 2)",
    ))
    assert ok
    assert salida == ["-3 -3 -3"]


def test_variables_hermanas_con_el_mismo_nombre(compilar):
    ok, salida = compilar(programa(
        "yupay a = 1",
        "ari (a > 0) {",
        "    yupay x = 10",
        "    rikuchiy (x)",
        "} mana_chayqa {",
        "    qaytu x = \"no\"",
        "    rikuchiy (x)",
        "}",
        "ari (a < 0) {",
        "    chunkayuq x = 2.5",
        "    rikuchiy (x)",
        "} mana_chayqa {",
        "    sananpa x = 'z'",
        "    rikuchiy (x)",
        "}",
    ))
    assert ok
    assert salida == ["10", "z"]


def test_valores_iniciales(compilar):
    ok, salida = compilar(programa(
        "yupay a",
        "chunkayuq b",
        "bool c",
        "qaytu d",
        "rikuchiy (a, \" \", b, \" \", c, \"[\", d, \"]\")",
    ))
    assert ok
    assert salida == ["0 0 0[]"]


def test_comparaciones_de_textos_caracteres_y_decimales(compilar):
    ok, salida = compilar(programa(
        "qaytu s = \"ab\"",
        "qaytu r = \"a\" + \"b\"",
        "sananpa c = 'b'",
        "chunkayuq d = 0.1 + 0.2",
        "rikuchiy (s == r, s != r, c > 'a', c <= 'a', d > 0.3, d == 0.3)",
    ))
    assert ok
    assert salida == ["101010"]


def test_cortocircuito_en_condiciones_anidadas(compilar):
    ok, salida = compilar(programa(
        "yupay a = 3",
        "yupay b = 0",
        "ari ((a > 5 || b == 0) && (a == 3) == chiqaq) {",
        "    rikuchiy (\"si\")",
        "}",
        "bool v = a > 5 && a / b > 1",
        "rikuchiy (v)",
    ))
    assert ok
    # a / b no se evalúa (sería una división entre cero)
    assert salida == ["si", "0"]


def test_negativos_y_decimales(compilar):
    ok, salida = compilar(programa(
        "chunkayuq x = 1.5",
        "yupay n = 4",
        "x = -x * n + 0.25",
        "rikuchiy (x, \" \", -(n - 10), \" \", 10 / 4.0)",
    ))
    assert ok
    assert salida == ["-5.75 6 2.5"]


def test_bucles(compilar):
    ok, salida = compilar(programa(
        "yupay suma = 0",
        "imapaq (yupay i = 1; i <= 4; i = i + 1) {",
        "    imapaq (yupay j = 0; j < i; j = j + 1) {",
        "        suma = suma + j",
        "    }",
        "}",
        "chunkayuq x = 1.0",
        "chaykama (x < 100.0) {",
        "    x = x * 2.5",
        "}",
        "qaytu s = \"\"",
        "yupay n = 3",
        "chaykama (n > 0) {",
        "    s = s + \"ab\"",
        "    n = n - 1",
        "}",
        "rikuchiy (suma, \" \", x, \" \", s)",
    ))
    assert ok
    assert salida == ["10 244.141 ababab"]


def test_bucle_que_no_se_ejecuta(compilar):
    ok, salida = compilar(programa(
        "chaykama (yanqa) {",
        "    rikuchiy (\"nunca\")",
        "}",
        "rikuchiy (\"fin\")",
    ))
    assert ok
    assert salida == ["fin"]


def test_caracteres_unicode(compilar):
    ok, salida = compilar(programa(
        "sananpa a = 'ñ'",
        "sananpa b = '€'",
        "sananpa c = '😀'",
        "rikuchiy (a, b, c, 'z', a < b, b < c)",
        "rikuchiy (\"ñandú\")",
    ))
    assert ok
    assert salida == ["ñ€😀z11", "ñandú"]


def test_ejemplo_main_awi(compilar):
    ok, salida = compilar((RAIZ / "inputs" / "main.awi").read_text(
        encoding="utf-8"))
    assert ok
    assert salida == ["a es mayor que 10"] + [
        f"i es {i}" for i in range(5)] + [
        f"Contador es {i}" for i in range(3)]
