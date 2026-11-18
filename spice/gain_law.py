"""Measure local and multi-point driven 525C compression ratios by control setting."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from drive_history import measure_window, source_text, HOLD_S, RAMP_S, COLUMNS
from verify import MODES, PAIRS, ROOT, archive_models, solve_deck, writer


LEVELS = (-40, -30, -24, -20, -18, -16, -14, -12, -10, -8, -6, -4, -2, 0, 2, 4, 8, 12, 18)
NOMINAL = {"C": 2, "L": 20}
POINTS = ((.25, 10), (.5, 10), (.9, 10), (.25, 16), (.5, 16), (.9, 16), (.5, 20), (.9, 20))


def gain_curve(args, case):
    position, mark, trim, deess = case
    amp, detector = args.pair.split("/")
    name = f"{amp}-{detector}-{args.mode}-in{position:g}-c{mark}-trim{trim:g}-ds{deess}"
    dest = args.output / name
    dest.mkdir(exist_ok=True)
    path = dest / "gain-law.dat"
    end = len(LEVELS) * (HOLD_S + RAMP_S)
    params = ["--opamp", amp, "--detector-opamp", detector, "--mode", args.mode,
              "--detector-transformer", "ap2623", "--input", str(position), "--ceiling", str(mark//2),
              "--limit-trim", str(trim), "--deess", str(deess), "--seconds", str(end),
              "--max-step", str(args.step), "--transient", "--trace", str(path.relative_to(args.output))]
    original = subprocess.check_output(["python3", "fixture.py", *params], cwd=ROOT, text=True)
    deck = []
    for line in original.splitlines():
        if line.startswith("VIN "):
            line = source_text(LEVELS)
        if line.startswith("fourier "):
            continue
        if line.startswith("wrdata "):
            line = f"wrdata {path.relative_to(args.output)} " + " ".join(f"v({node})" for node in COLUMNS)
        deck.append(line)
    status, data = solve_deck(args, dest, path, "\n".join(deck) + "\n", len(COLUMNS) + 1)
    common = {"id": name, "pair": args.pair, "mode": args.mode, "input_position": position,
              "ceiling_mark": mark, "limit_trim": trim, "deess": deess, "solver": status}
    if data is None:
        return [common]
    times = data[:, 0]
    if times[-1] < end - 1e-7 or np.any(np.diff(times) <= 0):
        return [{**common, "solver": "incomplete_trace"}]
    rows = []
    quiet_gain = None
    for index, level in enumerate(LEVELS):
        onset = index * (HOLD_S + RAMP_S)
        near = measure_window(times, data[:, 1:], onset + .260)
        late = measure_window(times, data[:, 1:], onset + .310)
        if quiet_gain is None:
            quiet_gain = late["a1_gain_db"]
        drift = late["out_dbu"] - near["out_dbu"]
        rows.append({**common, "input_dbu": level, **late,
                     "gr_from_quiet_db": quiet_gain - late["a1_gain_db"],
                     "output_drift_db": drift, "stable": abs(drift) <= .05,
                     "near_fet_cutoff": late["a1_gain_db"] < 1})
    return rows


def slope_windows(rows, target):
    # Local ratios show knee and cutoff. Three or more successive settled
    # points across at least 4 dB provide the specification-screen windows.
    stages = []
    for width in (2, 3):
        for start in range(len(rows) - width + 1):
            selected = rows[start:start+width]
            first, last = selected[0], selected[-1]
            x = np.array([r["measured_input_dbu"] for r in selected])
            y = np.array([r["out_dbu"] for r in selected])
            line = np.polyfit(x, y, 1)
            slope = line[0]
            residual = float(np.max(np.abs(y - np.polyval(line, x))))
            ratio = 1 / slope if slope > 0 else None
            eligible = (width == 3 and x[-1]-x[0] >= 3.99 and
                        all(r["stable"] and not r["near_fet_cutoff"] and r["gr_from_quiet_db"] >= 1
                            for r in selected) and residual <= .10)
            stages.append({"id": first["id"], "start_dbu": first["input_dbu"],
                           "end_dbu": last["input_dbu"], "points": width, "slope_db_per_db": slope,
                           "ratio": ratio, "nominal_ratio": target, "fit_residual_db": residual,
                           "eligible": eligible,
                           "within_10pct": eligible and ratio is not None and abs(ratio/target-1) <= .10})
    return stages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", choices=PAIRS, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--subset", choices=("controls", "trim", "quick"), default="controls")
    parser.add_argument("--shard", type=int, choices=(0, 1), help="Select half of the matrix")
    parser.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--step", type=float, default=1e-5)
    args = parser.parse_args()
    archive_models(args)
    candidates = {
        "controls": [(p,m,.3,d) for (p,m),d in product(POINTS,(0,1))],
        "trim": [(.5,m,t,0) for m,t in product((10,16),(.1,.3,.6,.9))],
        "quick": [(.5, 16, .3, 0), (.9, 16, .3, 0)],
    }[args.subset]
    if args.shard is not None:
        candidates = candidates[args.shard::2]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        curves = list(pool.map(lambda case: gain_curve(args, case), candidates))
    writer(args.output / "points.csv", [r for curve in curves for r in curve])
    slopes = [r for curve in curves if curve[0]["solver"] == "complete"
              for r in slope_windows(curve, NOMINAL[args.mode])]
    writer(args.output / "slopes.csv", slopes)
    good = sum(curve[0]["solver"] == "complete" for curve in curves)
    eligible = [r for r in slopes if r["eligible"]]
    print(f"{args.pair} {args.mode}: {good}/{len(curves)} curves; "
          f"{sum(r['within_10pct'] for r in eligible)}/{len(eligible)} eligible windows within 10%")
    if good != len(curves):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
