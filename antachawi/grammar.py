"""
Gramática LL(1) de Antachawi: única fuente de verdad del lenguaje.

Los terminales se escriben con su lexema (``ari``, ``(``, ``+``, ``id``,
``entero``...) y se traducen a las etiquetas que produce el scanner usando
``lexema_a_etiqueta``. Además:

    NL  -> salto de línea (fin de sentencia)
    $   -> fin del archivo
    ε   -> cadena vacía

A partir de esta gramática se calculan los conjuntos PRIMEROS (FIRST) y
SIGUIENTES (FOLLOW) tal como en el Libro del Dragón (sección 4.4), y el
parser descendente recursivo los usa para decidir qué producción aplicar.
``conflictos_ll1()`` verifica que la gramática sea LL(1).

Una producción larga se puede continuar en la línea siguiente terminando
la línea con una barra invertida.

Saltos de línea: antes de parsear, el scanner normaliza los saltos de línea
(ver ``normalizar_saltos_linea`` en scanner.py):
  * varias líneas en blanco seguidas cuentan como un solo NL,
  * se ignoran los NL al inicio y al final del archivo,
  * se ignoran los NL antes de '{' y antes de mana_chayqa / mana_chayqa_ari.
Por eso la gramática solo exige NL al final de cada sentencia y después
de '{', y permite escribir tanto:

    ari (a > 1)            ari (a > 1) {
    {                          ...
        ...                } mana_chayqa {
    }                          ...
    mana_chayqa            }
    {
        ...
    }
"""
from itertools import combinations, permutations

from antachawi.definitions import EtiquetasAntachawy, lexema_a_etiqueta

EPSILON = "ε"
FIN = "$"

GRAMATICA = """
Programa -> Definicion
Definicion -> qhapaq ( ) Bloque
Bloque -> { NL ListaSentencias }
ListaSentencias -> Sentencias ListaSentencias | ε
Sentencias -> Declaraciones NL
            | Asignaciones NL
            | Condicional NL
            | Impresiones NL
            | Mientras NL
            | Para NL
Declaraciones -> Tipo id DeclaracionesPrime
DeclaracionesPrime -> = Expresion | ε
Asignaciones -> id = Expresion
Condicional -> ari ( Expresion ) Bloque CondicionalPrime
CondicionalPrime -> mana_chayqa_ari ( Expresion ) Bloque CondicionalPrime
                  | mana_chayqa Bloque
                  | ε
Mientras -> chaykama ( Expresion ) Bloque
Para -> imapaq ( ParaInicio ; Expresion ; Asignaciones ) Bloque
ParaInicio -> Declaraciones | Asignaciones
Impresiones -> rikuchiy ( ExpresionImpresion )
ExpresionImpresion -> Expresion ExpresionImpresionPrime
ExpresionImpresionPrime -> , ExpresionImpresion | ε
Tipo -> yupay | chunkayuq | sananpa | qaytu | bool
Expresion -> ExpresionY ExpresionOPrime
ExpresionOPrime -> || ExpresionY ExpresionOPrime | ε
ExpresionY -> ExpresionRelacional ExpresionYPrime
ExpresionYPrime -> && ExpresionRelacional ExpresionYPrime | ε
ExpresionRelacional -> ExpresionAditiva ExpresionRelacionalPrime
ExpresionRelacionalPrime -> OperadorRelacional ExpresionAditiva | ε
OperadorRelacional -> > | < | >= | <= | == | !=
ExpresionAditiva -> ExpresionMultiplicativa ExpresionAditivaPrime
ExpresionAditivaPrime -> OperadorAditivo ExpresionMultiplicativa \
                             ExpresionAditivaPrime
                       | ε
ExpresionMultiplicativa -> Termino ExpresionMultiplicativaPrime
ExpresionMultiplicativaPrime -> OperadorMultiplicativo Termino \
                                    ExpresionMultiplicativaPrime
                              | ε
OperadorAditivo -> + | -
OperadorMultiplicativo -> * | /
Termino -> - Termino
         | ( Expresion )
         | id
         | entero
         | flotante
         | caracter
         | cadena
         | chiqaq
         | yanqa
"""

SIMBOLO_INICIAL = "Programa"

_TERMINALES_ESPECIALES = {
    "NL": EtiquetasAntachawy.SALTO_LINEA,
    FIN: EtiquetasAntachawy.FIN_ARCHIVO,
}


