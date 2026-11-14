"""
API para otros programas (antachawi/api.py), posiciones en el código
intermedio y traza del intérprete (antachawi/interprete.py).
"""
import json
import subprocess
import sys

import pytest

from antachawi import api
from antachawi.intermedio import ETIQUETA, SALTO
from antachawi.interprete import ejecutar
from antachawi.plataformas import plataforma_actual
from conftest import RAIZ

BUCLE = """qhapaq()
{
    yupay a = 5
    yupay i = 0
    chaykama (i < a) {
        rikuchiy("i = ", i)
        i = i + 1
    }
}
"""


# ----------------------------------------------------------------------
# analizar
# ----------------------------------------------------------------------
def test_programa_correcto():
    r = api.analizar(BUCLE)
    assert r.exito and r.fase_fallida is None
    assert r.errores == [] and r.advertencias == []
    assert r.ast is not None and r.tabla is not None
    assert r.intermedio and r.optimizado
    assert len(r.bloques()) > 1


@pytest.mark.skipif(plataforma_actual() is None,
                    reason="se necesita x86-64")
def test_ensamblador():
    assert "main:" in api.analizar(BUCLE).ensamblador()


def test_sin_optimizar():
    r = api.analizar(BUCLE, optimizar_codigo=False)
    assert r.optimizado is None
    assert r.codigo_final() is r.intermedio


@pytest.mark.parametrize("codigo, fase, codigo_error", [
    ("qhapaq() {\n    yupay a = 1 # 2\n}", api.LEXICO, "LEX007"),
    ("qhapaq() {\n    yupay = 1\n}", api.SINTACTICO, "SIN001"),
    ("qhapaq() {\n    rikuchiy(b)\n}", api.SEMANTICO, "SEM004"),
])
def test_se_detiene_en_la_fase_con_errores(codigo, fase, codigo_error):
    r = api.analizar(codigo)
    assert not r.exito and r.fase_fallida == fase
    assert [e["codigo"] for e in r.errores] == [codigo_error]
    assert r.intermedio is None
    assert r.ensamblador() is None and r.ejecutar() is None


def test_advertencias_sin_errores():
    r = api.analizar("qhapaq() {\n    yupay a = 1\n}")
    assert r.exito
    assert [a["codigo"] for a in r.advertencias] == ["ADV001"]


