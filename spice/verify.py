"""Archive loaded AC and burst timing checks of the connected 525C fixture."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
from itertools import product
import math
from pathlib import Path
import subprocess

import numpy as np


ROOT = Path(__file__).resolve().parent
MODES = ("C", "L")
PAIRS = ("2520/2520", "990/2520")
RELEASE = ("00", "10", "01", "11")
BURST_DBU = 4
QUIET_DBU = -30
AC_PROBES_HZ = (20, 30, 100, 1000, 5000, 10000, 20000, 40000)


def writer(path, rows):
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        out = csv.DictWriter(stream, columns)
        out.writeheader()
        out.writerows(rows)


def run_fixture(args, name, params, *, ac=False, coupling=None):
    dest = args.output / name
    dest.mkdir(parents=True, exist_ok=True)
    raw = dest / ("ac.dat" if ac else "burst.dat")
    local_raw = raw.relative_to(args.output)
    flag = "--ac-trace" if ac else "--trace"
    variant = getattr(args, "detector_transformer", "legacy")
    deck = subprocess.check_output(
        ["python3", "fixture.py", *params, "--detector-transformer", variant, flag, str(local_raw)],
        cwd=ROOT, text=True,
    )
    if coupling is not None:
        alternate = dest / "magnetics.lib"
        source = (args.output / "magnetics.lib").read_text()
        marker = "Kcore Lpri Ls1 Ls2 .9997\n.ends T525C_OUT"
        if source.count(marker) != 1:
            raise ValueError("Output transformer coupling marker changed")
        alternate.write_text(source.replace(marker, f"Kcore Lpri Ls1 Ls2 {coupling}\n.ends T525C_OUT"))
        deck = deck.replace(".include magnetics.lib", f".include {alternate.relative_to(args.output)}")
    return solve_deck(args, dest, raw, deck, 5 if ac else 9)


def solve_deck(args, dest, raw, deck, columns, *, min_rows=2):
    deck_path = dest / "fixture.cir"
    log_path = dest / "ngspice.log"
    deck_path.write_text(deck)
    raw.unlink(missing_ok=True)
    with log_path.open("w") as log:
        try:
            result = subprocess.run([args.ngspice, "-b", str(deck_path.relative_to(args.output))], cwd=args.output,
                                    stdout=log, stderr=subprocess.STDOUT,
                                    check=False, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            return "timeout", None
    if result.returncode or not raw.exists() or raw.stat().st_size == 0:
        return "solver_error", None
    try:
        data = np.loadtxt(raw, skiprows=1, ndmin=2)
    except ValueError:
        return "invalid_waveform", None
    if len(data) < min_rows or data.shape[1] != columns or not np.isfinite(data).all():
        return "invalid_waveform", None
    return "complete", data


def ac_summary(data):
    f, gain, phase, detector, detector_phase = data.T
    if f[0] > 5.001 or f[-1] < 199000 or np.any(np.diff(f) <= 0):
        return {"solver": "incomplete_sweep"}
    phase = np.unwrap(phase)
    detector_phase = np.unwrap(detector_phase)
    delay = -np.gradient(phase, f) / (2 * np.pi)
    ref_gain = np.interp(1000, f, gain)
    def bounds(lo, hi):
        interior = (f > lo) & (f < hi)
        band = np.r_[gain[interior], np.interp([lo, hi], f, gain)] - ref_gain
        return float(band.min()), float(band.max())

    wide_min, wide_max = bounds(20, 40000)
    legacy_min, legacy_max = bounds(30, 20000)
    return {
        "gain_1k_db": ref_gain,
        "min_20_40k_relative_db": wide_min,
        "max_20_40k_relative_db": wide_max,
        "within_nominal_half_db": wide_min >= -.5 and wide_max <= .5,
        "min_30_20k_relative_db": legacy_min,
        "max_30_20k_relative_db": legacy_max,
        "within_legacy_half_db": legacy_min >= -.5 and legacy_max <= .5,
        **{f"gain_db_{hz}hz": np.interp(hz, f, gain) for hz in AC_PROBES_HZ},
        **{f"phase_deg_{hz}hz": math.degrees(np.interp(hz, f, phase)) for hz in AC_PROBES_HZ},
        **{f"group_delay_us_{hz}hz": np.interp(hz, f, delay) * 1e6 for hz in AC_PROBES_HZ},
        **{f"detector_a3_gain_db_{hz}hz": np.interp(hz, f, detector) for hz in AC_PROBES_HZ},
        **{f"detector_a3_phase_deg_{hz}hz": math.degrees(np.interp(hz, f, detector_phase))
           for hz in AC_PROBES_HZ},
    }


def ac_case(args, item):
    pair, mode, source, load, ds, coupling = item
    amp, detector = pair.split("/")
    # Ceiling index 8 selects the panel mark 16.
    name = f"ac-{amp}-{detector}-{mode}-{source}-{load}-ds{ds}"
    if coupling is not None:
        name += f"-k{coupling}"
    status, data = run_fixture(args, name, [
        "--opamp", amp, "--detector-opamp", detector, "--mode", mode, "--ac",
        "--input", ".9", "--ceiling", "8", "--source", str(source), "--load", str(load),
        "--deess", str(ds),
    ], ac=True, coupling=coupling)
    return {
        "id": name, "pair": pair, "mode": mode, "source_ohm": source, "load_ohm": load,
        "deess": ds, "output_coupling_override": coupling, "solver": status, **(ac_summary(data) if data is not None else {}),
    }


def cycle_envelope(data, carrier, end):
    # Use only whole carrier cycles at aligned peaks. A1+ observes the actual
    # audio voltage into the gain stage after the fixture attenuator.
    period = 1 / carrier
    count = round(end * carrier)
    t = np.arange(count * 128) * (period / 128)
    tone = np.exp(-2j*np.pi*np.arange(128)/128)
    def magnitude(column):
        waveform = np.interp(t, data[:, 0], data[:, column]).reshape(count, 128)
        return np.abs(waveform @ tone) / 64
    gain = 20*np.log10(np.maximum(magnitude(3), 1e-15) / np.maximum(magnitude(8), 1e-15))
    gate = np.interp(t, data[:, 0], data[:, 6]).reshape(count, 128)
    return (np.arange(count) + .5) * period, gain, gate.mean(axis=1)


def crossings(time, progress, targets, onset, scale, *, hold=1):
    result = []
    for target in targets:
        mask = progress >= target
        if hold > 1:
            mask = np.convolve(mask.astype(int), np.ones(hold, dtype=int), mode="valid") == hold
        hits = np.flatnonzero(mask)
        if hits.size == 0:
            result.append("")
            continue
        first = hits[0]
        if first:
            jump = progress[first] - progress[first-1]
            fraction = min(1, max(0, (target-progress[first-1])/jump)) if jump else 1
            t = time[first-1] + fraction*(time[first]-time[first-1])
        else:
            t = time[0]
        result.append((t-onset)*scale)
    return result


def med(values, low, high, time):
    selected = values[(time >= low) & (time < high)]
    return float(np.median(selected)) if len(selected) else math.nan


def envelope_summary(data, carrier, start, stop, end, kind):
    if data[-1, 0] < end * (1 - 1e-7):
        return {"solver": "incomplete_burst"}
    times, gain, gate = cycle_envelope(data, carrier, end)
    pre = med(gain, start-.004, start-.001, times)
    on = med(gain, stop-.004, stop-.001, times)
    if not math.isfinite(pre+on) or pre-on < 1:
        return {"solver": "insufficient_gr"}
    result = {"pre_a1_gain_db": pre, "burst_a1_gain_db": on, "gr_db": pre-on,
              "gain_envelope_resolution_us": 1e6/carrier}
    if kind == "attack":
        # The gate can be sampled at the original integration timesteps. Its
        # first crossings include ripple and may overshoot the settled gate.
        gate_start = med(gate, start-.004, start-.001, times)
        gate_end = med(gate, stop-.004, stop-.001, times)
        t, v = data[:, 0], data[:, 6]
        selected = (t >= start) & (t < stop)
        targets = (.1, .5, .632, .9)
        gate_swing = gate_start - gate_end
        attack = [""] * len(targets)
        if abs(gate_swing) > 1e-9:
            progress = (gate_start-v[selected]) / gate_swing
            attack = crossings(t[selected], progress, targets, start, 1e6)
        gain_sel = (times >= start) & (times < stop)
        gain_attack = crossings(times[gain_sel], (pre-gain[gain_sel])/(pre-on), targets, start, 1e6)
        for label, g_delay, a_delay in zip(("10", "50", "63_2", "90"), attack, gain_attack):
            result[f"gate_t{label}_us"] = g_delay
            result[f"cycle_gain_t{label}_us"] = a_delay
        if isinstance(attack[0], float) and isinstance(attack[-1], float):
            result["gate_10_90_us"] = attack[-1]-attack[0]
        result["gate_overshoot_v"] = max(0, gate_end-np.min(v[selected]))
    else:
        selected = times >= stop
        remaining = gain[selected]-on
        # Require consecutive cycles so a transient at the level switch cannot
        # report a false recovery crossing.
        rec = crossings(times[selected], remaining, ((pre-on)*.5, pre-on-1), stop, 1000, hold=5)
        result["release_to_half_ms"], result["release_to_1db_ms"] = rec
        for ms in (50, 100, 200, 500, 1000, 2000):
            if stop + ms/1000 <= times[-1]:
                result[f"remaining_gr_at_{ms}ms_db"] = pre-np.interp(stop+ms/1000, times, gain)
        result["remaining_gr_at_trace_end_db"] = pre-gain[-1]
        result["right_censored_1db"] = rec[1] == ""
    return result


def envelope_case(args, item):
    pair, mode, carrier, release, max_step = item
    amp, detector = pair.split("/")
    start, stop, end = (.01, .03, .032) if args.kind == "attack" else (.02, .08, 2.58)
    name = f"{args.kind}-{amp}-{detector}-{mode}-{carrier}-{release}-{max_step:.3g}"
    status, data = run_fixture(args, name, [
        "--opamp", amp, "--detector-opamp", detector, "--mode", mode,
        "--input", ".9", "--ceiling", "8", "--source", "150", "--load", "10000",
        "--release", release, "--hz", str(carrier), "--transient", "--dbu", str(QUIET_DBU),
        "--burst-dbu", str(BURST_DBU), "--burst-start", str(start), "--burst-stop", str(stop),
        "--seconds", str(end), "--max-step", str(max_step),
    ])
    metrics = envelope_summary(data, carrier, start, stop, end, args.kind) if data is not None else {}
    return {"id": name, "pair": pair, "mode": mode, "carrier_hz": carrier,
            "release": release, "max_step_s": max_step, "solver": status, **metrics}


def archive_models(args):
    args.output.mkdir(parents=True, exist_ok=True)
    libs = sorted(ROOT.glob("*.lib"))
    for lib in libs:
        (args.output/lib.name).write_bytes(lib.read_bytes())
    (args.output/"model-hashes.txt").write_text("\n".join(
        f"{hashlib.sha256(lib.read_bytes()).hexdigest()}  {lib.name}" for lib in libs)+"\n")
    (args.output/"ngspice-version.txt").write_text(subprocess.check_output([args.ngspice, "-v"], text=True))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("kind", choices=("ac", "attack", "release", "magnetics"))
    cli.add_argument("--pair", choices=PAIRS)
    cli.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    cli.add_argument("--ngspice", default="ngspice")
    cli.add_argument("--workers", type=int, default=4)
    cli.add_argument("--timeout", type=int, default=75)
    args = cli.parse_args()
    archive_models(args)
    pairs = (args.pair,) if args.pair else PAIRS
    if args.kind == "ac":
        cases = product(pairs, (*MODES, "OFF"), (50, 150, 600),
                        (600, 2000, 10000, 20000), (0, 1), (None,))
        worker = ac_case
    elif args.kind == "magnetics":
        cases = product(pairs, ("C", "OFF"), (150,), (600, 10000),
                        (0,), (None, .99997, .99999))
        worker = ac_case
    else:
        cases = (product(pairs, MODES, (1000,10000), ("00",), (2.5e-7,1.25e-7))
                 if args.kind == "attack" else product(pairs, MODES, (1000,), RELEASE, (1e-5,)))
        worker = envelope_case
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda item: worker(args, item), cases))
    writer(args.output/"summary.csv", rows)
    passed = sum(row["solver"]=="complete" for row in rows)
    print(f"{args.kind}: {passed}/{len(rows)} waveform or sweep rows measured")
    if passed != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
