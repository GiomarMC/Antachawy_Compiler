"""
Tabla de símbolos con ámbitos anidados (Libro del Dragón, sección 2.7).

Es una pila de tablas: se abre un ámbito al entrar a un bloque y se cierra
al salir. Para buscar un nombre se recorre desde el ámbito más interno
hacia afuera.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from tabulate import tabulate

from antachawi.ast_nodos import Posicion


@dataclass(eq=False)
class Simbolo:
    nombre: str
    tipo: str
    pos: Posicion               # dónde se declaró
    ambito: str                 # nombre del ámbito, para depuración
    nivel: int                  # 0 = bloque de qhapaq
    usado: bool = False         # se leyó su valor en alguna expresión


class TablaSimbolos:
    def __init__(self):
        self._ambitos: List[dict] = []
        self._nombres_ambitos: List[str] = []
        # Todos los símbolos declarados, en orden (para depuración)
        self.historial: List[Simbolo] = []

    @property
    def nivel(self) -> int:
        return len(self._ambitos) - 1

    def abrir_ambito(self, nombre: str):
        self._ambitos.append({})
        self._nombres_ambitos.append(nombre)

    def cerrar_ambito(self) -> List[Simbolo]:
        """Cierra el ámbito actual y devuelve sus símbolos."""
        self._nombres_ambitos.pop()
        return list(self._ambitos.pop().values())

    def buscar(self, nombre: str) -> Optional[Simbolo]:
        """Busca desde el ámbito más interno hacia afuera."""
        for ambito in reversed(self._ambitos):
            if nombre in ambito:
                return ambito[nombre]
        return None

    def buscar_en_ambito_actual(self, nombre: str) -> Optional[Simbolo]:
        return self._ambitos[-1].get(nombre)

    def declarar(self, nombre: str, tipo: str, pos: Posicion) -> Simbolo:
        simbolo = Simbolo(nombre, tipo, pos, self._nombres_ambitos[-1],
                          self.nivel)
        self._ambitos[-1][nombre] = simbolo
        self.historial.append(simbolo)
        return simbolo

    def como_tabla(self) -> str:
        encabezados = ["Nombre", "Tipo", "Ámbito", "Nivel", "Declarada en",
                       "Usada"]
        filas = [[s.nombre, s.tipo, s.ambito, s.nivel,
                  f"{s.pos.linea}:{s.pos.columna}", "sí" if s.usado else "no"]
                 for s in self.historial]
        return tabulate(filas, encabezados, tablefmt="grid")
