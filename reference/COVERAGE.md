# 525C reference coverage

The vintage 525C circuit runs with the AP2623-ratio detector candidate and provisional output transformer. The separate reissue hardwire BYP has no vintage schematic equivalent. Its audio identity belongs in the binary host tests.

| Measurement | Evidence |
| --- | --- |
| Stock and Mod gain laws, attack, release, phase and harmonics | [Reference index](../README.md) |
| AC at fixed IN and OUT | 1,056 cases for each source/load fixture. Both amplifier pairings, four Compress ratios, Limit, OFF, four release selections, both D-S states and eleven Ceiling positions. Both 150 Ω/2 kΩ and 150 Ω/20 kΩ also completed locally at the fixed pot anchor, alongside 150 Ω/10 kΩ. |
| AC at 1% pot resolution | 10,772,256 distinct vintage configurations per source/load fixture. The 1,056-case IN 25% / OUT 75% shard at 150 Ω / 10 kΩ completed locally. A separate 32-case shard completed and reused the archived traces successfully. |
| IMD | The CI job measures two coherent stimulus pairs, two drive levels, both amplifier pairings and six mode/ratio configurations. Each CSV records individual product levels and their summed energy relative to the upper tone. |
| Noise | [24 of 24 linearized sweeps](525c-noise-reference.csv) completed, covering both amplifier pairings and 600 Ω/10 kΩ. Noise integrates 20 Hz to 20 kHz around the idle operating point. These are model-card noise predictions. Driven residual remains a separate measurement. |
| Input impedance | [48 complex sweeps](525c-input-impedance.csv) across both amplifier pairings, both D-S states, all mode/ratio combinations and two output loads. At 1 kHz the real part is 10.299–10.300 kΩ in this vintage fixture. |
| Remaining reference work | Full pot matrix coverage and driven test families across it, matched gain reduction, long and repeated release histories, program material, stereo link, physical transformer nonlinearity and equivalent hardware validation. |

## Repeat a shard

Case IDs in the full grid order the IN position, OUT position, amplifier pairing, circuit mode/ratio, release state, D-S and Ceiling. The last axis changes fastest. Each simultaneous IN/OUT setting uses 1,056 consecutive IDs. The first workload beyond the fixed-pot anchor on GitHub uses IN 25% and OUT 75%.

```sh
export OPENBLAS_NUM_THREADS=1
python3 spice/reference_matrix.py ac --count
python3 spice/reference_matrix.py ac --preset anchor --output evidence/anchor
python3 spice/reference_matrix.py ac --start 2745600 --stop 2746656 --output evidence/full
python3 spice/reference_matrix.py tone --start 2745600 --stop 2745608 --hz 1000 --dbu -18 --output evidence/tone-1khz-minus18
python3 spice/intermodulation.py --pair 2520/2520 --stimuli smpte --output evidence/imd
python3 spice/noise_floor.py --pair 2520/2520 --output evidence/noise
python3 spice/input_impedance.py --output evidence/input-z
```

The runner checks the simulator, stimulus, circuit and measurement-code fingerprints before resuming. An existing valid trace and per-case result are reused. Missing or failed cases run again. Tone rows with excessive late-window drift also rerun. Changing the duration or circuit needs a new evidence directory. A completed waveform establishes coverage for that stimulus and control ID. It is not a hardware-match assertion.

[Control coverage and two-tone raw traces](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44258411537) · [Noise sweeps](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44258411594) · [Targeted Mod attack retries](https://github.com/jerrykilgore8995-dotcom/525/actions/runs/44259000497)
