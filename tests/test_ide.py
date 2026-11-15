"""
Entorno gráfico (antachawi/ide). Se ejecuta sin pantalla (Qt offscreen).
Se omite si PySide6 no está instalado.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from antachawi import api, mensajes  # noqa: E402
from antachawi.ide import iconos, sprite, tema  # noqa: E402
from antachawi.ide import ventana as modulo_ventana  # noqa: E402
from antachawi.ide.tunki import ESCALA, MARGEN_ARRIBA  # noqa: E402
from antachawi.ide.ventana import (  # noqa: E402
    EJEMPLOS,
    VentanaPrincipal,
    ejemplos_en,
    nombre_de_ejemplo,
)
from antachawi.mensajes import QU  # noqa: E402

CON_ERRORES = EJEMPLOS / "06_encuentra_el_error.awi"
ARREGLADO = 'qhapaq()\n{\n    yupay huevos = 3\n    rikuchiy(huevos)\n}\n'
DIVIDE_ENTRE_CERO = ('qhapaq()\n{\n    yupay a = 0\n'
                     '    rikuchiy("antes")\n    rikuchiy(5 / a)\n}\n')


@pytest.fixture(scope="module")
def aplicacion():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(aplicacion):
    v = VentanaPrincipal()
    v.resize(1000, 700)
    v.show()
    yield v
    if v.hilo is not None:
        v.hilo.wait()
    v.setWindowModified(False)
    v.close()


def esperar_ejecucion(ventana):
    for _ in range(200):
        if ventana.accion_ejecutar.isEnabled():
            return
        QTest.qWait(25)
    raise AssertionError("la ejecución no terminó")


def texto_del_globo(ventana):
    return ventana.tunki.globo.etiqueta.text()


# ----------------------------------------------------------------------
# Dibujo de Tunki
# ----------------------------------------------------------------------
def test_todas_las_filas_tienen_el_mismo_ancho():
    for humor in sprite.HUMORES:
        assert {len(f) for f in sprite.filas(humor)} == {sprite.ANCHO}
        assert len(sprite.filas(humor)) == sprite.ALTO


def test_solo_usa_colores_de_la_paleta():
    for humor in sprite.HUMORES:
        letras = set("".join(sprite.filas(humor))) - {"."}
        assert letras <= set(sprite.PALETA), humor


def test_los_humores_cambian_el_ojo(aplicacion):
    imagenes = {humor: sprite.imagen(humor) for humor in sprite.HUMORES}
    assert len({img.cacheKey() for img in imagenes.values()}) == len(
        sprite.HUMORES)
    assert len(set(map(tuple, (sprite.filas(h)
                               for h in sprite.HUMORES)))) == len(
        sprite.HUMORES)


# ----------------------------------------------------------------------
# Ejemplos
# ----------------------------------------------------------------------
def test_nombre_de_ejemplo():
    assert nombre_de_ejemplo(CON_ERRORES) == "Encuentra el error"


@pytest.mark.parametrize("ruta", sorted(EJEMPLOS.rglob("*.awi")),
                         ids=lambda r: str(r.relative_to(EJEMPLOS)))
def test_los_ejemplos_funcionan(ruta):
    """También los traducidos al quechua (ejemplos/qu/)."""
    resultado = api.analizar_archivo(ruta)
    if ruta.name.startswith(CON_ERRORES.name.split("_")[0] + "_"):
        assert [e["codigo"] for e in resultado.errores] == [
            "SEM004", "SEM001"]
        return
    assert resultado.exito and not resultado.advertencias
    traza = resultado.ejecutar()
    assert traza.termino and traza.salida


def test_los_ejemplos_en_quechua_tienen_su_original():
    numeros = {r.name[:2] for r in EJEMPLOS.glob("*.awi")}
    for ruta in modulo_ventana.EJEMPLOS_QUECHUA.glob("*.awi"):
        assert ruta.name[:2] in numeros, ruta.name


def test_ejemplos_en_quechua_si_existen(tmp_path, monkeypatch):
    (tmp_path / "01_prueba.awi").write_text("", encoding="utf-8")
    monkeypatch.setattr(modulo_ventana, "EJEMPLOS_QUECHUA", tmp_path)
    espanol = ejemplos_en(mensajes.ES)
    quechua = ejemplos_en(QU)
    assert len(quechua) == len(espanol)
    assert quechua[0] == tmp_path / "01_prueba.awi"
    assert quechua[1:] == espanol[1:]      # sin traducir: en español


# ----------------------------------------------------------------------
# Ventana
# ----------------------------------------------------------------------
def test_tunki_vuela_al_primer_error(ventana):
    ventana.abrir_ejemplo(CON_ERRORES)
    assert ventana.problemas.count() == 2
    assert ventana.tunki.linea == 5
    assert ventana.tunki.humor == sprite.SORPRENDIDO
    assert ventana.tunki.globo.isVisible()
    assert "huevo" in texto_del_globo(ventana)
    assert "mana churakusqa" in texto_del_globo(ventana)  # quechua


def test_el_ojo_de_tunki_queda_a_la_altura_de_la_linea(ventana):
    ventana.abrir_ejemplo(CON_ERRORES)
    ventana.tunki.volar_a_linea(5, animado=False)
    ojo = ventana.tunki.y() + (MARGEN_ARRIBA + 11) * ESCALA
    assert abs(ojo - ventana.editor.rect_de_linea(5).center().y()) <= 1


def test_al_tocar_a_tunki_pasa_al_siguiente_error(ventana):
    ventana.abrir_ejemplo(CON_ERRORES)
    ventana.tunki.clicado.emit()
    assert ventana.tunki.linea == 6
    ventana.tunki.clicado.emit()
    assert ventana.tunki.linea == 5


def test_al_arreglar_el_error_tunki_se_alegra(ventana):
    ventana.abrir_ejemplo(CON_ERRORES)
    ventana.editor.setPlainText(ARREGLADO)
    ventana.analizar_ahora()
    assert ventana.errores == []
    assert ventana.tunki.linea is None
    assert ventana.tunki.humor == sprite.FELIZ
    assert ventana.problemas.item(0).text() == (
        mensajes.IDE_SIN_PROBLEMAS.texto())


def test_ejecutar(ventana):
    ventana.editor.setPlainText(ARREGLADO)
    ventana.ejecutar()
    esperar_ejecucion(ventana)
    assert ventana.salida.toPlainText() == "3\n"
    assert ventana.tunki.humor == sprite.FELIZ


def test_no_ejecuta_con_errores(ventana):
    ventana.abrir_ejemplo(CON_ERRORES)
    ventana.ejecutar()
    assert ventana.hilo is None
    assert mensajes.TUNKI_ARREGLA_PRIMERO.texto() in texto_del_globo(
        ventana)


def test_error_al_ejecutar(ventana):
    ventana.editor.setPlainText(DIVIDE_ENTRE_CERO)
    ventana.ejecutar()
    esperar_ejecucion(ventana)
    assert ventana.salida.toPlainText() == "antes\n"
    assert ventana.tunki.linea == 5
    assert "EJE001" in texto_del_globo(ventana)


def test_cambiar_idioma(ventana):
    ventana.abrir_ejemplo(CON_ERRORES)
    ventana.selector_idioma.setCurrentIndex(
        ventana.selector_idioma.findData(QU))
    assert texto_del_globo(ventana).count("mana churakusqa") == 1
    assert "no fue declarada" not in texto_del_globo(ventana)
    assert ventana.accion_ejecutar.text() == mensajes.IDE_EJECUTAR.qu


def test_mientras_se_escribe_tunki_piensa(ventana):
    ventana.editor.insertPlainText("x")
    assert ventana.tunki.humor == sprite.PENSANDO
    assert not ventana.tunki.globo.isVisible()
    assert ventana.temporizador.isActive()
    assert ventana.isWindowModified()


def test_guardar(ventana, tmp_path):
    ruta = tmp_path / "mio.awi"
    ventana.ruta = ruta
    ventana.editor.setPlainText(ARREGLADO)
    assert ventana.guardar()
    assert ruta.read_text(encoding="utf-8") == ARREGLADO
    assert not ventana.isWindowModified()


def test_resaltado_de_palabras_clave(ventana):
    ventana.editor.setPlainText("qhapaq() :: comentario\n")
    formatos = ventana.editor.document().firstBlock().layout().formats()
    rangos = {(f.start, f.length) for f in formatos}
    assert (0, len("qhapaq")) in rangos
    assert (9, len(":: comentario")) in rangos


# ----------------------------------------------------------------------
# Tema, íconos y ayudas del editor
# ----------------------------------------------------------------------
@pytest.mark.parametrize("nombre", iconos.NOMBRES)
def test_iconos_cuadrados_y_con_colores_de_la_paleta(nombre):
    filas = iconos.filas(nombre)
    assert len(filas) == iconos.LADO
    assert {len(f) for f in filas} == {iconos.LADO}
    assert set("".join(filas)) - {"."} <= set(iconos.PALETA)


def test_el_tema_no_depende_del_tema_oscuro_del_sistema(ventana):
    # Aunque el escritorio use un tema oscuro, las letras son oscuras
    # sobre fondos claros.
    paleta = QApplication.instance().palette()
    assert paleta.text().color().lightness() < 80
    assert paleta.base().color().lightness() > 200
    assert paleta.buttonText().color().lightness() < 80


def escribir(ventana, texto):
    for letra in texto:
        if letra == "\n":
            QTest.keyClick(ventana.editor, Qt.Key.Key_Return)
        else:
            QTest.keyClicks(ventana.editor, letra)


def test_sangria_automatica(ventana):
    ventana.editor.clear()
    escribir(ventana, "qhapaq()\n{\nrikuchiy(1)\n}")
    assert ventana.editor.toPlainText() == (
        "qhapaq()\n{\n    rikuchiy(1)\n}")


def test_retroceso_borra_un_nivel_de_sangria(ventana):
    ventana.editor.setPlainText("        ")
    ventana.editor.moveCursor(QTextCursor.MoveOperation.End)
    QTest.keyClick(ventana.editor, Qt.Key.Key_Backspace)
    assert ventana.editor.toPlainText() == "    "


def test_cambiar_tamano_de_letra(ventana):
    antes = ventana.editor.tamano
    ventana.accion_agrandar.trigger()
    assert ventana.editor.tamano == antes + 1
    assert ventana.editor.font().pointSize() == antes + 1
    ventana.editor.cambiar_tamano(1000)
    assert ventana.editor.tamano == tema.TAMANO_MAXIMO


def test_barra_de_estado(ventana):
    ventana.abrir_ejemplo(CON_ERRORES)
    assert "2" in ventana.estado.text()
    assert ventana.insignia_problemas.text() == "2"
    ventana.editor.setPlainText(ARREGLADO)
    ventana.analizar_ahora()
    assert ventana.estado.text().endswith(
        mensajes.IDE_ESTADO_SIN_ERRORES.texto())
    ventana.editor.ir_a_linea(3, 5)
    assert ventana.posicion.text() == mensajes.IDE_POSICION.texto(
        linea=3, columna=5)


def test_en_quechua_cambian_botones_ejemplos_y_plantilla(ventana):
    ventana.selector_idioma.setCurrentIndex(
        ventana.selector_idioma.findData(QU))
    assert ventana.accion_ejecutar.text() == mensajes.IDE_EJECUTAR.qu
    ejemplos = [a.text() for a in ventana.boton_ejemplos.menu().actions()]
    assert len(ejemplos) == len(list(EJEMPLOS.glob("*.awi")))
    assert all("qu" == r.parent.name for r in ejemplos_en(QU))
    ventana.nuevo()
    assert "Napaykullayki" in ventana.editor.toPlainText()


def test_icono_de_la_aplicacion_es_cuadrado_y_tiene_a_tunki(aplicacion):
    for lado in iconos.TAMANOS_DEL_ICONO:
        imagen = iconos.imagen_de_la_aplicacion(lado)
        assert imagen.width() == imagen.height() == lado
        centro = imagen.pixelColor(lado // 2, lado // 2)
        assert centro.alpha() > 0
    assert not iconos.icono_de_la_aplicacion().isNull()
