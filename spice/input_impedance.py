"""Measure complex source-facing input impedance on the connected 525C deck."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from reference_matrix import MODES
from verify import PAIRS, ROOT, archive_models, solve_deck, writer


def measure(args, case):
    pair, (mode, resistor), deess, load = case
    amp, detector = pair.split("/")
    name = f"{amp}-{mode}-{resistor}-ds{deess}-{load}"
    directory = args.output / name
    directory.mkdir(exist_ok=True)
    raw = directory / "impedance.dat"
    relative = raw.relative_to(args.output)
    cmd = ["python3", "fixture.py", "--opamp", amp, "--detector-opamp", detector,
           "--detector-transformer", "ap2623", "--mode", mode, "--comp-r44", str(resistor),
           "--input", ".5", "--output", ".75", "--ceiling", "8", "--deess", str(deess),
           "--load", str(load), "--ac"]
    deck = subprocess.check_output(cmd, cwd=ROOT, text=True)
    deck = deck.replace("print vdb(oh) vp(oh)", "\n".join((
        "let zin = -v(ip)/i(VIN)", "set wr_singlescale", "set wr_vecnames",
        f"wrdata {relative} real(zin) imag(zin)")))
    status, data = solve_deck(args, directory, raw, deck, 3)
    row = {"id": name, "pair": pair, "mode": mode, "r44_ohm": resistor, "deess": deess,
           "load": load, "source": 150, "solver": status}
    if data is None:
        return row
    frequency, real, imag = data.T
    if frequency[-1] < 199000 or np.any(np.diff(frequency) <= 0):
        return {**row, "solver": "incomplete_sweep"}
    for hz in (20, 100, 1000, 5000, 10000, 20000, 40000):
        row[f"real_ohm_{hz}hz"] = np.interp(hz, frequency, real)
        row[f"imag_ohm_{hz}hz"] = np.interp(hz, frequency, imag)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=lambda p: Path(p).resolve())
    parser.add_argument("--ngspice", default="ngspice")
    args = parser.parse_args()
    args.timeout = 45
    archive_models(args)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda case: measure(args, case), product(PAIRS, MODES, (0,1), (600,10000))))
    writer(args.output / "summary.csv", rows)
    complete = sum(r["solver"] == "complete" for r in rows)
    print(f"{complete}/{len(rows)} source-facing AC impedance sweeps completed")
    if complete != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
