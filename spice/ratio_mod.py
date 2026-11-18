"""Screen physical Compress feedback resistor values against selectable ratios."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
from types import SimpleNamespace

from gain_law import gain_curve, slope_windows
from verify import PAIRS, archive_models, writer


DEFAULT_RESISTANCES = (22, 47, 100, 150, 200, 330, 470, 680, 1000)
DEFAULT_LEVELS = (-40, -24, -20, -18, -16, -14, -12, -10, -8, -6, -4, -2, 0, 2, 4, 6, 8, 12)
TARGET_RATIOS = (2, 4, 8, 12)


def evaluate(args, case):
    resistor, inp, ceiling = case
    rows = gain_curve(SimpleNamespace(**vars(args), r44=resistor, mode="C"), (inp, ceiling, .3, 0))
    slopes = []
    if rows[0]["solver"] == "complete":
        for target in TARGET_RATIOS:
            slopes.extend({**row, "r44_ohm": resistor, "input_position": inp, "ceiling_mark": ceiling}
                          for row in slope_windows(rows, target) if row["points"] == 3)
    return rows, slopes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", choices=PAIRS, default=PAIRS[0])
    parser.add_argument("--output", required=True, type=lambda p: Path(p).resolve())
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--resistors", type=float, nargs="+", default=DEFAULT_RESISTANCES)
    parser.add_argument("--levels", type=int, nargs="+", default=DEFAULT_LEVELS)
    parser.add_argument("--input", type=float, nargs="+", default=(.5,))
    parser.add_argument("--ceiling", type=int, choices=range(0, 21, 2), nargs="+", default=(16,))
    parser.add_argument("--step", type=float, default=1e-5)
    parser.add_argument("--hold", type=float, default=.13)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.hold < .075 or len(args.levels) < 3 or list(args.levels) != sorted(set(args.levels)):
        parser.error("Provide a hold of at least .075 seconds and three strictly increasing levels")
    archive_models(args)
    cases = list(product(sorted(set(args.resistors)), sorted(set(args.input)), sorted(set(args.ceiling))))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda case: evaluate(args, case), cases))
    writer(args.output / "points.csv", [row for rows, _ in results for row in rows])
    slopes = [r for _, windows in results for r in windows]
    writer(args.output / "slopes.csv", slopes)
    for target in TARGET_RATIOS:
        eligible = [r for r in slopes if r["nominal_ratio"] == target and r["eligible"] and r["ratio"]]
        for r in sorted(eligible, key=lambda row: abs(row["ratio"]/target-1))[:3]:
            print(f'{target}:1 target: {r["ratio"]:.3f}:1 with R44={r["r44_ohm"]:g} ohms '
                  f'from {r["start_dbu"]} to {r["end_dbu"]} dBu at IN={r["input_position"]:g}')
    valid = sum(rows[0]["solver"] == "complete" for rows, _ in results)
    print(f"{valid}/{len(cases)} resistor/control sweeps completed")
    if valid != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
