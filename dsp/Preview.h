#pragma once

#include "DetectorDrive.h"
#include "OutputAmplifier.h"
#include "OutputCeiling.h"
#include "../calibration/PreviewData.h"
#include <array>
#include <algorithm>
#include <cmath>

namespace vintage525 {

struct Controls {
    double input = .5, output = .75;
    int ceiling = 8, mode = 0, ratio = 0, release = 0, amp = 0;
    bool mod = false, deess = false;
    bool operator==(const Controls&) const = default;
};

class Preview {
public:
    explicit Preview(double sampleRate = 88200, double nyquist = 22050)
        : rate(sampleRate), hostNyquist(nyquist), a2(sampleRate)
    {
        attack = coefficient(6.83e-6);
        dc = coefficient(.08);
        low = coefficient(.0015);
        controls.ceiling = -1;
        configure({});
    }

    void configure(Controls next)
    {
        if (controls == next)
            return;
        controls = next;
        slot = next.mode == 1 ? 4 : (next.mod ? next.ratio : 0);
        output.configure(next.output, next.ceiling, rate);
        const auto outCoefficients = OutputCeiling::calculate(next.output, next.ceiling, rate);
        harmonicOutputGain = outCoefficients.gain / (1-outCoefficients.highPole) * 21 * 1.96;
        const auto currentTap = detectorDrive(next.input, next.ceiling, slot == 4);
        const auto referenceTap = detectorDrive(.5, 8, slot == 4);
        baseline = 25.09;
        const int availableAmp = hasGain(next.amp, slot) ? next.amp : 0;
        for (std::size_t n = 0; n < gainTable.size(); ++n) {
            const auto level = static_cast<double>(n) - 72;
            const auto shift = 20 * std::log10(std::max(1e-8, currentTap / referenceTap));
            gainTable[n] = std::clamp(curve(availableAmp, slot, level + shift), 0.0, baseline);
        }
        const int releaseSlot = slot == 4 ? 0 : slot;
        constexpr std::array<double, 4> fallback{.1213, .5417, 1.8415, 2.2591};
        for (int n = 0; n < 2; ++n) {
            const auto hz = n == 0 ? 100 : 1000;
            const data::ReleasePoint* found = nullptr;
            for (const auto& r : data::release)
                if (r.slot == releaseSlot && r.setting == next.release && r.hz == hz
                        && (r.amp == next.amp || found == nullptr))
                    found = &r;
            releaseSeconds[n] = found == nullptr ? fallback[next.release] : found->seconds;
        }
        refreshHarmonics(-18, 1000);
        refreshRelease(1000);
    }

    float process(float input) noexcept
    {
        const auto x = static_cast<double>(input);
        if (sinceCrossing < rate)
            ++sinceCrossing;
        if (previousSource <= 0 && x > 0) {
            if (sinceCrossing >= 4 && sinceCrossing < rate / 20) {
                frequency += .22 * (rate / sinceCrossing - frequency);
                period = sinceCrossing;
            }
            sinceCrossing = 0;
        }
        previousSource = x;
        const auto absolute = std::abs(x);
        if (absolute >= peak) {
            peak = absolute;
            hold = std::max(2, period);
        } else if (hold > 0) {
            --hold;
        } else {
            peak = absolute + peakDecay * (peak - absolute);
        }
        inputLow = x + low * (inputLow - x);
        const auto level = 22 + 20 * std::log10(std::max(peak, 1e-12));
        if (++controlsCounter >= 128) {
            refreshRelease(frequency);
            refreshHarmonics(level, frequency);
            controlsCounter = 0;
        }
        const auto boost = controls.deess ? 7.5 * std::abs(x-inputLow) / std::max(.00001, peak) : 0.0;
        const auto index = std::clamp(level + boost + 72, 0.0, static_cast<double>(gainTable.size()-1));
        const auto lower = static_cast<int>(index);
        const auto upper = std::min(lower+1, static_cast<int>(gainTable.size()-1));
        const auto target = gainTable[lower] + (gainTable[upper]-gainTable[lower])*(index-lower);
        gainDb = target + (target < gainDb ? attack : releaseCoeff) * (gainDb - target);
        const auto gain = std::exp(gainDb * logDb);
        const auto stageIn = x * (120.0 / 10450.0);
        // C1 in series with the gate-controlled FET attenuates the extra AC gain.
        const auto capPole = std::exp(-std::max(0.0, gain-1.0) / (1034.0 * .00025 * rate));
        stageLow = stageIn + capPole * (stageLow - stageIn);
        const auto a1 = stageIn + (gain-1)*(stageIn-stageLow);
        const auto a2In = controls.mode == 2 ? x * (300.0 / 10450.0) : output.process(a1);
        const auto linear = a2.process(a2In) * 1.96;
        auto out = linear;
        if (controls.mode <= 1 && peak > 1e-6) {
            const auto u = std::clamp(x / peak, -1.0, 1.0);
            auto prev = 1.0;
            auto current = u;
            double harmonics = 0;
            for (std::size_t h = 0; h < magnitude.size(); ++h) {
                const auto next = 2*u*current-prev;
                harmonics += magnitude[h] * next;
                prev = current;
                current = next;
            }
            // Weight the waveform by the corresponding output peak, keeping
            // harmonics out of the floor of the model's peak detector.
            out += harmonics * peak * gain * (120.0 / 10450.0) * harmonicOutputGain;
        }
        outDC = out + dc * (outDC - out);
        return static_cast<float>(out-outDC);
    }

