// Ecosystem.cpp - Metodos de la clase Ecosystem (version paralela con OpenMP)
// Todo es igual a la version secuencial menos moveRabbits y moveFoxes.

#include "Ecosystem.h"
#include <iostream>
#include <algorithm>
#include <omp.h>

using namespace std;

// ---------- Metodos de ayuda ----------

Cell Ecosystem::emptyCell() {
    Cell c;
    c.type = EMPTY;
    c.procAge = 0;
    c.foodAge = 0;
    return c;
}

bool Ecosystem::inside(int x, int y) {
    return x >= 0 && x < rows && y >= 0 && y < cols;
}

// Busca la celda a donde se mueve el animal en (x, y).
// Revisa las 4 vecinas y guarda las que tienen el tipo "wanted".
// Si hay opciones, escoge con (g + x + y) mod p y deja el destino en destX, destY.
// Devuelve cuantas opciones habia (p).
int Ecosystem::chooseCell(int x, int y, int wanted, int g, int &destX, int &destY) {
    int optX[4];
    int optY[4];
    int p = 0;

    for (int d = 0; d < 4; d++) {
        int nx = x + dirX[d];
        int ny = y + dirY[d];
        if (inside(nx, ny) && world[nx][ny].type == wanted) {
            optX[p] = nx;
            optY[p] = ny;
            p++;
        }
    }

    if (p > 0) {
        int pick = (g + x + y) % p;
        destX = optX[pick];
        destY = optY[pick];
    }
    return p;
}

// Copia del mundo sin los animales de un tipo
vector<vector<Cell>> Ecosystem::copyWithout(int type) {
    vector<vector<Cell>> newWorld = world;
    for (int x = 0; x < rows; x++) {
        for (int y = 0; y < cols; y++) {
            if (world[x][y].type == type) {
                newWorld[x][y] = emptyCell();
            }
        }
    }
    return newWorld;
}

// Imprime una linea de guiones del ancho del mundo
void Ecosystem::printBorder() {
    string line(cols + 2, '-');
    cout << line << "   " << line << " " << line << endl;
}

// ---------- Entrada ----------

// Lee los parametros y los objetos desde la entrada estandar
void Ecosystem::readInput() {
    int nObjects;
    cin >> genProcRabbits >> genProcFoxes >> genFoodFoxes >> nGen >> rows >> cols >> nObjects;

    world = vector<vector<Cell>>(rows, vector<Cell>(cols, emptyCell()));

    for (int i = 0; i < nObjects; i++) {
        string name;
        int x, y;
        cin >> name >> x >> y;
        if (name == "ROCK") {
            world[x][y].type = ROCK;
        } else if (name == "RABBIT") {
            world[x][y].type = RABBIT;
        } else if (name == "FOX") {
            world[x][y].type = FOX;
        }
    }
}

int Ecosystem::getNGen() {
    return nGen;
}

// ---------- Como se evitan los choques entre hilos ----------
//
// Cada animal se mueve maximo una celda, asi que un conejo o zorro de la fila x
// solo puede escribir en las filas x-1, x o x+1 del mundo nuevo.
//
// El mundo se parte en franjas de filas (bloques). Si dos franjas son vecinas,
// sus hilos podrian escribir en la misma celda del borde. Pero si entre dos
// franjas hay otra franja en medio (de al menos 2 filas), es imposible que se
// toquen.
//
// Entonces cada fase se hace en dos rondas:
//   ronda 0: se procesan en paralelo las franjas pares   (0, 2, 4, ...)
//   ronda 1: se procesan en paralelo las franjas impares (1, 3, 5, ...)
// Entre las dos rondas hay una barrera (la que pone "omp for" al final).
// Asi nunca hay dos hilos escribiendo la misma celda al mismo tiempo, y no se
// necesitan locks ni atomics.
//
// El resultado es igual al secuencial aunque el orden de llegada a una celda
// cambie: en un choque siempre gana el de mayor edad (o el menos hambriento),
// y si empatan en todo son celdas identicas, asi que da igual cual quede.
//
// Ademas, el mundo actual (world) solo se lee y el nuevo (newWorld) solo se
// escribe, igual que en la version secuencial.

