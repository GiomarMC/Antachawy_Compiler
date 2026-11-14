"""
Generación de código objetivo: ensamblador x86-64 (Libro del Dragón,
capítulo 8; organización de la memoria, capítulo 7).

Máquina objetivo
    Procesador x86-64, sintaxis Intel del ensamblador de GNU. Las
    diferencias entre Linux, macOS y Windows están en plataformas.py.
    Para imprimir se usan printf y putchar de la biblioteca de C.

Registro de activación (sección 7.2)
    Todo el programa es la función main. Las variables que alguna vez
    deben estar en memoria tienen un lugar fijo de 8 bytes en la pila,
    a una distancia conocida de rbp ([rbp - 8], [rbp - 16]...). Ahí
    también se guardan los registros que main debe conservar.

Representación de los valores
    yupay       entero con signo de 64 bits
    chunkayuq   decimal de 64 bits (double), en registros xmm
    sananpa     código Unicode del carácter (se imprime en UTF-8)
    bool        0 o 1
    qaytu       dirección de un texto UTF-8 terminado en 0

Asignación de registros (sección 8.6)
    El generador recorre cada bloque básico llevando dos descriptores:

    * descriptor de registros: qué variables tienen su valor actual en
      cada registro;
    * descriptor de direcciones: dónde está el valor actual de cada
      variable (en memoria, en uno o más registros).

    Para `x = y op z`, getReg elige un registro para x: el de y si y ya
    no se usa después (así `add` trabaja sobre él), uno libre, o el que
    menos guardados en memoria cueste. Una copia `x = y` no genera código:
    solo anota que x también está en el registro de y.

    Al terminar un bloque se guardan en memoria las variables que siguen
    vivas (análisis de variables vivas, sección 9.2.5) y solo están en un
    registro. Lo mismo se hace antes de llamar a una función de C con los
    registros que esa llamada destruye.

Asignación global de registros (sección 8.8.2)
    Antes de lo anterior, las variables enteras que pasan de un bloque a
    otro y más se usan (cada uso dentro de un bucle cuenta 10 veces)
    reciben un registro fijo para todo el programa (rbx, r12, r13). Esos
    registros sobreviven a las llamadas, así que esas variables nunca se
    guardan en memoria.
"""
from __future__ import annotations

import struct
from typing import Dict, List, Optional, Set

from antachawi.bloques_basicos import particionar
from antachawi.intermedio import (
    A_CHUNKAYUQ,
    ARITMETICOS,
    COPIA,
    ETIQUETA,
    LLAMADA,
    MENOS,
    PARAMETRO,
    RELACIONALES,
    SALTO,
    SALTOS_RELACIONALES,
    SI,
    SI_NO,
    Constante,
    Cuadrupla,
    es_variable,
    relacion,
)
from antachawi.optimizador import variables_vivas
from antachawi.plataformas import (
    LINUX,
    Plataforma,
    ayudante_concatenar,
    ayudante_imprimir_caracter,
)
from antachawi.tipos import BOOL, CHUNKAYUQ, QAYTU, SANANPA, YUPAY

TAMANO_PALABRA = 8
PAGINA = 4096
MEMORIA = "memoria"

# Sufijo de setcc / jcc para comparar enteros con signo
_CONDICION_ENTERA = {"<": "l", "<=": "le", ">": "g", ">=": "ge",
                     "==": "e", "!=": "ne"}
_INSTRUCCION_ENTERA = {"+": "add", "-": "sub", "*": "imul"}
_INSTRUCCION_DECIMAL = {"+": "addsd", "-": "subsd", "*": "mulsd",
                        "/": "divsd"}

# printf: %lld es un entero de 64 bits en las tres plataformas. Los
# decimales se imprimen con %g, igual que cout en C++.
_FORMATOS = {
    YUPAY: ("formato_yupay", "%lld"),
    BOOL: ("formato_yupay", "%lld"),
    CHUNKAYUQ: ("formato_chunkayuq", "%g"),
    QAYTU: ("formato_qaytu", "%s"),
}


