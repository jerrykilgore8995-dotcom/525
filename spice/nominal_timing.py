"""Measure audio gain timing and compare it with the vintage release ladder."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import math
from pathlib import Path
import subprocess

import numpy as np

from fixture import DETECTOR_TURNS
from verify import (MODES, PAIRS, RELEASE, ROOT, archive_models, crossings,
                    cycle_envelope, med, solve_deck, writer)


TARGETS = (.1, .5, .632, .9)
NOMINAL_MS = {"00": 100, "10": 500, "01": 2000, "11": 2500}
LABELS = ("10", "50", "63_2", "90")
CARRIER = 1000
INPUT_DBU, BURST_DBU = -30, -18


def release_ladder(path):
    """Read the drawn resistor values and calculate nominal time constants."""
    parts = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if fields and fields[0] in ("C3", "R60", "R61", "R62"):
            scale = {"u": 1e-6, "meg": 1e6}
            value = fields[3]
            unit = next(u for u in scale if value.endswith(u))
            parts[fields[0]] = float(value[:-len(unit)]) * scale[unit]
    # S2 bypasses R61 with button 1 out. S3 bypasses R62 with button 2 out
    # and bypasses R60 with button 2 in. The transistor network is downstream.
    for setting in RELEASE:
        first, second = (int(bit) for bit in setting)
        resistance = first * parts["R61"] + (parts["R62"] if second else parts["R60"])
        tau = resistance * parts["C3"] * 1000
        nominal = NOMINAL_MS[setting]
        yield {"release": setting, "ladder_ohm": resistance, "tau_ms": tau,
               "api_nominal_ms": nominal, "delta_pct": 100 * (tau - nominal) / nominal}


def render(args, dest, raw, start, stop, end, step, release, hz, phase, drive):
    amp, detector = args.pair.split("/")
    parameters = ["--opamp", amp, "--detector-opamp", detector, "--mode", args.mode,
                  "--input", ".9", "--ceiling", "8", "--detector-transformer", args.winding,
                  "--release-override-trim", str(args.override), "--release", release,
                  "--hz", str(hz), "--transient", "--dbu", str(INPUT_DBU),
                  "--burst-dbu", str(drive), "--burst-start", str(start),
                  "--burst-stop", str(stop), "--seconds", str(end), "--max-step", str(step),
                  "--trace", str(raw.relative_to(args.output))]
    deck = subprocess.check_output(["python3", "fixture.py", *parameters], cwd=ROOT, text=True)
    if phase:
        # Smooth the amplitude discontinuity at the crest with a 1 us PWL rise.
        quiet, loud = (.775 * math.sqrt(2) * 10**(level / 20) for level in (INPUT_DBU, drive))
        # A crest-down transition is unnecessary for an attack measurement.
        # Hold the loud plateau to the end of the attack-only trace.
        source = (f"VAMP amp 0 PWL(0 {quiet} {start} {quiet} {start+1e-6} {loud})\n"
                  "BINPUT src 0 V=v(amp)*v(carrier)")
        lines = []
        for line in deck.splitlines():
            if line.startswith("BINPUT "):
                line = source
            lines.append(line)
        deck = "\n".join(lines) + "\n"
    return solve_deck(args, dest, raw, deck, 9)


def audio_gain(y, x, pre_output_dc, pre_input_dc):
    return 20 * np.log10(np.maximum(abs(y-pre_output_dc), 1e-15) /
                         np.maximum(abs(x-pre_input_dc), 1e-15))


def summarize_attack(data, start, pre, delta):
    times, _, _, a1, _, _, gate, _, a1_plus = data.T
    # Stay on the first crest. Points beyond this interval approach a carrier
    # zero, where a ratio of two voltages is no longer an envelope estimate.
    mask = (times >= start + 1e-6) & (times <= start + .00012)
    quiet = (times >= start-.003) & (times < start-.001)
    q = np.arange(256) / (128 * CARRIER) + start - .003
    dc1 = np.interp(q, times[quiet], a1[quiet]).mean()
    dc2 = np.interp(q, times[quiet], a1_plus[quiet]).mean()
    values = audio_gain(a1[mask], a1_plus[mask], dc1, dc2)
    sample_us = .1
    grid = start + np.arange(10, 1201) * sample_us * 1e-6
    envelope = np.interp(grid, times[mask], values)
    # Require 5 us above threshold. Ignore isolated crossings caused by
    # propagation delay in the audio path during the source transition.
    hit = crossings(grid, (pre-envelope)/delta, TARGETS, start, 1e6, hold=50)
    result = {f"crest_t{label}_us": tick for label, tick in zip(LABELS, hit)}
    result["crest_10_90_us"] = hit[-1] - hit[0] if hit[-1] != "" and hit[0] != "" else ""
    result["crest_gr_at_15us_db"] = pre - np.interp(start+15e-6, times[mask], values)
    result["crest_gate_at_15us_v"] = np.interp(start+15e-6, times[mask], gate[mask])
    result["crest_max_observation_us"] = 120
    return result


def summarize_release(times, gain, gate, stop, pre, on, setting):
    delta = pre - on
    mask = times >= stop
    metrics = crossings(times[mask], gain[mask]-on,
                        (delta*.5, delta*.632, delta*.9, delta-1), stop, 1000, hold=5)
    result = dict(zip(("gain_t50_ms", "gain_t63_2_ms", "gain_t90_ms", "gain_to_1db_ms"), metrics))
    nominal = stop + NOMINAL_MS[setting] / 1000
    result["gr_left_at_nominal_db"] = pre - np.interp(nominal, times, gain)
    result["gate_at_nominal_v"] = np.interp(nominal, times, gate)
    result["right_censored_1db"] = metrics[-1] == ""
    return result


def measure(args, case):
    phase, setting, step, hz, drive = case
    if args.kind == "attack":
        shift = phase / (360 * hz)
        start, stop, end = .020 + shift, .041 + shift, .043 + shift
    else:
        start, stop, end = .120, .300, 4.300
    name = f"{args.kind}-{args.pair.replace('/', '-')}-{args.mode}-{args.winding}-{phase}-{setting}-{step:g}-{hz}-{drive:+}dBu"
    dest = args.output / name
    dest.mkdir(exist_ok=True)
    raw = dest / "timing.dat"
    status, data = render(args, dest, raw, start, stop, end, step, setting, hz, phase, drive)
    row = {"id": name, "pair": args.pair, "mode": args.mode, "detector": args.winding,
           "release": setting, "step_phase_deg": phase, "hz": hz, "max_step_s": step,
           "quiet_dbu": INPUT_DBU, "drive_dbu": drive,
           "release_override": args.override, "solver": status}
    if data is None:
        return row
    if data[-1, 0] < end - 1e-7 or np.any(np.diff(data[:, 0]) <= 0):
        return {**row, "solver": "incomplete_trace"}
    times, gain, gate = cycle_envelope(data, hz, end)
    width = max(.006, 3/hz)
    pre = med(gain, start-width, start-1/hz, times)
    on = med(gain, stop-width, stop-1/hz, times)
    delta = pre - on
    row.update(pre_a1_gain_db=pre, late_burst_a1_gain_db=on, gr_db=delta)
    if not math.isfinite(delta) or delta < 1.1:
        return {**row, "solver": "insufficient_gr"}
    if args.kind == "release":
        return {**row, **summarize_release(times, gain, gate, stop, pre, on, setting)}
    if phase == 90:
        row.update(summarize_attack(data, start, pre, delta))
    mask = (times >= start) & (times < stop)
    hits = crossings(times[mask], (pre-gain[mask])/delta, TARGETS, start, 1e6)
    row.update({f"cycle_t{label}_us": tick for label, tick in zip(LABELS, hits)})
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("attack", "release"))
    parser.add_argument("--mode", choices=MODES, default="C")
    parser.add_argument("--pair", choices=PAIRS, default="2520/2520")
    parser.add_argument("--winding", choices=tuple(DETECTOR_TURNS), default="ap2623")
    parser.add_argument("--override", type=float, default=.5)
    parser.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--timeout", type=int, default=200)
    args = parser.parse_args()
    archive_models(args)
    writer(args.output / "release-ladder.csv", list(release_ladder(args.output / "525c.lib")))
    cases = (product((0, 90), ("00",), (2.5e-7, 1.25e-7), (CARRIER,), (BURST_DBU, 4)) if args.kind == "attack"
             else product((0,), RELEASE, (1e-5,), (100, CARRIER), (BURST_DBU,)))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda case: measure(args, case), cases))
    writer(args.output / "summary.csv", rows)
    valid = sum(r["solver"] in ("complete", "insufficient_gr") for r in rows)
    print(f"{args.kind} {args.pair} {args.mode}: {valid}/{len(rows)} traces measured")
    if valid != len(rows):
        for row in rows:
            if row["solver"] not in ("complete", "insufficient_gr"):
                print(f'{row["id"]}: {row["solver"]}')
        raise SystemExit(1)


if __name__ == "__main__":
    main()
