"""
Colores del código Antachawi en el editor.

Las palabras se toman de antachawi/definitions.py, así que si el lenguaje
gana una palabra reservada nueva basta con agregarla a GRUPOS.
"""
import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from antachawi.definitions import LexemasAntachawy as L

# Grupo -> (palabras, color, negrita)
GRUPOS = {
    "tipo": ((L.YUPAY, L.CHUNKAYUQ, L.SANANPA, L.QAYTU, L.BOOL),
             "#1864ab", True),
    "control": ((L.ARI, L.MANA_CHAYQA_ARI, L.MANA_CHAYQA, L.IMAPAQ,
                 L.CHAYKAMA, L.CUTICHIY), "#a61e4d", True),
    "funcion": ((L.QHAPAQ, L.RIKUCHIY), "#c4561b", True),
    "valor": ((L.CHIQAQ, L.YANQA), "#2b8a3e", True),
}
COLOR_NUMERO = "#2b8a3e"
COLOR_TEXTO = "#9c4221"
COLOR_COMENTARIO = "#9a8c78"
COLOR_SIGNOS = "#8c7a63"

_NUMERO = re.compile(r"\b\d+(\.\d+)?\b")
_SIGNOS = re.compile(r"[(){}\[\],;]")
_TEXTO = re.compile(r'"([^"\\\n]|\\.)*"?|\'([^\'\\\n]|\\.)*\'?')
_COMENTARIO_LINEA = re.compile(r"::.*")
INICIO_BLOQUE = ":*"
FIN_BLOQUE = "*:"

# Estado de un bloque de texto (línea) para el resaltador
FUERA_DE_COMENTARIO = 0
DENTRO_DE_COMENTARIO = 1


def _formato(color, negrita=False, cursiva=False) -> QTextCharFormat:
    formato = QTextCharFormat()
    formato.setForeground(QColor(color))
    if negrita:
        formato.setFontWeight(QFont.Weight.Bold)
    formato.setFontItalic(cursiva)
    return formato


def _palabras(lista) -> re.Pattern:
    # Las más largas primero: mana_chayqa_ari antes que mana_chayqa
    alternativas = "|".join(sorted(lista, key=len, reverse=True))
    return re.compile(rf"\b({alternativas})\b")


class ResaltadorAntachawi(QSyntaxHighlighter):
    def __init__(self, documento):
        super().__init__(documento)
        self.reglas = [(_palabras(palabras), _formato(color, negrita))
                       for palabras, color, negrita in GRUPOS.values()]
        self.reglas.append((_NUMERO, _formato(COLOR_NUMERO)))
        self.reglas.append((_SIGNOS, _formato(COLOR_SIGNOS, negrita=True)))
        self.formato_texto = _formato(COLOR_TEXTO)
        self.formato_comentario = _formato(COLOR_COMENTARIO, cursiva=True)

    def highlightBlock(self, linea: str):
        for patron, formato in self.reglas:
            for encontrado in patron.finditer(linea):
                self.setFormat(encontrado.start(),
                               encontrado.end() - encontrado.start(), formato)
        # Textos y comentarios van al final: lo que hay dentro de ellos no
        # es código.
        for encontrado in _TEXTO.finditer(linea):
            self.setFormat(encontrado.start(),
                           encontrado.end() - encontrado.start(),
                           self.formato_texto)
        self._comentarios(linea)

    def _comentarios(self, linea: str):
        self.setCurrentBlockState(FUERA_DE_COMENTARIO)
        inicio = 0
        if self.previousBlockState() != DENTRO_DE_COMENTARIO:
            inicio = self._siguiente_comentario(linea, 0)
        while inicio >= 0:
            fin = linea.find(FIN_BLOQUE, inicio + len(INICIO_BLOQUE)
                             if linea.startswith(INICIO_BLOQUE, inicio)
                             else inicio)
            if fin < 0:
                self.setCurrentBlockState(DENTRO_DE_COMENTARIO)
                self.setFormat(inicio, len(linea) - inicio,
                               self.formato_comentario)
                return
            fin += len(FIN_BLOQUE)
            self.setFormat(inicio, fin - inicio, self.formato_comentario)
            inicio = self._siguiente_comentario(linea, fin)

    def _siguiente_comentario(self, linea: str, desde: int) -> int:
        """Posición del siguiente ':*' desde `desde`. Un '::' antes que él
        comenta el resto de la línea (y devuelve -1)."""
        bloque = linea.find(INICIO_BLOQUE, desde)
        de_linea = _COMENTARIO_LINEA.search(linea, desde)
        if de_linea and (bloque < 0 or de_linea.start() < bloque):
            self.setFormat(de_linea.start(), len(linea) - de_linea.start(),
                           self.formato_comentario)
            return -1
        return bloque
