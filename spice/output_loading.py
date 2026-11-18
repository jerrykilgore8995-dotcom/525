"""Bound AP2623 leakage using a catalog response limit and test 525C output loading."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from control_grid import SECONDS, tonal_summary
from verify import PAIRS, ROOT, ac_summary, archive_models, solve_deck, writer


MIN_LOAD = 300
LOADS = (300, 600, 2000, 10000, 20000)
DCR = {"Rpri": 15.7, "Rs1": 31.5, "Rs2": 31.5}
LIMIT_DB = -.5


def out_windings(source, coupling):
    """Change only T1. Preserve the detector transformer and all parasitics."""
    head, tail = source.split(".ends T525C_OUT", 1)
    lines = []
    for line in head.splitlines():
        fields = line.split()
        if fields and fields[0] in DCR:
            line = " ".join([*fields[:-1], str(DCR[fields[0]])])
        if fields and fields[0] == "Kcore":
            line = " ".join([*fields[:-1], f"{coupling:.12f}"])
        lines.append(line)
    return "\n".join(lines) + "\n.ends T525C_OUT" + tail


def transformer_case(args, name, load, library):
    dest = args.output / name
    dest.mkdir(exist_ok=True)
    raw = dest / "bench.dat"
    deck = f"""AP2623 series-secondary screen, ideal voltage drive
.include {library}
VIN pri 0 DC 0 AC 1
XT1 pri 0 out tap 0 T525C_OUT
RL out 0 {load}
.control
ac dec 160 5 200000
set wr_singlescale
set wr_vecnames
wrdata {raw.relative_to(args.output)} vdb(out) vp(out)
quit
.endc
.end
"""
    status, data = solve_deck(args, dest, raw, deck, 3)
    if data is None or data[-1, 0] < 199000 or np.any(np.diff(data[:, 0]) <= 0):
        raise RuntimeError(f"{name}: invalid transformer AC sweep ({status})")
    f, gain, phase = data.T
    ref = np.interp(1000, f, gain)
    band = np.r_[gain[(f > 30) & (f < 20000)], np.interp([30, 20000], f, gain)] - ref
    return {"id": name, "load_ohm": load, "gain_1k_db": ref,
            "min_30_20k_relative_db": float(band.min()),
            "max_30_20k_relative_db": float(band.max()),
            "relative_db_20khz": float(np.interp(20000, f, gain) - ref),
            "relative_db_40khz": float(np.interp(40000, f, gain) - ref)}


def bound(args):
    source = (args.output / "magnetics.lib").read_text()
    trials = []

    def probe(k):
        name = f"bound-{len(trials):02d}"
        dest = args.output / name
        dest.mkdir(exist_ok=True)
        lib = dest / "magnetics.lib"
        lib.write_text(out_windings(source, k))
        summary = transformer_case(args, name, MIN_LOAD, lib.relative_to(args.output))
        trials.append({"coupling": k, **summary})
        return summary["relative_db_20khz"] >= LIMIT_DB

    low, high = .9997, .999999
    if probe(low) or not probe(high):
        raise ValueError("The coupling bracket does not straddle the catalog-band limit")
    for _ in range(19):
        mid = (low + high) / 2
        if probe(mid):
            high = mid
        else:
            low = mid
    writer(args.output / "coupling-bound.csv", trials)
    candidate = args.output / "magnetics-litz-bound.lib"
    candidate.write_text(out_windings(source, high))
    return high, candidate.name


def loaded_case(args, case):
    pair, mode, load, library, level = case
    amp, detector = pair.split("/")
    is_ac = level is None
    name = f"{amp}-{detector}-{mode}-{load}-{library.removesuffix('.lib')}"
    if not is_ac:
        name += f"-{level:+}dBu"
    dest = args.output / name
    dest.mkdir(exist_ok=True)
    raw = dest / ("ac.dat" if is_ac else "tone.dat")
    raw_ref = str(raw.relative_to(args.output))
    params = ["--opamp", amp, "--detector-opamp", detector, "--mode", mode,
              "--input", ".9", "--ceiling", "8", "--source", "150", "--load", str(load)]
    if is_ac:
        params += ["--ac", "--ac-trace", raw_ref]
    else:
        params += ["--transient", "--seconds", str(SECONDS), "--max-step", "2e-6",
                   "--dbu", str(level), "--trace", raw_ref]
    deck = subprocess.check_output(["python3", "fixture.py", *params], cwd=ROOT, text=True)
    deck = deck.replace(".include magnetics.lib", f".include {library}")
    status, data = solve_deck(args, dest, raw, deck, 5 if is_ac else 9)
    summary = {}
    if data is not None:
        summary = ac_summary(data) if is_ac else tonal_summary(data)
    return {"id": name, "pair": pair, "mode": mode, "load_ohm": load, "library": library,
            "input_dbu": level, "solver": status, **summary}


def output_impedance(rows):
    groups = {(r["pair"], r["mode"], r["library"]) for r in rows}
    for pair, mode, library in sorted(groups):
        selected = {r["load_ohm"]: r for r in rows if (r["pair"], r["mode"], r["library"]) ==
                    (pair, mode, library) and r["solver"] == "complete"}
        if not {600, 10000} <= selected.keys():
            continue
        row = {"pair": pair, "mode": mode, "library": library}
        for hz in (30, 1000, 20000, 40000):
            a, b = 600, 10000
            delta_db = selected[a][f"gain_db_{hz}hz"] - selected[b][f"gain_db_{hz}hz"]
            delta_phase = selected[a][f"phase_deg_{hz}hz"] - selected[b][f"phase_deg_{hz}hz"]
            ratio = 10**(delta_db / 20) * np.exp(1j * np.radians(delta_phase))
            z = a * b * (1 - ratio) / (b * ratio - a)
            row[f"z_real_ohm_{hz}hz"] = z.real
            row[f"z_imag_ohm_{hz}hz"] = z.imag
        yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--driven", action="store_true", help="Also measure 1 kHz driven response")
    parser.add_argument("--timeout", type=int, default=40)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.output = args.output.resolve()
    archive_models(args)
    k, candidate = bound(args)
    standalone = [transformer_case(args, f"bench-{load}-{lib.removesuffix('.lib')}", load, lib)
                  for load, lib in product(LOADS, ("magnetics.lib", candidate))]
    writer(args.output / "transformer.csv", standalone)
    libraries = ("magnetics.lib", candidate)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda case: loaded_case(args, case),
                             product(PAIRS, ("C", "L", "OFF"), LOADS, libraries, (None,))))
        driven = []
        if args.driven:
            active = product(PAIRS, ("C", "L"), (600, 10000), libraries, (-18, 4))
            off = product(PAIRS, ("OFF",), (600, 10000), libraries, (4, 18, 24))
            driven = list(pool.map(lambda case: loaded_case(args, case), [*active, *off]))
            writer(args.output / "driven.csv", driven)
    writer(args.output / "summary.csv", rows)
    writer(args.output / "output-impedance.csv", list(output_impedance(rows)))
    success = sum(row["solver"] == "complete" for row in rows)
    print(f"Minimum coupling meeting the 20 kHz anchor at {MIN_LOAD} Ω: {k:.10f}")
    print(f"{success}/{len(rows)} connected 525C load sweeps completed")
    print(f"{sum(r['solver'] == 'complete' for r in driven)}/{len(driven)} driven sweeps completed")
    if any(row["solver"] != "complete" for row in [*rows, *driven]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