def test_no_imprime_ni_escribe_archivos(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    api.analizar(BUCLE).ensamblador()
    api.analizar("qhapaq() {\n    rikuchiy(b)\n}")
    assert capsys.readouterr().out == ""
    assert list(tmp_path.iterdir()) == []


def test_saltos_de_linea_de_windows():
    windows = api.analizar(BUCLE.replace("\n", "\r\n"))
    assert windows.exito
    assert ([str(c) for c in windows.intermedio]
            == [str(c) for c in api.analizar(BUCLE).intermedio])


def test_analizar_archivo():
    r = api.analizar_archivo(RAIZ / "inputs" / "main.awi")
    assert r.exito and r.fuente.filename.endswith("main.awi")


# ----------------------------------------------------------------------
# Posiciones en el código intermedio
# ----------------------------------------------------------------------
def lineas_por_instruccion(codigo):
    return [(str(c), c.pos.linea) for c in codigo]


def test_cada_instruccion_sabe_de_que_linea_viene():
    r = api.analizar(BUCLE, optimizar_codigo=False)
    assert all(c.pos is not None for c in r.intermedio)
    lineas = lineas_por_instruccion(r.intermedio)
    assert lineas[0] == ("a = 5", 3)
    assert ("if i >= a goto L2", 5) in lineas
    assert ("call rikuchiy, 2", 6) in lineas
    assert ("i = t1", 7) in lineas
    # El goto que vuelve al inicio y las etiquetas son del chaykama
    assert all(c.pos.linea == 5 for c in r.intermedio
               if c.op in (SALTO, ETIQUETA))


def test_imapaq_y_mana_chayqa_ari():
    r = api.analizar("""qhapaq()
{
    imapaq (yupay i = 0; i < 3; i = i + 1) {
        ari (i == 0) {
            rikuchiy(0)
        } mana_chayqa_ari (i == 1) {
            rikuchiy(1)
        }
    }
}
""", optimizar_codigo=False)
    lineas = lineas_por_instruccion(r.intermedio)
    assert lineas[0] == ("i = 0", 3)
    assert ("if i != 0 goto L4", 4) in lineas
    assert ("if i != 1 goto L3", 6) in lineas
    assert ("i = t1", 3) in lineas        # el paso del imapaq


def test_el_optimizador_conserva_las_posiciones():
    r = api.analizar(BUCLE)
    assert all(c.pos is not None for c in r.optimizado)
    assert ("i = i + 1", 7) in lineas_por_instruccion(r.optimizado)


# ----------------------------------------------------------------------
# Traza para el depurador
# ----------------------------------------------------------------------
def test_traza_completa():
    r = api.analizar(BUCLE)
    traza = r.ejecutar()
    assert traza.termino and traza.error is None
    assert traza.salida == "".join(f"i = {n}\n" for n in range(5))
    assert traza.salida == ejecutar(r.intermedio)
    final = {v.nombre: c.valor
             for v, c in traza.variables_en(len(traza.pasos)).items()}
    assert final == {"a": 5, "i": 5}


def test_variables_y_salida_paso_a_paso():
    traza = api.analizar(BUCLE).ejecutar()
    primer_rikuchiy = next(n for n, p in enumerate(traza.pasos)
                           if p.salida)
    assert traza.pasos[primer_rikuchiy].linea == 6
    assert traza.salida_hasta(primer_rikuchiy) == "i = 0\n"
    antes = {v.nombre: c.valor
             for v, c in traza.variables_en(primer_rikuchiy).items()}
    assert antes == {"a": 5, "i": 0}


def test_division_entre_cero_al_ejecutar():
    r = api.analizar("""qhapaq()
{
    yupay a = 0
    rikuchiy("antes")
    rikuchiy(10 / a)
}
""")
    traza = r.ejecutar()
    assert not traza.termino
    assert traza.salida == "antes\n"
    assert traza.error["codigo"] == "EJE001"
    assert traza.error["linea"] == 5
    assert traza.error["contenido"] == "    rikuchiy(10 / a)"


def test_bucle_infinito():
    r = api.analizar("""qhapaq()
{
    yupay i = 0
    chaykama (i < 3) {
        rikuchiy(i)
    }
}
""")
    traza = r.ejecutar(maximo_de_pasos=100)
    assert len(traza.pasos) == 100
    assert traza.error["codigo"] == "EJE002"
    assert traza.error["parametros"] == {"pasos": 100}
    assert traza.error["linea"] in (4, 5)


# ----------------------------------------------------------------------
# JSON y línea de comandos
# ----------------------------------------------------------------------
def test_a_json_es_serializable():
    datos = api.a_json(api.analizar(BUCLE), con_traza=True)
    json.dumps(datos)
    assert datos["exito"] is True
    assert datos["intermedio"][0] == {
        "texto": "a = 5", "op": "=",
        "pos": {"linea": 3, "columna": 11, "longitud": 1}}
    assert {s["nombre"] for s in datos["simbolos"]} == {"a", "i"}
    assert datos["ejecucion"]["salida"].startswith("i = 0\n")
    cambios = [p["variable"] for p in datos["ejecucion"]["pasos"]
               if p["variable"]]
    assert cambios[:2] == ["a", "i"]


def test_a_json_con_errores():
    datos = api.a_json(api.analizar("qhapaq() {\n    rikuchiy(b)\n}"),
                       con_traza=True)
    json.dumps(datos)
    assert datos["fase_fallida"] == "semantico"
    assert datos["errores"][0]["textos"]["qu"] == (
        "variable 'b' mana churakusqa.")
    assert datos["intermedio"] is None and datos["ejecucion"] is None


def cli(*argumentos):
    return subprocess.run(
        [sys.executable, "-m", "antachawi.main", *argumentos],
        cwd=RAIZ, capture_output=True, text=True, check=False)


@pytest.mark.parametrize("contenido, exito", [
    (BUCLE, True),
    ("qhapaq() {\n    rikuchiy(b)\n}", False),
])
def test_cli_json(tmp_path, contenido, exito):
    fuente = tmp_path / "programa.awi"
    fuente.write_text(contenido, encoding="utf-8")
    resultado = cli(str(fuente), "--json", "--traza")
    assert resultado.returncode == (0 if exito else 1)
    datos = json.loads(resultado.stdout)
    assert datos["exito"] is exito
    assert ("ejecucion" in datos) and (datos["ejecucion"] is None) != exito
