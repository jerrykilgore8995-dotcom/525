"""Measure driven gain, phase and K2–K20 of the 525C across frequency."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path

from control_grid import tonal_summary
from verify import PAIRS, MODES, archive_models, run_fixture, writer


FREQUENCIES = (30, 100, 1000, 5000, 10000, 20000)
LEVELS = (-30, -18, 4)


def measure(args, case):
    hz, level, deess = case
    amp, detector = args.pair.split("/")
    # At least 18 complete cycles, including a twelve-cycle analysis window.
    cycles = max(18, round(.08 * hz))
    end = cycles / hz
    step = min(5e-6, 1 / (400 * hz))
    name = f"{amp}-{detector}-{args.mode}-{args.load}-{hz}Hz-{level:+}dBu-ds{deess}"
    status, data = run_fixture(args, name, [
        "--opamp", amp, "--detector-opamp", detector, "--mode", args.mode,
        "--input", ".9", "--output", ".75", "--ceiling", "8", "--deess", str(deess),
        "--source", "150", "--load", str(args.load), "--transient", "--dbu", str(level),
        "--hz", str(hz), "--max-step", str(step), "--seconds", str(end),
    ])
    row = {"id": name, "solver": status, "pair": args.pair, "mode": args.mode,
           "load_ohm": args.load, "input_dbu": level, "hz": hz,
           "deess": deess, "max_step_s": step, "analysis_cycles": 12,
           "detector_transformer": args.detector_transformer}
    return {**row, **tonal_summary(data, seconds=end, tone_hz=hz)} if data is not None else row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", choices=PAIRS, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--load", choices=(600, 10000), type=int, default=10000)
    parser.add_argument("--hz", choices=FREQUENCIES, type=int, nargs="+", default=FREQUENCIES)
    parser.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    args.detector_transformer = "ap2623"
    archive_models(args)
    freqs = sorted(set(args.hz))
    cases = list(product(freqs, LEVELS, (0,)))
    cases += [(hz, -18, 1) for hz in (100, 5000) if hz in freqs]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda case: measure(args, case), cases))
    anchors = {r["hz"]: r["a1_gain_db"] for r in rows if r["solver"] == "complete"
               and r["input_dbu"] == LEVELS[0] and r["deess"] == 0}
    for r in rows:
        if r["solver"] == "complete" and r["hz"] in anchors:
            r["relative_to_quiet_a1_gain_reduction_db"] = anchors[r["hz"]] - r["a1_gain_db"]
    writer(args.output / "summary.csv", rows)
    valid = sum(row["solver"] == "complete" for row in rows)
    stable = sum(row.get("settled_half_window_0_1db", False) for row in rows)
    print(f"{args.pair} {args.mode} {args.load} Ω: {valid}/{len(rows)} valid traces, {stable} within window drift limit")
    if valid != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
