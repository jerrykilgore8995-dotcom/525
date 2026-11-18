#include "OutputAmplifier.h"

#include <cmath>
#include <complex>
#include <iomanip>
#include <iostream>

int main()
{
    double rate, frequency;
    std::cout << std::setprecision(17);
    while (std::cin >> rate >> frequency) {
        vintage525::OutputAmplifier amplifier(rate);
        const auto rotation = std::polar(1.0, -2 * std::acos(-1.0) * frequency / rate);
        std::complex<double> basis(1, 0), response(0, 0);
        for (int n = 0; n < rate; ++n) {
            response += amplifier.process(n == 0 ? 1 : 0) * basis;
            basis *= rotation;
        }
        std::cout << response.real() << ' ' << response.imag() << '\n';
    }
    return std::cin.eof() ? 0 : 1;
}
