"""Ensamblador generado: asignación de registros, registro de activación y
plataformas. Estas pruebas no ensamblan ni ejecutan nada, salvo las que
usan clang para ensamblar para otras plataformas."""
import shutil
import subprocess

import pytest

from antachawi.bloques_basicos import particionar
from antachawi.generador_x86 import (
    RegistroActivacion,
    bits_de_decimal,
    generar_ensamblador,
    registros_globales,
    texto_para_ensamblador,
)
from antachawi.intermedio import (
    PARAMETRO,
    Constante,
    Cuadrupla,
    Nombre,
    Temporal,
    generar_codigo_intermedio,
)
from antachawi.optimizador import optimizar, variables_vivas
from antachawi.plataformas import LINUX, MACOS, PLATAFORMAS, WINDOWS
from antachawi.tipos import CHUNKAYUQ, QAYTU, SANANPA, YUPAY
from programas_aleatorios import programa_aleatorio
from test_parser import programa


def lineas(codigo, plataforma=LINUX):
    return [linea.strip() for linea in
            generar_ensamblador(codigo, plataforma).split("\n")]


def instrucciones_de(codigo, comentario, plataforma=LINUX):
    """Instrucciones generadas para la instrucción de tres direcciones
    cuyo comentario es `comentario`."""
    todas = lineas(codigo, plataforma)
    inicio = todas.index(f"# | {comentario}") + 1
    fin = inicio
    while fin < len(todas) and not todas[fin].startswith("#"):
        fin += 1
    return todas[inicio:fin]


def imprimir(*direcciones):
    return [Cuadrupla(PARAMETRO, d) for d in direcciones] + [
        Cuadrupla("call", "rikuchiy", len(direcciones))]


# ----------------------------------------------------------------------
# Registro de activación
# ----------------------------------------------------------------------
def test_registro_de_activacion_alinea_a_16_bytes():
    registro = RegistroActivacion()
    a = Nombre("a", YUPAY)
    assert registro.lugar(a) == "QWORD PTR [rbp - 8]"
    assert registro.lugar(a) == "QWORD PTR [rbp - 8]"
    assert registro.tamano == 16
    assert registro.lugar("rbx") == "QWORD PTR [rbp - 16]"
    assert registro.tamano == 16
    # En Windows además se reservan 32 bytes de sombra
    assert RegistroActivacion(32).tamano == 32


def test_variables_que_viven_en_registros_no_ocupan_memoria():
    a, t1 = Nombre("a", YUPAY), Temporal(1, YUPAY)
    codigo = [Cuadrupla("=", Constante(2, YUPAY), resultado=a),
              Cuadrupla("*", a, a, t1),
              *imprimir(t1)]
    # El único lugar en la pila es para guardar rbx
    lugares = [linea for linea in lineas(codigo) if linea.startswith("#   [")]
    assert lugares == ["#   [rbp -   8]  rbx (registro conservado)"]


# ----------------------------------------------------------------------
# Asignación de registros (sección 8.6)
# ----------------------------------------------------------------------
def test_la_suma_reutiliza_el_registro_de_un_operando_muerto():
    a, b, t1 = Nombre("a", YUPAY), Nombre("b", YUPAY), Temporal(1, YUPAY)
    codigo = [Cuadrupla("=", Constante(2, YUPAY), resultado=a),
              Cuadrupla("=", Constante(3, YUPAY), resultado=b),
              Cuadrupla("+", a, b, t1),
              *imprimir(t1)]
    assert instrucciones_de(codigo, "a = 2") == ["mov rbx, 2"]
    assert instrucciones_de(codigo, "b = 3") == ["mov r12, 3"]
    # a ya no se usa: t1 se calcula en su mismo registro
    assert instrucciones_de(codigo, "t1 = a + b") == ["add rbx, r12"]


def test_una_copia_no_genera_codigo():
    a, b = Nombre("a", YUPAY), Nombre("b", YUPAY)
    codigo = [Cuadrupla("=", Constante(2, YUPAY), resultado=a),
              Cuadrupla("=", a, resultado=b),
              *imprimir(a, b)]
    assert instrucciones_de(codigo, "b = a") == []


def test_antes_de_una_llamada_se_guardan_los_registros_que_se_pierden():
    # Los xmm no sobreviven a printf: d debe ir a memoria antes de
    # imprimir porque se usa después.
    d = Nombre("d", CHUNKAYUQ)
    codigo = [Cuadrupla("=", Constante(1.5, CHUNKAYUQ), resultado=d),
              *imprimir(Constante("x", QAYTU)),
              *imprimir(d)]
    generado = lineas(codigo)
    guardado = generado.index("movsd QWORD PTR [rbp - 8], xmm2")
    assert guardado < generado.index("call printf@PLT")


