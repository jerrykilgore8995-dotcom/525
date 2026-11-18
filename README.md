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
