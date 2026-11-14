"""
Ayuda para traducir Antachawi al quechua (Collao) sin tocar el código.

    python -m antachawi.traduccion revisar
        Cuántos textos y ejemplos faltan, y si alguna traducción tiene
        problemas (llaves mal escritas, español que cambió...).

    python -m antachawi.traduccion actualizar
        Agrega a la hoja los mensajes nuevos que aparezcan en
        antachawi/mensajes.py, sin borrar lo ya traducido.

La hoja es antachawi/traducciones/quechua.csv; las instrucciones para quien
traduce están en antachawi/traducciones/LEEME.md.
"""
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from antachawi import mensajes
from antachawi.mensajes import (
    ARCHIVO_DE_TRADUCCION,
    BORRADOR,
    COLUMNAS,
    EQUIPO,
    Mensaje,
    campos,
    leer_traducciones,
    limpiar_traduccion,
    problema_de_traduccion,
)

EJEMPLOS = Path(__file__).parent / "ide" / "ejemplos"
EJEMPLOS_QUECHUA = EJEMPLOS / "qu"

DONDE = {
    "CON": "Consola: títulos de la lista de errores",
    "LEX": "Error: al leer las letras del programa",
    "SIN": "Error: algo falta o sobra en el programa",
    "SEM": "Error: algo no tiene sentido (variables, tipos)",
    "ADV": "Aviso (el programa igual funciona)",
    "EJE": "Error mientras el programa se ejecuta",
}


def donde(mensaje: Mensaje) -> str:
    if mensaje.codigo.startswith("IDE0"):
        return "Lo que dice Tunki en su globo"
    if mensaje.codigo.startswith("IDE"):
        return "Botones y paneles del entorno"
    return DONDE[mensaje.codigo[:3]]


def nota(mensaje: Mensaje) -> str:
    nombres = sorted(campos(mensaje.es))
    if not nombres:
        return ""
    llaves = ", ".join("{" + n + "}" for n in nombres)
    return f"Copiar sin traducir: {llaves}"


# ----------------------------------------------------------------------
# Ejemplos
# ----------------------------------------------------------------------
def numero_de_ejemplo(ruta: Path) -> str:
    """01_hola.awi -> "01" """
    return ruta.stem.split("_", 1)[0]


def ejemplos_sin_traducir() -> List[Path]:
    traducidos = {numero_de_ejemplo(r)
                  for r in EJEMPLOS_QUECHUA.glob("*.awi")}
    return [r for r in sorted(EJEMPLOS.glob("*.awi"))
            if numero_de_ejemplo(r) not in traducidos]


# ----------------------------------------------------------------------
# Revisar
# ----------------------------------------------------------------------
@dataclass
class Revision:
    total: int = 0
    traducidos: int = 0
    problemas: List[str] = field(default_factory=list)
    espanol_cambiado: List[str] = field(default_factory=list)
    borradores: List[str] = field(default_factory=list)
    faltan: List[Mensaje] = field(default_factory=list)
    ejemplos_faltan: List[Path] = field(default_factory=list)


def _revisar_fila(mensaje, fila, revision: Revision):
    quechua = limpiar_traduccion(mensaje, (fila or {}).get("quechua"))
    if not quechua:
        if mensaje.qu is None:
            revision.faltan.append(mensaje)
        else:
            revision.traducidos += 1
        return
    problema = problema_de_traduccion(mensaje, quechua)
    if problema:
        revision.problemas.append(f"{mensaje.codigo}: {problema}")
        revision.faltan.append(mensaje)
        return
    revision.traducidos += 1
    if (fila.get("origen") or "").strip() == BORRADOR:
        revision.borradores.append(mensaje.codigo)
    if (fila.get("espanol") or "").strip() != mensaje.es.strip():
        revision.espanol_cambiado.append(mensaje.codigo)


