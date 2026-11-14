"""
Generador de programas Antachawi aleatorios (y válidos) para las pruebas
diferenciales: se usan todas las construcciones del lenguaje, con bucles
que siempre terminan.
"""
import random

OPERADORES_RELACIONALES = ["<", ">", "<=", ">=", "==", "!="]
CARACTERES = ["a", "b", "z", "ñ", "λ", "€", "😀", "\\n"]
TEXTOS = ["hola", "", "a b", "ñandú", "x\\ty"]


class GeneradorDeProgramas:
    def __init__(self, semilla: int):
        self.r = random.Random(semilla)
        self.contador = 0
        self.generadores = {
            "yupay": self.entero,
            "chunkayuq": self.decimal,
            "bool": self.booleano,
            "qaytu": self.texto,
            "sananpa": self.caracter,
        }

    def _variables(self, variables, tipo):
        return [nombre for nombre, t in variables if t == tipo]

    def _nombre(self, prefijo="v"):
        self.contador += 1
        return f"{prefijo}{self.contador}"

    # ------------------------------------------------------------------
    # Expresiones
    # ------------------------------------------------------------------
    def entero(self, d, variables):
        r = self.r
        if d <= 0 or r.random() < .3:
            return r.choice([str(r.randint(-9, 20))]
                            + self._variables(variables, "yupay"))
        operador = r.choice("+-*/")
        if operador == "/":
            return f"({self.entero(d - 1, variables)} / {r.randint(1, 5)})"
        if r.random() < .1:
            return f"-({self.entero(d - 1, variables)})"
        return (f"({self.entero(d - 1, variables)} {operador} "
                f"{self.entero(d - 1, variables)})")

    def decimal(self, d, variables):
        r = self.r
        if d <= 0 or r.random() < .3:
            return r.choice([f"{r.randint(0, 9)}.{r.randint(0, 99)}"]
                            + self._variables(variables, "chunkayuq"))
        izquierda = (self.decimal(d - 1, variables) if r.random() < .7
                     else self.entero(d - 1, variables))
        operador = r.choice("+-*")
        if r.random() < .15:
            return f"({izquierda} / {r.randint(1, 4)}.5)"
        return f"({izquierda} {operador} {self.decimal(d - 1, variables)})"

    def booleano(self, d, variables):
        r = self.r
        opcion = r.random()
        if d <= 0 or opcion < .15:
            return r.choice(["chiqaq", "yanqa"]
                            + self._variables(variables, "bool"))
        relacional = r.choice(OPERADORES_RELACIONALES)
        if opcion < .45:
            return (f"({self.entero(d - 1, variables)} {relacional} "
                    f"{self.entero(d - 1, variables)})")
        if opcion < .55:
            return (f"({self.decimal(d - 1, variables)} "
                    f"{relacional} {self.entero(d - 1, variables)})")
        if opcion < .62:
            return (f"({self.caracter(0, variables)} {relacional} "
                    f"{self.caracter(0, variables)})")
        if opcion < .68:
            return (f"({self.texto(1, variables)} "
                    f"{r.choice(['==', '!='])} {self.texto(1, variables)})")
        return (f"({self.booleano(d - 1, variables)} "
                f"{r.choice(['&&', '||'])} {self.booleano(d - 1, variables)})")

    def texto(self, d, variables):
        r = self.r
        opciones = ['"' + r.choice(TEXTOS) + '"'] + self._variables(
            variables, "qaytu")
        if d <= 0 or r.random() < .5:
            return r.choice(opciones)
        return (f"{self.texto(d - 1, variables)} + "
                f"{self.texto(d - 1, variables)}")

    def caracter(self, _d, variables):
        return self.r.choice([f"'{self.r.choice(CARACTERES)}'"]
                             + self._variables(variables, "sananpa"))

    def expresion(self, tipo, d, variables):
        return self.generadores[tipo](d, variables)

    # ------------------------------------------------------------------
    # Sentencias
    # ------------------------------------------------------------------
    def bloque(self, profundidad, variables, sangria):
        lineas, locales = [], list(variables)
        for _ in range(self.r.randint(1, 5)):
            lineas += self.sentencia(profundidad, locales, sangria)
        # Se usan todas las variables nuevas para que no haya
        # advertencias de variables sin usar
        nuevas = [nombre for nombre, _ in locales[len(variables):]]
        if nuevas:
            lineas.append(f"{sangria}rikuchiy ({', '.join(nuevas)})")
        return lineas

    def sentencia(self, profundidad, locales, sangria):
        opcion = self.r.random()
        if opcion < .3:
            return [self._declaracion(locales, sangria)]
        if opcion < .5 and locales:
            nombre, tipo = self.r.choice(locales)
            # Un texto que se concatena consigo mismo en un bucle crecería
            # sin límite
            d = 0 if tipo == "qaytu" else 3
            return [f"{sangria}{nombre} = "
                    f"{self.expresion(tipo, d, locales)}"]
        if opcion < .75 or profundidad >= 3:
            argumentos = [self.expresion(self.r.choice(list(
                self.generadores)), 2, locales)
                for _ in range(self.r.randint(1, 3))]
            return [f"{sangria}rikuchiy ({', '.join(argumentos)})"]
        if opcion < .87:
            return self._si(profundidad, locales, sangria)
        return self._bucle(profundidad, locales, sangria)

    def _declaracion(self, locales, sangria):
        tipo = self.r.choice(list(self.generadores))
        nombre = self._nombre()
        if self.r.random() < .15:
            linea = f"{sangria}{tipo} {nombre}"
        else:
            linea = (f"{sangria}{tipo} {nombre} = "
                     f"{self.expresion(tipo, 3, locales)}")
        locales.append((nombre, tipo))
        return linea

    def _si(self, profundidad, locales, sangria):
        interior = sangria + "    "
        lineas = [f"{sangria}ari ({self.booleano(3, locales)}) {{"]
        lineas += self.bloque(profundidad + 1, locales, interior)
        if self.r.random() < .5:
            lineas.append(f"{sangria}}} mana_chayqa_ari "
                          f"({self.booleano(2, locales)}) {{")
            lineas += self.bloque(profundidad + 1, locales, interior)
        if self.r.random() < .5:
            lineas.append(f"{sangria}}} mana_chayqa {{")
            lineas += self.bloque(profundidad + 1, locales, interior)
        return lineas + [f"{sangria}}}"]

    def _bucle(self, profundidad, locales, sangria):
        # El contador no se asigna dentro del cuerpo: el bucle termina
        interior = sangria + "    "
        contador = self._nombre("i")
        vueltas = self.r.randint(0, 4)
        cuerpo = self.bloque(profundidad + 1, locales, interior)
        if self.r.random() < .5:
            return [f"{sangria}imapaq (yupay {contador} = 0; "
                    f"{contador} < {vueltas}; {contador} = {contador} + 1)"
                    " {", *cuerpo, f"{sangria}}}"]
        return [f"{sangria}yupay {contador} = {vueltas}",
                f"{sangria}chaykama ({contador} > 0) {{",
                *cuerpo,
                f"{interior}{contador} = {contador} - 1",
                f"{sangria}}}"]

    def programa(self):
        cuerpo = self.bloque(0, [], "    ")
        return "qhapaq ()\n{\n" + "\n".join(cuerpo) + "\n}\n"


def programa_aleatorio(semilla: int) -> str:
    return GeneradorDeProgramas(semilla).programa()
