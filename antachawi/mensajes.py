"""
Catálogo de todos los mensajes del compilador, en español y en quechua.

Cada mensaje tiene un código que no cambia (LEX001, SIN001, SEM001...),
así un IDE, la documentación o una búsqueda en internet pueden referirse
a él sin importar el idioma en que se muestre.

    LEX  errores léxicos          SEM  errores semánticos
    SIN  errores sintácticos      ADV  advertencias
    EJE  errores de ejecución     CON  textos de la consola
    IDE  textos del entorno gráfico (antachawi/ide) y de Tunki

Traducción al quechua
    `qu=None` significa PENDIENTE DE TRADUCCIÓN: mientras tanto se muestra
    el texto en español. Para traducir basta con escribir el texto en `qu`
    respetando los nombres entre llaves ({nombre}, {tipo}...); la prueba
    tests/test_mensajes.py verifica que coincidan con los del español.
    `pendientes_de_traduccion()` lista lo que falta.

    También se puede traducir SIN tocar este archivo, llenando la columna
    "quechua" de antachawi/traducciones/quechua.csv (se abre con
    LibreOffice Calc o Excel). Lo que esté en esa hoja tiene prioridad y se
    carga al importar este módulo. Ver antachawi/traducciones/LEEME.md.
"""
from __future__ import annotations

import csv
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

ES = "es"
QU = "qu"
IDIOMAS = (ES, QU)
AMBOS = "ambos"         # en la consola: español y, debajo, quechua

ERROR = "error"
ADVERTENCIA = "advertencia"

_FASES = {
    "LEX": "lexico",
    "SIN": "sintactico",
    "SEM": "semantico",
    "ADV": "semantico",
    "EJE": "ejecucion",
    "CON": "consola",
    "IDE": "ide",
}


@dataclass(frozen=True)
class Mensaje:
    codigo: str
    es: str
    qu: Optional[str] = None        # None: pendiente de traducción

    @property
    def fase(self) -> str:
        return _FASES[self.codigo[:3]]

    @property
    def gravedad(self) -> str:
        return ADVERTENCIA if self.codigo.startswith("ADV") else ERROR

    @property
    def traducido(self) -> bool:
        return self.qu is not None

    def plantilla(self, idioma: str = ES) -> str:
        """Texto sin completar; si falta la traducción, el del español."""
        if idioma == QU and self.qu is not None:
            return self.qu
        return self.es

    def texto(self, idioma: str = ES, **parametros) -> str:
        return self.plantilla(idioma).format(**parametros)

    def textos(self, **parametros) -> Dict[str, Optional[str]]:
        """{"es": ..., "qu": ...}; "qu" es None si falta la traducción."""
        return {
            ES: self.es.format(**parametros),
            QU: self.qu.format(**parametros) if self.qu else None,
        }


def campos(plantilla: str) -> set:
    """Nombres entre llaves de una plantilla: "{a} y {b}" -> {"a", "b"}."""
    return {nombre for _, nombre, _, _ in string.Formatter().parse(plantilla)
            if nombre}


# ----------------------------------------------------------------------
# Textos de la consola
# ----------------------------------------------------------------------
TITULO_ERRORES = Mensaje(
    "CON001", "Errores de compilación", "Pantachakuna ruwanakusqapi")
ENCABEZADO_ERROR = Mensaje(
    "CON002", "Error {codigo} en {ubicacion}: ",
    "Pantachay {codigo} {ubicacion} siq'isqapi: ")
TITULO_ADVERTENCIAS = Mensaje("CON003", "Advertencias")
ENCABEZADO_ADVERTENCIA = Mensaje(
    "CON004", "Advertencia {codigo} en {ubicacion}: ")

# ----------------------------------------------------------------------
# Errores léxicos
# ----------------------------------------------------------------------
COMENTARIO_SIN_CERRAR = Mensaje(
    "LEX001",
    "el comentario que empieza aquí nunca se cierra; falta '*:'.",
    "k'utu qillqa mana tukusqa chay ñiqin líniapi.")