def revisar(ruta: Path = ARCHIVO_DE_TRADUCCION) -> Revision:
    filas = leer_traducciones(ruta)
    revision = Revision(total=len(mensajes.catalogo()))
    for mensaje in mensajes.catalogo():
        _revisar_fila(mensaje, filas.get(mensaje.codigo), revision)
    revision.ejemplos_faltan = ejemplos_sin_traducir()
    sobrantes = set(filas) - {m.codigo for m in mensajes.catalogo()}
    revision.problemas += [f"{codigo}: este código ya no existe"
                           for codigo in sorted(sobrantes)]
    return revision


def informe(revision: Revision) -> str:
    lineas = [f"Mensajes traducidos: {revision.traducidos} de "
              f"{revision.total}"]
    ejemplos = len(list(EJEMPLOS.glob("*.awi")))
    listos = ejemplos - len(revision.ejemplos_faltan)
    lineas.append(f"Ejemplos traducidos: {listos} de {ejemplos}")
    if revision.borradores:
        lineas.append(
            f"Borradores sin revisar: {len(revision.borradores)} (cuando un "
            "hablante los revise, cambia «borrador» por «revisado» en la "
            "columna origen)")
    if revision.problemas:
        lineas.append("\nTraducciones con problemas (no se usan):")
        lineas += [f"  ✖ {p}" for p in revision.problemas]
    if revision.espanol_cambiado:
        lineas.append("\nEl español cambió después de traducir; "
                      "revisa que el quechua siga diciendo lo mismo:")
        lineas += [f"  ⚠ {c}" for c in revision.espanol_cambiado]
    if revision.faltan:
        lineas.append("\nFaltan:")
        lineas += [f"  · {m.codigo}  {m.es}" for m in revision.faltan]
    if revision.ejemplos_faltan:
        lineas.append("\nEjemplos sin versión en quechua "
                      f"(en {EJEMPLOS_QUECHUA}):")
        lineas += [f"  · {r.name}" for r in revision.ejemplos_faltan]
    return "\n".join(lineas)


# ----------------------------------------------------------------------
# Actualizar la hoja
# ----------------------------------------------------------------------
def filas_actualizadas(anteriores: Dict[str, Dict[str, str]]) -> List[dict]:
    """Una fila por mensaje, en el orden de mensajes.py. Conserva el
    quechua ya escrito y la columna "espanol" de lo ya traducido (para
    poder avisar si el español cambia)."""
    filas = []
    for mensaje in mensajes.catalogo():
        anterior = anteriores.get(mensaje.codigo, {})
        quechua = limpiar_traduccion(
            mensaje, anterior.get("quechua")) or (mensaje.qu or "")
        espanol = mensaje.es
        origen = (anterior.get("origen") or "").strip()
        if (anterior.get("quechua") or "").strip():
            espanol = anterior.get("espanol") or mensaje.es
        elif quechua:
            origen = EQUIPO         # venía escrita en mensajes.py
        filas.append({"codigo": mensaje.codigo, "donde": donde(mensaje),
                      "espanol": espanol, "quechua": quechua,
                      "origen": origen if quechua else "",
                      "nota": nota(mensaje)})
    return filas


def escribir_hoja(filas: List[dict], ruta: Path = ARCHIVO_DE_TRADUCCION):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig: Excel reconoce las tildes y la ñ
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)


def actualizar(ruta: Path = ARCHIVO_DE_TRADUCCION) -> int:
    """Devuelve cuántos mensajes nuevos se agregaron."""
    anteriores = leer_traducciones(ruta)
    filas = filas_actualizadas(anteriores)
    escribir_hoja(filas, ruta)
    return sum(1 for f in filas if f["codigo"] not in anteriores)


USO = __doc__


def main(argumentos=None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    orden = argumentos[0] if argumentos else ""
    if orden == "revisar":
        revision = revisar()
        print(informe(revision))
        return 1 if revision.problemas else 0
    if orden == "actualizar":
        nuevos = actualizar()
        print(f"Hoja actualizada: {ARCHIVO_DE_TRADUCCION}")
        print(f"Mensajes nuevos agregados: {nuevos}")
        return 0
    print(USO)
    return 2


if __name__ == "__main__":
    sys.exit(main())
