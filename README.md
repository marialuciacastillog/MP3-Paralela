# MP3 - Simulación de ecosistema: zorros, conejos y rocas

**Integrantes:** _Maria Lucía Castillo García_ · _Juliana González Sánchez_ · _Ana Daniela Paredes Tovar_

MP3 de Programación Paralela.

El programa simula un mundo en una matriz donde viven conejos y zorros, y donde también hay rocas. En cada generación primero se mueven todos los conejos y luego todos los zorros, siguiendo las reglas del enunciado. Al final imprime cómo quedó el mundo.

Incluye una versión secuencial, una versión paralela con OpenMP y una interfaz gráfica para ver la simulación y sus estadísticas.

## Contenido

1. [Estructura del repositorio](#estructura-del-repositorio)
2. [Requisitos](#requisitos)
3. [Inicio rápido](#inicio-rápido)
4. [Formato de entrada y salida](#formato-de-entrada-y-salida)
5. [Versión secuencial](#versión-secuencial)
6. [Versión paralela](#versión-paralela)
7. [Parte visual](#parte-visual)
8. [Resumen de pruebas](#resumen-de-pruebas)
9. [Resultado esperado](#resultado-esperado)

## Estructura del repositorio

```
secuencial/   versión secuencial (C++ con POO)
paralela/     versión paralela con OpenMP (solo cambian moveRabbits y moveFoxes)
visual/       parte visual y estadísticas (interfaz gráfica en Python)
tests/        archivos de prueba (entradas y salidas esperadas)
build/        ejecutables compilados que usa la interfaz (ecosistema_seq y ecosistema_par)
```

## Requisitos

| Para | Necesitas |
|---|---|
| Compilar | `g++` (la versión paralela necesita además OpenMP, opción `-fopenmp`) |
| Interfaz gráfica | Python 3 con Tkinter (viene con Python en Windows y macOS; en Debian/Ubuntu: `sudo apt install python3-tk`) |
| Generar mundos grandes | Python 3 |

La interfaz no usa librerías externas de Python.

## Inicio rápido

Desde la raíz del repositorio:

```
mkdir -p build
g++ -O2 -o build/ecosistema_seq secuencial/main.cpp secuencial/Ecosystem.cpp
g++ -O2 -fopenmp -o build/ecosistema_par paralela/main.cpp paralela/Ecosystem.cpp

./build/ecosistema_seq < tests/input5x5
python3 visual/app.py
```

En Windows los ejecutables se llaman `ecosistema_seq.exe` y `ecosistema_par.exe` (la carpeta `build/` ya los incluye) y la interfaz se abre con `python visual\app.py`.

## Formato de entrada y salida

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
FOX 1 0
FOX 1 4
ROCK 2 4
RABBIT 3 0
RABBIT 4 0
FOX 4 4
```

El programa lee la entrada por la entrada estándar y escribe el mundo final en la salida estándar, con el mismo formato (`N_GEN` queda en 0 y `N` es el nuevo número de objetos):

```
2 4 3 0 5 5 5
ROCK 0 0
ROCK 2 4
RABBIT 3 0
FOX 4 0
FOX 4 3
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
| `./ecosistema stats < ../tests/input5x5` | Cuántos conejos y zorros hay en cada generación (CSV: `generacion,conejos,zorros`) |

El tiempo de la simulación se imprime por `cerr`, así que no se mezcla con la salida.

### Probar que funciona

Se compara la salida con el archivo de salida esperada. Si `diff` no imprime nada, el resultado está bien.

```
./ecosistema < ../tests/input5x5 > salida.txt
diff salida.txt ../tests/output5x5
```

Los archivos de `tests/` vienen con finales de línea de Windows (CRLF). Si en Linux o macOS `diff` marca todas las líneas como distintas, ignora el retorno de carro:

```
diff <(tr -d '\r' < ../tests/output5x5) <(./ecosistema < ../tests/input5x5 2>/dev/null)
```

El modo `all` se compara igual con los archivos `allgen`:

```
diff <(tr -d '\r' < ../tests/allgen5x5) <(./ecosistema all < ../tests/input5x5 2>/dev/null)
```

La versión secuencial da el resultado esperado en todos los ejemplos: 5x5, 10x10, 20x20, 100x100, 100x100_unbal01, 100x100_unbal02 y 200x200. En el modo `all` coincide con `allgen5x5`, `allgen10x10` y `allgen20x20`.

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

Además se revisó, comparando contra la secuencial, con un mundo aleatorio de 500x700 (200 generaciones) con 2, 7 y 16 hilos, y con casos pequeños que podrían romper el reparto en franjas: una sola fila, una sola columna y un mundo de 3x3 con 8 hilos. En todos el resultado fue idéntico.

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

`medir.sh` espera que las dos versiones ya estén compiladas (`../secuencial/ecosistema` y `./ecosistema`). Para otro caso: `./medir.sh ../tests/input200x200`.

## Parte visual

Archivo: `visual/app.py` (Python con Tkinter, sin librerías externas).

### Abrir

```
python3 visual/app.py
```

En Windows: `python visual\app.py`.

La interfaz ejecuta los programas en C++ en el modo `all` y va leyendo las generaciones. Busca los ejecutables en `build/` (`ecosistema_seq` y `ecosistema_par`) y, si no están, en `secuencial/ecosistema` y `paralela/ecosistema`. Si no los encuentra, muestra un aviso: compílalos como en el inicio rápido o usa el botón **Cambiar...** para escoger uno.

### Qué tiene

| Requisito del enunciado | Dónde está |
|---|---|
| Visualización de la matriz con todas las entidades | Panel central con zorros, conejos y rocas. Al pasar el mouse sobre una celda muestra su tipo, edad de reproducción y hambre |
| Estadísticas de población en el tiempo | Contadores de conejos, zorros y rocas, y una gráfica de población por generación |
| Parámetros ajustables | Pestaña **Parametros**: reproducción de conejos y zorros, hambre de zorros, generaciones, filas, columnas, cantidad de conejos, zorros y rocas, y semilla |
| Control del tiempo | **Iniciar / Pausa / Continuar**, **Paso**, **Reiniciar**, botones de más rápido y más lento, y deslizador de velocidad (0.5 a 500 generaciones por segundo) |

También se puede:

- **Abrir archivo...**: cargar una entrada, por ejemplo las de `tests/`.
- **Generar mundo aleatorio**: crear un mundo con las poblaciones indicadas (la semilla permite repetirlo).
- **Aplicar reglas**: cambiar los parámetros del mundo actual sin regenerarlo.
- **Motor**: escoger entre la versión secuencial y la paralela con OpenMP, y en la paralela elegir el número de hilos.
- **Registro**: ver los mensajes y el tiempo que imprime el motor.

### Uso típico

1. Abre un archivo (por ejemplo `tests/input20x20`) o genera un mundo aleatorio.
2. Ajusta las reglas y pulsa **Aplicar reglas** si quieres cambiarlas.
3. Escoge el motor (y los hilos, si es el paralelo).
4. Pulsa **Iniciar** y regula la velocidad, o avanza con **Paso**.
5. Cambia un parámetro, pulsa **Reiniciar** y compara las gráficas para ver cómo cambia la estabilidad del ecosistema.

Los cambios se aplican al (re)iniciar la simulación.

### Pruebas de la interfaz

Se probó con ambos motores: iniciar, pausa, paso, reiniciar, cambiar la velocidad, cargar `input20x20`, generar mundos aleatorios y cambiar de motor. Al terminar `input20x20` los contadores de la interfaz (20 rocas, 105 conejos y 26 zorros) coinciden con `output20x20`, tanto con el motor secuencial como con el paralelo. Los datos inválidos (texto en un campo numérico, más animales que celdas) muestran un mensaje de error sin cerrar el programa.

## Resumen de pruebas

| Qué se probó | Contra qué | Resultado |
|---|---|---|
| Secuencial, 7 casos de `tests/` | `output*` | Igual |
| Paralela, 7 casos, 1/2/3/4/8/16/32 hilos | `output*` | Igual |
| Modo `all` (5x5, 10x10, 20x20), secuencial y paralela | `allgen*` | Igual |
| Modo `stats`, paralela | secuencial | Igual |
| Mundo aleatorio 1000x1000 y 500x700, varios hilos | secuencial | Igual |
| Una fila, una columna, 3x3 con 8 hilos | secuencial | Igual |
| Interfaz con motor secuencial y paralelo | `output20x20` | Igual (rocas, conejos y zorros) |
| Motor Python de la interfaz | modo `all` de C++ (5x5, 10x10, 20x20, 100x100_unbal01) | Igual |

## Resultado esperado

Las poblaciones de zorros y conejos suben y bajan de forma cíclica y desfasada: cuando hay muchos conejos crecen los zorros, y luego los conejos disminuyen. Las rocas modifican la dinámica local. Con la gráfica de la interfaz se puede ver cómo cambia la estabilidad del ecosistema al modificar los parámetros.
