# Genera un mundo aleatorio grande para medir tiempos.
# Uso: python3 generar_entrada.py R C N_GEN > entrada
# Ejemplo: python3 generar_entrada.py 1000 1000 500 > input1000x1000
import random
import sys

R = int(sys.argv[1])
C = int(sys.argv[2])
N_GEN = int(sys.argv[3])
random.seed(42)  # misma semilla = mismo mundo siempre

objetos = []
for x in range(R):
    for y in range(C):
        r = random.random()
        if r < 0.05:
            objetos.append(("ROCK", x, y))
        elif r < 0.25:
            objetos.append(("RABBIT", x, y))
        elif r < 0.30:
            objetos.append(("FOX", x, y))

print(3, 20, 10, N_GEN, R, C, len(objetos))
for nombre, x, y in objetos:
    print(nombre, x, y)
