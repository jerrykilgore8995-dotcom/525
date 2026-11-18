#pragma once

#include "../calibration/PotHarmonicData.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <utility>

namespace vintage525 {

// Use only complete interpolation cells for the exact circuit configuration.
// Missing cells leave the existing preview profile in use.
class PotHarmonics {
public:
    using Spectrum = std::array<double, 19>;

    void select(int amp, int slot, int ceiling, int release, bool deess, double input, double output) noexcept
    {
        count = 0;
        const double in = input * 100, out = output * 100;
        const auto cell = [](double pot) {
            return std::pair{static_cast<int>(10 * std::floor((pot + .00001)/10)),
                             static_cast<int>(10 * std::ceil((pot - .00001)/10))};
        };
        auto [inLo, inHi] = cell(in);
        auto [outLo, outHi] = cell(out);
        // OUT 0 is mute and has no usable relative harmonic spectrum.
        if (out < 9.99999)
            return;
        for (const auto& point : data::potHarmonics) {
            if (point.amp == amp && point.slot == slot && point.ceiling == ceiling &&
                point.release == release && point.deess == deess &&
                (point.input == inLo || point.input == inHi) &&
                (point.output == outLo || point.output == outHi) &&
                count < points.size())
                points[count++] = &point;
        }
        required = 1u << ((inLo != inHi) + (outLo != outHi));
        inWeight = inLo == inHi ? 0 : std::clamp((in-inLo)/(inHi-inLo), 0.0, 1.0);
        outWeight = outLo == outHi ? 0 : std::clamp(std::log(out/outLo)/std::log(double(outHi)/outLo), 0.0, 1.0);
        lowerInput = inLo;
        lowerOutput = outLo;
    }

    double apply(Spectrum& target, int hz, double level) const noexcept
    {
        const data::PotHarmonicPoint* lower = nullptr;
        const data::PotHarmonicPoint* upper = nullptr;
        for (std::size_t i = 0; i < count; ++i) {
            const auto* p = points[i];
            if (p->hz != hz)
                continue;
            if (p->level <= level && (lower == nullptr || p->level > lower->level))
                lower = p;
            if (p->level >= level && (upper == nullptr || p->level < upper->level))
                upper = p;
        }
        if (lower == nullptr) lower = upper;
        if (upper == nullptr) upper = lower;
        if (lower == nullptr)
            return 0;
        Spectrum lo{}, hi{};
        if (!interpolate(lo, hz, lower->level))
            return 0;
        if (upper->level == lower->level) {
            hi = lo;
        } else if (!interpolate(hi, hz, upper->level)) {
            return 0;
        }
        const double fraction = lower->level == upper->level ? 0 : (level-lower->level)/(upper->level-lower->level);
        const double distance = std::abs(level - std::clamp(level, lower->level, upper->level));
        const double strength = std::clamp(1 - distance / 6, 0.0, 1.0);
        for (std::size_t h = 0; h < target.size(); ++h)
            target[h] = std::lerp(target[h], std::pow(10.0, std::lerp(lo[h], hi[h], fraction) / 20), strength);
        return strength;
    }

private:
    bool interpolate(Spectrum& result, int hz, double level) const noexcept
    {
        std::size_t hits = 0;
        for (std::size_t i = 0; i < count; ++i) {
            const auto& p = *points[i];
            if (p.hz != hz || p.level != level)
                continue;
            const auto a = p.input == lowerInput ? 1-inWeight : inWeight;
            const auto b = p.output == lowerOutput ? 1-outWeight : outWeight;
            for (std::size_t h = 0; h < result.size(); ++h)
                result[h] += p.dbc[h] * a * b;
            ++hits;
        }
        return hits == required;
    }

    std::array<const data::PotHarmonicPoint*, 128> points{};
    std::size_t count{}, required{};
    int lowerInput{}, lowerOutput{};
    double inWeight{}, outWeight{};
};

} // namespace vintage525
