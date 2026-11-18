#include "Editor.h"

namespace {
const juce::Colour blue(0xff08a9df), white(0xffe5e9e7);
constexpr float headerRatio = 34.0f / 825.0f;
constexpr std::array<const char*, 4> ratioNames{"2:1", "4:1", "8:1", "12:1"};
}

Editor::Editor(Processor& processor)
    : AudioProcessorEditor(processor), owner(processor)
{
    auto knob = [this](juce::Slider& slider, const char* name, bool red) {
        slider.setSliderStyle(juce::Slider::RotaryVerticalDrag);
        slider.setRotaryParameters(juce::MathConstants<float>::pi * (red ? 1.23f : 1.25f),
                                   juce::MathConstants<float>::pi * (red ? 2.77f : 2.75f), true);
        slider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
        slider.setName(name);
        slider.setTitle(name);
        slider.setTooltip(name);
        slider.setLookAndFeel(&look);
        addAndMakeVisible(slider);
    };
    knob(input, "IN / THRESH", false);
    knob(output, "OUT / MAKE-UP", false);
    knob(ceiling, "CEILING", true);

    auto button = [this](juce::TextButton& control, const char* name, bool light, bool toggle) {
        control.setName(name);
        control.setTitle(name);
        control.setTooltip(name);
        control.setColour(juce::TextButton::buttonColourId, light ? white : juce::Colour(0xff151c1d));
        control.setClickingTogglesState(toggle);
        control.setLookAndFeel(&look);
        addAndMakeVisible(control);
    };
    button(release1, "Release 1", false, true);
    button(release2, "Release 2", false, true);
    button(deEss, "D-S", false, true);
    button(compress, "Compress", true, false);
    button(limit, "Limit", true, false);
    button(off, "Off", true, false);
    button(bypass, "Bypass", true, false);
    ratioLabel.setTooltip("Select Compress or cycle the Mod ratio in Compress");
    ratioLabel.setColour(juce::TextButton::buttonColourId, juce::Colours::transparentBlack);
    ratioLabel.setColour(juce::TextButton::textColourOffId, blue);
    addAndMakeVisible(ratioLabel);

    compress.onClick = [this] { owner.setValue("mode", 0); };
    limit.onClick = [this] { owner.setValue("mode", 1); };
    off.onClick = [this] { owner.setValue("mode", 2); };
    bypass.onClick = [this] { owner.setValue("mode", 3); };
    ratioLabel.onClick = [this] {
        if (owner.value("mode") == 0 && owner.value("mod") > .5f)
            owner.setValue("ratio", std::fmod(owner.value("ratio") + 1, 4.0f));
        else
            owner.setValue("mode", 0);
    };

    amplifier.addItem("2520", 1);
    amplifier.addItem("990", 2);
    amplifier.setTitle("Audio amplifier");
    amplifier.setTooltip("Select the audio amplifier model");
    addAndMakeVisible(amplifier);
    addAndMakeVisible(mod);

    auto& parameters = owner.parameters;
    inBinding = std::make_unique<SliderAttachment>(parameters, "in", input);
    outBinding = std::make_unique<SliderAttachment>(parameters, "out", output);
    ceilingBinding = std::make_unique<SliderAttachment>(parameters, "ceiling", ceiling);
    modBinding = std::make_unique<ButtonAttachment>(parameters, "mod", mod);
    rel1Binding = std::make_unique<ButtonAttachment>(parameters, "rel1", release1);
    rel2Binding = std::make_unique<ButtonAttachment>(parameters, "rel2", release2);
    dsBinding = std::make_unique<ButtonAttachment>(parameters, "ds", deEss);
    ampBinding = std::make_unique<ComboBoxAttachment>(parameters, "amp", amplifier);
    setResizable(true, true);
    setResizeLimits(160, 584, 380, 1387);
    getConstrainer()->setFixedAspectRatio(226.0 / 825.0);
    setSize(226, 825);
    timerCallback();
    startTimerHz(30);
}

