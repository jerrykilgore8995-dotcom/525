# Vintage 525C SPICE checkpoint

This is the connected vintage 525C engineering fixture at ±15 V inlet rails. The stock vintage test switches all three amplifier sockets together. An explicit detector override exercises the 2520 substitute independently of the audio amplifier choice. No result on this page establishes the 5% hardware tolerance.

## Discrete stages

| Selector | Components | Evidence and result |
| --- | ---: | --- |
| `2520-drawing` | 33 | 9 BJTs, 16 resistors, 5 capacitors, 3 MZ2361 parts. Direct transcription of the circulated [2520 redraw](https://www.scribd.com/document/334300673/API-2520-schematic-pdf). The literal drawing biases Q7's base from V+ through R9 and uses Q9's emitter at the same junction. The model draws over 2 A on the full module at idle and fails. |
| `2520-q9` | 33 | Q9 collector drives Q7 and the bias string, with the original 56 Ω R9 in Q9's emitter lead. The other device counts and values are unchanged. This is an engineering interpretation motivated by the [published variant disagreement at D2/Q9](https://groupdiy.com/threads/origin-of-2520-schematic.62035/), pending confirmation from a legible alternate drawing or traced module. DC and standalone follower audio are functional. The complete chain oscillates for tested conditions. |
| `2520` | 33 | Q9 correction plus 10 pF C5 from the inverting input to the lower output-drive node. Both alternatives are now testable. The capacitor value and use of the inverting-input connection have [independent 2520BC build reports](https://groupdiy.com/threads/api-312-thread.246/page-11) and [placement discussion](https://groupdiy.com/threads/ours-sound-like-the-2-5-2-0.4796/page-6). This exact combination is an engineering variant, pending module verification. |
| `990` | 44 | Original JE-990 values at ±15 V, including the LM394 matched halves, ferrite bypass inductors and all 12 diodes. The original R15/L3 isolator is represented separately and remains disconnected because the 525C sockets provide no corresponding feedback/output split. DC and selected audio diagnostics completed. High-drive transients and full calibration remain open. |

The 2N5087 and 2N5210 Gummel–Poon cards are from Fairchild-labelled entries in [the LTspice library mirror](https://github.com/mpkopec/ltspice-lib/blob/master/cmp/standard.bjt). The 2N5210 card represents the SKA4693 matched pair provisionally. The other obsolete transistor and rectifier cards are documented engineering estimates. The MZ2361 fit uses the [Motorola 1.24–1.38 V forward-drop band at 10 mA](https://www.bitsavers.org/components/motorola/_dataBooks/1988_Motorola_Rectifiers_and_Zener_Diodes_Data.pdf) rather than a one-junction diode. It still needs current/temperature and reversed-leakage data. The VCR2N nominal point and two transformer winding networks remain estimates. The transformers retain separate winding sections, resistance, leakage, capacitance and core loss. Core nonlinearity, authentic pin/turns data and individual transformer calibration are unresolved.

## Connected module and known differences

- The circuit audit checks all 120 vintage worksheet rows against 152 main-circuit and fixture entries, plus the discrete-stage counts. The count includes each electrically connected switch branch, split pot, fixture strap, and connector. It is a coverage check, with no claim that uncertain scan readings are cleared.
- Vintage C/L/OFF, de-ess, both release bits, and the two 11-position ceiling ladders are in the deck. Each ceiling selection now uses `ceiling_index`. The shorter name `ceil` conflicted with the ngspice built-in and silently selected 0 for tests made before the fix.
- Meter coil and lamp loads are estimates, as are some print readings. Specifically check R7 trim, R9 ladder, R64, R65, R66, R72 through R75, C5, C10, C12, C21 and the switch wiring against a clear copy or the board. The vintage test fixture references the module input low to common and references the secondary end for measurement. The reissue is a separate balanced circuit.
- The 525C drawing contains no reissue bypass relay or 2510. The owner authorized 2520 substitution, so a 2510 transistor-level model is no longer required for the substitute build. `--opamp 990 --detector-opamp 2520` keeps the 2520 in the vintage detector socket with JE-990 in both audio sockets. This is a test of the substitute under detector loading. The actual reissue 2510 assignment, footprints, input stage and bypass wiring remain to be verified.

## Results

ngspice 44.2, default fixture pots unless specified, 150 Ω source and 10 kΩ differential output load. Values here are diagnostics.

| Case | Result |
| --- | --- |
| 2520 literal drawing, full module | About 2.32 A positive idle rail and several volts of stage offset. |
| 2520 Q9 diagnostic, full module | At ceiling 0 and C, about 14.9 mA positive idle rail, with A1/A2/A3 DC offsets approximately −2.0/−9.4/+11.9 mV. |
| 2520 Q9 diagnostic, standalone follower | Around 4.05 mA per rail, −2.61 mV offset into 600 Ω, 0.7071 Vrms output for 1 V peak at 1 kHz. |
| 2520 Q9 diagnostic, complete module under drive | Some configurations oscillate and hit the rails. Example ceiling 0, C, +18 dBu, 1 kHz showed a dominant approximately 26 kHz output component. No THD value from this waveform can be used as reference. |
| JE-990 full module audio diagnostic | Ceiling 0, C, +4 dBu at 1 kHz gave 0.6140 Vrms and approximately −0.604 V minimum detector control. The output level is a path check with no settled gain reduction measurement. |
| JE-990 detector diagnostic | With IN at 0.9, −18 dBu at 1 kHz and a short run, ceiling 0 vs 20 moved detector minimum from −0.603 to −2.946 V. This verifies that the detector reacts to that control. A high-drive ceiling-20 run remained too slow for the diagnostic timeout. |

Reproduction with ngspice installed:

```sh
cd spice
python3 audit.py
python3 fixture.py --opamp 2520-drawing --ceiling 0 > /tmp/literal.cir
ngspice -b /tmp/literal.cir
python3 fixture.py --opamp 2520-q9 --ceiling 0 --ac > /tmp/q9.cir
ngspice -b /tmp/q9.cir
python3 fixture.py --opamp 990 --ceiling 0 --transient --diagnostic-tolerances \
  --trace /tmp/990-audio.dat > /tmp/990-audio.cir
ngspice -b /tmp/990-audio.cir
```

Do not treat DC or AC convergence as stability evidence. First establish stability and valid control trajectories under the actual termination, then compare with a smaller maximum timestep. Resolve the model and calibration gaps before scheduling the exhaustive SPICE matrix or fitting the real-time VST3.


## Loaded 2520 stability and 1 kHz measurements

Substitution at one socket at a time localized the strongest instability to the original C5 connection in the detector amplifier. It oscillated with JE-990 in both audio stages. With the Q9-only 2520 in the detector position, output at its A3 node could approach both rails even with a −18 dBu input and Ceiling zero. Reducing C5 to 10 pF at the old node still produced oscillation. Moving the 10 pF capacitor to the inverting input preserved all 33 parts and removed that behavior from the tested normal-load cases. Both previous variants remain available for comparison.

The first 50 ms matrix uses 1 kHz, ±15 V inlet power, a 150 Ω source and IN at 90%. It covers Ceiling marks 0/16/20 and input levels −40/−18/+4/+18 dBu in Compress and Limit. Output loading and timestep checks additionally exercise 600 Ω and 10 kΩ at +4 dBu in Compress, Limit and OFF. A completed row is a valid returned waveform window. Saturated or nonlinear operating points remain in the table. A timeout yields no measured row. This screening does not certify the whole matrix or exact hardware response.

| Audio stages / detector | Waveforms completed locally (9 s timeout) |
| --- | ---: |
| 2520 / 2520 | 33 / 34 |
| JE-990 / JE-990 | 20 / 34 |
| JE-990 / 2520 | 34 / 34 |

At Ceiling 16, +4 dBu, 10 kΩ, with the revised 2520 in all three positions:

| Mode | Output fundamental | A1 gain reduction | K2–K20 THD | Simulated residual THD+N |
| --- | ---: | ---: | ---: | ---: |
| Compress | −6.177 dBu | 21.020 dB | 0.02916% | 0.07437% |
| Limit | −10.245 dBu | 25.089 dB | 0.00306% | 0.02759% |
| OFF | +5.401 dBu | — | 0.00122% | 0.02251% |

A1 gain reduction is relative to A1's own low-drive baseline with matching op-amp and mode. The waveform residual includes modulation, incoherent components and interpolation effects. It does not represent physical noise with the transient noise sources disabled. At matching settings, reducing the maximum timestep from 2 μs to 1 μs changed output fundamental level by less than 0.0001 dB for these three cases. Compress THD changed from 0.02916% to 0.02913% at 10 kΩ. These convergence results apply to the listed conditions.

At Ceiling 16 in Compress, a −30 to +4 to −30 dBu burst at 1 kHz and release setting 00 reduced A1 gain from roughly 25 dB before the burst to 4.1 dB at its end. After falling back to −30 dBu at 50 ms, A1 gain was approximately 14.9 dB at 200 ms and 20.3 dB at 295 ms. This is a recovery trace, with no claim of 15 μs attack validation or matched release calibration.

The [Actions workflow](../.github/workflows/vintage-spice.yml) emits raw waveform tables, deck inputs, ngspice logs and harmonic/phase CSVs per amplifier pairing. Run locally from the repository root using:

```sh
python3 spice/characterize.py --output evidence --pair 2520/2520 --keep-all
python3 spice/characterize.py --output retry-evidence --timeout 60 --retry-from evidence/metrics.csv
```

Full-control characterization, nonlinear transformer validation, op-amp and FET parameter measurements, and sustained high-drive cases remain open. The VST3 fit follows the reference-validation gates described in the handoff.

## Loaded response, attack and recovery verification

The [response and timing workflow](../.github/workflows/vintage-verification.yml) archives each executable deck, ngspice log, raw trace, summary CSV and model hashes. These are vintage 525C fixture results at ±15 V, IN 90%, OUT 75%, Ceiling 16 and a 2520 detector. Audio stages use either the discrete 2520 or JE-990. The `complete` CSV status means the solver produced a usable trace for the test, with any censored recovery reported separately.

| Check | Completed locally | Conditions |
| --- | ---: | --- |
| AC magnitude, phase and group delay | 144/144 | C, L and OFF, D-S both positions, both amplifier pairings, 50/150/600 Ω source and 600 Ω/2 kΩ/10 kΩ/20 kΩ load. Sweep is 5 Hz–200 kHz with 160 points per decade. |
| Burst attack | 16/16 | C and L at 1 and 10 kHz, both pairings, 150 Ω source and 10 kΩ load, D-S off, release 00, 0.25 and 0.125 µs maximum solver steps. |
| Burst recovery | 16/16 | C and L at 1 kHz, both pairings, 150 Ω source and 10 kΩ load, D-S off, all four release states, 2.5 s observed recovery. |
| Output transformer coupling sensitivity | 24/24 | C and OFF, both amplifier pairings, 150 Ω source, 600 Ω/10 kΩ load, D-S off. Individual test decks change only the output transformer coupling. |

The loaded AC sweep normalizes magnitude to 1 kHz for the frequency-response check and retains the absolute gain, unwrapped output phase, group delay and A3 detector transfer. Twenty-four of 144 rows land within the reissue guide's nominal ±0.5 dB from 20 Hz to 40 kHz. Those rows all use OFF into 10 kΩ or 20 kΩ. The vintage and reissue fixtures and factory measurement conditions still need reconciliation. The result is a screening comparison. [API 525 user guide](https://apiaudio.com/docs/manuals/525_user_2020-12-15.pdf)

With 2520 audio stages and a 150 Ω source in Compress, the response at 20 Hz is −1.30 dB into 10 kΩ and −1.24 dB into 600 Ω. At 40 kHz it is −0.21 and −13.64 dB, respectively. With D-S enabled and the 10 kΩ load, the A3 response increases by 2.04 dB at 100 Hz and 7.91 dB at 5 kHz relative to D-S off. These are small-signal transfer results.

| Output transformer coupling | Compress 20 Hz into 600 Ω | Compress 40 kHz into 600 Ω | OFF 40 kHz into 600 Ω |
| --- | ---: | ---: | ---: |
| 0.9997, reference estimate | −1.24 dB | −13.64 dB | −13.70 dB |
| 0.99997, diagnostic | −1.29 dB | −1.03 dB | −1.09 dB |
| 0.99999, diagnostic | −1.29 dB | −0.31 dB | −0.37 dB |

The coupling test localizes the large high-frequency load sensitivity to the assumed output magnetics. It leaves the Compress low-frequency deficit essentially intact. The reference retains 0.9997 pending measured leakage, winding capacitance, ratio and loading. The diagnostic coupling values do not establish transformer accuracy.

The burst raises the source from −30 to +4 dBu at a carrier zero crossing. Attack uses a 20 ms burst, gate crossings relative to the pre-burst and late-burst medians and a whole-cycle A1 gain estimate derived from A1+ and A1 output. At 10 kHz with 2520 throughout, the 10–90% **gate** intervals are 18.93 µs in Compress and 20.72 µs in Limit at the finer step. Across all eight pairing/mode/carrier combinations, halving the maximum step changes the measured 10–90% gate interval by less than 0.007 µs. At 1 kHz, Compress reaches 90% gate excursion after roughly 652 µs while Limit does so after 46 µs. These are first crossings with control ripple and overshoot present. The A1 gain envelope has one-carrier-cycle resolution (1 ms at 1 kHz, 100 µs at 10 kHz). The test does not resolve a 15 µs audio-gain attack or establish the manufacturer's attack criterion.

Recovery uses a 60 ms burst and reports time to half the A1 gain reduction or to 1 dB remaining, requiring five consecutive cycles over each threshold. At 1 kHz, 2520 Compress recovers halfway in approximately 161/366/1038/1261 ms for release positions 00/10/01/11. It reaches 1 dB remaining after 508/2382 ms for 00/10. The latter two switch positions in both modes and pairings are right-censored at 2.5 s for the 1 dB criterion. The test verifies release-switch ordering and records recovery envelopes. Complete slow recovery and the factory release metric still need measurement.

Run from the repository root with Python, NumPy and ngspice 44.2:

```sh
OPENBLAS_NUM_THREADS=1 python3 spice/verify.py ac --output evidence/ac
OPENBLAS_NUM_THREADS=1 python3 spice/verify.py attack --output evidence/attack
OPENBLAS_NUM_THREADS=1 python3 spice/verify.py release --output evidence/release --timeout 150
OPENBLAS_NUM_THREADS=1 python3 spice/verify.py magnetics --output evidence/magnetics
```

Run an archived deck from its artifact's top-level directory with `ngspice -b <case-directory>/fixture.cir`. The deck writes a fresh trace to its own case directory.

## Control calibration and first real-time stage

At 10 kΩ with a 150 Ω source, Ceiling 16, IN 90% and OUT 75%, both amplifier pairs give nearly identical active-mode magnitude. With D-S off, the all-2520 Compress path is −0.609 dB at 30 Hz, −0.349 dB at 40 Hz, −0.049 dB at 20 kHz and −0.207 dB at 40 kHz, all relative to 1 kHz. The hybrid is −0.609, −0.349, −0.056 and −0.242 dB at the same frequencies. At 30 Hz the model is about 0.11 dB outside the earlier reissue's ±0.5 dB / 30 Hz–20 kHz nominal band. The 2020 reissue's nominal band starts at 20 Hz, where both pairings are approximately 1.30 dB down in Compress. Known 525C wiring and the unmodified device and transformer cards remain the circuit reference for these checks. [Earlier API spec sheet](https://www.barryrudolph.com/recall/manuals/br525.pdf) · [2020 user guide](https://apiaudio.com/docs/manuals/525_user_2020-12-15.pdf)

The control grid separately sweeps IN and OUT through their ranges for every 2 dB Ceiling mark and includes simultaneous off-grid IN/OUT holdouts. The AC matrix uses both D-S positions and C, L and OFF. The 1 kHz transient matrix uses six drive levels, selected D-S drive levels, pot sweeps and holdouts at +4 dBu. It records output level, phase, gate ripple, K2–K20 levels and phase, and late-window gain drift. A CSV solver completion indicates a valid trace. The gain-drift field separately flags cases that change by over 0.1 dB across the last 12 ms. Other release settings retain their dedicated timing matrix; their pot and drive interactions remain to be measured.

The output network is the first reduced real-time stage. [OutputCeiling.h](../dsp/OutputCeiling.h) implements the loaded OUT pot and Ceiling ladder plus the C5/R39/C6 input network of A2 using a two-pole filter with three history values. It leaves A1, gain reduction, A2 and transformer coloration to their own stage models. The C++ harness measures the impulse response through the actual sample processor. The comparison scales one SPICE response anchor (Ceiling 16, OUT 75%) by the measured digital tap ratio, and also tests the absolute digital tap against the independent circuit equation. OUT's exact-zero endpoint is excluded from relative error maxima because the SPICE deck uses a 1 µΩ numerical floor. Rows for that endpoint remain in the CSV.

In the first all-2520 Compress run, all 308 AC rows completed. The analog equation predicted the sampled output settings within 0.066 dB and 0.731° through 40 kHz. At 44.1 kHz, the compiled code reproduced the SPICE-relative magnitude to within 0.006 dB and phase to within 0.635° through the 20 kHz test point. These are small-signal control-law results at 10 kΩ with an anchored stage. They establish the OUT/CEILING transfer over the sampled settings. They do not include the compressor detector, attack/release or amplifier/transformer fit.

Run locally or use the [control calibration workflow](../.github/workflows/vintage-controls.yml):

```sh
export OPENBLAS_NUM_THREADS=1
python3 spice/control_grid.py ac --pair 2520/2520 --mode C --output evidence/control-ac
g++ -O2 -std=c++17 dsp/measure_output_ceiling.cpp -o /tmp/measure-tap
python3 spice/check_control_law.py evidence/control-ac/summary.csv evidence/control-ac/control-law.csv --dsp /tmp/measure-tap
python3 spice/control_grid.py tone --pair 2520/2520 --mode C --ceilings 16 18 20 --output evidence/control-tone
```

### Detector transformer ratio and unresolved gain law

The [vintage drawing](https://www.sowter.co.uk/schematics/API%20525C.pdf) shows matching AP2623 lead colors on both transformers. T1's two secondary sections are in series. T2 has the series junction grounded for full-wave rectification. [API's transformer catalog](https://www.steampoweredradio.com/pdf/api/manuals/api%201972%20schematics.pdf) gives the AP2623 1:1 or series 1:2 connection and [Sowter's replacement listing](https://www.sowter.co.uk/acatalog/VINTAGE-COMPRESSOR-TRANSFORMERS-A-to-K.html) specifies a 1:1:1 winding ratio for both the 525 output and control amplifiers.

The original provisional T2 card assumed 1:0.5:0.5. The fixture now supports a winding-ratio comparison using `--detector-transformer ap2623`. This holds the T2 primary, resistances, coupling and parasitics fixed and changes only the secondary inductances to equal the primary. The `legacy` default preserves the published SPICE traces and control calibration so the two runs can be compared. DCR, leakage, capacitance and core behavior still require independent data. The [detector comparison workflow](../.github/workflows/vintage-detector.yml) archives both versions with each audio amplifier and matched drive and attack stimuli.

At IN 90%, OUT 75%, Ceiling 16, 150 Ω source and 10 kΩ load, the local 1 kHz all-2520 tests show a material change in steady-state gain reduction:

| Test point | Legacy output | AP2623-ratio output |
| --- | ---: | ---: |
| C, −18 dBu source | −11.17 dBu | −14.82 dBu |
| C, −6 dBu source | −7.41 dBu | −12.35 dBu |
| L, −18 dBu source | −13.04 dBu | −17.51 dBu |
| L, −6 dBu source | −11.42 dBu | −16.93 dBu |

This is a comparison at fixed knobs and an identical rectifier and FET. The rate of rise in Compress is level dependent with either winding ratio. In the legacy 2 dB step sweep, the region from −18 to −16 dBu yields about 2.11:1, while the region from 0 to +2 dBu yields about 10.29:1. Some Limit cases continue drifting at the end of the 120 ms record, so do not interpret their slopes as settled. Both winding ratios can drive this particular FET card to cutoff, where A1 approaches unity gain and output slope returns to 1:1. A 2:1/20:1 pass across the rated range remains open pending revision-specific alignment and FET calibration. The historical factory procedure is indexed as [API 525C Docs.pdf, post 40](https://groupdiy.com/threads/api.44738/page-2#post-952903); direct access returned HTTP 403.

The T1 600 Ω/10 kΩ response ratio at 1 kHz implies a small-signal output impedance of approximately `196 + j91 Ω` for both amplifier pairings at the same control settings. That real part follows from the T1 estimates (32 Ω primary reflected by the 1:2 turns ratio plus two 34 Ω secondaries). It exceeds the earlier reissue's 100 Ω or the 2020 guide's 75 Ω stated output impedance. The revision and test conditions matter. This comparison and the separate coupling sensitivity test both point to T1 as the next load-calibration target.

## Sustained drive and output-load calibration

The [gain history and output calibration workflow](../.github/workflows/vintage-calibration.yml) preserves decks, model hashes, node waveforms and CSV summaries. Its gain tests use the 2520 detector, both audio amplifier configurations, both detector turns ratios and the C/L positions. At IN 90%, OUT 75%, Ceiling 16, D-S off, release 00, 150 Ω source and 10 kΩ load, a 1 kHz source either starts at +4 dBu and holds for 2.38 s or moves through −40, 0, +4, +8, +4, 0, −40 dBu using 20 ms ramps and 320 ms holds.

For the all-2520 Compress path with the AP2623-ratio detector, the initial 0 dBu plateau has approximately 2.39 dB of A1 gain and a −3.94 V mean gate after 300 ms. At the second 0 dBu plateau following overload, A1 remains at unity and the gate is approximately −6.93 V. Both +4 dBu plateaus and the 2.38 s constant +4 dBu run leave A1 at unity. The legacy ratio gives about 4.08 dB of A1 gain on both +4 dBu plateaus. In Limit with the legacy ratio, sustained +4 dBu produces about 1.05 dB of A1 gain after 300 ms, and about 1.25 dB after 2.34 s. The short-window drift test in the previous control grid can therefore miss slow motion and histories with distinct gain at the same input.

The output comparison puts a second, independently generated transformer library beside the original. The new library uses 15.7 Ω primary and 31.5 Ω per secondary from the CAPI 2623-1 Litz replacement guidance. It solves the minimum coupling in the specified bracket that places the **standalone** transformer within 0.5 dB of its 1 kHz value at 20 kHz, driven by an ideal source into the AP2623 catalog's 300 Ω minimum series-secondary load. The fitted value is approximately 0.9999752 per winding pair. Primary inductance, capacitance and loss otherwise retain their provisional values. This is a catalog-bounded candidate. The actual original transformer impedance, construction and magnetic nonlinearity remain unmeasured. [API transformer catalog](https://www.steampoweredradio.com/pdf/api/manuals/api%201972%20schematics.pdf) · [CAPI replacement winding guidance](https://groupdiy.com/threads/build-capi-vp28-500-series-2-stage-preamp-official-support-thread.48610/page-30)

In the connected all-2520 Compress fixture at 600 Ω, the candidate changes the 20 kHz relative gain from −7.93 to −0.24 dB, 40 kHz from −13.64 to −0.89 dB and the inferred 1 kHz output impedance from approximately 196 + j91 Ω to 126 + j8 Ω. Around 30 Hz, the candidate gives −0.61 dB into 600 Ω, and the connected 300 Ω case is still −0.58 dB at 20 kHz. These remaining errors matter for a full-module fit. Default magnetics are unchanged. The driven cases additionally compare gain, harmonic spectra and phase into 600 Ω and 10 kΩ using the two transformer libraries.

```sh
export OPENBLAS_NUM_THREADS=1
python3 spice/drive_history.py --pair 2520/2520 --output evidence/gain-history
python3 spice/output_loading.py --output evidence/output-loading --driven
```
