"""
Construye el instalador de Antachawi (lenguaje + Antachawi Yachay) para el
sistema operativo en el que se ejecuta. No se puede construir el de otro
sistema: el de Windows se construye en Windows, el de macOS en macOS, etc.
(GitHub Actions construye los tres: .github/workflows/instaladores.yml).

    pip install . PySide6-Essentials pyinstaller pillow
    python empaquetado/construir.py

Resultado en dist/instaladores/:
  * Linux:   AntachawiYachay-<versión>-linux-x86_64.tar.gz
             (se descomprime y se ejecuta ./instalar.sh)
  * Windows: AntachawiYachay-<versión>-windows-x64.exe (necesita Inno Setup)
  * macOS:   AntachawiYachay-<versión>-macos-<arquitectura>.dmg
"""
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AQUI = RAIZ / "empaquetado"
TRABAJO = RAIZ / "build" / "empaquetado"
PYINSTALLER = TRABAJO / "pyinstaller"
SALIDA = RAIZ / "dist" / "instaladores"

NOMBRE = "Antachawi Yachay"
NOMBRE_CORTO = "AntachawiYachay"
EJECUTABLE_IDE = "antachawi-yachay"
EJECUTABLE_CLI = "antachawi"
IDENTIFICADOR = "io.github.giomarmc.antachawi"

sys.path.insert(0, str(RAIZ))
from antachawi import __version__ as VERSION  # noqa: E402


def ejecutar(*comando, **opciones):
    print("+", " ".join(str(c) for c in comando), flush=True)
    subprocess.run([str(c) for c in comando], check=True, **opciones)


# Íconos