def bits_de_decimal(valor: float) -> int:
    """Los 64 bits de un double, como entero con signo (para `mov`)."""
    return struct.unpack("<q", struct.pack("<d", valor))[0]


def texto_para_ensamblador(texto: str) -> str:
    """Texto para la directiva .asciz, con los bytes no imprimibles en
    octal."""
    partes = []
    for byte in texto.encode("utf-8"):
        if 32 <= byte < 127 and chr(byte) not in '"\\':
            partes.append(chr(byte))
        else:
            partes.append(f"\\{byte:03o}")
    return '"' + "".join(partes) + '"'


def valor_inmediato(constante: Constante) -> int:
    if constante.tipo == CHUNKAYUQ:
        return bits_de_decimal(constante.valor)
    if constante.tipo == SANANPA:
        return ord(constante.valor)
    return int(constante.valor)


def _cabe_en_32_bits(valor: int) -> bool:
    # La mayoría de instrucciones solo aceptan inmediatos de 32 bits
    return -2 ** 31 <= valor < 2 ** 31


def es_decimal(direccion) -> bool:
    return direccion.tipo == CHUNKAYUQ


def vivas_despues(bloque, vivas_al_salir: Set) -> List[Set]:
    """Variables vivas justo después de cada instrucción del bloque
    (la información de "siguiente uso" de la sección 8.4.2)."""
    vivas, resultado = set(vivas_al_salir), []
    for instruccion in reversed(bloque.instrucciones):
        resultado.append(set(vivas))
        vivas.discard(instruccion.definicion())
        vivas.update(instruccion.usos())
    return resultado[::-1]


# ----------------------------------------------------------------------
# Asignación global de registros (sección 8.8.2)
# ----------------------------------------------------------------------
REGISTROS_GLOBALES = 3
PESO_BUCLE = 10


def _pesos_por_bucle(codigo: List[Cuadrupla]) -> List[int]:
    """Peso de cada instrucción: 10 ** (cantidad de bucles que la
    contienen). Un bucle es un salto hacia una etiqueta anterior."""
    posicion = {c.resultado: i for i, c in enumerate(codigo)
                if c.op == ETIQUETA}
    profundidad = [0] * len(codigo)
    for j, instruccion in enumerate(codigo):
        inicio = posicion.get(instruccion.resultado, j + 1) \
            if instruccion.es_salto() else j + 1
        for i in range(inicio, j + 1):
            profundidad[i] += 1
    return [PESO_BUCLE ** p for p in profundidad]


def registros_globales(codigo: List[Cuadrupla], salida: Dict,
                       registros) -> Dict:
    """Variable -> registro fijo. Solo compiten las variables enteras
    que están vivas al salir de algún bloque (las demás se resuelven
    bien dentro de su bloque)."""
    candidatas = {v for vivas in salida.values() for v in vivas
                  if not es_decimal(v)}
    usos: Dict[object, int] = {}
    for instruccion, peso in zip(codigo, _pesos_por_bucle(codigo)):
        nombres = instruccion.usos() + [instruccion.definicion()]
        for variable in nombres:
            if variable in candidatas:
                usos[variable] = usos.get(variable, 0) + peso
    elegidas = sorted(usos, key=lambda v: (-usos[v], str(v)))
    return dict(zip(elegidas, registros))


