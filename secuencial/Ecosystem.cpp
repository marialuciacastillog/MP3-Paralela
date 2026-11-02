// Ecosystem.cpp - Metodos de la clase Ecosystem (version secuencial)

#include "Ecosystem.h"
#include <iostream>

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

// ---------- Fase 1: conejos ----------
void Ecosystem::moveRabbits(int g) {
    // Mundo nuevo: igual al actual pero sin conejos
    vector<vector<Cell>> newWorld = copyWithout(RABBIT);

    for (int x = 0; x < rows; x++) {
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

    world = newWorld;
}

// ---------- Fase 2: zorros ----------
void Ecosystem::moveFoxes(int g) {
    // Mundo nuevo: igual al actual pero sin zorros
    vector<vector<Cell>> newWorld = copyWithout(FOX);

    for (int x = 0; x < rows; x++) {
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

    world = newWorld;
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