Editor::~Editor()
{
    stopTimer();
    for (auto* slider : {&input, &output, &ceiling})
        slider->setLookAndFeel(nullptr);
    for (auto* button : {&release1, &release2, &deEss, &compress, &limit, &off, &bypass})
        button->setLookAndFeel(nullptr);
}

juce::Rectangle<int> Editor::panelBounds(float x, float y, float width, float height) const
{
    const auto panel = getLocalBounds().toFloat().withTrimmedTop(getHeight() * headerRatio);
    return juce::Rectangle<float>{panel.getX() + (x - width * .5f) * panel.getWidth(),
                                  panel.getY() + (y - height * .5f) * panel.getHeight(),
                                  width * panel.getWidth(), height * panel.getHeight()}.getSmallestIntegerContainer();
}

void Editor::resized()
{
    auto header = getLocalBounds().removeFromTop(juce::roundToInt(getHeight() * headerRatio)).reduced(5, 3);
    amplifier.setBounds(header.removeFromLeft(header.getWidth() / 2).reduced(2, 0));
    mod.setBounds(header.reduced(4, 0));
    input.setBounds(panelBounds(.283f, .116f, .33f, .094f));
    output.setBounds(panelBounds(.682f, .116f, .33f, .094f));
    ceiling.setBounds(panelBounds(.442f, .828f, .57f, .168f));
    release1.setBounds(panelBounds(.333f, .478f, .145f, .046f));
    release2.setBounds(panelBounds(.333f, .551f, .145f, .046f));
    deEss.setBounds(panelBounds(.333f, .624f, .145f, .046f));
    compress.setBounds(panelBounds(.670f, .433f, .160f, .047f));
    limit.setBounds(panelBounds(.670f, .509f, .160f, .047f));
    off.setBounds(panelBounds(.673f, .584f, .160f, .047f));
    bypass.setBounds(panelBounds(.673f, .660f, .160f, .047f));
    ratioLabel.setBounds(panelBounds(.871f, .456f, .236f, .032f));
}

void Editor::timerCallback()
{
    const int mode = juce::roundToInt(owner.value("mode"));
    compress.setToggleState(mode == 0, juce::dontSendNotification);
    limit.setToggleState(mode == 1, juce::dontSendNotification);
    off.setToggleState(mode == 2, juce::dontSendNotification);
    bypass.setToggleState(mode == 3, juce::dontSendNotification);
    const auto ratio = owner.value("mod") > .5f ? juce::roundToInt(owner.value("ratio")) : 0;
    ratioLabel.setButtonText(ratioNames[static_cast<std::size_t>(ratio)]);
    for (std::size_t c = 0; c < displayed.size(); ++c)
        displayed[c] = std::max(owner.meter[c].load(std::memory_order_relaxed), displayed[c] * .84f);
    repaint(panelBounds(.508f, .280f, .51f, .10f));
}