# ----------------------------------------------------------------------
# Registro de activación
# ----------------------------------------------------------------------
class RegistroActivacion:
    """Lugares en la pila. Se asignan a medida que se necesitan: una
    variable que siempre vive en un registro no ocupa memoria."""

    def __init__(self, espacio_sombra: int = 0):
        self.desplazamientos: Dict[object, int] = {}
        self.espacio_sombra = espacio_sombra

    def lugar(self, clave) -> str:
        if clave not in self.desplazamientos:
            self.desplazamientos[clave] = TAMANO_PALABRA * (
                len(self.desplazamientos) + 1)
        return f"QWORD PTR [rbp - {self.desplazamientos[clave]}]"

    @property
    def tamano(self) -> int:
        """Bytes que se reservan; múltiplo de 16 porque la convención de
        llamadas exige rsp alineado a 16 antes de cada call."""
        total = TAMANO_PALABRA * len(self.desplazamientos)
        return (total + self.espacio_sombra + 15) // 16 * 16

    def describir(self) -> List[str]:
        lineas = []
        for clave, desplazamiento in self.desplazamientos.items():
            if isinstance(clave, str):
                descripcion = f"{clave} (registro conservado)"
            else:
                descripcion = f"{clave} : {clave.tipo}"
            lineas.append(f"#   [rbp - {desplazamiento:>3}]  {descripcion}")
        if self.espacio_sombra:
            lineas.append(f"#   [rsp + 0 .. {self.espacio_sombra - 1}]  "
                          "espacio de sombra para las llamadas")
        return lineas


# ----------------------------------------------------------------------
# Descriptores de registros y de direcciones (sección 8.6.1)
# ----------------------------------------------------------------------
class Descriptores:
    def __init__(self):
        self.registros: Dict[str, Set] = {}      # registro -> variables
        self.direcciones: Dict[object, Set] = {}  # variable -> lugares
        self.globales: Dict[object, str] = {}    # variable -> registro

    def reiniciar(self):
        """Al empezar un bloque, todos los valores están en memoria."""
        self.registros.clear()
        self.direcciones.clear()

    def lugares(self, variable) -> Set:
        if variable in self.globales:
            return {self.globales[variable]}
        return self.direcciones.get(variable, {MEMORIA})

    def registro_de(self, variable) -> Optional[str]:
        registros = sorted(self.lugares(variable) - {MEMORIA})
        return registros[0] if registros else None

    def en_registro(self, registro: str) -> Set:
        return self.registros.get(registro, set())

    def olvidar_registro(self, registro: str):
        for variable in self.registros.pop(registro, set()):
            self.direcciones[variable] = self.lugares(variable) - {registro}

    def cargado(self, variable, registro: str):
        """El registro ahora tiene (solo) el valor de la variable, que
        sigue también donde estaba."""
        self.olvidar_registro(registro)
        self.registros[registro] = {variable}
        self.direcciones[variable] = self.lugares(variable) | {registro}

    def guardado(self, variable):
        self.direcciones[variable] = self.lugares(variable) | {MEMORIA}

    def definido(self, variable, registro: str, copia: bool = False):
        """La variable recibió un valor nuevo, que solo está en el
        registro. Con copia=True el registro conserva lo que tenía
        (x = y: x e y comparten registro)."""
        for otro in self.lugares(variable) - {MEMORIA, registro}:
            self.registros.get(otro, set()).discard(variable)
        if not copia:
            self.olvidar_registro(registro)
        self.registros.setdefault(registro, set()).add(variable)
        self.direcciones[variable] = {registro}


