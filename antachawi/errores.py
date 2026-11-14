"""Formato común de los errores y advertencias que reportan todas las
etapas.

Un error es un diccionario (fácil de convertir a JSON para un IDE):

    codigo      "SEM004" (ver antachawi/mensajes.py)
    parametros  {"nombre": "x"}: con ellos se arma el texto en cualquier
                idioma
    textos      {"es": "...", "qu": "..." o None si falta la traducción}
    mensaje     el texto en español (igual a textos["es"])
    fase        lexico, sintactico, semantico o ejecucion
    gravedad    error o advertencia
    linea, columna, longitud, contenido: dónde está (ver nuevo_error)
"""
from antachawi.mensajes import ES, Mensaje


def nuevo_error(mensaje: Mensaje, linea, contenido, columna=None,
                longitud=1, parametros=None):
    """
    Crea un error de compilación.

    mensaje:    el Mensaje del catálogo.
    linea:      línea donde ocurrió (empieza en 1).
    contenido:  texto de esa línea en el código fuente.
    columna:    columna donde empieza el error (empieza en 1), o None si
                no se conoce; en ese caso solo se muestra la línea.
    longitud:   cuántos caracteres se subrayan desde `columna`.
    parametros: diccionario con los valores para las llaves del mensaje
                ({nombre}...).
    """
    parametros = dict(parametros or {})
    textos = mensaje.textos(**parametros)
    return {
        "codigo": mensaje.codigo,
        "parametros": parametros,
        "textos": textos,
        "mensaje": textos[ES],
        "fase": mensaje.fase,
        "gravedad": mensaje.gravedad,
        "linea": linea,
        "columna": columna,
        "longitud": max(1, longitud),
        "contenido": contenido,
    }


def texto_de(error, idioma=ES) -> str:
    """Texto del error en `idioma`; si falta la traducción, en español."""
    return error["textos"].get(idioma) or error["textos"][ES]
