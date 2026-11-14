class Token:
    """Unidad léxica con su posición en el archivo fuente."""

    def __init__(self, lexema, etiqueta, linea, idx, columna=1):
        self.lexema = lexema
        self.etiqueta = etiqueta
        self.linea = linea        # línea, empieza en 1
        self.idx = idx            # posición absoluta en el archivo
        self.columna = columna    # columna, empieza en 1

    @property
    def columna_final(self) -> int:
        """Columna justo después del último carácter del token."""
        return self.columna + len(self.lexema)

    def __str__(self) -> str:
        return f"({self.lexema}, {self.etiqueta}, {self.linea}:{self.columna})"
