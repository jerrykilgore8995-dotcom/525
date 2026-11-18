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
