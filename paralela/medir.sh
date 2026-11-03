#!/bin/bash
# Mide el tiempo de la version secuencial y de la paralela con varios hilos.
# Uso (desde la carpeta paralela): ./medir.sh ../tests/input200x200
# Antes hay que compilar las dos versiones (ver README).

ENTRADA=$1

echo "Secuencial:"
../secuencial/ecosistema < "$ENTRADA" > /dev/null

for HILOS in 1 2 4 8; do
    echo "Paralela con $HILOS hilos:"
    OMP_NUM_THREADS=$HILOS ./ecosistema < "$ENTRADA" > /dev/null
done