void Editor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(0xff272c2d));
    const auto body = panelBounds(.5f, .5f, 1.0f, 1.0f);
    g.setGradientFill(juce::ColourGradient(juce::Colour(0xff171d1d), 0, 0,
                                          juce::Colour(0xff2b302e), static_cast<float>(body.getRight()), 0, false));
    g.fillRect(body);
    auto label = [&](const char* name, float x, float y, float width, float height, juce::Colour colour) {
        auto frame = panelBounds(x, y, width, height);
        g.setColour(colour);
        g.setFont(static_cast<float>(frame.getHeight()) * .84f);
        g.drawFittedText(name, frame, juce::Justification::centred, 1);
    };
    auto scale = [&](float x, float y, float radius, int steps) {
        const auto center = panelBounds(x, y, 0, 0).getCentre().toFloat();
        const auto r = radius * getWidth();
        const auto size = getWidth() * .021f;
        g.setColour(blue);
        for (int i = 0; i < steps; ++i) {
            const float angle = -2.36f + 4.72f * i / (steps - 1);
            const auto at = center.getPointOnCircumference(r, angle);
            g.fillEllipse(at.x - size / 2, at.y - size / 2, size, size);
        }
    };
    for (float y : {.031f, .970f}) {
        auto screw = panelBounds(.505f, y, .118f, .034f).toFloat();
        g.setColour(juce::Colour(0xff090c0c));
        g.fillEllipse(screw);
        screw.reduce(screw.getWidth() * .2f, screw.getHeight() * .2f);
        g.setColour(juce::Colour(0xffb1b5ae));
        g.fillEllipse(screw);
        g.setColour(juce::Colour(0xff535954));
        g.drawLine(screw.getX() + 3, screw.getCentreY() + 2, screw.getRight() - 3, screw.getCentreY() - 2, 1.2f);
    }
    label("525", .808f, .037f, .24f, .046f, blue);
    scale(.283f, .116f, .182f, 9);
    scale(.682f, .116f, .182f, 9);
    label("IN", .283f, .190f, .33f, .028f, white);
    label("OUT", .682f, .190f, .36f, .028f, white);
    label("THRESH", .283f, .215f, .34f, .022f, blue);
    label("MAKE-UP", .682f, .215f, .40f, .022f, blue);

    paintMeter(g);
    label("REL", .333f, .388f, .27f, .033f, white);
    label("MODE", .670f, .388f, .31f, .033f, white);
    g.setColour(blue);
    g.drawRoundedRectangle(panelBounds(.441f, .501f, .245f, .164f).toFloat(), 4, 1);
    label("sec: 0.1", .390f, .434f, .36f, .023f, blue);
    label("1", .112f, .478f, .13f, .025f, white);
    label("1+2", .118f, .514f, .23f, .026f, blue);
    label("2", .112f, .551f, .13f, .025f, white);
    label("0.5", .477f, .478f, .16f, .024f, blue);
    label("2.0", .477f, .514f, .16f, .024f, blue);
    label("2.5", .477f, .551f, .16f, .024f, blue);
    label("D-S", .112f, .624f, .22f, .029f, white);
    label("C", .871f, .430f, .20f, .026f, white);
    label("L", .871f, .507f, .20f, .026f, white);
    label("20:1", .871f, .532f, .22f, .019f, blue);
    label("OFF", .871f, .584f, .21f, .029f, white);
    label("BYP", .871f, .660f, .21f, .029f, white);

    scale(.442f, .828f, .374f, 7);
    label("4", .041f, .829f, .086f, .024f, white);
    label("8", .216f, .733f, .102f, .024f, white);
    label("12", .632f, .733f, .16f, .024f, white);
    label("16", .840f, .829f, .16f, .024f, white);
    label("0", .190f, .927f, .102f, .025f, white);
    label("20", .665f, .927f, .154f, .025f, white);
    label("CEILING", .443f, .944f, .56f, .024f, white);
    label("LESS", .823f, .704f, .26f, .019f, blue);
    label("MORE", .823f, .951f, .26f, .019f, blue);
    auto arrow = panelBounds(.78f, .830f, .36f, .235f).toFloat();
    juce::Path arc;
    arc.addCentredArc(arrow.getX(), arrow.getCentreY(), arrow.getWidth(), arrow.getHeight() * .54f, 0,
                       .45f, 2.73f, true);
    g.setColour(blue);
    g.strokePath(arc, juce::PathStrokeType(1.2f));
    g.drawArrow({arc.getCurrentPosition().translated(5, -4), arc.getCurrentPosition()}, 1.2f, 5, 6);
}

