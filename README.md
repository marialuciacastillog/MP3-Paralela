# Simulación de ecosistema: zorros, conejos y rocas

Proyecto de Programación Paralela.

El programa simula un mundo en una matriz donde viven conejos y zorros, y donde también hay rocas. En cada generación primero se mueven todos los conejos y luego todos los zorros, siguiendo las reglas del enunciado. Al final imprime cómo quedó el mundo.

## Estructura del repositorio

```
secuencial/   versión secuencial (C++ con POO)
paralela/     versión paralela con OpenMP
visual/       parte visual y estadísticas
tests/        archivos de prueba (entradas y salidas esperadas)
```

## Versión secuencial

Archivos en la carpeta `secuencial/`:

- `Ecosystem.h`: la clase `Ecosystem` (atributos y métodos) y la estructura `Cell`.
- `Ecosystem.cpp`: el código de cada método.
- `main.cpp`: el programa principal.

### Compilar

```
cd secuencial
g++ -O2 -o ecosistema main.cpp Ecosystem.cpp
```

### Ejecutar

El programa lee la entrada por teclado (entrada estándar), así que se le pasa el archivo con `<`. Los ejemplos están en la carpeta `tests/`.

| Comando | Qué imprime |
|---|---|
| `./ecosistema < ../tests/input5x5` | El mundo final, en el mismo formato de la entrada |
| `./ecosistema all < ../tests/input5x5` | Cada generación, igual que los archivos `allgen` |
| `./ecosistema stats < ../tests/input5x5` | Cuántos conejos y zorros hay en cada generación |

### Formato de entrada

La primera línea tiene los parámetros, en este orden:

```
GEN_PROC_RABBITS GEN_PROC_FOXES GEN_FOOD_FOXES N_GEN R C N
```

Después vienen N líneas, una por objeto: `ROCK`, `RABBIT` o `FOX`, seguido de la fila y la columna. Ejemplo:

```
2 4 3 6 5 5 9
ROCK 0 0
RABBIT 0 2
FOX 0 4
...
```

### Probar que funciona

Se compara la salida con el archivo de salida esperada. Si `diff` no imprime nada, el resultado está bien.

```
./ecosistema < ../tests/input5x5 > salida.txt
diff salida.txt ../tests/output5x5
```

La versión secuencial da el resultado esperado en todos los ejemplos: 5x5, 10x10, 20x20, 100x100, 100x100_unbal01, 100x100_unbal02 y 200x200.

### Cómo está organizado el código

- `Cell`: lo que hay en cada celda (tipo, edad de reproducción y hambre).
- Clase `Ecosystem`: guarda los parámetros y la matriz del mundo. Sus métodos son:
  - `readInput`: lee el archivo de entrada.
  - `chooseCell`: revisa las celdas de arriba, derecha, abajo e izquierda, cuenta las opciones y escoge con `(G + X + Y) mod P`.
  - `moveRabbits`: fase 1. Mueve los conejos, los reproduce y resuelve los choques.
  - `moveFoxes`: fase 2. Los zorros comen, mueren de hambre, se mueven, se reproducen y se resuelven los choques.
  - `nextGeneration`: una generación completa (conejos y luego zorros).
  - `printGeneration`, `printStats` y `printFinal`: los tres modos de salida.
- `main`: lee, simula las N_GEN generaciones e imprime según el modo.

Las dos fases miran el mundo como estaba antes (`world`) y escriben en un mundo nuevo (`newWorld`). Así todos los animales se mueven "a la vez" y el orden en que se recorren no cambia el resultado.

## Versión paralela

Pendiente.

## Parte visual

Pendiente.
