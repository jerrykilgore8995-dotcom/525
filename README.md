# 525

Component-level reconstruction of the API 525 500-series reissue followed by a Windows x64 VST3. The project is at the circuit evidence stage. See the [current reconstruction checkpoint](reference/RECONSTRUCTION.md) for the vintage 525C trace, original Jensen JE-990 component audit, reissue control table and gaps preventing simulation.

- [Engineering gates](AGENTS.md)
- [Measurement and acceptance protocol](MEASUREMENT.md)
- [Faceplate specification](GUI.md)
- [Source provenance](SOURCES.md)

The provided matrix generator emits stable configuration IDs. Run `python3 matrix.py --count` for the provisional 11-position ceiling grid, or `python3 matrix.py --start 0 --stop 8` to emit an example shard.