def leer_gramatica(texto: str = GRAMATICA) -> dict:
    """Devuelve {NoTerminal: [produccion, ...]}; cada producción es una
    lista de símbolos (vacía para ε)."""
    producciones = {}
    actual = None
    for linea in texto.strip().splitlines():
        linea = linea.strip()
        if not linea:
            continue
        if "->" in linea:
            izquierda, derecha = linea.split("->", 1)
            actual = izquierda.strip()
            producciones.setdefault(actual, [])
        elif linea.startswith("| ") and actual is not None:
            derecha = linea[2:]
        else:
            raise ValueError(f"Línea de gramática inválida: {linea!r}")
        # Las alternativas se separan con " | " (con espacios), así el
        # operador "||" no se confunde con el separador.
        for alternativa in f" {derecha} ".split(" | "):
            simbolos = alternativa.split()
            if simbolos == [EPSILON]:
                simbolos = []
            producciones[actual].append(simbolos)
    return producciones


def etiqueta_de(simbolo: str) -> str:
    """Traduce un terminal de la gramática a la etiqueta del scanner."""
    if simbolo in _TERMINALES_ESPECIALES:
        return _TERMINALES_ESPECIALES[simbolo]
    if simbolo in lexema_a_etiqueta:
        return lexema_a_etiqueta[simbolo]
    raise KeyError(f"Terminal desconocido en la gramática: {simbolo!r}")


def _primeros_de_secuencia(secuencia, primeros, producciones):
    resultado = set()
    for simbolo in secuencia:
        if simbolo in producciones:
            resultado |= primeros[simbolo] - {EPSILON}
            if EPSILON not in primeros[simbolo]:
                return resultado
        else:
            resultado.add(etiqueta_de(simbolo))
            return resultado
    resultado.add(EPSILON)
    return resultado


def calcular_primeros(producciones: dict) -> dict:
    primeros = {nt: set() for nt in producciones}
    cambio = True
    while cambio:
        cambio = False
        for nt, alternativas in producciones.items():
            for alternativa in alternativas:
                nuevos = _primeros_de_secuencia(alternativa, primeros,
                                                producciones)
                if not nuevos <= primeros[nt]:
                    primeros[nt] |= nuevos
                    cambio = True
    return primeros


def _siguientes_de_produccion(nt, alternativa, primeros, siguientes,
                              producciones):
    """Para A -> α B β, B recibe PRIMEROS(β) - {ε}, y además SIGUIENTES(A)
    si β puede derivar ε. Devuelve los pares (B, símbolos para B)."""
    for i, simbolo in enumerate(alternativa):
        if simbolo not in producciones:
            continue
        resto = _primeros_de_secuencia(alternativa[i + 1:], primeros,
                                       producciones)
        nuevos = resto - {EPSILON}
        if EPSILON in resto:
            nuevos |= siguientes[nt]
        yield simbolo, nuevos


def calcular_siguientes(producciones: dict, primeros: dict) -> dict:
    siguientes = {nt: set() for nt in producciones}
    siguientes[SIMBOLO_INICIAL].add(etiqueta_de(FIN))
    cambio = True
    while cambio:
        cambio = False
        for nt, alternativas in producciones.items():
            for alternativa in alternativas:
                for simbolo, nuevos in _siguientes_de_produccion(
                        nt, alternativa, primeros, siguientes, producciones):
                    if not nuevos <= siguientes[simbolo]:
                        siguientes[simbolo] |= nuevos
                        cambio = True
    return siguientes


def _conflictos_de(nt, conjuntos, siguientes_nt):
    """Conflictos entre las alternativas de un no terminal, dados los
    PRIMEROS de cada alternativa."""
    conflictos = []
    for primero, segundo in combinations(conjuntos, 2):
        comun = (primero & segundo) - {EPSILON}
        if comun:
            conflictos.append(f"{nt}: PRIMEROS/PRIMEROS {sorted(comun)}")
    for anulable, otro in permutations(conjuntos, 2):
        comun = otro & siguientes_nt if EPSILON in anulable else set()
        if comun:
            conflictos.append(f"{nt}: PRIMEROS/SIGUIENTES {sorted(comun)}")
    return conflictos


def conflictos_ll1(producciones=None):
    """Lista de conflictos que impedirían que la gramática sea LL(1).
    Una gramática LL(1) debe devolver una lista vacía."""
    producciones = producciones or PRODUCCIONES
    primeros = calcular_primeros(producciones)
    siguientes = calcular_siguientes(producciones, primeros)
    conflictos = []
    for nt, alternativas in producciones.items():
        conjuntos = [_primeros_de_secuencia(a, primeros, producciones)
                     for a in alternativas]
        conflictos.extend(_conflictos_de(nt, conjuntos, siguientes[nt]))
    return conflictos


PRODUCCIONES = leer_gramatica()
_PRIMEROS_CON_EPSILON = calcular_primeros(PRODUCCIONES)
SIGUIENTES = calcular_siguientes(PRODUCCIONES, _PRIMEROS_CON_EPSILON)
# El parser solo necesita etiquetas reales, sin ε.
PRIMEROS = {nt: conjunto - {EPSILON}
            for nt, conjunto in _PRIMEROS_CON_EPSILON.items()}
