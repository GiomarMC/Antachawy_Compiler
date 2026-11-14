"""
Controlador del compilador: encadena las fases del Libro del Dragón
(figura 1.6).

    código fuente
      -> análisis léxico          (scanner.py)
      -> análisis sintáctico      (parser.py, constructor_ast.py)
      -> análisis semántico       (semantic.py)
      -> código intermedio        (intermedio.py)
      -> optimización             (optimizador.py)
      -> generación de código     (generador_x86.py)
    ensamblador x86-64

El archivo .s resultante se ensambla y enlaza con la biblioteca de C
usando el ensamblador y el enlazador del sistema (cc, gcc o clang), como
hace cualquier compilador de C. Plataformas: Linux, macOS y Windows
(MinGW), en x86-64 (ver plataformas.py).

Las fases se ejecutan con antachawi/api.py, que no imprime nada; aquí solo
se muestran los resultados y se guardan los archivos de depuración.
"""
import os
import shutil
import subprocess
import tempfile

from tabulate import tabulate

from antachawi import api
from antachawi.ast_nodos import formatear
from antachawi.bloques_basicos import formatear_bloques
from antachawi.consolehandler import ConsoleHandler
from antachawi.intermedio import formatear_codigo
from antachawi.mensajes import AMBOS
from antachawi.parser import export_tree, render_tree
from antachawi.plataformas import plataforma_actual
from antachawi.sourcecode import SourceCode

DIRECTORIO_LEXICO = "outputs/lexicon"
DIRECTORIO_SINTACTICO = "outputs/sintactic"
DIRECTORIO_SEMANTICO = "outputs/semantic"
DIRECTORIO_INTERMEDIO = "outputs/intermediate"
DIRECTORIO_ENSAMBLADOR = "outputs/codegen"
ARCHIVO_ENSAMBLADOR = "programa.s"

# Fases de análisis, en orden, con el nombre que se muestra en la consola
_FASES = [
    (api.LEXICO, "Lexical Analysis"),
    (api.SINTACTICO, "Syntax Analysis"),
    (api.SEMANTICO, "Semantic Analysis"),
]


def plataforma_soportada():
    return plataforma_actual() is not None


def buscar_enlazador():
    """cc, gcc o clang: se usan solo para ensamblar y enlazar."""
    return shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")


def _guardar(directorio, nombre, contenido):
    os.makedirs(directorio, exist_ok=True)
    ruta = os.path.join(directorio, nombre)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    return ruta


