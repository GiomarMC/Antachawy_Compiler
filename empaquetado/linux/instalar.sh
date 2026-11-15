#!/bin/sh
# Instala Antachawi (el lenguaje) y Antachawi Yachay (el entorno con Tunki).
#
#   ./instalar.sh          para tu usuario (no pide contraseña)
#   sudo ./instalar.sh     para todos los usuarios del equipo
#
# Después:  antachawi-ide           abre el entorno (también está en el menú)
#           antachawi programa.awi  compila desde la terminal (necesita gcc)
set -eu

ORIGEN=$(cd "$(dirname "$0")" && pwd)

if [ "$(id -u)" -eq 0 ]; then
    PROGRAMA=/opt/antachawi-yachay
    BINARIOS=/usr/local/bin
    COMPARTIDO=/usr/share
else
    PROGRAMA="${XDG_DATA_HOME:-$HOME/.local/share}/antachawi-yachay"
    BINARIOS="$HOME/.local/bin"
    COMPARTIDO="${XDG_DATA_HOME:-$HOME/.local/share}"
fi

if [ "$ORIGEN" = "$(cd "$PROGRAMA" 2>/dev/null && pwd)" ]; then
    echo "Ejecuta instalar.sh desde la carpeta descomprimida, no desde $PROGRAMA." >&2
    exit 1
fi

echo "Instalando Antachawi Yachay en $PROGRAMA"
rm -rf "$PROGRAMA"
mkdir -p "$PROGRAMA" "$BINARIOS" "$COMPARTIDO/applications" "$COMPARTIDO/mime/packages"
cp -R "$ORIGEN"/. "$PROGRAMA"/

ln -sf "$PROGRAMA/antachawi-yachay" "$BINARIOS/antachawi-ide"
ln -sf "$PROGRAMA/antachawi" "$BINARIOS/antachawi"

for icono in "$PROGRAMA"/iconos/*.png; do
    lado=$(basename "$icono" .png)
    destino="$COMPARTIDO/icons/hicolor/${lado}x${lado}/apps"
    mkdir -p "$destino"
    cp "$icono" "$destino/antachawi-yachay.png"
done

sed "s|@PROGRAMA@|$PROGRAMA|g" "$ORIGEN/antachawi-yachay.desktop" \
    > "$COMPARTIDO/applications/antachawi-yachay.desktop"
cp "$ORIGEN/antachawi-yachay.xml" "$COMPARTIDO/mime/packages/"

# Actualiza el menú, los íconos y los tipos de archivo (si existen las
# herramientas; si no, se ven al volver a iniciar sesión).
update-mime-database "$COMPARTIDO/mime" >/dev/null 2>&1 || true
update-desktop-database "$COMPARTIDO/applications" >/dev/null 2>&1 || true
gtk-update-icon-cache -q -t "$COMPARTIDO/icons/hicolor" >/dev/null 2>&1 || true

echo "Listo. Busca \"Antachawi Yachay\" en el menú o escribe: antachawi-ide"
case ":$PATH:" in
    *":$BINARIOS:"*) ;;
    *) echo "Nota: agrega $BINARIOS a tu PATH para usar los comandos en la terminal." ;;
esac
