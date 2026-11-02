// Ecosystem.h - Clase Ecosystem (version secuencial)

#ifndef ECOSYSTEM_H
#define ECOSYSTEM_H

#include <vector>
#include <string>

// Tipos de celda
const int EMPTY = 0;
const int ROCK = 1;
const int RABBIT = 2;
const int FOX = 3;

struct Cell {
    int type;      // EMPTY, ROCK, RABBIT o FOX
    int procAge;   // generaciones desde que nacio o se reprodujo
    int foodAge;   // generaciones sin comer (solo zorros)
};

class Ecosystem {
private:
    // Parametros del archivo
    int genProcRabbits;
    int genProcFoxes;
    int genFoodFoxes;
    int nGen;
    int rows;
    int cols;

    // El mundo
    std::vector<std::vector<Cell>> world;

    // Movimientos en orden: arriba, derecha, abajo, izquierda
    int dirX[4] = {-1, 0, 1, 0};
    int dirY[4] = {0, 1, 0, -1};

    Cell emptyCell();
    bool inside(int x, int y);
    int chooseCell(int x, int y, int wanted, int g, int &destX, int &destY);
    std::vector<std::vector<Cell>> copyWithout(int type);
    void printBorder();

public:
    void readInput();
    int getNGen();

    void moveRabbits(int g);
    void moveFoxes(int g);
    void nextGeneration(int g);

    int countType(int type);
    void printGeneration(int g);
    void printStats(int g);
    void printFinal();
};

#endif