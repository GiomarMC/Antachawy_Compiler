"""
Plataformas para las que se genera código x86-64.

El procesador es el mismo en las tres, pero cambian:

* la convención de llamadas: en qué registros van los argumentos, qué
  registros conserva una función y si hay que reservar "espacio de sombra"
  de 32 bytes antes de cada llamada (Windows);
* cómo se escriben los nombres: en macOS los símbolos de C llevan '_'
  delante; en Linux las funciones de bibliotecas compartidas se llaman a
  través de la PLT (printf@PLT);
* los nombres de las secciones y algunas directivas del ensamblador.

macOS: el código es x86-64 y se enlaza con `cc -arch x86_64`; en una Mac
con procesador Apple (arm64) se ejecuta con Rosetta 2.
"""
from __future__ import annotations

import platform as _sistema
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Plataforma:
    nombre: str
    argumentos: Tuple[str, ...]       # registros para argumentos enteros
    espacio_sombra: int               # bytes que reserva quien llama
    prefijo_simbolo: str              # '_' en macOS
    sufijo_llamada: str               # '@PLT' en Linux
    prefijo_local: str                # etiquetas locales al archivo
    seccion_textos: str
    directivas_main: Tuple[str, ...]
    directivas_fin: Tuple[str, ...]
    # Registros que el generador puede asignar a variables
    conservados: Tuple[str, ...]      # sobreviven a una llamada
    no_conservados: Tuple[str, ...]   # una llamada los destruye
    decimales: Tuple[str, ...]        # xmm (una llamada los destruye)
    opciones_enlazador: Tuple[str, ...] = ()
    salida_por_defecto: str = "run"

    def simbolo(self, nombre: str) -> str:
        return self.prefijo_simbolo + nombre

    def llamada(self, funcion: str) -> str:
        """Llamada a una función de la biblioteca de C."""
        return f"call {self.simbolo(funcion)}{self.sufijo_llamada}"

    def local(self, nombre: str) -> str:
        return self.prefijo_local + nombre


_ENTEROS_CONSERVADOS = ("rbx", "r12", "r13", "r14", "r15")
_ENTEROS_NO_CONSERVADOS = ("r8", "r9", "r10", "r11")

LINUX = Plataforma(
    nombre="linux",
    argumentos=("rdi", "rsi", "rdx", "rcx", "r8", "r9"),
    espacio_sombra=0,
    prefijo_simbolo="",
    sufijo_llamada="@PLT",
    prefijo_local=".L",
    seccion_textos=".section .rodata",
    directivas_main=(".globl main", ".type main, @function"),
    # La pila del programa no necesita ser ejecutable
    directivas_fin=(".size main, .-main",
                    '.section .note.GNU-stack,"",@progbits'),
    conservados=_ENTEROS_CONSERVADOS,
    no_conservados=_ENTEROS_NO_CONSERVADOS,
    decimales=tuple(f"xmm{i}" for i in range(2, 16)),
)

MACOS = Plataforma(
    nombre="macos",
    argumentos=LINUX.argumentos,       # misma convención (System V)
    espacio_sombra=0,
    prefijo_simbolo="_",
    sufijo_llamada="",
    prefijo_local="L",
    seccion_textos=".section __TEXT,__cstring,cstring_literals",
    directivas_main=(".globl _main",),
    directivas_fin=(),
    conservados=_ENTEROS_CONSERVADOS,
    no_conservados=_ENTEROS_NO_CONSERVADOS,
    decimales=LINUX.decimales,
    opciones_enlazador=("-arch", "x86_64"),
)

WINDOWS = Plataforma(
    nombre="windows",
    argumentos=("rcx", "rdx", "r8", "r9"),
    espacio_sombra=32,
    prefijo_simbolo="",
    sufijo_llamada="",
    prefijo_local=".L",
    seccion_textos='.section .rdata,"dr"',
    directivas_main=(".globl main",
                     ".def main; .scl 2; .type 32; .endef"),
    directivas_fin=(),
    conservados=_ENTEROS_CONSERVADOS,
    no_conservados=_ENTEROS_NO_CONSERVADOS,
    # xmm6 a xmm15 se conservan en Windows: guardarlos costaría 16 bytes
    # cada uno, así que no se usan.
    decimales=("xmm2", "xmm3", "xmm4", "xmm5"),
    salida_por_defecto="run.exe",
)

PLATAFORMAS = {p.nombre: p for p in (LINUX, MACOS, WINDOWS)}


def plataforma_actual() -> Optional[Plataforma]:
    """Plataforma en la que se ejecuta el compilador, o None si no está
    soportada."""
    sistema = _sistema.system()
    maquina = _sistema.machine().lower()
    if sistema == "Darwin":
        return MACOS            # x86-64 nativo o con Rosetta 2
    if maquina not in ("x86_64", "amd64"):
        return None
    return {"Linux": LINUX, "Windows": WINDOWS}.get(sistema)