    double reduction() const noexcept { return controls.mode <= 1 ? std::max(0.0, baseline-gainDb) : 0; }

private:
    static constexpr double logDb = .11512925464970229;
    double coefficient(double seconds) const noexcept { return std::exp(-1/(rate*seconds)); }

    static bool hasGain(int amp, int slot)
    {
        for (const auto& point : data::gain)
            if (point.amp == amp && point.slot == slot)
                return true;
        return false;
    }

    static double curve(int amp, int slot, double level)
    {
        const data::GainPoint* lo = nullptr;
        const data::GainPoint* hi = nullptr;
        double bestAnchor = 100;
        for (const auto& p : data::gain) {
            if (p.slot != slot || p.amp != amp)
                continue;
            const auto distance = std::abs(p.input-.5) + .1*std::abs(p.ceiling-8);
            if (distance > bestAnchor)
                continue;
            if (distance < bestAnchor) {
                bestAnchor = distance;
                lo = hi = nullptr;
            }
            if (p.level <= level && (lo == nullptr || p.level > lo->level))
                lo = &p;
            if (p.level >= level && (hi == nullptr || p.level < hi->level))
                hi = &p;
        }
        if (lo == nullptr)
            return hi == nullptr ? 25.09 : hi->gain;
        if (hi == nullptr)
            return std::max(0.0, lo->gain - std::max(0.0, level-lo->level)*.9);
        if (lo->level == hi->level)
            return lo->gain;
        return lo->gain + (hi->gain-lo->gain) * (level-lo->level)/(hi->level-lo->level);
    }

    void refreshRelease(double hz) noexcept
    {
        const auto f = std::clamp(std::log10(std::max(20.0, hz)/100), 0.0, 1.0);
        releaseCoeff = coefficient(releaseSeconds[0] + (releaseSeconds[1]-releaseSeconds[0])*f);
        peakDecay = coefficient(.0005);
    }

    void refreshHarmonics(double level, double hz) noexcept
    {
        magnitude.fill(0);
        if (controls.mode > 1)
            return;
        const auto hslot = slot == 4 ? 0 : slot;
        double covered = 0;
        for (const auto& r : data::harmonics) {
            if (r.slot != hslot || r.amp != controls.amp)
                continue;
            const auto distance = (level-r.level) / 12;
            const auto frequencyDistance = std::log2(std::max(20.0,hz)/r.hz);
            const auto weight = 1 / (.12 + distance*distance + frequencyDistance*frequencyDistance);
            covered += weight;
            for (std::size_t h = 0; h < magnitude.size(); ++h)
                magnitude[h] += weight * r.magnitude[h];
        }
        if (covered > 0)
            for (std::size_t h = 0; h < magnitude.size(); ++h) {
                const auto taper = std::clamp((hostNyquist-(h+2)*hz)/(hostNyquist*.15),0.0,1.0);
                magnitude[h] *= taper / covered;
            }
    }

    double rate, hostNyquist;
    OutputAmplifier a2;
    OutputCeiling output;
    Controls controls;
    std::array<double, 96> gainTable{};
    std::array<double, 19> magnitude{};
    std::array<double, 2> releaseSeconds{};
    double attack{}, dc{}, low{}, releaseCoeff{}, peakDecay{}, baseline{};
    double peak{}, gainDb = 25.09, previousSource{}, frequency = 1000;
    double inputLow{}, stageLow{}, outDC{}, harmonicOutputGain{};
    int sinceCrossing{}, period = 88, hold{}, controlsCounter{}, slot{};
};

} // namespace vintage525
