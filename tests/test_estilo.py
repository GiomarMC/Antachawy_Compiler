"""Verifica el estilo del código:
* flake8 (configuración en .flake8): máximo 79 caracteres por línea y
  complejidad cognitiva de hasta 15.
* isort (configuración en pyproject.toml): orden de los imports.
"""
import subprocess
import sys

import pytest

from conftest import RAIZ


def ejecutar(*argumentos):
    return subprocess.run(
        [sys.executable, "-m", *argumentos, "antachawi", "tests"],
        cwd=RAIZ, capture_output=True, text=True, check=False)


def test_flake8():
    pytest.importorskip("flake8")
    pytest.importorskip("flake8_cognitive_complexity")
    resultado = ejecutar("flake8")
    assert resultado.returncode == 0, resultado.stdout


def test_orden_de_imports():
    pytest.importorskip("isort")
    resultado = ejecutar("isort", "--check-only", "--diff")
    assert resultado.returncode == 0, resultado.stdout
