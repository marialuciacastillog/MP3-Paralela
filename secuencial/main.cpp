// Simulacion de ecosistema (zorros, conejos y rocas) - version secuencial
// Compilar: g++ -O2 -o ecosistema main.cpp Ecosystem.cpp
// Ejecutar:
//   ./ecosistema < input5x5          -> imprime solo el mundo final
//   ./ecosistema all < input5x5      -> imprime cada generacion (como los archivos allgen)
//   ./ecosistema stats < input5x5    -> imprime cuantos conejos y zorros hay en cada generacion

#include "Ecosystem.h"
#include <iostream>
#include <string>
#include <chrono>

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

    // Empieza a medir el tiempo (solo la simulacion, no la lectura)
    chrono::steady_clock::time_point start = chrono::steady_clock::now();

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

    // Termina de medir el tiempo
    chrono::steady_clock::time_point end = chrono::steady_clock::now();
    double seconds = chrono::duration<double>(end - start).count();

    if (mode == "final") {
        eco.printFinal();
    }

    // El tiempo va por cerr para que no se mezcle con la salida
    // (asi el archivo de salida se puede seguir comparando con fc o diff)
    cerr << fixed << "Tiempo: " << seconds << " segundos" << endl;

    return 0;
}