#pragma once

#include <algorithm>
#include <array>

namespace vintage525 {

// Mono-linked R43, S5A and S1B path from the A1 output to A3+.
// The detector amplifier, rectifier and release network follow this tap.
inline double detectorDrive(double position, int ceilingIndex, bool limit) noexcept
{
    constexpr std::array<double, 11> ladder{0, 88800, 41800, 25800, 16700, 11100,
                                            7200, 4500, 2700, 1200, 0};
    constexpr double contact = .02;
    constexpr double inputResistance = 3900;
    constexpr double limitPath = 82000 + contact;
    const auto index = static_cast<unsigned>(std::clamp(ceilingIndex, 0, 10));
    if (index == 0 && !limit)
        return 0.0;
    position = std::clamp(position, 0.0, 1.0);
    const auto upper = std::max(1e-6, 1000 * (1 - position));
    const auto lower = std::max(1e-6, 1000 * position);
    const auto total = upper + lower;
    const auto potResistance = upper * lower / total;
    auto series = ladder[index] + contact;
    auto load = inputResistance;
    if (limit) {
        if (index == 0) {
            series = limitPath;
            load = inputResistance * contact / (inputResistance + contact);
        } else {
            series = series * limitPath / (series + limitPath);
        }
    }
    return (lower / total) * load / (load + series + potResistance);
}

} // namespace vintage525
