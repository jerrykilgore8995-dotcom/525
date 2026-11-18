#include "PreviewData.h"
#include <juce_audio_processors/juce_audio_processors.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <iostream>
#include <numbers>
#include <stdexcept>
#include <sstream>

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

void render(Plugin& plugin, const vintage525::data::HarmonicPoint& point, std::ostream& out)
{
    plugin.releaseResources();
    plugin.prepareToPlay(rate, blockSize);
    set(plugin, "Audio amplifier", static_cast<float>(point.amp));
    set(plugin, "Mod", 1);
    set(plugin, "Mod ratio", static_cast<float>(point.slot) / 3);
    set(plugin, "Mode", 0);
    set(plugin, "IN Threshold", .5f);
    set(plugin, "OUT Make-Up", .75f);
    set(plugin, "Ceiling", .8f);
    set(plugin, "Release 1", 0);
    set(plugin, "Release 2", 0);
    set(plugin, "D-S", 0);
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
    out << point.amp << ',' << point.slot << ',' << point.hz << ',' << point.level << ','
        << reference << ',' << measured << ',' << 100 * (measured/reference-1) << ','
        << point.gainDb << ',' << 20 * std::log10(fundamental/amplitude) << ','
        << point.phaseDeg << ',' << phase << ',' << plugin.getLatencySamples() << ','
        << percentile(.5) << ',' << percentile(.95) << ',' << percentile(.99) << ',' << blockMillis.back() << '\n';
}

void snapshot(Plugin& plugin, const juce::File& folder)
{
    std::unique_ptr<juce::AudioProcessorEditor> editor(plugin.createEditorIfNeeded());
    if (!editor)
        throw std::runtime_error("VST3 did not create an editor");
    if (auto* host = dynamic_cast<juce::Component*>(editor.get())) {
        host->addToDesktop(0);
        host->setVisible(true);
        juce::PNGImageFormat png;
        for (const float scale : {1.f, 1.5f, 2.f}) {
            const auto output = host->createComponentSnapshot(host->getLocalBounds(), true, scale);
            auto file = folder.getChildFile("editor-" + juce::String(juce::roundToInt(scale * 100)) + ".png");
            if (auto stream = file.createOutputStream())
                png.writeImageToStream(output, *stream);
        }
        host->removeFromDesktop();
    }
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
                   "spice_phase_deg,vst3_phase_deg,latency_samples,block_p50_ms,block_p95_ms,block_p99_ms,block_max_ms\n";
            for (const auto& point : vintage525::data::harmonics)
                render(*plugin, point, csv);
            stream->writeText(juce::String(csv.str()), false, false, nullptr);
        } else {
            throw std::runtime_error("Could not create VST3 measurements CSV");
        }
        set(*plugin, "Mod", 0);
        set(*plugin, "Mod ratio", 0);
        set(*plugin, "Audio amplifier", 0);
        snapshot(*plugin, folder);
        plugin->releaseResources();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
