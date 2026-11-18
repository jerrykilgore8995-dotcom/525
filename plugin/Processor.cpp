#include "Processor.h"
#include "Editor.h"

namespace {
constexpr std::array<const char*, 10> keys{
    "in", "out", "ceiling", "mode", "rel1", "rel2", "ds", "amp", "mod", "ratio"
};
}

Processor::Processor()
    : AudioProcessor(BusesProperties().withInput("Input", juce::AudioChannelSet::stereo(), true)
                                      .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      parameters(*this, nullptr, "Vintage525Parameters", layout())
{
    for (std::size_t i = 0; i < keys.size(); ++i)
        values[i] = parameters.getRawParameterValue(keys[i]);
}

juce::AudioProcessorValueTreeState::ParameterLayout Processor::layout()
{
    using namespace juce;
    AudioProcessorValueTreeState::ParameterLayout result;
    result.add(std::make_unique<AudioParameterFloat>(ParameterID{"in", 1}, "IN Threshold",
                   NormalisableRange<float>{0, 1, .01f}, .5f));
    result.add(std::make_unique<AudioParameterFloat>(ParameterID{"out", 1}, "OUT Make-Up",
                   NormalisableRange<float>{0, 1, .01f}, .75f));
    result.add(std::make_unique<AudioParameterInt>(ParameterID{"ceiling", 1}, "Ceiling", 0, 10, 8));
    result.add(std::make_unique<AudioParameterChoice>(ParameterID{"mode", 1}, "Mode",
                   StringArray{"Compress", "Limit", "Off", "Bypass"}, 0));
    for (const auto& item : std::array<std::pair<const char*,const char*>,4>{
            {{"rel1","Release 1"},{"rel2","Release 2"},{"ds","D-S"},{"mod","Mod"}}})
        result.add(std::make_unique<AudioParameterBool>(ParameterID{item.first, 1}, item.second, false));
    result.add(std::make_unique<AudioParameterChoice>(ParameterID{"amp", 1}, "Audio amplifier",
                   StringArray{"2520", "990"}, 0));
    result.add(std::make_unique<AudioParameterChoice>(ParameterID{"ratio", 1}, "Mod ratio",
                   StringArray{"2:1", "4:1", "8:1", "12:1"}, 0));
    return result;
}

void Processor::prepareToPlay(double sampleRate, int block)
{
    maxBlock = juce::jmax(1, block);
    const auto channels = static_cast<size_t>(getTotalNumInputChannels());
    oversampling = std::make_unique<juce::dsp::Oversampling<float>>(
        channels, 1, juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR, true, true);
    oversampling->initProcessing(static_cast<size_t>(maxBlock));
    oversampling->reset();
    const auto latency = juce::roundToInt(oversampling->getLatencyInSamples());
    setLatencySamples(latency);
    dryDelay.setMaximumDelayInSamples(latency + 2);
    dryDelay.prepare({sampleRate, static_cast<juce::uint32>(maxBlock), static_cast<juce::uint32>(channels)});
    dryDelay.setDelay(static_cast<float>(latency));
    for (auto& stage : channel)
        stage = vintage525::Preview(sampleRate * 2, sampleRate * .5);
}

void Processor::releaseResources()
{
    if (oversampling != nullptr)
        oversampling->reset();
    dryDelay.reset();
}

bool Processor::isBusesLayoutSupported(const BusesLayout& layoutToCheck) const
{
    const auto out = layoutToCheck.getMainOutputChannelSet();
    return out == layoutToCheck.getMainInputChannelSet() &&
           (out == juce::AudioChannelSet::mono() || out == juce::AudioChannelSet::stereo());
}

void Processor::processBlock(juce::AudioBuffer<float>& audio, juce::MidiBuffer&)
{
    process(audio, false);
}

void Processor::processBlockBypassed(juce::AudioBuffer<float>& audio, juce::MidiBuffer&)
{
    process(audio, true);
}

void Processor::process(juce::AudioBuffer<float>& audio, bool forceBypass)
{
    if (oversampling == nullptr)
        return;
    juce::ScopedNoDenormals noDenormals;
    const auto p = [this](std::size_t i){ return values[i]->load(std::memory_order_relaxed); };
    const vintage525::Controls controls{p(0), p(1), juce::roundToInt(p(2)), juce::roundToInt(p(3)),
        juce::roundToInt(p(9)), (p(4) > .5f ? 1 : 0) + (p(5) > .5f ? 2 : 0),
        juce::roundToInt(p(7)), p(8) > .5f, p(6) > .5f};
    const int nchan = getTotalNumInputChannels();
    if (forceBypass || controls.mode == 3) {
        for (int c = 0; c < nchan; ++c) {
            auto* samples = audio.getWritePointer(c);
            for (int i = 0; i < audio.getNumSamples(); ++i) {
                dryDelay.pushSample(c, samples[i]);
                samples[i] = dryDelay.popSample(c);
            }
            meter[static_cast<std::size_t>(c)].store(0, std::memory_order_relaxed);
        }
        return;
    }
    for (int c = 0; c < nchan; ++c)
        channel[static_cast<std::size_t>(c)].configure(controls);
    for (int c = 0; c < nchan; ++c) {
        const auto* samples = audio.getReadPointer(c);
        for (int i = 0; i < audio.getNumSamples(); ++i) {
            dryDelay.pushSample(c, samples[i]);
            (void)dryDelay.popSample(c);
        }
    }
    juce::dsp::AudioBlock<float> host(audio);
    for (int offset = 0; offset < audio.getNumSamples(); offset += maxBlock) {
        const auto len = std::min(maxBlock, audio.getNumSamples()-offset);
        auto block = host.getSubBlock(static_cast<std::size_t>(offset), static_cast<std::size_t>(len));
        auto up = oversampling->processSamplesUp(block);
        for (int c = 0; c < nchan; ++c) {
            auto* samples = up.getChannelPointer(static_cast<std::size_t>(c));
            auto& stage = channel[static_cast<std::size_t>(c)];
            for (std::size_t i = 0; i < up.getNumSamples(); ++i)
                samples[i] = stage.process(samples[i]);
            meter[static_cast<std::size_t>(c)].store(static_cast<float>(stage.reduction()), std::memory_order_relaxed);
        }
        oversampling->processSamplesDown(block);
    }
}

void Processor::getStateInformation(juce::MemoryBlock& block)
{
    if (auto xml = parameters.copyState().createXml())
        copyXmlToBinary(*xml, block);
}

void Processor::setStateInformation(const void* bytes, int size)
{
    if (auto xml = getXmlFromBinary(bytes, size))
        if (xml->hasTagName(parameters.state.getType().toString()))
            parameters.replaceState(juce::ValueTree::fromXml(*xml));
}

float Processor::value(const juce::String& id) const
{
    return parameters.getRawParameterValue(id)->load(std::memory_order_relaxed);
}

void Processor::setValue(const juce::String& id, float actual)
{
    if (auto* control = parameters.getParameter(id)) {
        control->beginChangeGesture();
        control->setValueNotifyingHost(control->convertTo0to1(actual));
        control->endChangeGesture();
    }
}

juce::AudioProcessorEditor* Processor::createEditor() { return new Editor(*this); }
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new Processor; }