// Numero de filas de cada franja. Minimo 2 para que la regla de arriba funcione.
// Se hacen varias franjas por hilo para que schedule(dynamic) reparta mejor
// cuando unas zonas tienen muchos mas animales que otras (casos unbal).
static int blockSize(int rows) {
    int nThreads = omp_get_max_threads();
    int size = rows / (4 * nThreads);
    if (size < 2) {
        size = 2;
    }
    return size;
}

// ---------- Fase 1: conejos ----------
void Ecosystem::moveRabbits(int g) {
    // Se crea una sola vez y despues se reutiliza (el contenido se sobreescribe abajo)
    if ((int) newWorld.size() != rows) {
        newWorld = vector<vector<Cell>>(rows, vector<Cell>(cols));
    }
    int size = blockSize(rows);
    int nBlocks = (rows + size - 1) / size;

    #pragma omp parallel
    {
        // Mundo nuevo: igual al actual pero sin conejos (cada hilo copia sus filas)
        #pragma omp for schedule(static)
        for (int x = 0; x < rows; x++) {
            for (int y = 0; y < cols; y++) {
                if (world[x][y].type == RABBIT) {
                    newWorld[x][y] = emptyCell();
                } else {
                    newWorld[x][y] = world[x][y];
                }
            }
        }

        // Ronda 0: franjas pares. Ronda 1: franjas impares.
        for (int round = 0; round < 2; round++) {
            #pragma omp for schedule(dynamic)
            for (int b = round; b < nBlocks; b += 2) {
                int firstRow = b * size;
                int lastRow = min(firstRow + size, rows);

                for (int x = firstRow; x < lastRow; x++) {
                    for (int y = 0; y < cols; y++) {
                        if (world[x][y].type == RABBIT) {
                            Cell rabbit = world[x][y];
                            int destX = x;
                            int destY = y;
                            int p = chooseCell(x, y, EMPTY, g, destX, destY);

                            if (p == 0) {
                                // No se puede mover: se queda y envejece
                                rabbit.procAge++;
                                newWorld[x][y] = rabbit;
                            } else {
                                if (rabbit.procAge >= genProcRabbits) {
                                    // Se reproduce: deja un conejo nuevo donde estaba
                                    Cell baby = emptyCell();
                                    baby.type = RABBIT;
                                    newWorld[x][y] = baby;
                                    rabbit.procAge = 0;
                                } else {
                                    rabbit.procAge++;
                                }

                                // Choque: si ya llego otro conejo, se queda el de mayor edad
                                Cell &there = newWorld[destX][destY];
                                if (there.type != RABBIT || rabbit.procAge > there.procAge) {
                                    there = rabbit;
                                }
                            }
                        }
                    }
                }
            }
            // Aqui hay una barrera implicita: nadie empieza las impares
            // hasta que todos terminen las pares
        }
    }

    // swap solo intercambia punteros, no copia la matriz.
    // El mundo viejo queda en newWorld y se reutiliza en la siguiente fase.
    world.swap(newWorld);
}

