#pragma once

#include <cmath>

namespace vintage525 {

// Linear feedback network of A2, between its + input and transformer primary.
// Pole and zero locations come from R40, R41, C7 and C8 in 525c.lib.
class OutputAmplifier {
public:
    explicit OutputAmplifier(double sampleRate) noexcept
    {
        constexpr double r40 = 1000;
        constexpr double r41 = 20000;
        constexpr double c7 = 33e-6;
        constexpr double c8 = 47e-12;
        constexpr double slowTime = r40 * c7;
        constexpr double fastTime = r41 * c8;
        constexpr double zeroSum = (r40 + r41) * c7 + fastTime;
        const auto longZero = .5 * (zeroSum + std::sqrt(zeroSum * zeroSum - 4 * slowTime * fastTime));
        const auto shortZero = slowTime * fastTime / longZero;
        const auto twoRate = 2 * sampleRate;
        const auto mapTimeConstant = [twoRate](double time) {
            return (twoRate * time - 1) / (twoRate * time + 1);
        };
        poleSlow = mapTimeConstant(slowTime);
        poleFast = mapTimeConstant(fastTime);
        zeroSlow = mapTimeConstant(longZero);
        zeroFast = mapTimeConstant(shortZero);
        scale = (1 + twoRate * longZero) * (1 + twoRate * shortZero)
                / ((1 + twoRate * slowTime) * (1 + twoRate * fastTime));
    }

    double process(double input) noexcept
    {
        const auto first = input - zeroSlow * previousInput + poleSlow * previousFirst;
        const auto second = first - zeroFast * previousFirst + poleFast * previousSecond;
        previousInput = input;
        previousFirst = first;
        previousSecond = second;
        return scale * second;
    }

private:
    double poleSlow, poleFast, zeroSlow, zeroFast, scale;
    double previousInput = 0, previousFirst = 0, previousSecond = 0;
};

} // namespace vintage525
