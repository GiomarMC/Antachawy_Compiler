"""
Traducción al quechua desde la hoja antachawi/traducciones/quechua.csv
(antachawi/traduccion.py y la carga en antachawi/mensajes.py).
"""
import pytest

from antachawi import mensajes, traduccion
from antachawi.mensajes import QU, cargar_traducciones, leer_traducciones


@pytest.fixture
def sin_cambios_en_el_catalogo():
    """Las pruebas cargan traducciones de mentira; al final se deja todo
    como estaba."""
    antes = {m.codigo: m.qu for m in mensajes.catalogo()}
    yield
    for mensaje in mensajes.catalogo():
        object.__setattr__(mensaje, "qu", antes[mensaje.codigo])


def hoja(tmp_path, *filas):
    ruta = tmp_path / "quechua.csv"
    traduccion.escribir_hoja(
        [dict(zip(("codigo", "espanol", "quechua"), f)) for f in filas],
        ruta)
    return ruta


def test_la_hoja_tiene_todos_los_mensajes():
    """Si falla: python -m antachawi.traduccion actualizar"""
    filas = leer_traducciones()
    assert list(filas) == [m.codigo for m in mensajes.catalogo()]


def test_la_hoja_no_tiene_problemas():
    assert traduccion.revisar().problemas == []


def test_todos_los_ejemplos_estan_en_quechua():
    assert traduccion.ejemplos_sin_traducir() == []


def test_se_carga_la_traduccion(tmp_path, sin_cambios_en_el_catalogo):
    m = mensajes.IDE_LINEA
    ruta = hoja(tmp_path, (m.codigo, m.es, "  QU {linea}  "))
    assert cargar_traducciones(ruta) == 1
    assert m.texto(QU, linea=4) == "QU 4"


def test_conserva_el_espacio_final_del_espanol(tmp_path,
                                               sin_cambios_en_el_catalogo):
    m = mensajes.ENCABEZADO_ADVERTENCIA
    ruta = hoja(tmp_path, (m.codigo, m.es, "QU {codigo} {ubicacion}:"))
    cargar_traducciones(ruta)
    assert m.qu == "QU {codigo} {ubicacion}: "


@pytest.mark.parametrize("malo", ["QU {line}", "QU {linea", "QU {}"])
def test_no_carga_llaves_mal_escritas(tmp_path, malo,
                                      sin_cambios_en_el_catalogo):
    m = mensajes.IDE_LINEA
    object.__setattr__(m, "qu", None)
    ruta = hoja(tmp_path, (m.codigo, m.es, malo))
    assert cargar_traducciones(ruta) == 0
    assert m.qu is None
    assert any(p.startswith(m.codigo)
               for p in traduccion.revisar(ruta).problemas)


def test_avisa_si_el_espanol_cambio(tmp_path):
    m = mensajes.IDE_NUEVO
    ruta = hoja(tmp_path, (m.codigo, "Texto viejo", "QU"))
    assert m.codigo in traduccion.revisar(ruta).espanol_cambiado


def test_actualizar_conserva_lo_traducido(tmp_path):
    m = mensajes.IDE_NUEVO
    ruta = hoja(tmp_path, (m.codigo, m.es, "QU"))
    nuevos = traduccion.actualizar(ruta)
    filas = leer_traducciones(ruta)
    assert filas[m.codigo]["quechua"] == "QU"
    assert nuevos == len(mensajes.catalogo()) - 1
    assert "{linea}" in filas[mensajes.IDE_LINEA.codigo]["nota"]


def test_revisar_desde_la_consola(capsys):
    assert traduccion.main(["revisar"]) == 0
    assert "Mensajes traducidos" in capsys.readouterr().out
    assert traduccion.main([]) == 2
