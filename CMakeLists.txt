cmake_minimum_required(VERSION 3.25)
project(Vintage525 VERSION 0.1.0 LANGUAGES C CXX)

set(VINTAGE525_JUCE_PATH "" CACHE PATH "Optional local JUCE 8.0.6 checkout")
if(VINTAGE525_JUCE_PATH)
    add_subdirectory("${VINTAGE525_JUCE_PATH}" JUCE)
else()
    include(FetchContent)
    FetchContent_Declare(JUCE
        GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
        GIT_TAG 8.0.6
        GIT_SHALLOW TRUE)
    FetchContent_MakeAvailable(JUCE)
endif()

juce_add_plugin(Vintage525
    COMPANY_NAME "525"
    BUNDLE_ID "audio.vintage525.compressor"
    PLUGIN_MANUFACTURER_CODE V525
    PLUGIN_CODE Cm52
    PRODUCT_NAME "525"
    FORMATS VST3
    VST3_CATEGORIES Fx Dynamics
    COPY_PLUGIN_AFTER_BUILD FALSE)
target_sources(Vintage525 PRIVATE plugin/Processor.cpp plugin/Editor.cpp)
target_compile_features(Vintage525 PRIVATE cxx_std_20)
target_compile_definitions(Vintage525 PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(Vintage525 PRIVATE juce::juce_audio_processors juce::juce_dsp
    juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)
