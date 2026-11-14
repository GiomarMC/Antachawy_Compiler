"""
Análisis semántico sobre el AST (Libro del Dragón, capítulos 2.7 y 6.5).

* Resuelve los nombres con una tabla de símbolos con ámbitos anidados: cada
  bloque abre un ámbito.
* Calcula el tipo de cada expresión (atributo sintetizado `tipo`) con las
  reglas de antachawi/tipos.py y verifica declaraciones, asignaciones y
  condiciones.
* Reporta advertencias que no detienen la compilación: variables sin usar,
  variables que podrían usarse sin valor y divisiones entre cero.

Además enlaza cada Variable, Declaracion y Asignacion con su símbolo
(atributo `simbolo`), que usa la generación de código intermedio.

No calcula valores: eso no es posible en general en tiempo de compilación
(depende de las condiciones) y le corresponde a la optimización
(antachawi/optimizador.py).
"""
import os

from antachawi import mensajes
from antachawi.ast_nodos import (
    Asignacion,
    Binaria,
    Declaracion,
    Imprimir,
    Literal,
    Mientras,
    Para,
    Si,
    Unaria,
    Variable,
    formatear,
)
from antachawi.errores import nuevo_error
from antachawi.sourcecode import SourceCode
from antachawi.symboltable import TablaSimbolos
from antachawi.tipos import (
    BOOL,
    ERROR,
    LOGICOS,
    NUMERICOS,
    es_asignable,
    tipo_binario,
    tipo_unario,
)

DIRECTORIO_SALIDA = "outputs/semantic"


def _es_cero(expresion):
    return (isinstance(expresion, Literal)
            and expresion.tipo_literal in NUMERICOS
            and float(expresion.valor) == 0)


def _ordenar(lista):
    lista.sort(key=lambda e: (e["linea"], e["columna"] or 0))


