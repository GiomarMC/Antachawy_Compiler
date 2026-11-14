import os

from tabulate import tabulate

from antachawi import mensajes
from antachawi.definitions import (
    EtiquetasAntachawy,
    lexema_a_etiqueta,
    simbolos_compuestos,
)
from antachawi.errores import nuevo_error
from antachawi.sourcecode import SourceCode
from antachawi.token import Token

E = EtiquetasAntachawy

# Secuencias de escape válidas dentro de textos y caracteres (las mismas
# de C++, así el literal se copia tal cual al código generado).
ESCAPES_VALIDOS = set("ntr0\\'\"")

# Tokens antes de los cuales se ignora un salto de línea: permiten escribir
# "ari (x) {" o "ari (x)" + "{" en la línea siguiente, y "} mana_chayqa"
# o "}" + "mana_chayqa" en la línea siguiente.
_IGNORAR_SALTO_ANTES_DE = {
    E.LLAVE_IZQ,
    E.CONDICION_MANA_CHAYQA,
    E.CONDICION_MANA_CHAYQA_ARI,
}


def _es_salto(token):
    return token.etiqueta == E.SALTO_LINEA


def normalizar_saltos_linea(tokens):
    """
    Filtro entre el scanner y el parser (ver antachawi/grammar.py):
      * varias líneas en blanco seguidas -> un solo SALTO_LINEA,
      * se eliminan los SALTO_LINEA al inicio y al final del archivo,
      * se elimina el SALTO_LINEA antes de '{', mana_chayqa y mana_chayqa_ari.
    """
    resultado = []
    for token in tokens:
        if _es_salto(token) and (not resultado or _es_salto(resultado[-1])):
            continue
        if token.etiqueta in _IGNORAR_SALTO_ANTES_DE:
            while resultado and _es_salto(resultado[-1]):
                resultado.pop()
        resultado.append(token)
    while resultado and _es_salto(resultado[-1]):
        resultado.pop()
    return resultado


