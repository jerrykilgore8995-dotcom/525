#pragma once

namespace vintage525 {

enum class CompressRatio { two, four, eight, twelve };

// R44 candidates measured at IN 50%, OUT 75%, Ceiling 16, D-S off.
// This mapping identifies the circuit configuration used to fit the DSP.
constexpr double compressFeedbackOhms(bool mod, CompressRatio ratio) noexcept
{
    if (!mod)
        return 200.0;
    switch (ratio) {
        case CompressRatio::four: return 68.0;
        case CompressRatio::eight: return 30.0;
        case CompressRatio::twelve: return 20.0;
        case CompressRatio::two: return 200.0;
    }
    return 200.0;
}

constexpr CompressRatio nextCompressRatio(CompressRatio ratio) noexcept
{
    switch (ratio) {
        case CompressRatio::two: return CompressRatio::four;
        case CompressRatio::four: return CompressRatio::eight;
        case CompressRatio::eight: return CompressRatio::twelve;
        case CompressRatio::twelve: return CompressRatio::two;
    }
    return CompressRatio::two;
}

} // namespace vintage525
