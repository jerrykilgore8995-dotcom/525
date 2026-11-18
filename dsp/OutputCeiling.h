#pragma once

#include <algorithm>
#include <array>
#include <cmath>

namespace vintage525 {

// Reduced transfer of the vintage R38 / S5B / R64 / C5 / R39 / C6 network,
// assuming a stiff A1 output and a high impedance A2+ input. Excludes A2.
class OutputCeiling {
public:
    struct Coefficients {
        double lowPole;
        double highPole;
        double gain;
    };

    // Called after a change in OUT, CEILING or sample rate. Preserve the
    // history of both filters across coefficient updates.
    void configure(double outputPosition, int ceilingIndex, double sampleRate) noexcept
    {
        coefficients = calculate(outputPosition, ceilingIndex, sampleRate);
    }

    void reset() noexcept
    {
        previousInput = 0.0;
        previousHighPass = 0.0;
        previousOutput = 0.0;
    }

    double process(double input) noexcept
    {
        const auto highPass = input - previousInput + coefficients.lowPole * previousHighPass;
        const auto output = coefficients.gain * highPass + coefficients.highPole * previousOutput;
        previousInput = input;
        previousHighPass = highPass;
        previousOutput = output;
        return output;
    }

    static Coefficients calculate(double position, int ceilingIndex, double sampleRate) noexcept
    {
        constexpr std::array<double, 11> ladder{36600, 28400, 21600, 16500, 12200, 8900,
                                               6200, 4000, 2400, 1100, 0};
        constexpr double rShunt = 3300.0;
        constexpr double contact = .02;
        constexpr double conductance = 1.0 / 62000.0;
        constexpr double coupling = 5e-6;
        constexpr double inputCap = 47e-12;
        const auto index = static_cast<unsigned>(std::clamp(ceilingIndex, 0, 10));
        position = std::clamp(position, 0.0, 1.0);
        const auto upper = std::max(1e-6, 1000 * (1.0 - position));
        const auto lower = std::max(1e-6, 1000 * position);
        const auto total = upper + lower;
        const auto series = ladder[index] + contact + upper * lower / total;
        const auto sum = series + rShunt;
        const auto linear = sum * (inputCap + contact * coupling * conductance + coupling)
                            + series * rShunt * coupling * conductance;
        const auto quadratic = (sum * contact + series * rShunt) * coupling * inputCap;
        const auto dc = sum * conductance;
        const auto root = linear + std::sqrt(linear * linear - 4.0 * dc * quadratic);
        const auto slow = 2.0 * dc / root;
        const auto fast = root / (2.0 * quadratic);
        const auto lowPole = std::exp(-slow / sampleRate);
        const auto highPole = std::exp(-fast / sampleRate);
        const auto midGain = (lower / total) * rShunt * coupling * 2.0 / root;
        return {lowPole, highPole, midGain * (1.0 + lowPole) * .5 * (1.0 - highPole)};
    }

private:
    Coefficients coefficients{};
    double previousInput = 0.0;
    double previousHighPass = 0.0;
    double previousOutput = 0.0;
};

} // namespace vintage525
