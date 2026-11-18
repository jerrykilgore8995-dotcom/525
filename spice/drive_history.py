"""Measure gain and gate settling at the same level approached from both directions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from fixture import DETECTOR_TURNS
from verify import ROOT, PAIRS, MODES, archive_models, solve_deck, writer


HOLD_S = .320
RAMP_S = .020
SCHEDULES = {"cold": (4, 4, 4, 4, 4, 4, 4),
             "sweep": (-40, 0, 4, 8, 4, 0, -40)}
HZ = 1000
PROBES = (20, 100, 200, 300)
END_S = len(SCHEDULES["sweep"]) * (HOLD_S + RAMP_S)
COLUMNS = ("src", "oh", "x525.a1_out", "x525.a2_out", "x525.a3_out",
           "x525.fet_gate", "x525.detector_control", "x525.a1_plus",
           "x525.fet_drain", "x525.t2_high", "x525.t2_low")
WINDOW_CYCLES = 12


def source_text(levels):
    points = [(0, levels[0])]
    for i, (before, after) in enumerate(zip(levels, levels[1:]), 1):
        edge = i * (HOLD_S + RAMP_S)
        points += [(edge - RAMP_S, before), (edge, after)]
    levels_str = " ".join(f"{t:.6f} {level}" for t, level in points)
    return (f"Vschedule level 0 PWL({levels_str})\n"
            f"Vcarrier carrier 0 SIN(0 1 {HZ})\n"
            "Binput src 0 V=.775*sqrt(2)*exp(log(10)*v(level)/20)*v(carrier)")


def measure_window(times, data, end):
    points = 128
    t = end - WINDOW_CYCLES / HZ + np.arange(WINDOW_CYCLES * points) / (points * HZ)
    window = np.array([np.interp(t, times, values) for values in data.T])
    hs = 2 * np.fft.rfft(window, axis=1)[:, WINDOW_CYCLES] / len(t)
    gate, detector = window[5:7]
    return {
        "measured_input_dbu": float(20 * np.log10(abs(hs[0]) / (.775 * np.sqrt(2)))),
        "out_dbu": float(20 * np.log10(abs(hs[1]) / (.775 * np.sqrt(2)))),
        "a1_gain_db": float(20 * np.log10(abs(hs[2] / hs[7]))),
        "a1_plus_vpk": abs(hs[7]),
        "a1_vpk": abs(hs[2]),
        "a2_vpk": abs(hs[3]),
        "a3_vpk": abs(hs[4]),
        "gate_mean_v": float(gate.mean()),
        "gate_min_v": float(gate.min()),
        "gate_max_v": float(gate.max()),
        "detector_mean_v": float(detector.mean()),
        "fet_drain_vpk": abs(hs[8]),
        "secondary_hi_vpk": abs(hs[9]),
        "secondary_lo_vpk": abs(hs[10]),
    }


def run_history(args, case):
    mode, winding, schedule = case
    amp, detector = args.pair.split("/")
    name = f"{amp}-{detector}-{mode}-{winding}-{schedule}-in{args.input:g}-c{args.ceiling}"
    dest = args.output / name
    dest.mkdir(exist_ok=True)
    raw = dest / "history.dat"
    params = ["--opamp", amp, "--detector-opamp", detector, "--mode", mode, "--input", str(args.input),
              "--ceiling", str(args.ceiling // 2), "--detector-transformer", winding,
              "--seconds", str(END_S), "--max-step", str(args.step),
              "--transient", "--trace", str(raw.relative_to(args.output))]
    original = subprocess.check_output(["python3", "fixture.py", *params], cwd=ROOT, text=True)
    deck = []
    for line in original.splitlines():
        if line.startswith("VIN "):
            line = source_text(SCHEDULES[schedule])
        if line.startswith("fourier "):
            continue
        if line.startswith("wrdata "):
            line = f"wrdata {raw.relative_to(args.output)} " + " ".join(f"v({x})" for x in COLUMNS)
        deck.append(line)
    status, data = solve_deck(args, dest, raw, "\n".join(deck) + "\n", len(COLUMNS) + 1)
    common = {"id": name, "pair": args.pair, "mode": mode, "detector_transformer": winding,
              "schedule": schedule, "input_position": args.input, "ceiling_mark": args.ceiling,
              "max_step_s": args.step, "solver": status}
    if data is None:
        return [common]
    times = data[:, 0]
    if times[-1] < END_S - 1e-7 or np.any(np.diff(times) <= 0):
        return [{**common, "solver": "incomplete_trace"}]
    return [
        {**common, "plateau": i, "input_dbu": level, "elapsed_plateau_ms": ms,
         **measure_window(times, data[:, 1:], i * (HOLD_S + RAMP_S) + ms / 1000)}
        for i, level in enumerate(SCHEDULES[schedule]) for ms in PROBES
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", choices=PAIRS, required=True)
    parser.add_argument("--input", type=float, default=.9, help="IN pot position from 0 to 1")
    parser.add_argument("--ceiling", type=int, default=16, choices=range(0, 21, 2), help="Panel mark")
    parser.add_argument("--mode", choices=MODES, help="Run only this switch position")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--step", type=float, default=5e-6)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 0 <= args.input <= 1:
        parser.error("--input must be a position from 0 to 1")
    args.output = args.output.resolve()
    archive_models(args)
    modes = (args.mode,) if args.mode else MODES
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        groups = list(pool.map(lambda case: run_history(args, case),
                               product(modes, DETECTOR_TURNS, SCHEDULES)))
    writer(args.output / "summary.csv", [row for group in groups for row in group])
    success = sum(group[0]["solver"] == "complete" for group in groups)
    print(f"{args.pair}: {success}/{len(groups)} drive histories completed")
    if success != len(groups):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
