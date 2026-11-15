#!/bin/sh
# Opcional: permite usar "antachawi" y "antachawi-ide" en la Terminal.
# Primero arrastra "Antachawi Yachay" a Aplicaciones y luego haz doble clic
# en este archivo (pedirá tu contraseña).
set -eu
APP="/Applications/Antachawi Yachay.app"
if [ ! -d "$APP" ]; then
    echo "Primero arrastra \"Antachawi Yachay\" a la carpeta Aplicaciones."
    exit 1
fi
sudo mkdir -p /usr/local/bin
sudo ln -sf "$APP/Contents/Resources/cli/antachawi" /usr/local/bin/antachawi
sudo ln -sf "$APP/Contents/MacOS/antachawi-yachay" /usr/local/bin/antachawi-ide
echo "Listo: ya puedes escribir \"antachawi-ide\" o \"antachawi programa.awi\"."