class Scanner:
    def __init__(self, source_code: SourceCode):
        self.code = ""                  # Contenido del archivo fuente
        self.lineno = 1                 # Línea actual
        self.inicio_linea = 0           # Índice donde empieza la línea actual
        self.current_char = ""          # Carácter actual
        self.idx = 0                    # Índice del siguiente carácter
        self.tokens = []                # Tokens generados
        self.errors = []                # Errores encontrados
        self.source_code = source_code  # Objeto SourceCode

    # ------------------------------------------------------------------
    # Lectura de caracteres
    # ------------------------------------------------------------------
    def __open_file(self, filename: str):
        with open(filename, "r", encoding='utf-8') as file:
            self.code = file.read()

    def __get_next_char(self):
        # Avanza un carácter y lo devuelve (None al final del archivo)
        if self.idx < len(self.code):
            self.current_char = self.code[self.idx]
            self.idx += 1
        else:
            self.current_char = None
        return self.current_char

    def __peek_next_char(self):
        # Devuelve el siguiente carácter sin avanzar
        if self.idx < len(self.code):
            return self.code[self.idx]
        return None

    def __consumir_mientras(self, condicion):
        # Avanza mientras el siguiente carácter cumpla la condición y
        # devuelve el texto consumido.
        texto = ""
        while (self.__peek_next_char() is not None
               and condicion(self.__peek_next_char())):
            texto += self.__get_next_char()
        return texto

    def __nueva_linea(self):
        # Se llama justo después de consumir un '\n'
        self.lineno += 1
        self.inicio_linea = self.idx

    def __inicio_token(self):
        # (índice, columna) del carácter actual, que inicia un token
        inicio = self.idx - 1
        return inicio, inicio - self.inicio_linea + 1

    def __error(self, mensaje, columna, longitud=1, linea=None,
                parametros=None):
        linea = linea or self.lineno
        self.errors.append(nuevo_error(
            mensaje, linea, self.source_code.get_line(linea),
            columna, longitud, parametros))

    # ------------------------------------------------------------------
    # Análisis
    # ------------------------------------------------------------------
    def __get_tokens(self):
        while self.__get_next_char() is not None:
            token = self.__siguiente_token()
            if token:
                self.tokens.append(token)
        return self.tokens

    def __siguiente_token(self):
        # Reconoce el token que empieza en el carácter actual. Devuelve None
        # para espacios, comentarios y lexemas con error.
        caracter = self.current_char
        if caracter == "\n":
            inicio, columna = self.__inicio_token()
            self.__nueva_linea()
            return Token("\n", E.SALTO_LINEA, self.lineno - 1, inicio,
                         columna)
        if caracter.isspace():
            return None
        if caracter == ":" and self.__peek_next_char() in (":", "*"):
            self.__skip_comment()
            return None
        if caracter == '"':
            return self.__get_string()
        if caracter == "'":
            return self.__get_character()
        if self.__empieza_numero():
            return self.__get_number()
        if caracter.isalpha():
            return self.__get_id()
        return self.__get_special_character()

    def __empieza_numero(self):
        # Un número empieza con un dígito, o con '.' seguido de un dígito
        # (ej.: .5)
        siguiente = self.__peek_next_char() or ""
        return self.current_char.isdigit() or (
            self.current_char == "." and siguiente.isdigit())

    def __skip_comment(self):
        if self.__get_next_char() == ":":
            # Comentario de línea: se deja el '\n' para el bucle principal
            self.__consumir_mientras(lambda c: c != "\n")
        else:
            self.__skip_block_comment()

    def __skip_block_comment(self):
        # Ya se consumió ':*'. El error se reporta donde empieza el
        # comentario, no al final del archivo.
        linea_inicio = self.lineno
        columna_inicio = self.idx - 2 - self.inicio_linea + 1
        while True:
            caracter = self.__get_next_char()
            if caracter is None:
                self.__error(mensajes.COMENTARIO_SIN_CERRAR, columna_inicio, 2,
                             linea=linea_inicio)
                return
            if caracter == "*" and self.__peek_next_char() == ":":
                self.__get_next_char()
                return
            if caracter == "\n":
                self.__nueva_linea()

    def __leer_literal(self, delimitador):
        """
        Lee el contenido de un texto o carácter hasta `delimitador`, sin
        consumirlo. Devuelve (contenido, cantidad de caracteres); una
        secuencia de escape como \\n cuenta como un solo carácter y se
        guarda tal como está escrita.
        """
        contenido, cantidad = "", 0
        while self.__peek_next_char() not in (None, "\n", delimitador):
            caracter = self.__get_next_char()
            contenido += caracter
            cantidad += 1
            if caracter == "\\":
                contenido += self.__leer_escape()
        return contenido, cantidad

    def __leer_escape(self):
        # Ya se consumió la barra invertida
        columna = self.idx - self.inicio_linea
        siguiente = self.__peek_next_char()
        if siguiente is None or siguiente == "\n":
            return ""       # el literal queda sin cerrar
        self.__get_next_char()
        if siguiente not in ESCAPES_VALIDOS:
            self.__error(mensajes.ESCAPE_INVALIDO, columna, 2,
                         parametros={"secuencia": "\\" + siguiente})
        return siguiente

    def __get_string(self):
        inicio, columna = self.__inicio_token()
        contenido, _ = self.__leer_literal('"')
        lexema = '"' + contenido
        if self.__peek_next_char() != '"':
            self.__error(mensajes.CADENA_SIN_CERRAR, columna, len(lexema))
            return None
        lexema += self.__get_next_char()
        return Token(lexema, E.CADENA, self.lineno, inicio, columna)

    def __get_character(self):
        inicio, columna = self.__inicio_token()
        contenido, cantidad = self.__leer_literal("'")
        if self.__peek_next_char() != "'":
            self.__error(mensajes.CARACTER_SIN_CERRAR, columna,
                         len(contenido) + 1)
            return None
        self.__get_next_char()
        lexema = f"'{contenido}'"
        if cantidad == 0:
            self.__error(mensajes.CARACTER_VACIO, columna, len(lexema))
            return None
        if cantidad > 1:
            self.__error(mensajes.CARACTER_LARGO, columna, len(lexema))
            return None
        return Token(lexema, E.CARACTER, self.lineno, inicio, columna)

    def __get_number(self):
        inicio, columna = self.__inicio_token()
        lexema = self.current_char + self.__consumir_mientras(
            lambda c: c.isdigit() or c == ".")
        siguiente = self.__peek_next_char()
        if siguiente is not None and siguiente.isalpha():
            # Ej.: 10abc -> se marca el lexema completo como error
            lexema += self.__consumir_mientras(
                lambda c: c.isalnum() or c == "_")
            self.__error(mensajes.NUMERO_CON_LETRAS, columna, len(lexema))
            return None
        if lexema.count(".") > 1:
            self.__error(mensajes.VARIOS_PUNTOS, columna, len(lexema))
            return None
        etiqueta = E.NUMEROFLOTANTE if "." in lexema else E.NUMEROENTERO
        return Token(lexema, etiqueta, self.lineno, inicio, columna)

    def __get_id(self):
        # Identificador o palabra reservada
        inicio, columna = self.__inicio_token()
        lexema = self.current_char + self.__consumir_mientras(
            lambda c: c.isalnum() or c == "_")
        etiqueta = lexema_a_etiqueta.get(lexema, E.ID)
        return Token(lexema, etiqueta, self.lineno, inicio, columna)

    def __get_special_character(self):
        inicio, columna = self.__inicio_token()
        doble = self.code[inicio:inicio + 2]
        if doble in simbolos_compuestos:
            self.__get_next_char()
            return Token(doble, simbolos_compuestos[doble], self.lineno,
                         inicio, columna)
        if self.current_char in lexema_a_etiqueta:
            return Token(self.current_char,
                         lexema_a_etiqueta[self.current_char], self.lineno,
                         inicio, columna)
        self.__error(mensajes.SIMBOLO_DESCONOCIDO, columna)
        return None

    def tokenize(self, filename: str = None):
        """Tokeniza el archivo `filename` o, si no se indica, el texto del
        SourceCode, y normaliza los saltos de línea."""
        if filename is None:
            self.code = self.source_code.texto
        else:
            self.__open_file(filename)
        self.__get_tokens()
        self.tokens = normalizar_saltos_linea(self.tokens)
        return self.tokens

    def save_tokens(self, filename="tokens.txt"):
        os.makedirs("outputs/lexicon", exist_ok=True)
        filepath = os.path.join("outputs/lexicon", filename)
        headers = ["Lexema", "Etiqueta", "Linea", "Columna"]
        rows = [[token.lexema, token.etiqueta, token.linea, token.columna]
                for token in self.tokens]
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(tabulate(rows, headers, tablefmt="grid"))
