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
