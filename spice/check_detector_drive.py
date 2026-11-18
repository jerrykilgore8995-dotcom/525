"""Compare the native IN/CEILING detector tap to the fully connected 525C deck."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from verify import MODES, PAIRS, ROOT, archive_models, solve_deck, writer


def spice_tap(args, case):
    position, index, mode = case
    amp, detector = args.pair.split("/")
    dest = args.output / f"{mode}-{index:02}-{position:g}"
    dest.mkdir(exist_ok=True)
    path = dest / "ac.dat"
    params = ["--opamp", amp, "--detector-opamp", detector, "--detector-transformer", "ap2623",
              "--mode", mode, "--input", str(position), "--ceiling", str(index), "--ac",
              "--ac-trace", str(path.relative_to(args.output))]
    original = subprocess.check_output(["python3", "fixture.py", *params], cwd=ROOT, text=True)
    deck = []
    for line in original.splitlines():
        if line.startswith("ac "):
            line = "ac lin 1 1000 1000"
        if line.startswith("print vdb"):
            continue
        if line.startswith("wrdata "):
            line = f"wrdata {path.relative_to(args.output)} vm(x525.a3_plus) vm(x525.a1_out)"
        deck.append(line)
    status, data = solve_deck(args, dest, path, "\n".join(deck) + "\n", 3, min_rows=1)
    return status, data[0,1] / data[0,2] if status == "complete" else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", choices=PAIRS, required=True)
    parser.add_argument("--dsp", required=True, type=lambda p: Path(p).resolve())
    parser.add_argument("--output", required=True, type=lambda p: Path(p).resolve())
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.timeout = 20
    archive_models(args)
    controls = list(product((0, .01, .13, .25, .5, .66, .9, 1), range(11), MODES))
    lines = "".join(f"{position} {index} {int(mode == 'L')}\n" for position, index, mode in controls)
    native = subprocess.check_output([args.dsp], input=lines, text=True)
    ratios = np.loadtxt(native.splitlines())
    if ratios.shape != (len(controls),) or not np.isfinite(ratios).all():
        raise ValueError("Unexpected native measurement count or non-finite value")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        observations = list(pool.map(lambda case: spice_tap(args, case), controls))
    rows = []
    for control, measurement, predicted in zip(controls, observations, ratios):
        status, actual = measurement
        position, index, mode = control
        row = {"solver": status, "input_position": position, "ceiling_mark": 2*index,
               "mode": mode, "native_gain": predicted, "spice_gain": actual}
        if actual is not None:
            row["absolute_error"] = abs(predicted - actual)
            if actual > 1e-5:
                row["error_db"] = 20*np.log10(predicted/actual)
        rows.append(row)
    writer(args.output / "summary.csv", rows)
    valid = [r for r in rows if r["solver"] == "complete"]
    if not valid:
        raise SystemExit("No valid native control comparisons")
    db = max(abs(r["error_db"]) for r in valid if "error_db" in r)
    err = max(r["absolute_error"] for r in valid)
    print(f"{args.pair}: {len(valid)}/{len(rows)} rows, max {db:.6f} dB, absolute gain error {err:.7g}")
    if len(valid) != len(rows) or db > .1 or err > .002:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