class SemanticAnalyzer:
    def __init__(self, source_code: SourceCode):
        self.source_code = source_code
        self.errors = []
        self.advertencias = []
        self.tabla = TablaSimbolos()
        self.programa = None
        # Símbolos que con seguridad tienen un valor en este punto del
        # programa, sin importar qué rama de los ari se haya tomado.
        self.inicializadas = set()
        self._advertidas_sin_valor = set()
        self._sentencias = {
            Declaracion: self.visitar_declaracion,
            Asignacion: self.visitar_asignacion,
            Imprimir: self.visitar_imprimir,
            Si: self.visitar_si,
            Mientras: self.visitar_mientras,
            Para: self.visitar_para,
        }
        self._expresiones = {
            Literal: self._tipo_literal,
            Variable: self._tipo_variable,
            Unaria: self._tipo_unaria,
            Binaria: self._tipo_binaria,
        }

    def analyze(self, programa):
        """Analiza el AST y lo devuelve con los tipos completados."""
        self.programa = programa
        self.visitar_bloque(programa.cuerpo, "qhapaq")
        _ordenar(self.errors)
        _ordenar(self.advertencias)
        return programa

    # ------------------------------------------------------------------
    # Errores y advertencias
    # ------------------------------------------------------------------
    def _reportar(self, lista, mensaje, pos, parametros):
        lista.append(nuevo_error(
            mensaje, pos.linea, self.source_code.get_line(pos.linea),
            pos.columna, pos.longitud, parametros))

    def error(self, mensaje, pos, **parametros):
        self._reportar(self.errors, mensaje, pos, parametros)

    def advertencia(self, mensaje, pos, **parametros):
        self._reportar(self.advertencias, mensaje, pos, parametros)

    # ------------------------------------------------------------------
    # Sentencias
    # ------------------------------------------------------------------
    def visitar_bloque(self, bloque, nombre_ambito):
        self.tabla.abrir_ambito(nombre_ambito)
        for sentencia in bloque.sentencias:
            self._sentencias[type(sentencia)](sentencia)
        self._cerrar_ambito()

    def _cerrar_ambito(self):
        for simbolo in self.tabla.cerrar_ambito():
            if not simbolo.usado:
                self.advertencia(mensajes.VARIABLE_NO_USADA, simbolo.pos,
                                 nombre=simbolo.nombre)
            self.inicializadas.discard(simbolo)

    def visitar_declaracion(self, declaracion):
        # El valor se analiza antes de declarar: en "yupay a = a + 1" la
        # 'a' de la derecha todavía no existe.
        if declaracion.valor is not None:
            self.verificar_asignable(declaracion.nombre, declaracion.tipo,
                                     declaracion.valor)

        if self._ya_declarada(declaracion):
            return
        simbolo = self.tabla.declarar(declaracion.nombre, declaracion.tipo,
                                      declaracion.pos)
        declaracion.simbolo = simbolo
        if declaracion.valor is not None:
            self.inicializadas.add(simbolo)

    def _ya_declarada(self, declaracion):
        """Reporta si el nombre ya existe en este bloque o en uno exterior
        (no se permite ocultar variables)."""
        existente = self.tabla.buscar_en_ambito_actual(declaracion.nombre)
        mensaje = mensajes.VARIABLE_REDECLARADA
        if existente is None:
            existente = self.tabla.buscar(declaracion.nombre)
            mensaje = mensajes.VARIABLE_OCULTA
        if existente is None:
            return False
        self.error(mensaje, declaracion.pos, nombre=declaracion.nombre,
                   linea=existente.pos.linea)
        return True

    def visitar_asignacion(self, asignacion):
        simbolo = self.tabla.buscar(asignacion.nombre)
        if simbolo is None:
            self.tipo_de(asignacion.valor)
            self.error(mensajes.ASIGNAR_NO_DECLARADA, asignacion.pos,
                       nombre=asignacion.nombre)
            return
        asignacion.simbolo = simbolo
        self.verificar_asignable(asignacion.nombre, simbolo.tipo,
                                 asignacion.valor)
        self.inicializadas.add(simbolo)

    def verificar_asignable(self, nombre, tipo_destino, expresion):
        tipo_expresion = self.tipo_de(expresion)
        if not es_asignable(tipo_destino, tipo_expresion):
            self.error(mensajes.ASIGNACION_INCOMPATIBLE, expresion.pos,
                       nombre=nombre, tipo=tipo_destino,
                       tipo_expresion=tipo_expresion)

    def visitar_imprimir(self, imprimir):
        for argumento in imprimir.argumentos:
            self.tipo_de(argumento)

    def verificar_condicion(self, condicion):
        tipo = self.tipo_de(condicion)
        if tipo not in (BOOL, ERROR):
            self.error(mensajes.CONDICION_NO_BOOL, condicion.pos,
                       tipo=tipo)

    def visitar_si(self, si):
        self.verificar_condicion(si.condicion)

        # Una variable queda con valor seguro después del ari solo si lo
        # recibió en todas las ramas (sin mana_chayqa, la rama "vacía"
        # no asigna nada).
        antes = set(self.inicializadas)
        self.visitar_bloque(si.entonces, f"ari (línea {si.pos.linea})")
        despues_entonces = self.inicializadas

        self.inicializadas = set(antes)
        if isinstance(si.si_no, Si):
            self.visitar_si(si.si_no)
        elif si.si_no is not None:
            self.visitar_bloque(
                si.si_no, f"mana_chayqa (línea {si.si_no.pos.linea})")
        self.inicializadas = despues_entonces & self.inicializadas

    def visitar_mientras(self, mientras):
        # El cuerpo puede no ejecutarse nunca: lo que se asigna dentro no
        # cuenta como valor seguro después del bucle.
        self.verificar_condicion(mientras.condicion)
        antes = set(self.inicializadas)
        self.visitar_bloque(mientras.cuerpo,
                            f"chaykama (línea {mientras.pos.linea})")
        self.inicializadas = antes

    def visitar_para(self, para):
        # La variable de imapaq vive en su propio ámbito, que contiene
        # también al cuerpo.
        self.tabla.abrir_ambito(f"imapaq (línea {para.pos.linea})")
        self._sentencias[type(para.inicio)](para.inicio)
        self.verificar_condicion(para.condicion)
        antes = set(self.inicializadas)
        self.visitar_bloque(para.cuerpo, "cuerpo de imapaq")
        self.visitar_asignacion(para.paso)
        self.inicializadas = antes
        self._cerrar_ambito()

    # ------------------------------------------------------------------
    # Expresiones: cada una devuelve su tipo y lo guarda en el nodo
    # ------------------------------------------------------------------
    def tipo_de(self, expresion):
        expresion.tipo = self._expresiones[type(expresion)](expresion)
        return expresion.tipo

    @staticmethod
    def _tipo_literal(literal):
        return literal.tipo_literal

    def _tipo_variable(self, variable):
        simbolo = self.tabla.buscar(variable.nombre)
        if simbolo is None:
            self.error(mensajes.USAR_NO_DECLARADA, variable.pos,
                       nombre=variable.nombre)
            return ERROR
        variable.simbolo = simbolo
        simbolo.usado = True
        sin_valor = simbolo not in self.inicializadas
        if sin_valor and simbolo not in self._advertidas_sin_valor:
            self._advertidas_sin_valor.add(simbolo)
            self.advertencia(mensajes.VARIABLE_SIN_VALOR, variable.pos,
                             nombre=variable.nombre)
        return simbolo.tipo

    def _tipo_unaria(self, unaria):
        tipo_operando = self.tipo_de(unaria.operando)
        resultado = tipo_unario(unaria.operador, tipo_operando)
        if resultado is None:
            self.error(mensajes.OPERADOR_UNARIO_INVALIDO, unaria.pos,
                       operador=unaria.operador, tipo=tipo_operando)
            return ERROR
        return resultado

    def _tipo_binaria(self, binaria):
        izquierdo = self.tipo_de(binaria.izquierda)
        derecho = self.tipo_de(binaria.derecha)
        resultado = tipo_binario(binaria.operador, izquierdo, derecho)
        if resultado is None:
            plantilla = (mensajes.OPERADOR_LOGICO_NO_BOOL
                         if binaria.operador in LOGICOS
                         else mensajes.TIPOS_INCOMPATIBLES)
            self.error(plantilla, binaria.pos_operador,
                       operador=binaria.operador, izquierdo=izquierdo,
                       derecho=derecho)
            return ERROR
        if binaria.operador == "/" and _es_cero(binaria.derecha):
            self.advertencia(mensajes.DIVISION_ENTRE_CERO,
                             binaria.derecha.pos)
        return resultado

    # ------------------------------------------------------------------
    # Archivos de depuración
    # ------------------------------------------------------------------
    def save_symbol_table(self, filename="symbol_table.txt"):
        os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)
        filepath = os.path.join(DIRECTORIO_SALIDA, filename)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write("Tabla de Símbolos:\n")
            file.write(self.tabla.como_tabla())

    def save_ast(self, filename="ast.txt"):
        os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)
        filepath = os.path.join(DIRECTORIO_SALIDA, filename)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(formatear(self.programa) + "\n")
