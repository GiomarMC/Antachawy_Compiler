import argparse
import json
import sys
from pathlib import Path

from antachawi import __version__
from antachawi.api import a_json, analizar_archivo
from antachawi.compiler import Compiler
from antachawi.mensajes import AMBOS, ES, QU


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Antachawi compiler CLI\n"
            "— Antachawi tupaq willay ruwana purichiq"),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=False
        )
    parser.add_argument(
        "-h",
        "--help",
        "--yanapa",
        action="help",
        help=(
            "Muestra este mensaje de ayuda\n"
            "— Kay yanapanaq willaykuna")
        )
    parser.add_argument(
        "file_path",
        type=Path,
        help=(
            "Archivo de entrada con código fuente\n"
            "— Yaykuy qillqa kódigowan")
        )
    parser.add_argument(
        "-o",
        "--output",
        "--lluqsi",
        type=str,
        help=(
            "Nombre del archivo de salida\n"
            "— Lluqsisqa qillqap sutin")
        )
    parser.add_argument(
        "-d",
        "--debug",
        "--pantaymaskay",
        action="store_true",
        help=(
            "Genera archivos de depuración en la carpeta outputs\n"
            "— Pantay maskaq qillqakunata ruwachin")
        )
    parser.add_argument(
        "-n",
        "--no-optimizar",
        "--mana-allinchaspa",
        action="store_true",
        help=(
            "Genera el código sin la fase de optimización\n"
            "— Mana allinchaspa kódigota ruwan")
        )
    parser.add_argument(
        "-i",
        "--idioma",
        "--simi",
        choices=[ES, QU, AMBOS],
        default=AMBOS,
        help="Idioma de los mensajes de error: es, qu o ambos"
        )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Solo analiza el programa y muestra el resultado en JSON "
            "(para editores e IDEs); no crea el ejecutable")
        )
    parser.add_argument(
        "--traza",
        action="store_true",
        help=(
            "Con --json, ejecuta el programa con el intérprete e incluye "
            "la traza paso a paso")
        )
    parser.add_argument(
        "-v",
        "--version",
        "--wichay",
        action="version",
        version=f"Antachawi compiler version {__version__}",
        help=(
            "Muestra la versión del compilador\n"
            "— Tupaq willay ruwap wersiónninta rikuchin")
        )

    args = parser.parse_args()

    file_path = args.file_path
    output_file = args.output if args.output else None
    debug = args.debug

    if not file_path.exists():
        parser.error(f"El archivo {file_path} no existe")

    if args.json:
        resultado = analizar_archivo(file_path,
                                     optimizar_codigo=not args.no_optimizar)
        print(json.dumps(a_json(resultado, con_traza=args.traza),
                         ensure_ascii=False, indent=2))
        return 0 if resultado.exito else 1

    compiler = Compiler(str(file_path), output_file, debug,
                        optimize=not args.no_optimizar, idioma=args.idioma)
    result = compiler.compile()

    if result:
        print("Successful compilation")
        return 0
    print("Failed compilation")
    return 1


if __name__ == "__main__":
    sys.exit(main())
