import os

from anytree import Node, RenderTree
from anytree.exporter import UniqueDotExporter

from antachawi import mensajes
from antachawi.definitions import EtiquetasAntachawy, etiqueta_a_lexema
from antachawi.errores import nuevo_error
from antachawi.grammar import PRIMEROS, SIGUIENTES
from antachawi.scanner import Scanner
from antachawi.sourcecode import SourceCode
from antachawi.token import Token

E = EtiquetasAntachawy
SALTO_DE_LINEA = 'salto de línea'

# Puntos de sincronización del modo pánico: fin de sentencia, fin de bloque
# y fin de archivo.
_SINCRONIZACION = {E.SALTO_LINEA, E.LLAVE_DER, E.FIN_ARCHIVO}


def render_tree(root: object, filename: str):
    tree_str = ""
    for pre, _, node in RenderTree(root):
        tree_str += f"{pre}{node.name}\n"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(tree_str)


def export_tree(root: object, filename: str):
    UniqueDotExporter(root).to_dotfile(filename + ".dot")
    UniqueDotExporter(root).to_picture(filename + ".png")


class RecursiveDescentParser:
    """
    Parser descendente recursivo para la gramática de antachawi/grammar.py.
    Hay un método por cada no terminal; cuando un no terminal tiene varias
    producciones, se elige mirando el token actual contra PRIMEROS (y
    SIGUIENTES para las producciones ε).

    Cada token consumido se guarda como hoja con el lexema y, debajo, un
    nodo con el número de línea (que también guarda la columna en el
    atributo `columna`). La hoja guarda el token completo en `token`, que es
    lo que usa el constructor del AST (antachawi/constructor_ast.py).
    """

    def __init__(self, scanner: Scanner, source_code: SourceCode):
        self.scanner = scanner
        self.tokens = []
        self.current_token_idx = 0
        self.current_token = None
        self.root = None
        self.errors = []
        self.source_code = source_code
        # Mientras está activo no se registran errores nuevos: evita la
        # cascada de errores que provoca un solo token inesperado.
        self.en_panico = False

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def get_current_line_content(self, line):
        return self.source_code.get_line(line)

    @property
    def etiqueta(self):
        return self.current_token.etiqueta

    def parse(self):
        self.tokens = list(self.scanner.tokens)
        if self.tokens:
            ultimo = self.tokens[-1]
            fin = Token("$", E.FIN_ARCHIVO, ultimo.linea, -1,
                        ultimo.columna_final)
        else:
            fin = Token("$", E.FIN_ARCHIVO, 1, -1, 1)
        self.tokens.append(fin)
        self.current_token_idx = 0
        self.current_token = self.tokens[0]
        self.errors = []
        self.en_panico = False

        self.root = self.programa()

        # Si sobra código después de la '}' final, el error se reporta en
        # ese código y no en el salto de línea que lo separa.
        if self.etiqueta == E.SALTO_LINEA:
            self.next_token()
        if self.etiqueta != E.FIN_ARCHIVO:
            self.error_esperado([E.FIN_ARCHIVO], self.root)
        return self.root

    def next_token(self):
        if self.current_token_idx < len(self.tokens) - 1:
            self.current_token_idx += 1
        self.current_token = self.tokens[self.current_token_idx]

    @staticmethod
    def describir(etiqueta, lexema=None):
        if etiqueta in (E.SALTO_LINEA, E.FIN_ARCHIVO) or lexema is None:
            return etiqueta_a_lexema.get(etiqueta, etiqueta)
        return lexema

    def consume(self, expected_tag, parent: Node):
        """
        Consume el token actual si tiene la etiqueta esperada y lo agrega
        como hoja de `parent`. Si no coincide, registra el error y entra en
        modo pánico. Devuelve True si consumió el token.
        """
        if self.etiqueta != expected_tag:
            self.error_esperado([expected_tag], parent)
            return False

        token = self.current_token
        if token.etiqueta == E.SALTO_LINEA:
            nombre = SALTO_DE_LINEA
        elif token.etiqueta in (E.CARACTER, E.CADENA):
            nombre = token.lexema[1:-1]
        else:
            nombre = token.lexema
        hoja = Node(nombre, parent=parent, token=token)
        Node(token.linea, parent=hoja, columna=token.columna)
        self.en_panico = False
        self.next_token()
        return True

    def error_esperado(self, etiquetas_esperadas, parent: Node):
        """Registra 'se encontró X, se esperaba Y' y sincroniza."""
        Node('ERROR', parent=parent)
        if not self.en_panico:
            encontrado = self.describir(self.etiqueta,
                                        self.current_token.lexema)
            esperado = ", ".join(sorted(
                f"'{self.describir(e)}'" for e in etiquetas_esperadas))
            self.register_error(mensajes.TOKEN_INESPERADO,
                                encontrado=encontrado, esperado=esperado)
        self.en_panico = True
        self.panic_mode()

    def panic_mode(self):
        """
        Modo pánico: descarta tokens hasta un punto de sincronización
        (salto de línea, '}' o fin de archivo) sin consumirlo.
        """
        while self.etiqueta not in _SINCRONIZACION:
            self.next_token()

    def posicion_error(self):
        """
        Devuelve (línea, columna, longitud) que se señala en un error:

        * Si el token actual está en la misma línea que el anterior, el
          error es ese token y se subraya completo.
        * Si el token actual es un salto de línea, el fin del archivo o ya
          está en otra línea, lo que pasó es que *faltó* algo al final de
          la línea anterior: se señala justo después del último token
          válido. Ej.: en "ari (a > 1" + "{" en la línea siguiente, el
          error está en la línea del ari, no en la de la llave.
        """
        actual = self.current_token
        anterior = (self.tokens[self.current_token_idx - 1]
                    if self.current_token_idx > 0 else None)
        falta_al_final = (
            anterior is not None
            and anterior.etiqueta != E.SALTO_LINEA
            and (actual.etiqueta in (E.SALTO_LINEA, E.FIN_ARCHIVO)
                 or actual.linea != anterior.linea)
        )
        if falta_al_final:
            return anterior.linea, anterior.columna_final, 1
        return actual.linea, actual.columna, len(actual.lexema)

    def register_error(self, mensaje, **parametros):
        linea, columna, longitud = self.posicion_error()
        parametros = {nombre: valor.replace('\n', SALTO_DE_LINEA)
                      for nombre, valor in parametros.items()}
        self.errors.append(nuevo_error(
            mensaje, linea, self.get_current_line_content(linea), columna,
            longitud, parametros))

    # ------------------------------------------------------------------
    # Programa, bloques y sentencias
    # ------------------------------------------------------------------
    def programa(self):
        # Programa -> Definicion
        node = Node("Programa")
        self.definicion().parent = node
        return node

    def definicion(self):
        # Definicion -> qhapaq ( ) Bloque
        node = Node("Definicion")
        self.consume(E.PROGRAMA, node)
        self.consume(E.PAREN_IZQ, node)
        self.consume(E.PAREN_DER, node)
        self.bloque().parent = node
        return node

    def bloque(self):
        # Bloque -> { NL ListaSentencias }
        node = Node("Bloque")
        self.consume(E.LLAVE_IZQ, node)
        self.consume(E.SALTO_LINEA, node)
        self.lista_sentencias().parent = node
        self.consume(E.LLAVE_DER, node)
        return node

    def lista_sentencias(self):
        # ListaSentencias -> Sentencias ListaSentencias | ε
        # Se implementa con un bucle (sin recursión) para no depender del
        # límite de recursión de Python en programas largos; el árbol queda
        # igual al de la versión recursiva.
        raiz = Node("ListaSentencias")
        actual = raiz
        while True:
            if self.etiqueta in PRIMEROS["Sentencias"]:
                self.sentencias().parent = actual
                actual = Node("ListaSentencias", parent=actual)
            elif (self.etiqueta in SIGUIENTES["ListaSentencias"]
                  or self.etiqueta == E.FIN_ARCHIVO):
                return raiz
            else:
                # Sentencia que no empieza con un token válido: se reporta,
                # se salta la línea completa y se sigue con la siguiente.
                self.error_esperado(PRIMEROS["Sentencias"], actual)
                if self.etiqueta == E.SALTO_LINEA:
                    self.next_token()
                    self.en_panico = False

    def sentencias(self):
        # Sentencias -> (Declaraciones | Asignaciones | Condicional
        #                | Impresiones | Mientras | Para) NL
        node = Node("Sentencias")
        if self.etiqueta in PRIMEROS["Declaraciones"]:
            self.declaraciones().parent = node
        elif self.etiqueta in PRIMEROS["Asignaciones"]:
            self.asignaciones().parent = node
        elif self.etiqueta in PRIMEROS["Impresiones"]:
            self.impresion().parent = node
        elif self.etiqueta in PRIMEROS["Condicional"]:
            self.condicional().parent = node
        elif self.etiqueta in PRIMEROS["Mientras"]:
            self.mientras().parent = node
        elif self.etiqueta in PRIMEROS["Para"]:
            self.para().parent = node
        self.consume(E.SALTO_LINEA, node)
        return node

    def declaraciones(self):
        # Declaraciones -> Tipo id DeclaracionesPrime
        node = Node("Declaraciones")
        self.tipo().parent = node
        self.consume(E.ID, Node("ID", parent=node))
        self.declaraciones_prime().parent = node
        return node

    def declaraciones_prime(self):
        # DeclaracionesPrime -> = Expresion | ε
        node = Node("DeclaracionesPrime")
        if self.etiqueta == E.ASIGNACION:
            self.consume(E.ASIGNACION, Node("ASIGNACION", parent=node))
            self.expresion().parent = node
        return node

    def asignaciones(self):
        # Asignaciones -> id = Expresion
        node = Node("Asignaciones")
        self.consume(E.ID, Node("ID", parent=node))
        self.consume(E.ASIGNACION, Node("ASIGNACION", parent=node))
        self.expresion().parent = node
        return node

    def impresion(self):
        # Impresiones -> rikuchiy ( ExpresionImpresion )
        node = Node("Impresiones")
        self.consume(E.IMPRESION, node)
        self.consume(E.PAREN_IZQ, node)
        self.expresion_impresion().parent = node
        self.consume(E.PAREN_DER, node)
        return node

    def expresion_impresion(self):
        # ExpresionImpresion -> Expresion ExpresionImpresionPrime
        node = Node("ExpresionImpresion")
        self.expresion().parent = node
        self.expresion_impresion_prime().parent = node
        return node

    def expresion_impresion_prime(self):
        # ExpresionImpresionPrime -> , ExpresionImpresion | ε
        node = Node("ExpresionImpresionPrime")
        if self.etiqueta == E.COMA:
            self.consume(E.COMA, node)
            self.expresion_impresion().parent = node
        return node

    def tipo(self):
        # Tipo -> yupay | chunkayuq | sananpa | qaytu | bool
        node = Node("Tipo")
        if self.etiqueta in PRIMEROS["Tipo"]:
            self.consume(self.etiqueta, node)
        else:
            self.error_esperado(PRIMEROS["Tipo"], node)
        return node

    # ------------------------------------------------------------------
    # Condicionales
    # ------------------------------------------------------------------
    def condicional(self):
        # Condicional -> ari ( Expresion ) Bloque CondicionalPrime
        node = Node("Condicional")
        self.consume(E.CONDICION_ARI, node)
        self.consume(E.PAREN_IZQ, node)
        self.expresion().parent = node
        self.consume(E.PAREN_DER, node)
        self.bloque().parent = node
        self.condicional_prime().parent = node
        return node

    def condicional_prime(self):
        # CondicionalPrime -> mana_chayqa_ari ( Expresion ) Bloque
        #                     CondicionalPrime
        #                   | mana_chayqa Bloque
        #                   | ε
        node = Node("CondicionalPrime")
        if self.etiqueta == E.CONDICION_MANA_CHAYQA_ARI:
            self.consume(E.CONDICION_MANA_CHAYQA_ARI, node)
            self.consume(E.PAREN_IZQ, node)
            self.expresion().parent = node
            self.consume(E.PAREN_DER, node)
            self.bloque().parent = node
            self.condicional_prime().parent = node
        elif self.etiqueta == E.CONDICION_MANA_CHAYQA:
            self.consume(E.CONDICION_MANA_CHAYQA, node)
            self.bloque().parent = node
        return node

    # ------------------------------------------------------------------
    # Bucles
    # ------------------------------------------------------------------
    def mientras(self):
        # Mientras -> chaykama ( Expresion ) Bloque
        node = Node("Mientras")
        self.consume(E.BUCLE_WHILE, node)
        self.consume(E.PAREN_IZQ, node)
        self.expresion().parent = node
        self.consume(E.PAREN_DER, node)
        self.bloque().parent = node
        return node

    def para(self):
        # Para -> imapaq ( ParaInicio ; Expresion ; Asignaciones ) Bloque
        node = Node("Para")
        self.consume(E.BUCLE_FOR, node)
        self.consume(E.PAREN_IZQ, node)
        self.para_inicio().parent = node
        self.consume(E.PUNTOYCOMA, node)
        self.expresion().parent = node
        self.consume(E.PUNTOYCOMA, node)
        self.asignaciones().parent = node
        self.consume(E.PAREN_DER, node)
        self.bloque().parent = node
        return node

    def para_inicio(self):
        # ParaInicio -> Declaraciones | Asignaciones
        node = Node("ParaInicio")
        if self.etiqueta in PRIMEROS["Declaraciones"]:
            self.declaraciones().parent = node
        elif self.etiqueta in PRIMEROS["Asignaciones"]:
            self.asignaciones().parent = node
        else:
            self.error_esperado(PRIMEROS["ParaInicio"], node)
        return node

    # ------------------------------------------------------------------
    # Expresiones. Cada nivel tiene mayor precedencia que el anterior:
    #   ||  <  &&  <  relacionales  <  + -  <  * /  <  - unario
    # ------------------------------------------------------------------
    def operador(self, nombre):
        # Operador -> el token actual (ya verificado por quien llama)
        node = Node(nombre)
        self.consume(self.etiqueta, node)
        return node

    def _nivel(self, nombre, operando, nombre_prima, operadores,
               nombre_operador):
        """
        Nivel de precedencia con operadores asociativos por la izquierda:
            X -> Operando XPrime
            XPrime -> Operador Operando XPrime | ε
        La recursión de XPrime se implementa con un bucle; el árbol queda
        igual que con la versión recursiva.
        """
        node = Node(nombre)
        operando().parent = node
        prima = Node(nombre_prima, parent=node)
        while self.etiqueta in operadores:
            self.operador(nombre_operador).parent = prima
            operando().parent = prima
            prima = Node(nombre_prima, parent=prima)
        return node

    def expresion(self):
        # Expresion -> ExpresionY ExpresionOPrime
        # ExpresionOPrime -> || ExpresionY ExpresionOPrime | ε
        return self._nivel("Expresion", self.expresion_y, "ExpresionOPrime",
                           {E.O_LOGICO}, "OperadorLogico")

    def expresion_y(self):
        # ExpresionY -> ExpresionRelacional ExpresionYPrime
        # ExpresionYPrime -> && ExpresionRelacional ExpresionYPrime | ε
        return self._nivel("ExpresionY", self.expresion_relacional,
                           "ExpresionYPrime", {E.Y_LOGICO}, "OperadorLogico")

    def expresion_relacional(self):
        # ExpresionRelacional -> ExpresionAditiva ExpresionRelacionalPrime
        # ExpresionRelacionalPrime -> OperadorRelacional ExpresionAditiva | ε
        # (no es asociativa: "a < b < c" no es válido)
        node = Node("ExpresionRelacional")
        self.expresion_aditiva().parent = node
        prima = Node("ExpresionRelacionalPrime", parent=node)
        if self.etiqueta in PRIMEROS["OperadorRelacional"]:
            self.operador("OperadorRelacional").parent = prima
            self.expresion_aditiva().parent = prima
        return node

    def expresion_aditiva(self):
        # ExpresionAditiva -> ExpresionMultiplicativa ExpresionAditivaPrime
        return self._nivel("ExpresionAditiva", self.expresion_multiplicativa,
                           "ExpresionAditivaPrime",
                           PRIMEROS["OperadorAditivo"], "OperadorAditivo")

    def expresion_multiplicativa(self):
        # ExpresionMultiplicativa -> Termino ExpresionMultiplicativaPrime
        return self._nivel("ExpresionMultiplicativa", self.termino,
                           "ExpresionMultiplicativaPrime",
                           PRIMEROS["OperadorMultiplicativo"],
                           "OperadorMultiplicativo")

    def termino(self):
        # Termino -> - Termino | ( Expresion ) | id | entero | flotante
        #          | caracter | cadena | chiqaq | yanqa
        node = Node("Termino")
        if self.etiqueta == E.MENOS:
            self.consume(E.MENOS, node)
            self.termino().parent = node
        elif self.etiqueta == E.PAREN_IZQ:
            self.consume(E.PAREN_IZQ, node)
            self.expresion().parent = node
            self.consume(E.PAREN_DER, node)
        elif self.etiqueta in PRIMEROS["Termino"]:
            self.consume(self.etiqueta, Node(self.etiqueta, parent=node))
        else:
            self.error_esperado(PRIMEROS["Termino"], node)
        return node

    def save_syntax_outputs(self, root: object, base_filename: str):
        os.makedirs("outputs/sintactic", exist_ok=True)
        render_tree(root, base_filename + ".txt")
        export_tree(root, base_filename)
