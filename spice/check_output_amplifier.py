"""Compare the compiled A2 feedback filter to the connected vintage 525C."""
import argparse
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from verify import PAIRS, ROOT, archive_models, solve_deck, writer


def measure(args, pair, load):
    amp, detector = pair.split("/")
    name = f"{amp}-{load}"
    dest = args.output / name
    dest.mkdir(exist_ok=True)
    raw = dest / "ac.dat"
    cmd = ["python3", "fixture.py", "--opamp", amp, "--detector-opamp", detector,
           "--detector-transformer", "ap2623", "--mode", "C", "--load", str(load), "--ac",
           "--ac-trace", str(raw.relative_to(args.output))]
    deck = subprocess.check_output(cmd, cwd=ROOT, text=True)
    deck = deck.replace("vdb(oh) vp(oh) vdb(x525.a3_out) vp(x525.a3_out)",
                        "vdb(x525.a2_out) vp(x525.a2_out) vdb(x525.a2_plus) vp(x525.a2_plus)")
    status, data = solve_deck(args, dest, raw, deck, 5)
    if status != "complete":
        raise RuntimeError(f"{name}: {status}")
    hz, output, output_phase, input_, input_phase = data.T
    if hz[-1] < 20000 or hz[0] > 20 or np.any(np.diff(hz) <= 0):
        raise ValueError(f"{name}: invalid AC frequency grid")
    probes = np.geomspace(20, 20000, 100)
    gain = np.interp(probes, hz, output-input_)
    phase = np.interp(probes, hz, np.unwrap(output_phase-input_phase))
    for rate in (44100, 88200, 96000, 176400):
        stimulus = "".join(f"{rate} {f}\n" for f in probes)
        native = subprocess.check_output([args.dsp], input=stimulus, text=True)
        real, imag = np.loadtxt(native.splitlines()).T
        if real.shape != probes.shape or not np.isfinite(real+1j*imag).all():
            raise ValueError("Invalid native filter output")
        gain_error = 20*np.log10(np.hypot(real, imag)) - gain
        phase_error = np.angle((real+1j*imag)*np.exp(-1j*phase), deg=True)
        yield {"pair": pair, "load_ohm": load, "internal_rate_hz": rate,
               "max_gain_error_db": max(abs(gain_error)),
               "max_phase_error_deg": max(abs(phase_error))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsp", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--ngspice", default="ngspice")
    args = parser.parse_args()
    args.timeout = 30
    archive_models(args)
    rows = [row for pair, load in product(PAIRS, (600, 10000)) for row in measure(args, pair, load)]
    writer(args.output/"summary.csv", rows)
    for row in rows:
        print(row)
    if any(row["internal_rate_hz"] > 44100 and
           (row["max_gain_error_db"] > .05 or row["max_phase_error_deg"] > 2)
           for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
