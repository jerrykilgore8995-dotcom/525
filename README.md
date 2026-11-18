# 525

Component-level reconstruction of the API 525 500-series reissue followed by a Windows x64 VST3. The [vintage SPICE checkpoint](reference/SPICE.md) includes a connected 525C deck with part-level 2520 and JE-990 variants, reproducible diagnostics, and documented stability failures. See the [current reconstruction checkpoint](reference/RECONSTRUCTION.md) for the vintage 525C trace, original Jensen JE-990 component audit, reissue control table and gaps preventing simulation.

- [Engineering gates](AGENTS.md)
- [Measurement and acceptance protocol](MEASUREMENT.md)
- [Faceplate specification](GUI.md)
- [Source provenance](SOURCES.md)

The provided matrix generator emits stable configuration IDs. Run `python3 matrix.py --count` for the provisional 11-position ceiling grid, or `python3 matrix.py --start 0 --stop 8` to emit an example shard.

## Current verification

The [loaded response and timing checkpoint](reference/SPICE.md#loaded-response-attack-and-recovery-verification) covers the all-2520 circuit and the JE-990 audio stages with a 2520 detector. The [GitHub Actions run](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44226891307) contains the decks, raw traces and measurements.

A 20 Hz node trace at IN 90%, OUT 75%, Ceiling 16, D-S off, 150 Ω source and 10 kΩ load places the all-2520 Compress loss relative to 1 kHz in these stages:

| Stage | 20 Hz relative gain |
| --- | ---: |
| A1+ to A1 output, including the FET feedback branch | −1.043 dB |
| A2+ to A2 output | −0.245 dB |
| A2 output to the fixture output | −0.004 dB |
| Complete path | −1.296 dB |

In OFF the signal enters the output stage through the test tap, skipping A1. The complete-path loss is −0.252 dB. For the Compress result, sweeping the provisional VCR2N card across independent data-sheet cutoff and on-resistance limits changed the A1 contribution from −0.77 to −4.97 dB. Those corners demonstrate model sensitivity. When testing the nominal card directly, it returned 52 Ω at zero gate bias and −3.98 V at the data-sheet 1 µA cutoff condition, both inside the specified bands. Its simulated gate forward voltage was 0.477 V at 1 mA, compared with a typical 0.7 V in the data sheet. A hardware VCR2N curve or selected device bin would narrow these results. [Siliconix VCR2N data sheet](https://www.technicalaudio.com/pdf/Siliconix/Siliconix_VCR2N-4N-7N_voltage-controlled_resistor_FET.pdf)

The [control calibration run](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44231985549) completed 1,848 small-signal and 968 driven cases. The compiled OUT/CEILING stage tracked the measured small-signal control changes within 0.019 dB and 0.64° through 20 kHz at 44.1 kHz, using an anchored transfer for each mode, amplifier pairing and D-S position. The driven CSVs flag late-window drift independently of solver success.

The [detector transformer run](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44232740951) compares the earlier 1:0.5:0.5 detector assumption to the schematic-supported 1:1:1 AP2623 winding ratio. Both variants are selectable in the SPICE fixture. The comparison shows several dB difference at identical settings, so use the winding selection when interpreting the gain or timing curves. The detailed [SPICE report](reference/SPICE.md#detector-transformer-ratio-and-unresolved-gain-law) records gain-law and load discrepancies that still affect the compressor fit.

The [gain-history and output-load run](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44239379454) completed 16 drive histories, 60 connected AC sweeps and 56 driven sweeps. The catalog-bounded output-transformer candidate yields −0.24 dB at 20 kHz into 600 Ω and an inferred 1 kHz output impedance of 126 + j8 Ω at the documented Compress settings. The generated candidate library and both sets of traces are in the output-loading artifact.

A separate 0 → +8 → 0 dBu burst with the 1:1:1 detector winding, all-2520 Compress, Ceiling 16 and IN 90%, exposed a recovery interval specific to FET cutoff. After the drop to 0 dBu, A1 took 2.02 s to regain 1 dB of stage gain with release 00. Release 11 had yet to regain it after 4 s. This measures recovery from an overloaded operating state, which differs from the nominal gain-reduction release tests. In the gradual drive sweep, reducing the R52 release-override trim from 50% to 10% brought the return to 0 dBu within 0.01 dB of the first 0 dBu plateau, while the FET still reached cutoff at +4 dBu. At the default trim, reducing IN to 50% kept A1 at 3.62 dB gain at +4 dBu. The fixture exposes R7, R75 and R52 for alignment sweeps. The factory trim positions and gain law remain open.

## Audio timing and driven response

The drawn C3, R60, R61 and R62 and release switch contacts give nominal ladder time constants of 100, 570, 2,000 and 2,470 ms. The 570 ms position is 14% longer than the 500 ms nominal label. This is the passive ladder calculation. The loaded Q2/Q4 and override network, the FET transfer and the frequency and level of the stimulus determine the audio release envelope.

In the all-2520, 1:1:1 detector, Compress test at IN 90%, OUT 75%, Ceiling 16, 10 kΩ and D-S off, a 1 kHz crest step from −30 to +4 dBu gives a 15.01 µs 10–90% change in A1 audio gain and a 31.78 µs delay from onset to the 90% crossing. It reaches the FET cutoff region. The −30 to −18 dBu step gives 26.45 µs and 41.57 µs respectively, with 6.14 dB of measured gain reduction. The timed ratio uses A1 output divided by A1 input with pre-step DC removed, on the first crest only, with 5 µs crossing persistence. Halving the solver step from 250 to 125 ns changes these 10–90% results by less than 0.002 µs. API publishes 15 µs, but the public spec does not define the test stimulus or measurement crossing. The software comparison establishes a 15 µs case under the stated conditions. [API user guide](https://apiaudio.com/docs/manuals/525_user_2020-12-15.pdf)

For the same circuit and −30 to −18 dBu stimulus, 1 kHz audio gain recovers 63.2% in about 121, 542, 1,842 and 2,259 ms. The times to 1 dB remaining are about 184, 889, 3,006 and 3,681 ms. At 100 Hz the fastest position takes about 194 ms to recover 63.2%. The [audio timing workflow](.github/workflows/vintage-timing-alignment.yml) measures these criteria with both audio amplifier pairings, both modes and all release states. The drawn timing parts were checked against the schematic. Factory alignment and equivalent hardware-protocol results remain open.

The [driven-band workflow](.github/workflows/vintage-driven-band.yml) uses the 1:1:1 detector into 600 Ω and 10 kΩ, with the original output model. It measures absolute fundamental gain and phase, A1 gain reduction relative to the quiet row, K2–K20 magnitude and phase, residual and gain drift at 30 Hz, 100 Hz, 1 kHz, 5 kHz, 10 kHz and 20 kHz. D-S is exercised at 100 Hz and 5 kHz. In the 10 kΩ all-2520 Compress run at −18 dBu, D-S increases gain reduction from 6.19 to 7.66 dB at 100 Hz and from 5.77 to 11.69 dB at 5 kHz. The recorded residual includes modulation and numerical residual. Compare against the drift flag before treating a row as settled.

An R52 sweep checked whether release can be aligned using the existing trim. At 1 kHz, trim 0.10 gives approximately the same 121/542 ms recovery to 63.2% as the nominal 0.50 setting for positions 00/10. Trim 0.03 gives 89/140 ms and reduces the measured gain reduction, so this trim setting cannot align both positions to the published labels. Repeating release 00 at 5 µs maximum step gives 121.12 ms versus 121.28 ms at 10 µs. Release behavior should be calibrated against a matching hardware curve and the relevant frequency, level and recovery criterion. API's brochure also gives different slow values in its prose than the 2020 guide and faceplate. The comparison uses the latter's 2.0/2.5 s labels. [API brochure](https://apiaudio.com/docs/brochures/br525.pdf)

A focused driven-transformer comparison at −18 dBu in Compress into 600 Ω gives a 20 kHz transfer relative to 1 kHz of −7.31 dB with the original output model and +0.39 dB with the catalog-bounded candidate. The corresponding absolute phases at 20 kHz are −76.05° and −21.35°. These are model predictions at the same controls.

[Audio timing measurements and raw decks](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44251661993) · [Driven gain, phase and harmonic measurements](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44251068207)

The driven sweep returned 160 usable waveforms. All 80 Compress cases were within the 0.1 dB late-window drift criterion. The 20 Limit rows that exceeded it remain flagged. A local follow-up of all 20 flagged Limit cases across both amplifier pairings and loads used a total tone duration of 0.8 s at 100 Hz and 0.32 s at 5/10 kHz. All 20 met the drift criterion with less than 0.006 dB of output drift over the same analysis window.

## Gain slopes and THD calibration

The measured SPICE gain-recovery envelopes are accepted as the plug-in reference. The gain-law fixture holds each 1 kHz drive level for 320 ms with a 20 ms transition, measures the fundamental near the end and reports the late output drift. The slope screen fits three successive points over at least 4 dB. It requires at least 1 dB of gain reduction, A1 above the cutoff exclusion and a maximum 0.10 dB fit residual. Ratios are input dB change divided by output dB change. The original reference circuit and the provisional 1:1:1 AP2623 detector remain available in the fixture.

At IN 50%, OUT 75%, Ceiling 16, D-S off, 150 Ω source and 10 kΩ load, all-2520 Compress gives 2.04:1 from −20 to −16 dBu, with a 0.039 dB maximum fit residual. The same 4 dB window at IN 90% measures 3.69:1. The resulting gain law depends on the controls and level. The narrow successful span does not establish a global 2:1 match.

The compiled [IN/CEILING detector control](dsp/DetectorDrive.h) matches the SPICE ratio from A1 output to A3 input within 0.007 dB (2520/2520) and 0.004 dB (990/2520). Both mode-switch positions and all eleven Ceiling detents were exercised at eight IN positions in each mode. Relative error is evaluated above a (10^{-5}) absolute gain floor. The output also includes an absolute-error check at endpoints.

The [THD calibration CSV](reference/525c-thd-reference.csv) records the 2520/2520 Compress fixture with the AP2623-ratio detector, original output model, IN 90%, OUT 75%, Ceiling 16, D-S off, release 00, 150 Ω source and 10 kΩ load. Tone lengths are 800 ms at 100 Hz and 320 ms otherwise. The final twelve coherent periods were used for K2–K20. The `detail=2` rows halve the maximum timestep at 1 and 10 kHz and −18 dBu. THD changes by 0.24% and 0.10% relative respectively. Harmonics in this analog simulation above the plug-in's Nyquist limit are outside the direct host harmonic comparison. The +4 dBu condition is near FET cutoff at these controls.

At the same IN/OUT and Ceiling with the 2520/2520 pair in Limit, the initial R75 setting (0.30) yields 17.63:1 over 0 to +4 dBu in the broad sweep. With R75 at 0.90 the focused +2/+4/+6 dBu measurement gives 21.08:1 at a 10 µs maximum timestep and 21.07:1 at 5 µs. Gain reduction spans about 18 to 22 dB, with a maximum fit residual of 0.008 dB. R75 at 1.00 gives 21.01:1 on the same +2 to +6 dBu span at 10 µs. These are candidate alignment points. The 0.90 setting also gives 16.01:1 over 0 to +4 dBu in the focused sweep, so applying a global fixed slope would erase measured behavior.

Reproduce the gain-law checks with:

```sh
export OPENBLAS_NUM_THREADS=1
python3 spice/gain_law.py --pair 2520/2520 --mode C --subset quick --levels -40 -30 -24 -20 -18 -16 --step 5e-6 --output evidence/compress-check
python3 spice/gain_law.py --pair 2520/2520 --mode L --subset alignment --levels -40 -18 -8 -4 0 2 4 6 8 --step 5e-6 --output evidence/limit-check
```

[Broader gain-law, trim and detector-control run](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44255132690)

## Compress Mod ratios

The [Mod control design](GUI.md#mod-ratios) adds a toggle outside the faceplate and makes the Compress ratio label cycle 2:1, 4:1, 8:1 and 12:1. The [native mapping](dsp/CompressRatio.h) identifies the reference circuit for each setting. The fixture changes R44 in the A3 negative-feedback return in Compress. Existing Limit and OFF use the stock resistance. With the default resistance, the old and new C, L and OFF AC trace files compared byte for byte.

The [measured calibration points](reference/525c-mod-ratios.csv) use ngspice 44.2, both audio amplifier pairings with a 2520 detector, the AP2623-ratio T2 candidate, provisional T1, IN 50%, OUT 75%, Ceiling 16, D-S off, release 00, 150 Ω source and 10 kΩ load. Each slope is a fit over −20, −18 and −16 dBu at 1 kHz, after stepped plateaus of 320 ms with a 20 ms ramp, at a 5 µs maximum solver step.

| Mod label | R44 | 2520 audio | JE-990 audio |
| --- | ---: | ---: | ---: |
| 2:1 | 200 Ω | 2.04:1 | 2.04:1 |
| 4:1 | 68 Ω | 4.15:1 | 4.15:1 |
| 8:1 | 30 Ω | 8.17:1 | 8.17:1 |
| 12:1 | 20 Ω | 11.73:1 | 11.73:1 |

The ratios are local slopes, with threshold and curvature changing along with R44. The [Mod characterization workflow](.github/workflows/vintage-ratio-mod.yml) measures the resulting curves across IN and Ceiling and records phase, distortion, attack and release for each ratio with both amplifier pairings. The Windows preview uses the measured curves at covered settings and interpolates outside that coverage.

The [8:1 harmonic measurements](reference/525c-mod-8-harmonics.csv) capture K2–K20 and fundamental phase. With all-2520, D-S off and −18 dBu, THD is 0.1111%, 0.01936%, 0.02174%, and 0.02424% at 100 Hz, 1 kHz, 5 kHz, and 10 kHz. These are analog bandwidth figures under the measured drive conditions. [Extended characterization results](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44256694480)

The [coverage ledger](reference/COVERAGE.md) tracks the exact pot matrix, switch coverage, noise, IMD, and work still required for the VST3 reference.

## Native A2 output-amplifier stage

[OutputAmplifier.h](dsp/OutputAmplifier.h) implements the linear A2 feedback response using two pole-zero sections derived from R40/R41/C7/C8. No SPICE solver runs in this stage. The [comparison](spice/check_output_amplifier.py) executes the compiled sample processor and measures it against the complete SPICE circuit from A2+ to the transformer primary. At 88.2 kHz internal rate, worst-case deviation across 100 points from 20 Hz to 20 kHz was 0.029 dB and 1.36° over both amplifier pairings and 600 Ω/10 kΩ loads. At 96 kHz the corresponding errors were 0.023 dB and 1.11°. The 44.1 kHz direct implementation missed the target at about 1.14 dB and 21.48°. These tests cover the linear amplifier stage. The future oversampling filters, saturation, transformer, detector, and assembled Windows plug-in require their own parity tests.

## Windows 525 VST3 preview

The Windows x64 workflow packages the native JUCE VST3 and its SHA-256. It also runs a separate host executable against the compiled bundle to compare 100 Hz, 1 kHz, 5 kHz, and 10 kHz at the measured drive levels and capture the editor at three scales. The harmonic comparison uses the same harmonic orders below 22.05 kHz on both sides. Test tone scaling uses 0 dBFS peak = +22 dBu for this preview. The test uses IN 50% for Compress and IN 90% for Limit, with OUT 75%, Ceiling 16, D-S off, release 00, and the 10 kΩ reference load.

The plug-in runs native reduced-order processing with 2× internal oversampling and latency-compensated dry bypass. Mono uses one signal path. Stereo uses two independent paths and two gain reduction readings on the shared panel. Attack uses measured 10–90% anchors where available. Release uses the measured 63.2% points with frequency interpolation. These parameters require separate end-to-end timing verification.

The 5–10% target remains open across the full control grid. The preview interpolates from sparse pot and level measurements. The measured harmonic tables provide amplitudes. Harmonic phase, the remaining Limit spectra, transformer saturation and load behavior, and control combinations outside the measured grid remain incomplete. Whole-path gain, phase and timing data must be verified before this build is considered final.

At 1 kHz, the offline core sweep over −20 to −16 dBu measured about 2.04:1,
4.15:1, 8.17:1, and 11.74:1 at the documented IN/OUT/Ceiling anchor.
The Limit candidate measured 21.05:1 over +2 to +6 dBu at IN 50%.
The 63.2% recovery crossings after a −18 to −30 dBu step at IN 90% were
121, 538, 1825, and 2238 ms. These are fixed test conditions, with separate
numerical checks required for other control settings.

### Independent IN and OUT harmonic calibration

The [pot grid](.github/workflows/vintage-harmonic-pots.yml) measures all 121
IN × OUT anchors at 10% increments, plus 100 independently measured midpoint
holdouts. The first run uses stock Compress, the 2520 pairing, ceiling 16,
release 00, and D-S off. It sweeps four frequencies from 100 Hz to 10 kHz and
six source levels from −30 to +24 dBu. The workflow can also run other
amplifier and switch configurations. Reference rows include K2–K20 amplitude,
phase, absolute output level, and late-window drift.

The embedded data cover +18 dBu at 1 kHz on the 10% grid for IN 0–100% and
OUT 10–100%. Build the sparse harmonic table with
`python3 calibration/generate_pot_harmonics.py reference/harmonic-pots/*.csv`.
Measured midpoint rows are held out from the table. OUT 0 is included in
SPICE as an absolute output-level check. Its harmonics relative to a near-zero
fundamental are below the calibration range. Missing calibration cells
continue to use the previous preview interpolation. Full coverage and
per-harmonic 5–10% agreement remain open.
