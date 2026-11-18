#pragma once

#include "Processor.h"

class Editor final : public juce::AudioProcessorEditor, private juce::Timer {
public:
    explicit Editor(Processor&);
    ~Editor() override;
    void paint(juce::Graphics&) override;
    void resized() override;

private:
    class PanelLook final : public juce::LookAndFeel_V4 {
    public:
        void drawRotarySlider(juce::Graphics&, int, int, int, int, float, float, float, juce::Slider&) override;
        void drawButtonBackground(juce::Graphics&, juce::Button&, const juce::Colour&, bool, bool) override;
    };

    void timerCallback() override;
    juce::Rectangle<int> panelBounds(float x, float y, float width, float height) const;
    void paintMeter(juce::Graphics&);

    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;
    using ComboBoxAttachment = juce::AudioProcessorValueTreeState::ComboBoxAttachment;
    Processor& owner;
    PanelLook look;
    juce::Slider input, output, ceiling;
    juce::ToggleButton mod{"Mod"};
    juce::ComboBox amplifier;
    juce::TextButton release1, release2, deEss, compress, limit, off, bypass, ratioLabel;
    std::unique_ptr<SliderAttachment> inBinding, outBinding, ceilingBinding;
    std::unique_ptr<ButtonAttachment> modBinding, rel1Binding, rel2Binding, dsBinding;
    std::unique_ptr<ComboBoxAttachment> ampBinding;
    std::array<float, 2> displayed{};
};