class Compiler:
    """Compilador de consola: ejecuta las fases con antachawi/api.py,
    muestra los resultados y, si todo sale bien, ensambla y enlaza."""

    def __init__(self, source_code: str, output_file: str,
                 debug: bool = False, optimize: bool = True,
                 idioma: str = AMBOS):
        self.source_code = source_code
        self.code = SourceCode(source_code)
        self.plataforma = plataforma_actual()
        self.output_file = output_file or self.default_output_file()
        self.debug = debug
        self.optimize = optimize
        self.console_handler = ConsoleHandler(idioma)
        self.resultado = None

    def default_output_file(self):
        if self.plataforma is None:
            return "run"
        return self.plataforma.salida_por_defecto

    def compile(self):
        resultado = api.analizar_fuente(self.code, self.optimize)
        self.resultado = resultado
        if not self.report_analysis(resultado):
            return False
        self.report_synthesis(resultado)
        ensamblador = self.generate_target_code(resultado)
        if ensamblador is None:
            return False
        return self.assemble_and_link(ensamblador, self.output_file)

    # ------------------------------------------------------------------
    # Análisis
    # ------------------------------------------------------------------
    def report_analysis(self, resultado):
        """Muestra el resultado de las fases de análisis (y guarda sus
        archivos de depuración). Devuelve True si no hubo errores."""
        for fase, nombre in _FASES:
            if fase == api.SEMANTICO:
                self.console_handler.show_warnings(resultado.advertencias)
            if resultado.fase_fallida == fase:
                print(f"--> {nombre} Failed")
                self.console_handler.show_errors(resultado.errores)
                return False
            print(f"--> {nombre} Passed")
            if self.debug:
                self.save_analysis_outputs(fase, resultado)
        return True

    @staticmethod
    def save_analysis_outputs(fase, resultado):
        if fase == api.LEXICO:
            filas = [[t.lexema, t.etiqueta, t.linea, t.columna]
                     for t in resultado.tokens]
            _guardar(DIRECTORIO_LEXICO, "tokens.txt", tabulate(
                filas, ["Lexema", "Etiqueta", "Linea", "Columna"],
                tablefmt="grid"))
        elif fase == api.SINTACTICO:
            os.makedirs(DIRECTORIO_SINTACTICO, exist_ok=True)
            base = os.path.join(DIRECTORIO_SINTACTICO, "AbstractSyntaxTree")
            render_tree(resultado.arbol, base + ".txt")
            export_tree(resultado.arbol, base)
        else:
            _guardar(DIRECTORIO_SEMANTICO, "symbol_table.txt",
                     "Tabla de Símbolos:\n" + resultado.tabla.como_tabla())
            _guardar(DIRECTORIO_SEMANTICO, "ast.txt",
                     formatear(resultado.ast) + "\n")

    # ------------------------------------------------------------------
    # Síntesis
    # ------------------------------------------------------------------
    def report_synthesis(self, resultado):
        print("--> Intermediate Code Generated")
        if self.debug:
            self._guardar_codigo("codigo_intermedio.txt",
                                 "bloques_basicos.txt",
                                 resultado.intermedio,
                                 resultado.bloques(optimizado=False))
        if resultado.optimizado is None:
            return
        print(f"--> Code Optimized ({len(resultado.intermedio)} -> "
              f"{len(resultado.optimizado)} instructions)")
        if self.debug:
            self._guardar_codigo("codigo_optimizado.txt",
                                 "bloques_optimizados.txt",
                                 resultado.optimizado, resultado.bloques())

    @staticmethod
    def _guardar_codigo(archivo_codigo, archivo_bloques, codigo, bloques):
        _guardar(DIRECTORIO_INTERMEDIO, archivo_codigo,
                 formatear_codigo(codigo) + "\n")
        _guardar(DIRECTORIO_INTERMEDIO, archivo_bloques,
                 formatear_bloques(bloques))

    def generate_target_code(self, resultado):
        if self.plataforma is None:
            print("--> Error: unsupported platform. The compiler generates "
                  "x86-64 code for Linux, macOS and Windows.")
            return None
        ensamblador = resultado.ensamblador(self.plataforma)
        print(f"--> x86-64 Assembly Generated ({self.plataforma.nombre})")
        if self.debug:
            _guardar(DIRECTORIO_ENSAMBLADOR, ARCHIVO_ENSAMBLADOR,
                     ensamblador)
        return ensamblador

    def assemble_and_link(self, ensamblador, output_file):
        """Ensambla y enlaza el programa. Devuelve True solo si se creó
        el ejecutable."""
        enlazador = buscar_enlazador()
        if enlazador is None:
            print("--> Error: cc/gcc/clang was not found. Install gcc "
                  "(MinGW-w64 on Windows) to assemble and link the "
                  "executable.")
            return False
        with tempfile.TemporaryDirectory() as directorio:
            fuente = _guardar(directorio, ARCHIVO_ENSAMBLADOR, ensamblador)
            comando = [enlazador, *self.plataforma.opciones_enlazador,
                       "-x", "assembler", fuente, "-o", output_file]
            resultado = subprocess.run(comando, capture_output=True,
                                       text=True, check=False)
        if resultado.returncode != 0:
            print(f"--> Error while assembling: {resultado.stderr}")
            return False
        print("--> Compilation successful. "
              f"Executable created: {output_file}")
        return True
