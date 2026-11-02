// Simulacion de ecosistema (zorros, conejos y rocas) - version secuencial
// Compilar: g++ -O2 -o ecosistema main.cpp Ecosystem.cpp
// Ejecutar:
//   ./ecosistema < input5x5          -> imprime solo el mundo final
//   ./ecosistema all < input5x5      -> imprime cada generacion (como los archivos allgen)
//   ./ecosistema stats < input5x5    -> imprime cuantos conejos y zorros hay en cada generacion

#include "Ecosystem.h"
#include <iostream>
#include <string>

using namespace std;

int main(int argc, char *argv[]) {
    // Modo: "final" (por defecto), "all" o "stats"
    string mode = "final";
    if (argc > 1) {
        mode = argv[1];
    }

    Ecosystem eco;
    eco.readInput();
    int nGen = eco.getNGen();

    if (mode == "stats") {
        cout << "generacion,conejos,zorros" << endl;
    }

    for (int g = 0; g <= nGen; g++) {
        // Mostrar la generacion g antes de moverla
        if (mode == "all") {
            if (g > 0) {
                cout << endl;
            }
            eco.printGeneration(g);
        } else if (mode == "stats") {
            eco.printStats(g);
        }

        if (g < nGen) {
            eco.nextGeneration(g);
        }
    }

    if (mode == "final") {
        eco.printFinal();
    }

    return 0;
}