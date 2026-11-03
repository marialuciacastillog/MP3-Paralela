# Simulación de ecosistema: zorros, conejos y rocas

Proyecto de Programación Paralela.

El programa simula un mundo en una matriz donde viven conejos y zorros, y donde también hay rocas. En cada generación primero se mueven todos los conejos y luego todos los zorros, siguiendo las reglas del enunciado. Al final imprime cómo quedó el mundo.

## Estructura del repositorio

```
secuencial/   versión secuencial (C++ con POO)
paralela/     versión paralela con OpenMP (solo cambian moveRabbits y moveFoxes)
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

Archivos en la carpeta `paralela/`. Es la misma clase `Ecosystem` de la versión secuencial y la entrada, la salida y los tres modos (`final`, `all` y `stats`) funcionan igual. Lo que cambia es `moveRabbits` y `moveFoxes`, que ahora usan OpenMP. En `Ecosystem.h` solo se agregó la matriz `newWorld` como atributo, para reutilizarla en cada fase en vez de crear una nueva cada vez.

- `Ecosystem.h`, `Ecosystem.cpp`, `main.cpp`: el programa paralelo.
- `generar_entrada.py`: crea mundos aleatorios grandes para medir tiempos.
- `medir.sh`: corre la versión secuencial y la paralela con 1, 2, 4 y 8 hilos.

### Compilar

```
cd paralela
g++ -O2 -fopenmp -o ecosistema main.cpp Ecosystem.cpp
```

### Ejecutar

Igual que la secuencial. El número de hilos se escoge con la variable `OMP_NUM_THREADS` (si no se pone, OpenMP usa todos los núcleos):

```
OMP_NUM_THREADS=4 ./ecosistema < ../tests/input200x200
OMP_NUM_THREADS=4 ./ecosistema stats < ../tests/input100x100
```

En Windows (cmd) es `set OMP_NUM_THREADS=4` y luego `ecosistema < ..\tests\input200x200`.

Por `cerr` imprime cuántos hilos usó y el tiempo, así que la salida se puede seguir comparando con `diff`.

### Cómo se reparte el trabajo

El mundo se divide en franjas de filas y cada hilo mueve los animales de las franjas que le tocan. En cada fase primero se copia el mundo sin conejos (o sin zorros) en paralelo, y después se mueven los animales.

El problema está en los bordes. Como un animal se mueve máximo una celda, uno que está en la última fila de una franja puede caer en la primera fila de la franja de abajo, y ahí mismo puede llegar otro animal que mueve el hilo de esa franja. Si los dos hilos escriben la misma celda al mismo tiempo, el resultado puede quedar mal (condición de carrera).

Para evitarlo, cada fase se hace en dos rondas: primero se mueven en paralelo solo las franjas pares (0, 2, 4...) y después solo las impares (1, 3, 5...). Entre las dos rondas hay una barrera, la que OpenMP pone al final de cada `#pragma omp for`. Como entre dos franjas pares siempre hay una impar de por medio (de mínimo 2 filas), dos hilos nunca pueden escribir en la misma celda a la vez, y no hace falta usar locks, `critical` ni `atomic`.

Cambiar el orden en que llegan los animales a una celda no cambia el resultado, porque en un choque siempre se queda el de mayor edad de reproducción (y en los zorros, si empatan, el menos hambriento). Si empatan en todo, son exactamente iguales, así que da lo mismo cuál quede.

Para el balance de carga se hacen unas 4 franjas por hilo y se reparten con `schedule(dynamic)`: cuando un hilo termina su franja toma la siguiente que esté libre. Así, si una zona del mundo tiene muchos más animales que otra (como en los casos `unbal`), ningún hilo se queda mucho tiempo sin hacer nada.

### Pruebas

La versión paralela da el mismo resultado que el esperado en todos los ejemplos (5x5, 10x10, 20x20, 100x100, 100x100_unbal01, 100x100_unbal02 y 200x200) con 1, 2, 3, 4, 8, 16 y 32 hilos. También coincide con los archivos `allgen` en el modo `all`, con la secuencial en el modo `stats`, y con la secuencial en un mundo aleatorio de 1000x1000.

### Tiempos

Medidos en Windows con MinGW (g++ -O2), una sola corrida por caso. El speedup es el tiempo secuencial dividido entre el tiempo paralelo.

| Entrada | Secuencial | 1 hilo | 2 hilos | 4 hilos | 8 hilos |
|---|---|---|---|---|---|
| 200x200 (10000 gen.) | 9.26 s | 8.95 s | 5.64 s | 4.67 s | 6.55 s |
| Speedup | | 1.03 | 1.64 | 1.98 | 1.41 |
| 1000x1000 (300 gen.) | 9.70 s | 5.91 s | 2.61 s | 1.55 s | 1.35 s |
| Speedup | | 1.64 | 3.72 | 6.26 | 7.18 |

En el 1000x1000 la versión paralela con 1 hilo ya es más rápida que la secuencial. Eso no viene de los hilos, sino de que la paralela reutiliza la matriz `newWorld` e intercambia los mundos con `swap`, en vez de crear y copiar una matriz completa en cada fase. Si se compara solo contra la paralela con 1 hilo, la mejora por los hilos es de 2.26 con 2 hilos, 3.81 con 4 y 4.38 con 8.

Mientras más grande el mundo, mejor se aprovechan los hilos. En el 200x200 cada generación tiene poco trabajo y hay 10000 generaciones, así que crear los hilos y esperar en las barreras pesa casi lo mismo que mover los animales. Por eso con 8 hilos es más lento que con 4: hay más hilos esperando y franjas más pequeñas. En el 1000x1000 cada generación tiene mucho más trabajo y el costo de sincronizar casi no se nota.

El mundo de 1000x1000 se genera con:

```
python3 generar_entrada.py 1000 1000 300 > input1000x1000
./medir.sh input1000x1000
```

## Parte visual

Pendiente.