CADENA_SIN_CERRAR = Mensaje(
    "LEX002",
    "el texto no se cerró: falta la comilla doble (\") al final de "
    "la línea.",
    "qillqa ch’usaq simincha mana tukusqa chay ñiqin líniapi.")
CARACTER_LARGO = Mensaje(
    "LEX003",
    "un 'sananpa' solo puede tener un carácter; para un texto usa "
    "comillas dobles (\"...\").",
    "achkha uqalla qillqa ch’usaq uqallapi.")
CARACTER_SIN_CERRAR = Mensaje(
    "LEX004",
    "el carácter no se cerró: falta la comilla simple (').",
    "qillqa ch’usaq uqalla mana tukusqa chay ñiqin líniapi.")
VARIOS_PUNTOS = Mensaje(
    "LEX005",
    "un número decimal solo puede tener un punto.",
    "t’aqraq yupay punchu hukman aswan tiyachisqa.")
NUMERO_CON_LETRAS = Mensaje(
    "LEX006",
    "un número no puede tener letras; si es un nombre de variable, debe "
    "empezar con una letra.",
    "yupay qatiq mana hayñisqa uqallawan.")
SIMBOLO_DESCONOCIDO = Mensaje(
    "LEX007",
    "este símbolo no pertenece al lenguaje.",
    "uqalla mana riqsisqa.")
CARACTER_VACIO = Mensaje(
    "LEX008", "un carácter no puede estar vacío: ''.")
ESCAPE_INVALIDO = Mensaje(
    "LEX009",
    "secuencia de escape no válida: '{secuencia}'. Las válidas son "
    "\\n, \\t, \\r, \\0, \\\\, \\' y \\\".")

# ----------------------------------------------------------------------
# Errores sintácticos
# ----------------------------------------------------------------------
TOKEN_INESPERADO = Mensaje(
    "SIN001",
    "se encontró '{encontrado}', pero se esperaba {esperado}.",
    "'{encontrado}' tariqchasqa, ichaqa {esperado} suyaywasqa.")

# ----------------------------------------------------------------------
# Errores semánticos
# ----------------------------------------------------------------------
TIPOS_INCOMPATIBLES = Mensaje(
    "SEM001",
    "no se puede usar '{operador}' entre un valor '{izquierdo}' y uno "
    "'{derecho}'.",
    "mana atisqa ruwanakuy '{izquierdo}' hina '{derecho}'wan.")
ASIGNACION_INCOMPATIBLE = Mensaje(
    "SEM002",
    "la variable '{nombre}' es de tipo '{tipo}', pero el valor que se le "
    "da es '{tipo_expresion}'.",
    "t’ukupa '{nombre}'qa '{tipo}' ruwasqa, ichaqa kay rimanakuyqa "
    "'{tipo_expresion}' ruwasqa.")
ASIGNAR_NO_DECLARADA = Mensaje(
    "SEM003",
    "la variable '{nombre}' no fue declarada; declárala antes con su "
    "tipo, por ejemplo: yupay {nombre} = 0.",
    "t’ukupa '{nombre}' mana willaykusqa.")
USAR_NO_DECLARADA = Mensaje(
    "SEM004",
    "la variable '{nombre}' no fue declarada.",
    "variable '{nombre}' mana churakusqa.")
VARIABLE_REDECLARADA = Mensaje(
    "SEM005",
    "la variable '{nombre}' ya fue declarada en este bloque "
    "(línea {linea}).")
VARIABLE_OCULTA = Mensaje(
    "SEM006",
    "la variable '{nombre}' ya existe en un bloque exterior "
    "(línea {linea}); usa otro nombre.")
CONDICION_NO_BOOL = Mensaje(
    "SEM007",
    "la condición debe ser de tipo 'bool', pero es '{tipo}'.")
OPERADOR_LOGICO_NO_BOOL = Mensaje(
    "SEM008",
    "el operador '{operador}' necesita operandos 'bool', pero recibió "
    "'{izquierdo}' y '{derecho}'.")
OPERADOR_UNARIO_INVALIDO = Mensaje(
    "SEM009",
    "el operador '{operador}' no se puede aplicar a un valor '{tipo}'.")

