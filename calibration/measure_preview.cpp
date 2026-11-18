#include "../dsp/Preview.h"
#include <array>
#include <cmath>
#include <cstdio>
#include <numbers>

int main() {
    constexpr double rate = 88200;
    constexpr double unityDbu = 22;
    std::puts("amp,slot,hz,input_dbu,reference_thd_pct,native_thd_pct,relative_error_pct,native_gain_db,native_phase_degrees");
    for (const auto& point : vintage525::data::harmonics) {
        vintage525::Preview processor(rate, rate/4);
        vintage525::Controls c;
        c.amp = point.amp;
        c.mod = true;
        c.mode = point.slot == 4 ? 1 : 0;
        c.input = c.mode == 1 ? .9 : .5;
        c.ratio = c.mode == 1 ? 0 : point.slot;
        processor.configure(c);
        const double amplitude = std::pow(10.0, (point.level-unityDbu)/20);
        const double omega = 2*std::numbers::pi*point.hz/rate;
        constexpr int settling = 220500, analysis = 8820;
        std::array<double, 20> sine{}, cosine{};
        const auto harmonics = std::min(20, static_cast<int>((rate/4-1)/point.hz));
        for (int i=0; i<settling+analysis; ++i) {
            const double phase = omega*i;
            const auto signal = processor.process(static_cast<float>(amplitude*std::sin(phase)));
            if (i>=settling) {
                for (int h=1; h<=harmonics; ++h) {
                    sine[h-1] += signal*std::sin(h*phase);
                    cosine[h-1] += signal*std::cos(h*phase);
                }
            }
        }
        const auto fundamental = std::hypot(sine[0], cosine[0])*2/analysis;
        double sum = 0, reference = 0;
        for (int h=2; h<=harmonics; ++h) {
            sum += (sine[h-1]*sine[h-1]+cosine[h-1]*cosine[h-1]);
            reference += point.magnitude[h-2]*point.magnitude[h-2];
        }
        const auto native = std::sqrt(sum)*200/analysis/fundamental;
        reference = 100*std::sqrt(reference);
        std::printf("%d,%d,%d,%.0f,%.6f,%.6f,%.3f,%.3f,%.3f\n", point.amp, point.slot,
                    point.hz, point.level, reference, native, 100*(native/reference-1),
                    20*std::log10(fundamental/amplitude),
                    std::atan2(cosine[0],sine[0])*180/std::numbers::pi);
    }
}