class GeneradorX86:
    def __init__(self, codigo: List[Cuadrupla],
                 plataforma: Plataforma = LINUX):
        self.codigo = codigo
        self.p = plataforma
        self.registro = RegistroActivacion(plataforma.espacio_sombra)
        self.d = Descriptores()
        self.cuerpo: List[str] = []
        self.textos: Dict[str, str] = {}     # texto -> etiqueta
        self.formatos: Dict[str, str] = {}   # etiqueta -> formato
        self.conservados_usados: List[str] = []
        self.ayudantes: Set[str] = set()
        self.parametros = []
        self.vivas: Set = set()              # vivas tras la instrucción
        self._instrucciones = {
            COPIA: self._copia,
            MENOS: self._menos,
            A_CHUNKAYUQ: self._a_chunkayuq,
            SALTO: lambda c: self.emitir(f"jmp {self.etiqueta(c.resultado)}"),
            SI: lambda c: self._si(c, "jne"),
            SI_NO: lambda c: self._si(c, "je"),
            ETIQUETA: lambda c: self.cuerpo.append(
                f"{self.etiqueta(c.resultado)}:"),
            PARAMETRO: lambda c: self.parametros.append(c.arg1),
            LLAMADA: self._rikuchiy,
        }

    # ------------------------------------------------------------------
    # Programa completo
    # ------------------------------------------------------------------
    def generar(self) -> str:
        bloques = particionar(self.codigo)
        salida = variables_vivas(bloques)
        self.d.globales = registros_globales(
            self.codigo, salida, self.p.conservados[:REGISTROS_GLOBALES])
        for registro in self.d.globales.values():
            self._usar_conservado(registro)
        for bloque in bloques:
            self._bloque(bloque, salida[bloque])
        cuerpo = self.cuerpo
        self.cuerpo = []
        self._prologo()
        self.cuerpo += cuerpo
        self._epilogo()
        return "\n".join(self.cuerpo) + "\n"

    def _bloque(self, bloque, vivas_al_salir: Set):
        self.d.reiniciar()
        vivas = vivas_despues(bloque, vivas_al_salir)
        for i, instruccion in enumerate(bloque.instrucciones):
            self.vivas = vivas[i]
            if instruccion.op != ETIQUETA:
                # "# |": en macOS el ensamblador pasa por el preprocesador
                # de C, que tomaría "# if ..." como la directiva #if
                self.cuerpo.append(f"    # | {instruccion}")
            if instruccion.es_salto():
                self._guardar_vivas(vivas_al_salir)
            self._traducir(instruccion)
        ultima = bloque.ultima
        if ultima is None or not ultima.es_salto():
            self._guardar_vivas(vivas_al_salir)

    def _prologo(self):
        main = self.p.simbolo("main")
        for registro in self.conservados_usados:
            self.registro.lugar(registro)       # su lugar para guardarlo
        self.cuerpo += [
            "# Generado por el compilador de Antachawi "
            f"(x86-64, {self.p.nombre})",
            "    .intel_syntax noprefix",
            "    .text",
            *(f"    {d}" for d in self.p.directivas_main),
            "",
            "# Registro de activación de main:",
            *self.registro.describir(),
            "# Variables con registro fijo:",
            *(f"#   {r}  {v} : {v.tipo}"
              for v, r in self.d.globales.items()),
            f"{main}:",
            "    push rbp",
            "    mov rbp, rsp",
        ]
        self._reservar_pila(self.registro.tamano)
        for registro in self.conservados_usados:
            self.emitir(f"mov {self.registro.lugar(registro)}, {registro}")

    def _reservar_pila(self, tamano: int):
        if tamano >= PAGINA and self.p.espacio_sombra:
            # Windows solo agranda la pila de a una página: hay que
            # tocarlas en orden (lo mismo que hace gcc con MinGW)
            self.emitir(f"mov rax, {tamano}")
            self.llamar("___chkstk_ms")
            self.emitir("sub rsp, rax")
        elif tamano:
            self.emitir(f"sub rsp, {tamano}")

    def _epilogo(self):
        self.cuerpo.append("    # fin de qhapaq: return 0")
        for registro in self.conservados_usados:
            self.emitir(f"mov {registro}, {self.registro.lugar(registro)}")
        self.cuerpo += ["    xor eax, eax", "    leave", "    ret",
                        *(f"    {d}" for d in self.p.directivas_fin
                          if not d.startswith(".section"))]
        if "concatenar" in self.ayudantes:
            self.cuerpo += ["", *ayudante_concatenar(self.p)]
        if "caracter" in self.ayudantes:
            self.cuerpo += ["", *ayudante_imprimir_caracter(
                self.p, self._formato(QAYTU))]
        self.cuerpo += ["", f"    {self.p.seccion_textos}"]
        datos = list(self.formatos.items()) + [
            (etiqueta, texto) for texto, etiqueta in self.textos.items()]
        for etiqueta, texto in datos:
            self.cuerpo += [f"{etiqueta}:",
                            f"    .asciz {texto_para_ensamblador(texto)}"]
        self.cuerpo += [f"    {d}" for d in self.p.directivas_fin
                        if d.startswith(".section")]

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def emitir(self, instruccion: str):
        self.cuerpo.append(f"    {instruccion}")

    def etiqueta(self, nombre: str) -> str:
        return self.p.local(nombre)

    def _texto(self, texto: str) -> str:
        if texto not in self.textos:
            self.textos[texto] = self.p.local(f"texto{len(self.textos)}")
        return self.textos[texto]

    def _formato(self, tipo: str) -> str:
        nombre, formato = _FORMATOS[tipo]
        etiqueta = self.p.local(nombre)
        self.formatos[etiqueta] = formato
        return etiqueta

    def _memoria(self, variable) -> str:
        return self.registro.lugar(variable)

    # ------------------------------------------------------------------
    # Cargar y guardar
    # ------------------------------------------------------------------
    def cargar_en(self, registro: str, direccion):
        """Copia un valor a un registro (de los que no se asignan a
        variables: rax, argumentos, xmm0, xmm1) o a uno elegido por
        getReg."""
        if registro.startswith("xmm"):
            self._cargar_en_xmm(registro, direccion)
        elif isinstance(direccion, Constante):
            if direccion.tipo == QAYTU:
                texto = self._texto(direccion.valor)
                self.emitir(f"lea {registro}, [rip + {texto}]")
            else:
                self.emitir(f"mov {registro}, {valor_inmediato(direccion)}")
        else:
            origen = self.d.registro_de(direccion) or self._memoria(
                direccion)
            if origen != registro:
                instruccion = "movq" if origen.startswith("xmm") else "mov"
                self.emitir(f"{instruccion} {registro}, {origen}")

    def _cargar_en_xmm(self, registro: str, direccion):
        if isinstance(direccion, Constante):
            self.emitir(f"mov rax, {valor_inmediato(direccion)}")
            self.emitir(f"movq {registro}, rax")
            return
        origen = self.d.registro_de(direccion) or self._memoria(direccion)
        if origen != registro:
            self.emitir(f"movsd {registro}, {origen}")

    def operando(self, direccion, auxiliar: str) -> str:
        """Operando fuente de una instrucción: registro, memoria o
        inmediato. Si no se puede usar directamente se carga en
        `auxiliar`."""
        if es_variable(direccion):
            return self.d.registro_de(direccion) or self._memoria(direccion)
        if (not auxiliar.startswith("xmm") and direccion.tipo != QAYTU
                and _cabe_en_32_bits(valor_inmediato(direccion))):
            return str(valor_inmediato(direccion))
        self.cargar_en(auxiliar, direccion)
        return auxiliar

    def guardar(self, variable):
        """Copia a memoria el valor de una variable que solo está en un
        registro."""
        if MEMORIA in self.d.lugares(variable) \
                or variable in self.d.globales:
            return
        registro = self.d.registro_de(variable)
        instruccion = "movsd" if registro.startswith("xmm") else "mov"
        self.emitir(f"{instruccion} {self._memoria(variable)}, {registro}")
        self.d.guardado(variable)

    def _guardar_vivas(self, vivas: Set):
        for registro in sorted(self.d.registros):
            for variable in sorted(self.d.en_registro(registro), key=str):
                if variable in vivas:
                    self.guardar(variable)

    def antes_de_llamar(self, vivas: Set):
        """Una llamada destruye los registros no conservados y los xmm:
        se guardan los valores que se necesitan después."""
        for registro in self.p.no_conservados + self.p.decimales:
            for variable in sorted(self.d.en_registro(registro), key=str):
                if variable in vivas:
                    self.guardar(variable)
            self.d.olvidar_registro(registro)

    def llamar(self, funcion: str):
        self.emitir(self.p.llamada(funcion))

    # ------------------------------------------------------------------
    # getReg (sección 8.6.2)
    # ------------------------------------------------------------------
    def _registros_de_clase(self, decimal: bool):
        if decimal:
            return self.p.decimales
        fijos = set(self.d.globales.values())
        return tuple(r for r in self.p.conservados + self.p.no_conservados
                     if r not in fijos)

    def _usar_conservado(self, registro: str):
        """main debe devolver los registros conservados como los
        recibió: se guardan en el prólogo y se restauran al final."""
        if registro in self.p.conservados \
                and registro not in self.conservados_usados:
            self.conservados_usados.append(registro)

    def definir(self, variable, registro: str):
        """El valor nuevo de la variable está en `registro`."""
        fijo = self.d.globales.get(variable)
        if fijo is None:
            self.d.definido(variable, registro)
        elif fijo != registro:
            self.emitir(f"mov {fijo}, {registro}")

    def _costo(self, registro: str, destino) -> int:
        """Cuántos valores habría que guardar en memoria para usar este
        registro: los que siguen vivos y no están en otro lugar."""
        return sum(1 for v in self.d.en_registro(registro)
                   if v != destino and v in self.vivas
                   and self.d.lugares(v) == {registro})

    def obtener_registro(self, decimal: bool, evitar=(), destino=None):
        candidatos = [r for r in self._registros_de_clase(decimal)
                      if r not in evitar]
        # Primero los libres; luego el que menos guardados cueste
        elegido = min(candidatos, key=lambda r: (
            self._costo(r, destino), len(self.d.en_registro(r))))
        for variable in sorted(self.d.en_registro(elegido), key=str):
            if variable != destino and variable in self.vivas:
                self.guardar(variable)
        self.d.olvidar_registro(elegido)
        self._usar_conservado(elegido)
        return elegido

    def _registro_para_resultado(self, c: Cuadrupla, decimal: bool) -> str:
        """Registro para x en x = y op z con el valor de y ya cargado:
        el de y si y ya no hace falta allí, o uno nuevo con una copia."""
        y, z, x = c.arg1, c.arg2, c.resultado
        if x in self.d.globales:
            return self._registro_para_global(y, z, x)
        registro_y = self.d.registro_de(y) if es_variable(y) else None
        if (registro_y is not None and self._costo(registro_y, x) == 0
                and (y == x or y not in self.vivas)):
            return registro_y
        evitar = {registro_y}
        if es_variable(z):
            evitar.add(self.d.registro_de(z))
        registro = self.obtener_registro(decimal, evitar, x)
        self.cargar_en(registro, y)
        return registro

    def _registro_para_global(self, y, z, x) -> str:
        fijo = self.d.globales[x]
        if y == x:
            return fijo                     # x = x op z: en el mismo lugar
        if z == x:
            # x = y op x: cargar y en el registro de x destruiría a x
            self.cargar_en("rax", y)
            return "rax"
        self.cargar_en(fijo, y)
        return fijo

    # ------------------------------------------------------------------
    # Traducción de cada instrucción
    # ------------------------------------------------------------------
    def _traducir(self, instruccion: Cuadrupla):
        op = instruccion.op
        if op in ARITMETICOS:
            self._aritmetica(instruccion)
        elif op in RELACIONALES:
            self._relacional(instruccion)
        elif op in SALTOS_RELACIONALES:
            self._salto_relacional(instruccion)
        else:
            self._instrucciones[op](instruccion)

    def _copia(self, c: Cuadrupla):
        y, x = c.arg1, c.resultado
        if y == x:
            return
        if x in self.d.globales:
            self.cargar_en(self.d.globales[x], y)
            return
        registro = self.d.registro_de(y) if es_variable(y) else None
        if y in self.d.globales:
            registro = None     # un registro fijo no se comparte
        if registro is None:
            registro = self.obtener_registro(es_decimal(x), destino=x)
            self.cargar_en(registro, y)
            if es_variable(y):
                self.d.cargado(y, registro)
        self.d.definido(x, registro, copia=es_variable(y))

    def _menos(self, c: Cuadrupla):
        registro = self._registro_para_resultado(c, es_decimal(c.resultado))
        if es_decimal(c.resultado):
            # Se cambia el bit de signo
            self.emitir(f"movq rax, {registro}")
            self.emitir("btc rax, 63")
            self.emitir(f"movq {registro}, rax")
        else:
            self.emitir(f"neg {registro}")
        self.definir(c.resultado, registro)

    def _a_chunkayuq(self, c: Cuadrupla):
        origen = self.operando(c.arg1, "rax")
        if origen.lstrip("-").isdigit():
            self.cargar_en("rax", c.arg1)
            origen = "rax"
        registro = self.obtener_registro(True, destino=c.resultado)
        self.emitir(f"cvtsi2sd {registro}, {origen}")
        self.definir(c.resultado, registro)

    def _aritmetica(self, c: Cuadrupla):
        tipo = c.resultado.tipo
        if tipo == QAYTU:
            self._concatenar(c)
        elif tipo == CHUNKAYUQ:
            registro = self._registro_para_resultado(c, True)
            origen = self.operando(c.arg2, "xmm1")
            self.emitir(f"{_INSTRUCCION_DECIMAL[c.op]} {registro}, {origen}")
            self.definir(c.resultado, registro)
        elif c.op == "/":
            self._division(c)
        else:
            registro = self._registro_para_resultado(c, False)
            origen = self.operando(c.arg2, "rcx")
            self.emitir(f"{_INSTRUCCION_ENTERA[c.op]} {registro}, {origen}")
            self.definir(c.resultado, registro)

    def _division(self, c: Cuadrupla):
        # idiv divide rdx:rax; el cociente queda en rax
        self.cargar_en("rax", c.arg1)
        self.emitir("cqo")
        divisor = self.operando(c.arg2, "rcx")
        if divisor.lstrip("-").isdigit():
            self.emitir(f"mov rcx, {divisor}")
            divisor = "rcx"
        self.emitir(f"idiv {divisor}")
        self._resultado_en_rax(c.resultado)

    def _resultado_en_rax(self, destino):
        if destino in self.d.globales:
            self.definir(destino, "rax")
            return
        registro = self.obtener_registro(False, destino=destino)
        self.emitir(f"mov {registro}, rax")
        self.d.definido(destino, registro)

    def _concatenar(self, c: Cuadrupla):
        self.ayudantes.add("concatenar")
        self.cargar_en(self.p.argumentos[0], c.arg1)
        self.cargar_en(self.p.argumentos[1], c.arg2)
        self.antes_de_llamar(self.vivas)
        self.emitir("call awi_concatenar")
        self._resultado_en_rax(c.resultado)

    # ------------------------------------------------------------------
    # Comparaciones
    # ------------------------------------------------------------------
    def comparar(self, operador: str, a, b) -> Optional[str]:
        """Compara a y b. Devuelve el sufijo de condición para setcc/jcc
        o, con decimales, None y deja el resultado (0 o 1) en rax."""
        if a.tipo == CHUNKAYUQ:
            self._comparar_decimales(operador, a, b)
            return None
        if a.tipo == QAYTU:
            self.cargar_en(self.p.argumentos[0], a)
            self.cargar_en(self.p.argumentos[1], b)
            self.antes_de_llamar(self.vivas | {v for v in (a, b)
                                               if es_variable(v)})
            self.llamar("strcmp")
            self.emitir("cmp eax, 0")
        else:
            izquierdo = self.d.registro_de(a) if es_variable(a) else None
            if izquierdo is None:
                self.cargar_en("rax", a)
                izquierdo = "rax"
            self.emitir(f"cmp {izquierdo}, {self.operando(b, 'rcx')}")
        return _CONDICION_ENTERA[operador]

    def _comparar_decimales(self, operador: str, a, b):
        """ucomisd marca 'sin orden' si algún valor es NaN; las
        condiciones 'a' y 'ae' (above) son falsas en ese caso, por eso
        a < b se calcula como b > a."""
        if operador in ("<", "<="):
            a, b = b, a
        self.cargar_en("xmm0", a)
        self.emitir(f"ucomisd xmm0, {self.operando(b, 'xmm1')}")
        if operador in ("==", "!="):
            igual = operador == "=="
            self.emitir("sete al" if igual else "setne al")
            self.emitir("setnp cl" if igual else "setp cl")
            self.emitir("and al, cl" if igual else "or al, cl")
        else:
            self.emitir("seta al" if operador in ("<", ">") else "setae al")
        self.emitir("movzx eax, al")

    def _relacional(self, c: Cuadrupla):
        condicion = self.comparar(c.op, c.arg1, c.arg2)
        if condicion is not None:
            self.emitir(f"set{condicion} al")
            self.emitir("movzx eax, al")
        self._resultado_en_rax(c.resultado)

    def _salto_relacional(self, c: Cuadrupla):
        condicion = self.comparar(relacion(c.op), c.arg1, c.arg2)
        destino = self.etiqueta(c.resultado)
        if condicion is None:
            self.emitir("test rax, rax")
            self.emitir(f"jne {destino}")
        else:
            self.emitir(f"j{condicion} {destino}")

    def _si(self, c: Cuadrupla, salto: str):
        registro = self.d.registro_de(c.arg1) if es_variable(c.arg1) \
            else None
        if registro is None:
            self.cargar_en("rax", c.arg1)
            registro = "rax"
        self.emitir(f"test {registro}, {registro}")
        self.emitir(f"{salto} {self.etiqueta(c.resultado)}")

    # ------------------------------------------------------------------
    # rikuchiy: una llamada por argumento y al final un salto de línea
    # ------------------------------------------------------------------
    def _rikuchiy(self, c: Cuadrupla):
        cantidad = c.arg2
        argumentos = self.parametros[len(self.parametros) - cantidad:]
        del self.parametros[len(self.parametros) - cantidad:]
        self.antes_de_llamar(self.vivas | {a for a in argumentos
                                           if es_variable(a)})
        for argumento in argumentos:
            self._imprimir(argumento)
        self.emitir(f"mov {self.p.argumentos[0]}, 10")      # '\n'
        self.llamar("putchar")

    def _imprimir(self, argumento):
        primero, segundo = self.p.argumentos[0], self.p.argumentos[1]
        if argumento.tipo == SANANPA:
            self.ayudantes.add("caracter")
            self.cargar_en(primero, argumento)
            self.emitir("call awi_imprimir_caracter")
            return
        if argumento.tipo == CHUNKAYUQ:
            self._decimal_para_printf(argumento)
        else:
            self.cargar_en(segundo, argumento)
            self.emitir("xor eax, eax")
        self.emitir(f"lea {primero}, [rip + {self._formato(argumento.tipo)}]")
        self.llamar("printf")

    def _decimal_para_printf(self, argumento):
        if self.p.espacio_sombra:
            # Windows: en funciones con argumentos variables el decimal
            # va en xmm1 y también en rdx
            self.cargar_en("xmm1", argumento)
            self.emitir(f"movq {self.p.argumentos[1]}, xmm1")
        else:
            # System V: en xmm0; al indica cuántos xmm se usan
            self.cargar_en("xmm0", argumento)
            self.emitir("mov eax, 1")


def generar_ensamblador(codigo: List[Cuadrupla],
                        plataforma: Plataforma = LINUX) -> str:
    return GeneradorX86(codigo, plataforma).generar()