# ----------------------------------------------------------------------
# Advertencias (no detienen la compilación)
# ----------------------------------------------------------------------
VARIABLE_NO_USADA = Mensaje(
    "ADV001", "la variable '{nombre}' se declara pero nunca se usa.")
VARIABLE_SIN_VALOR = Mensaje(
    "ADV002",
    "la variable '{nombre}' podría usarse sin tener un valor asignado.")
DIVISION_ENTRE_CERO = Mensaje("ADV003", "división entre cero.")

# ----------------------------------------------------------------------
# Errores de ejecución (los detecta el intérprete, antachawi/interprete.py)
# ----------------------------------------------------------------------
EJECUCION_DIVISION_ENTRE_CERO = Mensaje(
    "EJE001", "el programa intentó dividir entre cero.")
EJECUCION_SIN_FIN = Mensaje(
    "EJE002",
    "el programa no terminó después de {pasos} pasos; puede ser un bucle "
    "infinito. Revisa que la condición del bucle llegue a ser falsa.")


# ----------------------------------------------------------------------
# Entorno gráfico: lo que dice Tunki
# ----------------------------------------------------------------------
TUNKI_SALUDO = Mensaje(
    "IDE001",
    "¡Hola! Soy Tunki. Escribe tu programa y te aviso si algo no está "
    "bien.")
TUNKI_ERROR = Mensaje("IDE002", "¡Ay! Mira la línea {linea}:")
TUNKI_ERROR_EJECUCION = Mensaje(
    "IDE003", "¡Tu programa se detuvo en la línea {linea}!")
TUNKI_EXITO = Mensaje("IDE004", "¡Muy bien! Tu programa funcionó.")
TUNKI_ARREGLA_PRIMERO = Mensaje(
    "IDE005", "Primero arreglemos este error y luego lo ejecutamos.")
TUNKI_TODO_BIEN = Mensaje(
    "IDE006", "Todo se ve bien. ¡Presiona Ejecutar!")
TUNKI_VARIOS_ERRORES = Mensaje(
    "IDE007", "(hay {total} errores; este es el {numero})")
TUNKI_EJECUTANDO = Mensaje("IDE008", "Ejecutando tu programa...")

# ----------------------------------------------------------------------
# Entorno gráfico: botones y paneles
# ----------------------------------------------------------------------
IDE_EJECUTAR = Mensaje("IDE101", "Ejecutar")
IDE_NUEVO = Mensaje("IDE102", "Nuevo")
IDE_ABRIR = Mensaje("IDE103", "Abrir")
IDE_GUARDAR = Mensaje("IDE104", "Guardar")
IDE_EJEMPLOS = Mensaje("IDE105", "Ejemplos")
IDE_IDIOMA = Mensaje("IDE106", "Idioma")
IDE_SALIDA = Mensaje("IDE107", "Lo que muestra tu programa")
IDE_PROBLEMAS = Mensaje("IDE108", "Problemas")
IDE_SIN_PROBLEMAS = Mensaje("IDE109", "No hay problemas.")
IDE_LINEA = Mensaje("IDE110", "Línea {linea}")
IDE_GUARDAR_CAMBIOS = Mensaje(
    "IDE111", "Tu programa tiene cambios sin guardar. ¿Guardarlos?")
IDE_SIN_SALIDA = Mensaje("IDE112", "(tu programa no mostró nada)")
IDE_LETRA_MAS_GRANDE = Mensaje("IDE113", "Letra más grande")
IDE_LETRA_MAS_PEQUENA = Mensaje("IDE114", "Letra más pequeña")
IDE_POSICION = Mensaje("IDE115", "Línea {linea}, columna {columna}")
IDE_ESTADO_SIN_ERRORES = Mensaje("IDE116", "Todo bien")
IDE_ESTADO_ERRORES = Mensaje("IDE117", "Errores: {total}")
IDE_ESTADO_ADVERTENCIAS = Mensaje("IDE118", "Avisos: {total}")
IDE_ESTADO_EJECUTANDO = Mensaje("IDE119", "Ejecutando...")
IDE_SUBTITULO = Mensaje("IDE120", "Aprende a programar con Tunki")
IDE_PISTA_EJECUTAR = Mensaje("IDE121", "Ejecutar el programa (F5)")
IDE_PISTA_EJEMPLOS = Mensaje(
    "IDE122", "Programas listos para probar y aprender")
