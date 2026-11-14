from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from antachawi import mensajes
from antachawi.errores import texto_de
from antachawi.mensajes import AMBOS, ES, QU


def _subrayado(contenido, columna, longitud):
    """
    Línea con '^' debajo de las columnas [columna, columna + longitud).
    Los tabuladores de la línea original se copian para que el '^' quede
    alineado aunque el código use tabs.
    """
    prefijo = "".join("\t" if c == "\t" else " "
                      for c in contenido[:columna - 1])
    return prefijo + "^" * longitud


def _idioma_principal(idioma):
    return QU if idioma == QU else ES


def titulo_en(titulo, idioma=AMBOS) -> str:
    """Título de la consola; con AMBOS: "español — quechua"."""
    if idioma == AMBOS and titulo.traducido:
        return f"{titulo.es} — {titulo.qu}"
    return titulo.plantilla(_idioma_principal(idioma))


def formatear_error(error, encabezado=mensajes.ENCABEZADO_ERROR,
                    estilo="bold red", idioma=AMBOS) -> list:
    """
    Da formato a un error (ver antachawi/errores.py). Devuelve el encabezado
    con el mensaje (con AMBOS, también el mensaje en quechua debajo) y, si
    se conoce la línea, el código con el error subrayado:

        Error SEM004 en 4:15: la variable 'b' no fue declarada.
            qu: variable 'b' mana churakusqa.
            4 |     a = b + 1
              |         ^
    """
    linea = error["linea"]
    columna = error.get("columna")
    ubicacion = f"{linea}:{columna}" if columna else f"{linea}"
    principal = _idioma_principal(idioma)

    titulo = Text()
    titulo.append(encabezado.texto(principal, codigo=error["codigo"],
                                   ubicacion=ubicacion), style=estilo)
    titulo.append(texto_de(error, principal), style="cyan")
    quechua = error["textos"].get(QU)
    if idioma == AMBOS and quechua:
        titulo.append(f"\n    {QU}: {quechua}", style="italic cyan")

    contenido = error.get("contenido")
    if contenido is None:
        return [titulo]

    # El código y el '^' no se parten en varias líneas para que el
    # subrayado quede alineado.
    codigo = Text(no_wrap=True, overflow="ellipsis")
    margen = f"{linea:>5} | "
    codigo.append(margen, style="dim")
    codigo.append(contenido, style="magenta")
    if columna:
        codigo.append("\n" + " " * (len(margen) - 2) + "| ", style="dim")
        codigo.append(
            _subrayado(contenido, columna, error.get("longitud", 1)),
            style=estilo)
    return [titulo, codigo]


class ConsoleHandler:
    console = Console()

    def __init__(self, idioma=AMBOS):
        self.idioma = idioma

    def print_title(self):
        self.console.print(Markdown("     Antachawy Compiler "))

    def scan_debug_table(self, tokens):
        debug_table = Table(title="Tabla de Tokens")
        debug_table.add_column("Lexema", style="cyan", justify="center")
        debug_table.add_column("Etiqueta", style="magenta", justify="center")
        debug_table.add_column("Linea", style="green", justify="center")
        for token in tokens:
            debug_table.add_row(token.lexema, token.etiqueta,
                                str(token.linea))
        self.console.print(debug_table, justify="center")

    def show_errors(self, errors):
        if not errors:
            self.console.print(Panel("No se encontraron errores",
                                     border_style="green"))
            return
        self._mostrar(errors, mensajes.TITULO_ERRORES,
                      mensajes.ENCABEZADO_ERROR, "red")

    def show_warnings(self, advertencias):
        if advertencias:
            self._mostrar(advertencias, mensajes.TITULO_ADVERTENCIAS,
                          mensajes.ENCABEZADO_ADVERTENCIA, "yellow")

    def _mostrar(self, lista, titulo, encabezado, color):
        bloques = []
        for elemento in lista:
            bloques.extend(formatear_error(elemento, encabezado,
                                           f"bold {color}", self.idioma))
        self.console.print(Panel(Group(*bloques),
                                 title=titulo_en(titulo, self.idioma),
                                 border_style=color))
