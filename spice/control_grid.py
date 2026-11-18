"""Measure the 525C potentiometer, ceiling, and mode response for a reduced-order model."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import math
from pathlib import Path

import numpy as np

from verify import PAIRS, ac_summary, archive_models, run_fixture, writer


REFERENCE = (90, 75)
POT_POSITIONS = (0, 25, 50, 75, 100)
HOLDOUT = ((13, 87), (37, 33), (66, 42), (87, 59))
LEVELS = (-40, -18, -6, 4, 12, 18)
SECONDS = .12
TONE_HZ = 1000
FLOOR = 1e-15


def cases(kind, ceilings, mode):
    """Return separate pot axes and independent simultaneous-control holdouts."""
    in_ref, out_ref = REFERENCE
    pots = [(x, out_ref, "input") for x in POT_POSITIONS if x != in_ref]
    pots += [(in_ref, x, "output") for x in POT_POSITIONS if x != out_ref]
    if kind == "ac":
        for mark, deess in product(ceilings, (0, 1)):
            for x, y, tag in [(in_ref, out_ref, "reference"), *pots, *((x, y, "holdout") for x, y in HOLDOUT)]:
                yield mark, deess, x, y, tag, None
    elif mode == "OFF":
        for level in LEVELS:
            yield 8, 0, in_ref, out_ref, "reference", level
    else:
        for mark in ceilings:
            for level in LEVELS:
                yield mark, 0, in_ref, out_ref, "reference", level
            for x, y, tag in pots:
                yield mark, 0, x, y, tag, 4
            for x, y in HOLDOUT:
                yield mark, 0, x, y, "holdout", 4
            for level in (-18, 4, 18):
                yield mark, 1, in_ref, out_ref, "reference", level


def amplitude_db(x):
    return 20 * math.log10(max(FLOOR, abs(x)))


def phase_deg(x):
    return math.degrees(np.angle(x))


def tonal_summary(data):
    times = data[:, 0]
    if times[0] > 1e-9 or times[-1] < SECONDS - 1e-9 or np.any(np.diff(times) <= 0):
        return {"solver": "incomplete_burst"}
    cycles = 12
    points = 256
    sample_rate = points * TONE_HZ
    t = SECONDS - cycles / TONE_HZ + np.arange(cycles * points) / sample_rate
    columns = (1, 2, 3, 4, 5, 8)
    samples = np.array([np.interp(t, times, data[:, col]) for col in columns])
    phases = np.fft.rfft(samples.reshape(len(columns), cycles, points), axis=2) * (2 / points)
    src, out, a1, a2, a3, a1_plus = phases.mean(axis=1)
    early, late = np.split(phases[:, :, 1], 2, axis=1)
    half_gain = [abs(half[2].mean() / half[5].mean()) for half in (early, late)]
    gain_drift = amplitude_db(half_gain[1]) - amplitude_db(half_gain[0])
    audio_drift = amplitude_db(late[1].mean()) - amplitude_db(early[1].mean())
    primary = max(FLOOR, abs(out[1]))
    ideal = np.real(out[1] * np.exp(2j * np.pi * np.arange(cycles * points) / points))
    residual = samples[1] - samples[1].mean() - ideal
    gate = np.interp(t, times, data[:, 6])
    detector = np.interp(t, times, data[:, 7])
    return {
        "out_dbu": amplitude_db(primary / (.775 * math.sqrt(2))),
        "gain_db": amplitude_db(out[1] / src[1]),
        "phase_deg": phase_deg(out[1] / src[1]),
        "a1_gain_db": amplitude_db(a1[1] / a1_plus[1]),
        "a1_phase_deg": phase_deg(a1[1] / a1_plus[1]),
        "a2_fundamental_vpk": abs(a2[1]),
        "a3_fundamental_vpk": abs(a3[1]),
        "output_peak_v": float(np.max(np.abs(data[:, 2]))),
        "gate_mean_v": float(gate.mean()),
        "gate_ripple_vpp": float(np.ptp(gate)),
        "detector_mean_v": float(detector.mean()),
        "gain_drift_db": gain_drift,
        "output_drift_db": audio_drift,
        "settled_half_window_0_1db": max(abs(gain_drift), abs(audio_drift)) <= .1,
        "thd_k2_k20_pct": 100 * np.linalg.norm(out[2:21]) / primary,
        "residual_pct": 100 * np.sqrt(2 * np.mean(residual**2)) / primary,
        **{f"k{k}_dbc": amplitude_db(out[k] / primary) for k in range(2, 21)},
        **{f"k{k}_phase_deg": phase_deg(out[k] * (np.conj(src[1]) / abs(src[1]))**k)
           for k in range(2, 21)},
    }


def measure(args, spec):
    mark, deess, inp, outp, tag, level = spec
    amp, detector = args.pair.split("/")
    name = f"{args.kind}-{amp}-{detector}-{args.mode}-c{mark:02d}-ds{deess}-in{inp:03d}-out{outp:03d}"
    if level is not None:
        name += f"-{level:+}dBu"
    params = ["--opamp", amp, "--detector-opamp", detector, "--mode", args.mode,
              "--ceiling", str(mark // 2), "--deess", str(deess), "--input", str(inp / 100),
              "--output", str(outp / 100), "--source", "150", "--load", str(args.load)]
    if args.kind == "ac":
        params += ["--ac"]
    else:
        params += ["--transient", "--seconds", str(SECONDS), "--max-step", "2e-6",
                   "--dbu", str(level), "--hz", str(TONE_HZ)]
    status, data = run_fixture(args, name, params, ac=args.kind == "ac")
    metrics = {}
    if data is not None:
        metrics = ac_summary(data) if args.kind == "ac" else tonal_summary(data)
    return {"id": name, "pair": args.pair, "mode": args.mode, "ceiling_mark": mark,
            "deess": deess, "input_pct": inp, "output_pct": outp, "region": tag,
            "input_dbu": level, "source_ohm": 150, "load_ohm": args.load, "release": "00",
            "solver": status, **metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("ac", "tone"))
    parser.add_argument("--pair", choices=PAIRS, default=PAIRS[0])
    parser.add_argument("--mode", choices=("C", "L", "OFF"), default="C")
    parser.add_argument("--ceilings", type=int, choices=range(0, 21, 2), nargs="+", default=range(0, 21, 2))
    parser.add_argument("--load", type=int, choices=(600, 2000, 10000, 20000), default=10000)
    parser.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--timeout", type=int, default=75)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--ngspice", default="ngspice")
    args = parser.parse_args()
    archive_models(args)
    selected = list(cases(args.kind, sorted(set(args.ceilings)), args.mode))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda spec: measure(args, spec), selected))
    writer(args.output / "summary.csv", rows)
    total = sum(row["solver"] == "complete" for row in rows)
    print(f"{args.pair} {args.mode} {args.kind}: {total}/{len(rows)} cases measured")
    if total != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
