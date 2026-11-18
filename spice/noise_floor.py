"""Measure linearized SPICE noise across the 525C signal paths."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from reference_matrix import MODES
from verify import PAIRS, ROOT, archive_models, solve_deck, writer


def measure(args, configuration):
    mode, resistance = configuration
    amp, detector = args.pair.split("/")
    dest = args.output / f"{mode}-{resistance}"
    dest.mkdir(exist_ok=True)
    raw = dest / "noise.dat"
    params = ["--opamp", amp, "--detector-opamp", detector, "--mode", mode,
              "--comp-r44", str(resistance), "--detector-transformer", "ap2623",
              "--input", ".5", "--output", ".75", "--ceiling", "8", "--load", str(args.load)]
    deck = subprocess.check_output(["python3", "fixture.py", *params], cwd=ROOT, text=True)
    commands = [
        "noise v(oh,ol) VIN dec 160 20 20000",
        "setplot noise1",
        "set wr_singlescale",
        "set wr_vecnames",
        "set numdgt=16",
        f"wrdata {raw.relative_to(args.output)} onoise_spectrum inoise_spectrum",
    ]
    deck = deck.replace("\nquit\n", "\n" + "\n".join(commands) + "\nquit\n")
    status, data = solve_deck(args, dest, raw, deck, 3)
    row = {"pair": args.pair, "mode": mode, "r44_ohm": resistance, "source_ohm": 150,
           "load_ohm": args.load, "solver": status}
    if data is None:
        return row
    frequency, output, input_referred = data.T
    if frequency[0] > 20.01 or frequency[-1] < 19999 or np.any(np.diff(frequency) <= 0):
        return {**row, "solver": "incomplete_trace"}
    for label, density in (("output", output), ("input_referred", input_referred)):
        power = np.dot(np.diff(frequency), (density[:-1]**2 + density[1:]**2)*.5)
        if power <= 0:
            return {**row, "solver": "invalid_noise_power"}
        row[f"{label}_noise_vrms"] = np.sqrt(power)
        row[f"{label}_noise_dbu"] = 20*np.log10(np.sqrt(power)/.775)
        row[f"{label}_noise_at_1khz_v_sqrthz"] = np.interp(1000, frequency, density)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", choices=PAIRS, required=True)
    parser.add_argument("--load", type=int, choices=(600, 10000), default=10000)
    parser.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--ngspice", default="ngspice")
    args = parser.parse_args()
    args.timeout = 60
    archive_models(args)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda cfg: measure(args, cfg), MODES))
    writer(args.output / "summary.csv", rows)
    done = sum(r["solver"] == "complete" for r in rows)
    print(f"{args.pair} {args.load} ohms: {done}/{len(rows)} noise sweeps completed")
    if done != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