# ----------------------------------------------------------------------
# Funciones auxiliares que se agregan al programa cuando se usan
# ----------------------------------------------------------------------
def ayudante_concatenar(p: Plataforma) -> List[str]:
    """awi_concatenar(a, b) -> a + b: reserva memoria con malloc y copia
    los dos textos."""
    a, b = p.argumentos[0], p.argumentos[1]
    sombra = p.espacio_sombra
    lineas = [
        "# awi_concatenar(a, b): devuelve en rax un texto nuevo a + b",
        "awi_concatenar:",
        "    push rbx",
        "    push r12",
        "    push r13",
    ]
    if sombra:
        lineas.append(f"    sub rsp, {sombra}")
    lineas += [
        f"    mov rbx, {a}",
        f"    mov r12, {b}",
        f"    {p.llamada('strlen')}",
        "    mov r13, rax",
        f"    mov {a}, r12",
        f"    {p.llamada('strlen')}",
        f"    lea {a}, [r13 + rax + 1]",
        f"    {p.llamada('malloc')}",
        f"    mov {a}, rax",
        f"    mov {b}, rbx",
        f"    {p.llamada('strcpy')}",
        f"    mov {a}, rax",
        f"    mov {b}, r12",
        f"    {p.llamada('strcat')}",
    ]
    if sombra:
        lineas.append(f"    add rsp, {sombra}")
    return lineas + ["    pop r13", "    pop r12", "    pop rbx", "    ret"]


# Bytes UTF-8 de un código de carácter: (desplazamiento, máscara, prefijo)
_UTF8 = {
    2: [(6, 0x1F, 0xC0), (0, 0x3F, 0x80)],
    3: [(12, 0x0F, 0xE0), (6, 0x3F, 0x80), (0, 0x3F, 0x80)],
    4: [(18, 0x07, 0xF0), (12, 0x3F, 0x80), (6, 0x3F, 0x80),
        (0, 0x3F, 0x80)],
}
_LIMITES_UTF8 = {2: 0x800, 3: 0x10000}


def _bytes_utf8(cantidad: int, base: int) -> List[str]:
    lineas = []
    for i, (desplazamiento, mascara, prefijo) in enumerate(
            _UTF8[cantidad]):
        lineas.append("    mov r10, rax")
        if desplazamiento:
            lineas.append(f"    shr r10, {desplazamiento}")
        lineas += [f"    and r10, {mascara:#x}",
                   f"    or r10, {prefijo:#x}",
                   f"    mov BYTE PTR [rsp + {base + i}], r10b"]
    lineas.append(f"    mov BYTE PTR [rsp + {base + cantidad}], 0")
    return lineas


def ayudante_imprimir_caracter(p: Plataforma, formato_texto: str
                               ) -> List[str]:
    """awi_imprimir_caracter(c): imprime el carácter de código c en
    UTF-8. Si es ASCII basta con putchar; si no, se arman sus 2 a 4 bytes
    en la pila y se imprimen con printf("%s")."""
    a, b = p.argumentos[0], p.argumentos[1]
    base = p.espacio_sombra                 # el texto va sobre la sombra
    pila = 24 + p.espacio_sombra            # mantiene rsp alineado a 16
    imprimir, fin = p.local("car_imprimir"), p.local("car_fin")
    lineas = [
        "# awi_imprimir_caracter(c): imprime el carácter c en UTF-8",
        "awi_imprimir_caracter:",
        f"    sub rsp, {pila}",
        f"    mov rax, {a}",
        "    cmp rax, 0x80",
        f"    jae {p.local('car_2')}",
        f"    {p.llamada('putchar')}",
        f"    jmp {fin}",
    ]
    for cantidad in (2, 3, 4):
        lineas.append(f"{p.local(f'car_{cantidad}')}:")
        if cantidad in _LIMITES_UTF8:
            lineas += [f"    cmp rax, {_LIMITES_UTF8[cantidad]:#x}",
                       f"    jae {p.local(f'car_{cantidad + 1}')}"]
        lineas += _bytes_utf8(cantidad, base)
        if cantidad != 4:
            lineas.append(f"    jmp {imprimir}")
    lineas += [
        f"{imprimir}:",
        f"    lea {b}, [rsp + {base}]",
        f"    lea {a}, [rip + {formato_texto}]",
        "    xor eax, eax",
        f"    {p.llamada('printf')}",
        f"{fin}:",
        f"    add rsp, {pila}",
        "    ret",
    ]
    return lineas