void Editor::paintMeter(juce::Graphics& g)
{
    auto frame = panelBounds(.508f, .280f, .500f, .096f).toFloat();
    g.setColour(juce::Colour(0xff090d0b));
    g.fillRoundedRectangle(frame, 3);
    g.setColour(juce::Colour(0xff53564c));
    g.drawRoundedRectangle(frame, 3, 1.2f);
    frame.reduce(frame.getWidth() * .057f, frame.getHeight() * .1f);
    auto legend = frame.removeFromTop(frame.getHeight() * .29f);
    g.setFont(legend.getHeight() * .8f);
    g.setColour(white);
    g.drawText("0     5    10    15    20    25", legend.toNearestInt(), juce::Justification::centredLeft);
    const int n = owner.getTotalNumInputChannels() == 2 ? 2 : 1;
    const float rowHeight = frame.getHeight() / n;
    for (int c = 0; c < n; ++c) {
        auto row = frame.removeFromTop(rowHeight).reduced(0, rowHeight * .12f);
        auto number = row.removeFromRight(row.getWidth() * .25f);
        const auto value = displayed[static_cast<std::size_t>(c)];
        const float segmentWidth = row.getWidth() / 20;
        for (int i = 0; i < 20; ++i) {
            auto segment = row.removeFromLeft(segmentWidth).reduced(.55f, 0);
            g.setColour(i < value * .8f ? juce::Colour(0xffa7c38c) : juce::Colour(0xff233123));
            g.fillRect(segment);
        }
        g.setColour(white);
        g.setFont(rowHeight * .64f);
        g.drawText(juce::String(value, 1), number.toNearestInt(), juce::Justification::centredRight);
    }
}

void Editor::PanelLook::drawRotarySlider(juce::Graphics& g, int x, int y, int width, int height,
                                        float position, float start, float end, juce::Slider& slider)
{
    const bool red = slider.getName() == "CEILING";
    const float size = static_cast<float>(std::min(width, height)) * (red ? .82f : .91f);
    const auto center = juce::Point<float>{x + width * .5f, y + height * .5f};
    const auto angle = start + position * (end - start);
    auto knob = juce::Rectangle<float>(size, size).withCentre(center);
    g.setColour(juce::Colours::black.withAlpha(.78f));
    g.fillEllipse(knob.translated(1, 3));
    g.setGradientFill(juce::ColourGradient(juce::Colour(0xffeef0e5), knob.getX(), knob.getY(),
        juce::Colour(0xff9c9d93), knob.getRight(), knob.getBottom(), false));
    g.fillEllipse(knob);
    juce::Path pointer;
    pointer.addRoundedRectangle(center.x - size * .08f, center.y - size * (red ? .77f : .55f),
                                size * .16f, size * .48f, size * .04f);
    pointer.applyTransform(juce::AffineTransform::rotation(angle, center.x, center.y));
    g.fillPath(pointer);
    const auto cap = knob.reduced(size * .13f);
    const auto colour = red ? juce::Colour(0xffdd2928) : juce::Colour(0xff158b79);
    g.setGradientFill(juce::ColourGradient(colour.darker(.6f), cap.getX(), cap.getY(),
                                          colour.brighter(.25f), cap.getRight(), cap.getBottom(), false));
    g.fillEllipse(cap);
    g.setColour(juce::Colours::black.withAlpha(.6f));
    g.drawEllipse(cap, 1);
}

void Editor::PanelLook::drawButtonBackground(juce::Graphics& g, juce::Button& button,
                                            const juce::Colour& colour, bool hover, bool down)
{
    auto base = button.getLocalBounds().toFloat().reduced(1.5f);
    g.setColour(juce::Colour(0xff070808));
    g.fillRoundedRectangle(base, 2);
    base.reduce(base.getWidth() * .12f, base.getHeight() * .12f);
    const bool active = down || button.getToggleState();
    auto top = (active ? colour.darker(.48f) : colour).brighter(hover ? .2f : .08f);
    g.setGradientFill(juce::ColourGradient(top, 0, base.getY(), top.darker(.35f), 0, base.getBottom(), false));
    g.fillRoundedRectangle(base, 1.5f);
    if (active) {
        g.setColour(blue.withAlpha(.75f));
        g.drawRoundedRectangle(base, 1.5f, 1.0f);
    }
}
