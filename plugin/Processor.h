#pragma once

#include "../dsp/Preview.h"
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_dsp/juce_dsp.h>

class Processor final : public juce::AudioProcessor {
public:
    Processor();
    void prepareToPlay(double, int) override;
    void releaseResources() override;
    bool isBusesLayoutSupported(const BusesLayout&) const override;
    using AudioProcessor::processBlock;
    using AudioProcessor::processBlockBypassed;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    void processBlockBypassed(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return "525"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock&) override;
    void setStateInformation(const void*, int) override;

    float value(const juce::String& id) const;
    void setValue(const juce::String& id, float actual);
    juce::AudioProcessorValueTreeState parameters;
    std::array<std::atomic<float>, 2> meter{};

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout layout();
    void process(juce::AudioBuffer<float>&, bool forceBypass);
    std::array<vintage525::Preview, 2> channel{vintage525::Preview{}, vintage525::Preview{}};
    std::unique_ptr<juce::dsp::Oversampling<float>> oversampling;
    juce::dsp::DelayLine<float, juce::dsp::DelayLineInterpolationTypes::None> dryDelay;
    int maxBlock = 1;
    std::array<std::atomic<float>*, 10> values{};
};
