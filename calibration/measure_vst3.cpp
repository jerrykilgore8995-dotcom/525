#include "PreviewData.h"
#include "PotHarmonicData.h"
#include <juce_audio_processors/juce_audio_processors.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <iostream>
#include <numbers>
#include <stdexcept>
#include <sstream>
#include <vector>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

namespace {
using Plugin = juce::AudioPluginInstance;
constexpr int rate = 44100, blockSize = 512;
constexpr double fullScaleDbu = 22;

void set(Plugin& plugin, const juce::String& name, float value)
{
    for (auto* parameter : plugin.getParameters())
        if (parameter->getName(80) == name) {
            parameter->setValueNotifyingHost(value);
            return;
        }
    throw std::runtime_error("Missing host parameter " + name.toStdString());
}

void render(Plugin& plugin, const vintage525::data::HarmonicPoint& point, std::ostream& out,
            float input = -.1f, float output = .75f, int ceiling = 8, int release = 0, int deess = 0)
{
    plugin.releaseResources();
    plugin.prepareToPlay(rate, blockSize);
    set(plugin, "Audio amplifier", static_cast<float>(point.amp));
    set(plugin, "Mod", 1);
    const auto limit = point.slot == 4;
    set(plugin, "Mod ratio", point.slot >= 4 ? 0 : static_cast<float>(point.slot) / 3);
    set(plugin, "Mode", point.slot == 5 ? 2.f / 3 : (limit ? 1.f / 3 : 0));
    const auto position = input >= 0 ? input : (limit ? .9f : .5f);
    set(plugin, "IN Threshold", position);
    set(plugin, "OUT Make-Up", output);
    set(plugin, "Ceiling", static_cast<float>(ceiling) / 10);
    set(plugin, "Release 1", static_cast<float>(release & 1));
    set(plugin, "Release 2", static_cast<float>((release >> 1) & 1));
    set(plugin, "D-S", static_cast<float>(deess));
    constexpr int analysis = rate / 10, settle = rate * 3;
    const auto amplitude = std::pow(10.0, (point.level - fullScaleDbu) / 20);
    const auto omega = 2 * std::numbers::pi * point.hz / rate;
    const auto order = std::min(20, (rate/2 - 1) / point.hz);
    const auto nchan = plugin.getTotalNumInputChannels();
    juce::AudioBuffer<float> audio(nchan, blockSize);
    juce::MidiBuffer midi;
    std::array<double, 20> sine{}, cosine{};
    std::vector<double> blockMillis;
    for (int i = 0; i < settle + analysis; i += blockSize) {
        for (int j = 0; j < blockSize; ++j) {
            const auto sample = static_cast<float>(amplitude * std::sin(omega * (i+j)));
            for (int c = 0; c < nchan; ++c)
                audio.setSample(c, j, sample);
        }
        const auto start = std::chrono::steady_clock::now();
        plugin.processBlock(audio, midi);
        const auto elapsed = std::chrono::steady_clock::now() - start;
        blockMillis.push_back(std::chrono::duration<double, std::milli>(elapsed).count());
        for (int j = std::max(0, settle-i); j < std::min(blockSize, settle+analysis-i); ++j) {
            const auto phase = omega * (i+j);
            const auto output = audio.getSample(0, j);
            if (!std::isfinite(output))
                throw std::runtime_error("VST3 output contains a non-finite sample");
            for (int h = 1; h <= order; ++h) {
                sine[h-1] += output * std::sin(h*phase);
                cosine[h-1] += output * std::cos(h*phase);
            }
        }
    }
    const auto fundamental = std::hypot(sine[0], cosine[0]) * 2 / analysis;
    double thd = 0, reference = 0;
    for (int h = 2; h <= order; ++h) {
        thd += sine[h-1]*sine[h-1] + cosine[h-1]*cosine[h-1];
        reference += point.magnitude[h-2] * point.magnitude[h-2];
    }
    const auto measured = std::sqrt(thd) * 200 / analysis / fundamental;
    reference = std::sqrt(reference) * 100;
    const auto phase = std::remainder((std::atan2(cosine[0], sine[0])
        + omega * plugin.getLatencySamples()) * 180 / std::numbers::pi, 360);
    std::sort(blockMillis.begin(), blockMillis.end());
    const auto percentile = [&blockMillis](double p) { return blockMillis[std::size_t(p * (blockMillis.size()-1))]; };
    const bool baseline = input < 0;
    out << point.amp << ',' << point.slot << ',' << point.hz << ',' << point.level << ','
        << reference << ',' << measured << ',';
    if (reference > 0)
        out << 100 * (measured/reference-1);
    out << ',';
    if (baseline)
        out << point.gainDb;
    out << ',' << 20 * std::log10(fundamental/amplitude) << ',';
    if (baseline)
        out << point.phaseDeg;
    out << ',' << phase << ',' << plugin.getLatencySamples() << ','
        << percentile(.5) << ',' << percentile(.95) << ',' << percentile(.99) << ',' << blockMillis.back()
        << ',' << std::round(position*100) << ',' << std::round(output*100) << ',' << ceiling << ',' << release << ',' << deess;
    for (int h = 2; h <= 20; ++h) {
        out << ',';
        if (h <= order)
            out << 20 * std::log10(std::max(1e-15, std::hypot(sine[h-1], cosine[h-1])*2/analysis/fundamental));
    }
    out << '\n';
}

juce::Image captureWindow(HWND handle)
{
    RECT bounds{};
    GetClientRect(handle, &bounds);
    const int width = bounds.right, height = bounds.bottom;
    if (width <= 0 || height <= 0)
        return {};
    auto screen = GetDC(handle);
    auto memory = CreateCompatibleDC(screen);
    auto bitmap = CreateCompatibleBitmap(screen, width, height);
    auto original = SelectObject(memory, bitmap);
    PrintWindow(handle, memory, 2);
    SelectObject(memory, original);
    BITMAPINFO info{};
    info.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    info.bmiHeader.biWidth = width;
    info.bmiHeader.biHeight = -height;
    info.bmiHeader.biPlanes = 1;
    info.bmiHeader.biBitCount = 32;
    info.bmiHeader.biCompression = BI_RGB;
    std::vector<juce::uint32> pixels(static_cast<std::size_t>(width) * height);
    GetDIBits(memory, bitmap, 0, height, pixels.data(), &info, DIB_RGB_COLORS);
    const bool blank = std::all_of(pixels.begin(), pixels.end(), [colour=pixels.front()](auto p) { return p == colour; });
    if (blank) {
        SelectObject(memory, bitmap);
        BitBlt(memory, 0, 0, width, height, screen, 0, 0, SRCCOPY);
        SelectObject(memory, original);
        GetDIBits(memory, bitmap, 0, height, pixels.data(), &info, DIB_RGB_COLORS);
    }
    DeleteObject(bitmap);
    DeleteDC(memory);
    ReleaseDC(handle, screen);
    if (std::all_of(pixels.begin(), pixels.end(), [colour=pixels.front()](auto p) { return p == colour; }))
        return {};
    juce::Image result(juce::Image::RGB, width, height, false);
    for (int y=0; y<height; ++y)
        for (int x=0; x<width; ++x)
            result.setPixelAt(x, y, juce::Colour(pixels[static_cast<std::size_t>(y)*width+x] | 0xff000000u));
    return result;
}

void snapshot(Plugin& plugin, const juce::File& folder)
{
    std::unique_ptr<juce::AudioProcessorEditor> editor(plugin.createEditorIfNeeded());
    if (!editor)
        throw std::runtime_error("VST3 did not create an editor");
    editor->setTopLeftPosition(24, 24);
    editor->addToDesktop(juce::ComponentPeer::windowHasTitleBar);
    editor->setVisible(true);
    juce::PNGImageFormat png;
    for (const float scale : {1.f, 1.5f, 2.f}) {
        editor->setScaleFactor(scale);
        const auto handle = static_cast<HWND>(editor->getWindowHandle());
        RedrawWindow(handle, nullptr, nullptr, RDW_UPDATENOW | RDW_INVALIDATE | RDW_ALLCHILDREN);
        const auto output = captureWindow(handle);
        if (!output.isValid()) {
            std::cerr << "Native editor capture unavailable at " << scale << '\n';
            continue;
        }
        auto file = folder.getChildFile("editor-" + juce::String(juce::roundToInt(scale * 100)) + ".png");
        if (auto stream = file.createOutputStream())
            png.writeImageToStream(output, *stream);
    }
    editor->removeFromDesktop();
}
}

