"""
Prueba diferencial: programas aleatorios se compilan (con y sin
optimización), se ejecutan, y su salida se compara con la de un
intérprete del código de tres direcciones sin optimizar. Así se prueban
juntos el optimizador, la asignación de registros y la generación de
código.
"""
import subprocess

import pytest

from antachawi.compiler import (
    Compiler,
    buscar_enlazador,
    plataforma_soportada,
)
from antachawi.intermedio import generar_codigo_intermedio
from antachawi.interprete import ejecutar
from programas_aleatorios import programa_aleatorio

pytestmark = pytest.mark.skipif(
    not plataforma_soportada() or buscar_enlazador() is None,
    reason="se necesita x86-64 con cc, gcc o clang")

SEMILLAS = range(25)


@pytest.mark.parametrize("semilla", SEMILLAS)
def test_ejecutable_igual_al_interprete(semilla, analizar, tmp_path,
                                        monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    codigo = programa_aleatorio(semilla)
    r = analizar(codigo, semantico=True)
    assert not r.errores_semanticos
    esperado = ejecutar(generar_codigo_intermedio(r.ast))

    fuente = tmp_path / "aleatorio.awi"
    fuente.write_text(codigo, encoding="utf-8")
    for optimizar in (True, False):
        ejecutable = tmp_path / f"run{int(optimizar)}"
        assert Compiler(str(fuente), str(ejecutable),
                        optimize=optimizar).compile()
        salida = subprocess.run([str(ejecutable)], capture_output=True,
                                timeout=10, check=True).stdout
        # glibc imprime -nan donde Python imprime nan
        assert salida.decode().replace("-nan", "nan") == esperado, codigo
    capsys.readouterr()
