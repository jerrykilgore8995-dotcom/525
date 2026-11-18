#include "OutputCeiling.h"

#include <cmath>
#include <complex>
#include <iomanip>
#include <iostream>

int main()
{
    std::cout << std::setprecision(17);
    double out, rate, hz;
    int index;
    while (std::cin >> out >> index >> rate >> hz) {
        vintage525::OutputCeiling stage;
        stage.configure(out, index, rate);
        const auto radians = std::acos(-1.0) * 2.0 * hz / rate;
        // Use the impulse response of the same process() path the plugin
        // will call. The slowest pole settles well within two seconds.
        const auto rotation = std::polar(1.0, -radians);
        std::complex<double> basis{1.0, 0.0}, response{0.0, 0.0};
        for (int n = 0; n < 2 * rate; ++n) {
            response += stage.process(n == 0 ? 1.0 : 0.0) * basis;
            basis *= rotation;
        }
        std::cout << response.real() << ' ' << response.imag() << '\n';
    }
    return std::cin.eof() ? 0 : 1;
}