int main(int argc, char** argv)
{
    if (argc != 3)
        return 2;
    try {
        const juce::ScopedJuceInitialiser_GUI gui;
        juce::AudioPluginFormatManager formats;
        auto* format = new juce::VST3PluginFormat;
        formats.addFormat(format);
        const auto path = juce::File::getCurrentWorkingDirectory().getChildFile(juce::String::fromUTF8(argv[1]));
        juce::OwnedArray<juce::PluginDescription> types;
        format->findAllTypesForFile(types, path.getFullPathName());
        if (types.isEmpty())
            throw std::runtime_error("Could not scan the compiled Windows VST3");
        juce::String error;
        auto plugin = formats.createPluginInstance(*types[0], rate, blockSize, error);
        if (!plugin)
            throw std::runtime_error(error.toStdString());
        const auto folder = juce::File::getCurrentWorkingDirectory().getChildFile(juce::String::fromUTF8(argv[2]));
        folder.createDirectory();
        if (auto stream = folder.getChildFile("vst3-measurements.csv").createOutputStream()) {
            std::ostringstream csv;
            csv << "amp,slot,hz,input_dbu,spice_thd_pct,vst3_thd_pct,relative_thd_error_pct,spice_gain_db,vst3_gain_db,"
                   "spice_phase_deg,vst3_phase_deg,latency_samples,block_p50_ms,block_p95_ms,block_p99_ms,block_max_ms,input_pct,output_pct,ceiling,release,deess";
            for (int h = 2; h <= 20; ++h)
                csv << ",k" << h << "_dbc";
            csv << '\n';
            for (const auto& point : vintage525::data::harmonics)
                render(*plugin, point, csv);
            for (const auto& point : vintage525::data::potHarmonics) {
                vintage525::data::HarmonicPoint spec{point.amp, point.slot, point.hz, point.level, 0, 0, 0, {}};
                for (std::size_t h = 0; h < std::size(spec.magnitude); ++h)
                    spec.magnitude[h] = std::pow(10, point.dbc[h]/20);
                render(*plugin, spec, csv, point.input/100.f, point.output/100.f, point.ceiling, point.release, point.deess);
            }
            for (int output = 0; output <= 100; output += 5) {
                vintage525::data::HarmonicPoint holdout{0, 0, 1000, 18, 0, 0, 0, {}};
                render(*plugin, holdout, csv, .95f, output/100.f);
            }
            stream->writeText(juce::String(csv.str()), false, false, nullptr);
        } else {
            throw std::runtime_error("Could not create VST3 measurements CSV");
        }
        set(*plugin, "Mod", 0);
        set(*plugin, "Mod ratio", 0);
        set(*plugin, "Audio amplifier", 0);
        set(*plugin, "Mode", 0);
        set(*plugin, "IN Threshold", .5f);
        snapshot(*plugin, folder);
        plugin->releaseResources();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