// ---------- Fase 2: zorros ----------
void Ecosystem::moveFoxes(int g) {
    // Se crea una sola vez y despues se reutiliza (el contenido se sobreescribe abajo)
    if ((int) newWorld.size() != rows) {
        newWorld = vector<vector<Cell>>(rows, vector<Cell>(cols));
    }
    int size = blockSize(rows);
    int nBlocks = (rows + size - 1) / size;

    #pragma omp parallel
    {
        // Mundo nuevo: igual al actual pero sin zorros (cada hilo copia sus filas)
        #pragma omp for schedule(static)
        for (int x = 0; x < rows; x++) {
            for (int y = 0; y < cols; y++) {
                if (world[x][y].type == FOX) {
                    newWorld[x][y] = emptyCell();
                } else {
                    newWorld[x][y] = world[x][y];
                }
            }
        }

        // Ronda 0: franjas pares. Ronda 1: franjas impares.
        for (int round = 0; round < 2; round++) {
            #pragma omp for schedule(dynamic)
            for (int b = round; b < nBlocks; b += 2) {
                int firstRow = b * size;
                int lastRow = min(firstRow + size, rows);

                for (int x = firstRow; x < lastRow; x++) {
                    for (int y = 0; y < cols; y++) {
                        if (world[x][y].type == FOX) {
                            Cell fox = world[x][y];
                            int destX = x;
                            int destY = y;
                            bool alive = true;

                            // 1. Buscar un conejo al lado
                            int p = chooseCell(x, y, RABBIT, g, destX, destY);

                            if (p > 0) {
                                fox.foodAge = 0;
                            } else {
                                // 2. No comio: revisar si se muere de hambre
                                fox.foodAge++;
                                if (fox.foodAge >= genFoodFoxes) {
                                    alive = false;
                                } else {
                                    // 3. Buscar una celda vacia
                                    p = chooseCell(x, y, EMPTY, g, destX, destY);
                                }
                            }

                            if (alive) {
                                if (p == 0) {
                                    // No se puede mover: se queda y envejece
                                    fox.procAge++;
                                    newWorld[x][y] = fox;
                                } else {
                                    if (fox.procAge >= genProcFoxes) {
                                        // Se reproduce: deja un zorro nuevo donde estaba
                                        Cell baby = emptyCell();
                                        baby.type = FOX;
                                        newWorld[x][y] = baby;
                                        fox.procAge = 0;
                                    } else {
                                        fox.procAge++;
                                    }

                                    // Choque: se queda el de mayor edad; si empatan, el menos hambriento
                                    Cell &there = newWorld[destX][destY];
                                    bool keepNew = true;
                                    if (there.type == FOX) {
                                        if (fox.procAge < there.procAge) {
                                            keepNew = false;
                                        } else if (fox.procAge == there.procAge && fox.foodAge >= there.foodAge) {
                                            keepNew = false;
                                        }
                                    }
                                    if (keepNew) {
                                        there = fox;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            // Barrera implicita entre la ronda de pares y la de impares
        }
    }

    world.swap(newWorld);
}

// Una generacion completa: primero conejos, luego zorros
void Ecosystem::nextGeneration(int g) {
    moveRabbits(g);
    moveFoxes(g);
}

// ---------- Salida ----------

// Cuenta cuantas celdas hay de un tipo
int Ecosystem::countType(int type) {
    int total = 0;
    for (int x = 0; x < rows; x++) {
        for (int y = 0; y < cols; y++) {
            if (world[x][y].type == type) {
                total++;
            }
        }
    }
    return total;
}

// Imprime la generacion g igual que los archivos allgen:
// 1. el mundo  2. la edad de reproduccion  3. el hambre de los zorros
void Ecosystem::printGeneration(int g) {
    cout << "Generation " << g << endl;
    printBorder();
    for (int x = 0; x < rows; x++) {
        string worldRow = "";
        string ageRow = "";
        string foodRow = "";
        for (int y = 0; y < cols; y++) {
            Cell c = world[x][y];
            if (c.type == EMPTY) {
                worldRow += " ";
                ageRow += " ";
                foodRow += " ";
            } else if (c.type == ROCK) {
                worldRow += "*";
                ageRow += "*";
                foodRow += "*";
            } else if (c.type == RABBIT) {
                worldRow += "R";
                ageRow += to_string(c.procAge);
                foodRow += "R";
            } else {
                worldRow += "F";
                ageRow += to_string(c.procAge);
                foodRow += to_string(c.foodAge);
            }
        }
        cout << "|" << worldRow << "|   |" << ageRow << "| |" << foodRow << "|" << endl;
    }
    printBorder();
}

// Imprime una linea con la poblacion de la generacion g
void Ecosystem::printStats(int g) {
    cout << g << "," << countType(RABBIT) << "," << countType(FOX) << endl;
}

// Imprime el mundo final en el mismo formato de la entrada
void Ecosystem::printFinal() {
    int total = countType(ROCK) + countType(RABBIT) + countType(FOX);

    cout << genProcRabbits << " " << genProcFoxes << " " << genFoodFoxes << " " << 0 << " "
         << rows << " " << cols << " " << total << endl;

    for (int x = 0; x < rows; x++) {
        for (int y = 0; y < cols; y++) {
            if (world[x][y].type == ROCK) {
                cout << "ROCK " << x << " " << y << endl;
            } else if (world[x][y].type == RABBIT) {
                cout << "RABBIT " << x << " " << y << endl;
            } else if (world[x][y].type == FOX) {
                cout << "FOX " << x << " " << y << endl;
            }
        }
    }
}