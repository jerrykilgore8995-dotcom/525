# Vintage 525C SPICE checkpoint

This is the connected vintage 525C engineering fixture at ±15 V inlet rails. The three vintage amplifier sockets switch together. The reissue and its 2510 remain separate. No result on this page establishes the 5% hardware tolerance.

## Discrete stages

| Selector | Components | Evidence and result |
| --- | ---: | --- |
| `2520-drawing` | 33 | 9 BJTs, 16 resistors, 5 capacitors, 3 MZ2361 parts. Direct transcription of the circulated [2520 redraw](https://www.scribd.com/document/334300673/API-2520-schematic-pdf). The literal drawing biases Q7's base from V+ through R9 and uses Q9's emitter at the same junction. The model draws over 2 A on the full module at idle and fails. |
| `2520` | 33 | Q9 collector drives Q7 and the bias string, with the original 56 Ω R9 in Q9's emitter lead. The other device counts and values are unchanged. This is an engineering interpretation motivated by the [published variant disagreement at D2/Q9](https://groupdiy.com/threads/origin-of-2520-schematic.62035/), pending confirmation from a legible alternate drawing or traced module. DC and standalone follower audio are functional. The complete chain oscillates for tested conditions. |
| `990` | 44 | Original JE-990 values at ±15 V, including the LM394 matched halves, ferrite bypass inductors and all 12 diodes. The original R15/L3 isolator is represented separately and remains disconnected because the 525C sockets provide no corresponding feedback/output split. DC and selected audio diagnostics completed. High-drive transients and full calibration remain open. |

The 2N5087 and 2N5210 Gummel–Poon cards are from Fairchild-labelled entries in [the LTspice library mirror](https://github.com/mpkopec/ltspice-lib/blob/master/cmp/standard.bjt). The 2N5210 card represents the SKA4693 matched pair provisionally. The other obsolete transistor and rectifier cards are documented engineering estimates. The MZ2361 fit uses the [Motorola 1.24–1.38 V forward-drop band at 10 mA](https://www.bitsavers.org/components/motorola/_dataBooks/1988_Motorola_Rectifiers_and_Zener_Diodes_Data.pdf) rather than a one-junction diode. It still needs current/temperature and reversed-leakage data. The VCR2N nominal point and two transformer winding networks remain estimates. The transformers retain separate winding sections, resistance, leakage, capacitance and core loss. Core nonlinearity, authentic pin/turns data and individual transformer calibration are unresolved.

## Connected module and known differences

- The circuit audit checks all 120 vintage worksheet rows against 152 main-circuit and fixture entries, plus the discrete-stage counts. The count includes each electrically connected switch branch, split pot, fixture strap, and connector. It is a coverage check, with no claim that uncertain scan readings are cleared.
- Vintage C/L/OFF, de-ess, both release bits, and the two 11-position ceiling ladders are in the deck. Each ceiling selection now uses `ceiling_index`. The shorter name `ceil` conflicted with the ngspice built-in and silently selected 0 for tests made before the fix.
- Meter coil and lamp loads are estimates, as are some print readings. Specifically check R7 trim, R9 ladder, R64, R65, R66, R72 through R75, C5, C10, C12, C21 and the switch wiring against a clear copy or the board. The vintage test fixture references the module input low to common and references the secondary end for measurement. The reissue is a separate balanced circuit.
- The 525C drawing contains no reissue bypass relay or 2510. The reissue schematic and fitted devices remain needed for the final target. The public 550L 2510 pin map contains external connections only. The distinct 525C pinout and vintage OFF route should not be used as the 500-series implementation.

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
python3 fixture.py --opamp 2520 --ceiling 0 --ac > /tmp/q9.cir
ngspice -b /tmp/q9.cir
python3 fixture.py --opamp 990 --ceiling 0 --transient --diagnostic-tolerances \
  --trace /tmp/990-audio.dat > /tmp/990-audio.cir
ngspice -b /tmp/990-audio.cir
```

Do not treat DC or AC convergence as stability evidence. First establish stability and valid control trajectories under the actual termination, then compare with a smaller maximum timestep. Resolve the model and calibration gaps before scheduling the exhaustive SPICE matrix or fitting the real-time VST3.