IDE_PISTA_SALIDA = Mensaje(
    "IDE123", "Presiona Ejecutar y aquí verás lo que muestra tu programa.")
IDE_AVANCE_QUECHUA = Mensaje(
    "IDE124", "Textos traducidos al quechua: {listos} de {total}")


# ----------------------------------------------------------------------
# Consultas sobre el catálogo
# ----------------------------------------------------------------------
def catalogo() -> List[Mensaje]:
    """Todos los mensajes, en el orden en que aparecen en este archivo."""
    return [valor for valor in globals().values()
            if isinstance(valor, Mensaje)]


def por_codigo(codigo: str) -> Mensaje:
    for mensaje in catalogo():
        if mensaje.codigo == codigo:
            return mensaje
    raise KeyError(codigo)


def pendientes_de_traduccion() -> List[Mensaje]:
    return [m for m in catalogo() if not m.traducido]


# ----------------------------------------------------------------------
# Traducciones desde la hoja de cálculo (antachawi/traducciones)
# ----------------------------------------------------------------------
ARCHIVO_DE_TRADUCCION = (Path(__file__).parent / "traducciones"
                         / "quechua.csv")
COLUMNAS = ("codigo", "donde", "espanol", "quechua", "origen", "nota")
# Columna "origen": quién escribió la traducción.
EQUIPO = "equipo"           # escrita por el equipo de Antachawi
BORRADOR = "borrador"       # borrador sin revisar por un hablante
REVISADO = "revisado"       # revisada por un hablante de quechua collao


def leer_traducciones(ruta: Path = ARCHIVO_DE_TRADUCCION
                      ) -> Dict[str, Dict[str, str]]:
    """Filas de la hoja, por código. {} si la hoja no existe."""
    if not ruta.is_file():
        return {}
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        return {fila["codigo"].strip(): fila
                for fila in csv.DictReader(archivo)
                if (fila.get("codigo") or "").strip()}


def limpiar_traduccion(mensaje: Mensaje, quechua: Optional[str]) -> str:
    """Quita espacios sobrantes de la celda, pero conserva el espacio
    final si el español lo tiene ("Error en línea 3: " + el mensaje)."""
    quechua = (quechua or "").strip()
    if quechua and mensaje.es.endswith(" "):
        quechua += " "
    return quechua


def problema_de_traduccion(mensaje: Mensaje,
                           quechua: str) -> Optional[str]:
    """Por qué una traducción no se puede usar, o None si está bien."""
    try:
        sobran = campos(quechua) - campos(mensaje.es)
        quechua.format(**{campo: "" for campo in campos(mensaje.es)})
    except (ValueError, IndexError, KeyError):
        return ("las llaves { } están mal escritas; deben quedar igual "
                "que en el español")
    if sobran:
        return ("usa nombres entre llaves que no están en el español: "
                + ", ".join("{" + c + "}" for c in sorted(sobran)))
    return None


def cargar_traducciones(ruta: Path = ARCHIVO_DE_TRADUCCION) -> int:
    """Pone en cada mensaje el quechua de la hoja. Las traducciones con
    problemas se ignoran (las informa `python -m antachawi.traduccion
    revisar`). Devuelve cuántas se cargaron."""
    mensajes = {m.codigo: m for m in catalogo()}
    cargadas = 0
    for codigo, fila in leer_traducciones(ruta).items():
        mensaje = mensajes.get(codigo)
        if mensaje is None:
            continue
        quechua = limpiar_traduccion(mensaje, fila.get("quechua"))
        if not quechua or \
                problema_de_traduccion(mensaje, quechua):
            continue
        # Mensaje es inmutable para el resto del programa; solo aquí,
        # al cargar, se completa su traducción.
        object.__setattr__(mensaje, "qu", quechua)
        cargadas += 1
    return cargadas


cargar_traducciones()
