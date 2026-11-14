"""
Bloques básicos y grafo de flujo (Libro del Dragón, sección 8.4).

Un bloque básico es una secuencia de instrucciones que siempre se ejecuta
completa: el control solo entra por la primera y solo sale por la última.
Para partir el código se buscan los líderes (algoritmo 8.5):

1. La primera instrucción es líder.
2. El destino de un salto es líder (aquí, cada etiqueta).
3. La instrucción que sigue a un salto es líder.

Cada líder empieza un bloque que llega hasta antes del siguiente líder.
En el grafo de flujo hay una arista B -> C si C puede ejecutarse justo
después de B: porque B termina con un salto a C, o porque C sigue a B y B
no termina con un goto.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from antachawi.intermedio import (
    ETIQUETA,
    SALTO,
    Cuadrupla,
)


@dataclass(eq=False)
class BloqueBasico:
    numero: int
    instrucciones: List[Cuadrupla]
    sucesores: List[BloqueBasico] = field(default_factory=list)
    predecesores: List[BloqueBasico] = field(default_factory=list)

    @property
    def nombre(self) -> str:
        return f"B{self.numero}"

    @property
    def etiquetas(self) -> List[str]:
        return [c.resultado for c in self.instrucciones if c.op == ETIQUETA]

    @property
    def ultima(self):
        return self.instrucciones[-1] if self.instrucciones else None


def _lideres(codigo: List[Cuadrupla]) -> List[int]:
    lideres = {0} if codigo else set()
    for i, instruccion in enumerate(codigo):
        if instruccion.op == ETIQUETA:
            lideres.add(i)
        if instruccion.es_salto() and i + 1 < len(codigo):
            lideres.add(i + 1)
    return sorted(lideres)


def particionar(codigo: List[Cuadrupla]) -> List[BloqueBasico]:
    """Parte el código en bloques básicos y arma el grafo de flujo."""
    lideres = _lideres(codigo)
    limites = zip(lideres, lideres[1:] + [len(codigo)])
    bloques = [BloqueBasico(n, list(codigo[inicio:fin]))
               for n, (inicio, fin) in enumerate(limites, start=1)]
    _conectar(bloques)
    return bloques


def _conectar(bloques: List[BloqueBasico]):
    por_etiqueta: Dict[str, BloqueBasico] = {
        etiqueta: bloque for bloque in bloques
        for etiqueta in bloque.etiquetas}
    for i, bloque in enumerate(bloques):
        ultima = bloque.ultima
        destinos = []
        if ultima is not None and ultima.es_salto():
            destinos.append(por_etiqueta[ultima.resultado])
        # Solo un goto impide pasar al bloque siguiente
        if (ultima is None or ultima.op != SALTO) and i + 1 < len(bloques):
            destinos.append(bloques[i + 1])
        for destino in destinos:
            if destino not in bloque.sucesores:
                bloque.sucesores.append(destino)
                destino.predecesores.append(bloque)


def alcanzables(bloques: List[BloqueBasico]) -> List[BloqueBasico]:
    """Bloques a los que se puede llegar desde el primero, en su orden
    original. El resto es código que nunca se ejecuta."""
    if not bloques:
        return []
    vistos, pendientes = {bloques[0]}, [bloques[0]]
    while pendientes:
        for sucesor in pendientes.pop().sucesores:
            if sucesor not in vistos:
                vistos.add(sucesor)
                pendientes.append(sucesor)
    return [b for b in bloques if b in vistos]


def aplanar(bloques: List[BloqueBasico]) -> List[Cuadrupla]:
    return [c for bloque in bloques for c in bloque.instrucciones]


def formatear_bloques(bloques: List[BloqueBasico]) -> str:
    """Bloques con sus instrucciones y aristas, para depuración:

        B1 -> B2, B3
            a = 5
            ...
    """
    partes = []
    for bloque in bloques:
        sucesores = ", ".join(s.nombre for s in bloque.sucesores)
        partes.append(f"{bloque.nombre} -> {sucesores or 'fin'}")
        partes.extend(str(c) if c.op == ETIQUETA else f"    {c}"
                      for c in bloque.instrucciones)
        partes.append("")
    return "\n".join(partes)