def generar_iconos() -> dict:
    """Dibuja a Tunki en varios tamaños (con Qt, sin pantalla) y arma el
    .ico de Windows y el .icns de macOS con Pillow."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PIL import Image
    from PySide6.QtGui import QGuiApplication

    from antachawi.ide import iconos

    _ = QGuiApplication.instance() or QGuiApplication([])
    carpeta = TRABAJO / "iconos"
    carpeta.mkdir(parents=True, exist_ok=True)
    pngs = {}
    for lado in iconos.TAMANOS_DEL_ICONO:
        ruta = carpeta / f"{EJECUTABLE_IDE}-{lado}.png"
        iconos.imagen_de_la_aplicacion(lado).save(str(ruta))
        pngs[lado] = ruta
    grande = Image.open(pngs[512])
    ico = carpeta / f"{EJECUTABLE_IDE}.ico"
    grande.save(ico, sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
    icns = carpeta / f"{EJECUTABLE_IDE}.icns"
    grande.save(icns)
    return {"png": pngs, "ico": ico, "icns": icns}


# PyInstaller


def pyinstaller(lanzador: str, nombre: str, *opciones):
    ejecutar(
        sys.executable, "-m", "PyInstaller", AQUI / lanzador,
        "--noconfirm", "--clean", "--onedir", "--name", nombre,
        "--collect-data", "antachawi",
        "--exclude-module", "PIL", "--exclude-module", "tkinter",
        "--distpath", PYINSTALLER / "dist",
        "--workpath", PYINSTALLER / "trabajo",
        "--specpath", PYINSTALLER,
        *opciones)
    return PYINSTALLER / "dist" / nombre


def construir_ejecutables(iconos: dict):
    icono = iconos["icns"] if sys.platform == "darwin" else iconos["ico"]
    ide = pyinstaller(
        "lanzador_ide.py", EJECUTABLE_IDE, "--windowed", "--icon", icono,
        "--osx-bundle-identifier", IDENTIFICADOR)
    cli = pyinstaller(
        "lanzador_cli.py", EJECUTABLE_CLI, "--console",
        "--contents-directory", "_cli",
        "--exclude-module", "PySide6", "--exclude-module", "shiboken6")
    return ide, cli


def juntar(ide: Path, cli: Path) -> Path:
    """Una sola carpeta con el IDE y el compilador. Cada uno trae sus
    bibliotecas en su propia subcarpeta (_internal y _cli)."""
    destino = TRABAJO / NOMBRE_CORTO
    shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(ide, destino, symlinks=True)
    shutil.copytree(cli, destino, symlinks=True, dirs_exist_ok=True)
    shutil.copy(RAIZ / "LICENSE", destino / "LICENSE.txt")
    return destino


# Un instalador por sistema


def instalador_linux(ide: Path, cli: Path, iconos: dict) -> Path:
    carpeta = juntar(ide, cli)
    (carpeta / "iconos").mkdir()
    for lado, png in iconos["png"].items():
        shutil.copy(png, carpeta / "iconos" / f"{lado}.png")
    for archivo in (AQUI / "linux").iterdir():
        shutil.copy(archivo, carpeta / archivo.name)
    for guion in ("instalar.sh", "desinstalar.sh"):
        (carpeta / guion).chmod(0o755)
    maquina = platform.machine().lower() or "x86_64"
    nombre = f"{NOMBRE_CORTO}-{VERSION}-linux-{maquina}"
    paquete = SALIDA / f"{nombre}.tar.gz"
    with tarfile.open(paquete, "w:gz") as tar:
        tar.add(carpeta, arcname=nombre)
    return paquete


def buscar_inno_setup() -> str:
    for candidato in (
            shutil.which("iscc"),
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe"):
        if candidato and Path(candidato).exists():
            return candidato
    sys.exit("No se encontró Inno Setup 6 (ISCC.exe). Instálalo desde "
             "https://jrsoftware.org/isdl.php o con: choco install innosetup")


def instalador_windows(ide: Path, cli: Path, iconos: dict) -> Path:
    carpeta = juntar(ide, cli)
    shutil.copy(iconos["ico"], carpeta / f"{EJECUTABLE_IDE}.ico")
    nombre = f"{NOMBRE_CORTO}-{VERSION}-windows-x64"
    ejecutar(
        buscar_inno_setup(), AQUI / "windows" / "antachawi.iss",
        f"/DVersion={VERSION}", f"/DOrigen={carpeta}",
        f"/DSalida={SALIDA}", f"/DNombreSalida={nombre}")
    return SALIDA / f"{nombre}.exe"


def completar_info_plist(ruta: Path):
    """Nombre visible, versión y los archivos .awi (doble clic los abre
    en Antachawi Yachay)."""
    with open(ruta, "rb") as archivo:
        info = plistlib.load(archivo)
    info.update({
        "CFBundleName": NOMBRE,
        "CFBundleDisplayName": NOMBRE,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "CFBundleDocumentTypes": [{
            "CFBundleTypeName": "Programa Antachawi",
            "CFBundleTypeRole": "Editor",
            "CFBundleTypeExtensions": ["awi"],
            "LSHandlerRank": "Owner",
        }],
    })
    with open(ruta, "wb") as archivo:
        plistlib.dump(info, archivo)


def instalador_macos(ide: Path, cli: Path) -> Path:
    aplicacion = TRABAJO / f"{NOMBRE}.app"
    shutil.rmtree(aplicacion, ignore_errors=True)
    shutil.copytree(ide.with_suffix(".app"), aplicacion, symlinks=True)
    # El compilador va dentro de la aplicación; instalar-terminal.command
    # lo enlaza en /usr/local/bin.
    shutil.copytree(cli, aplicacion / "Contents" / "Resources" / "cli",
                    symlinks=True)
    completar_info_plist(aplicacion / "Contents" / "Info.plist")
    ejecutar("codesign", "--force", "--deep", "--sign", "-", aplicacion)

    imagen = TRABAJO / "dmg"
    shutil.rmtree(imagen, ignore_errors=True)
    imagen.mkdir()
    shutil.copytree(aplicacion, imagen / aplicacion.name, symlinks=True)
    os.symlink("/Applications", imagen / "Applications")
    for archivo in (AQUI / "macos").iterdir():
        shutil.copy(archivo, imagen / archivo.name)
    (imagen / "instalar-terminal.command").chmod(0o755)

    nombre = f"{NOMBRE_CORTO}-{VERSION}-macos-{platform.machine()}"
    dmg = SALIDA / f"{nombre}.dmg"
    dmg.unlink(missing_ok=True)
    ejecutar("hdiutil", "create", "-volname", NOMBRE, "-srcfolder", imagen,
             "-ov", "-format", "UDZO", dmg)
    return dmg


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    iconos = generar_iconos()
    ide, cli = construir_ejecutables(iconos)
    if sys.platform.startswith("linux"):
        resultado = instalador_linux(ide, cli, iconos)
    elif sys.platform == "win32":
        resultado = instalador_windows(ide, cli, iconos)
    elif sys.platform == "darwin":
        resultado = instalador_macos(ide, cli)
    else:
        sys.exit(f"Sistema no soportado: {sys.platform}")
    print(f"\nListo: {resultado}")


if __name__ == "__main__":
    main()