def test_variables_de_bucle_reciben_registro_fijo(analizar):
    r = analizar(programa(
        "yupay suma = 0",
        "imapaq (yupay i = 0; i < 10; i = i + 1) {",
        "    suma = suma + i",
        "}",
        "rikuchiy (suma)",
    ), semantico=True)
    codigo = optimizar(generar_codigo_intermedio(r.ast))
    salida = variables_vivas(particionar(codigo))
    globales = registros_globales(codigo, salida, ("rbx", "r12", "r13"))
    assert {str(v): reg for v, reg in globales.items()} == {
        "i": "rbx", "suma": "r12"}
    assert instrucciones_de(codigo, "i = i + 1") == ["add rbx, 1"]


# ----------------------------------------------------------------------
# Instrucciones
# ----------------------------------------------------------------------
def test_division_de_decimales_usa_sse():
    d, t1 = Nombre("d", CHUNKAYUQ), Temporal(1, CHUNKAYUQ)
    codigo = [Cuadrupla("/", d, Constante(2.0, CHUNKAYUQ), t1),
              *imprimir(t1)]
    generado = instrucciones_de(codigo, "t1 = d / 2.0")
    assert f"mov rax, {bits_de_decimal(2.0)}" in generado
    assert "movq xmm1, rax" in generado
    assert generado[-1].startswith("divsd xmm")


def test_rikuchiy_llama_a_printf_y_textos_van_en_la_seccion_de_datos():
    codigo = lineas(imprimir(Constante("hola", QAYTU),
                             Constante(1.5, CHUNKAYUQ),
                             Constante(7, YUPAY)))
    assert codigo.count("call printf@PLT") == 3
    assert "call putchar@PLT" in codigo
    assert "mov eax, 1" in codigo          # el decimal va en xmm0
    assert '.asciz "hola"' in codigo
    assert '.asciz "%lld"' in codigo


def test_caracteres_se_imprimen_en_utf8():
    codigo = lineas(imprimir(Constante("ñ", SANANPA)))
    assert "mov rdi, 241" in codigo         # código Unicode de ñ
    assert "call awi_imprimir_caracter" in codigo
    assert "awi_imprimir_caracter:" in codigo


def test_concatenar_agrega_la_funcion_auxiliar():
    s, t1 = Nombre("s", QAYTU), Temporal(1, QAYTU)
    codigo = lineas([Cuadrupla("+", s, s, t1), *imprimir(t1)])
    assert "call awi_concatenar" in codigo
    assert "awi_concatenar:" in codigo


def test_textos_con_caracteres_especiales():
    assert texto_para_ensamblador('a"\\\nñ') == '"a\\042\\134\\012\\303\\261"'


# ----------------------------------------------------------------------
# Plataformas
# ----------------------------------------------------------------------
def test_diferencias_entre_plataformas():
    codigo = imprimir(Constante(1.5, CHUNKAYUQ))
    linux, mac, windows = (lineas(codigo, p)
                           for p in (LINUX, MACOS, WINDOWS))
    assert "_main:" in mac and "call _printf" in mac
    assert "main:" in windows and "call printf" in windows
    # Windows: argumentos en rcx, rdx; el decimal también en rdx
    assert "lea rcx, [rip + .Lformato_chunkayuq]" in windows
    assert "movq rdx, xmm1" in windows
    assert "sub rsp, 32" in windows                 # espacio de sombra
    assert "lea rdi, [rip + .Lformato_chunkayuq]" in linux


OBJETIVOS_CLANG = {
    "linux": "x86_64-linux-gnu",
    "macos": "x86_64-apple-macos11",
    "windows": "x86_64-w64-windows-gnu",
}


@pytest.mark.skipif(shutil.which("clang") is None,
                    reason="clang no está instalado")
@pytest.mark.parametrize("nombre", sorted(PLATAFORMAS))
def test_el_ensamblador_es_valido_en_cada_plataforma(analizar, tmp_path,
                                                     nombre):
    """clang puede ensamblar para cualquier plataforma: así se verifica
    el código de macOS y Windows desde Linux (sin enlazarlo)."""
    for semilla in range(8):
        r = analizar(programa_aleatorio(semilla), semantico=True)
        fuente = tmp_path / "programa.s"
        fuente.write_text(generar_ensamblador(
            generar_codigo_intermedio(r.ast), PLATAFORMAS[nombre]),
            encoding="utf-8")
        resultado = subprocess.run(
            ["clang", f"--target={OBJETIVOS_CLANG[nombre]}", "-c",
             str(fuente), "-o", str(tmp_path / "programa.o")],
            capture_output=True, text=True, check=False)
        assert resultado.returncode == 0, resultado.stderr
