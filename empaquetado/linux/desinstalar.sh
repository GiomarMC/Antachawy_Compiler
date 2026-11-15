#!/bin/sh
# Quita Antachawi Yachay. Usa sudo si lo instalaste con sudo.
set -eu

if [ "$(id -u)" -eq 0 ]; then
    PROGRAMA=/opt/antachawi-yachay
    BINARIOS=/usr/local/bin
    COMPARTIDO=/usr/share
else
    PROGRAMA="${XDG_DATA_HOME:-$HOME/.local/share}/antachawi-yachay"
    BINARIOS="$HOME/.local/bin"
    COMPARTIDO="${XDG_DATA_HOME:-$HOME/.local/share}"
fi

rm -f "$BINARIOS/antachawi-ide" "$BINARIOS/antachawi"
rm -f "$COMPARTIDO/applications/antachawi-yachay.desktop"
rm -f "$COMPARTIDO/mime/packages/antachawi-yachay.xml"
rm -f "$COMPARTIDO"/icons/hicolor/*/apps/antachawi-yachay.png
rm -rf "$PROGRAMA"
update-mime-database "$COMPARTIDO/mime" >/dev/null 2>&1 || true
update-desktop-database "$COMPARTIDO/applications" >/dev/null 2>&1 || true
echo "Antachawi Yachay se desinstaló."
