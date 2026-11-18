"""Run versioned shards of the vintage 525C control matrix."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import subprocess

from control_grid import tonal_summary
from verify import PAIRS, RELEASE, ROOT, archive_models, run_fixture, ac_summary, writer


MODES = (("C", 200), ("C", 68), ("C", 30), ("C", 20), ("L", 200), ("OFF", 200))
POTS = range(101)


@dataclass(frozen=True)
class Control:
    pair: str
    mode: str
    r44: int
    release: str
    deess: int
    ceiling: int
    input_pct: int
    output_pct: int


def axes(pots):
    return PAIRS, MODES, RELEASE, (0, 1), range(11), pots, pots


def control_at(index, grid):
    values = []
    for axis in reversed(grid):
        index, remainder = divmod(index, len(axis))
        values.append(axis[remainder])
    pair, (mode, r44), release, deess, ceiling, inp, out = reversed(values)
    return Control(pair, mode, r44, release, deess, ceiling, inp, out)


def signature(args, stimulus):
    paths = sorted(ROOT.glob("*.lib")) + [ROOT / name for name in
                                            ("fixture.py", "control_grid.py", "verify.py", Path(__file__).name)]
    return {
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "ngspice": subprocess.check_output([args.ngspice, "-v"], text=True),
        "source": args.source, "load": args.load, "stimulus": stimulus,
    }


def run_case(args, job, stimulus):
    index, control = job
    kind, hz, level, length, step = stimulus
    amp, detector = control.pair.split("/")
    case = f"{index:09d}"
    summary = args.output / case / "result.json"
    if summary.is_file():
        previous = json.loads(summary.read_text())
        trace = summary.parent / ("ac.dat" if kind == "ac" else "burst.dat")
        if previous["solver"] == "complete" and trace.is_file() and trace.stat().st_size:
            if kind == "ac" or previous["settled_half_window_0_1db"]:
                return previous

    options = ["--opamp", amp, "--detector-opamp", detector, "--mode", control.mode,
               "--comp-r44", str(control.r44), "--input", str(control.input_pct/100),
               "--output", str(control.output_pct/100), "--ceiling", str(control.ceiling),
               "--deess", str(control.deess), "--release", control.release, "--source", str(args.source),
               "--load", str(args.load)]
    ac = kind == "ac"
    options += ["--ac"] if ac else ["--transient", "--hz", str(hz), "--dbu", str(level),
                                      "--seconds", str(length), "--max-step", str(step)]
    status, data = run_fixture(args, case, options, ac=ac)
    row = {"id": index, **asdict(control), "hz": hz, "input_dbu": level,
           "source_ohm": args.source, "load_ohm": args.load, "solver": status}
    if data is not None:
        row.update(ac_summary(data) if ac else tonal_summary(data, seconds=length, tone_hz=hz))
    temporary = summary.with_suffix(".tmp")
    temporary.write_text(json.dumps(row, allow_nan=False) + "\n")
    temporary.replace(summary)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("ac", "tone"))
    parser.add_argument("--preset", choices=("full", "anchor"), default="full",
                        help="Use the 1%% pot grid or fixed IN 50%% and OUT 50%%")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--count", action="store_true")
    parser.add_argument("--output", type=lambda p: Path(p).resolve())
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--hz", type=int, default=1000)
    parser.add_argument("--dbu", type=float, default=-18)
    parser.add_argument("--seconds", type=float, default=.32)
    parser.add_argument("--source", type=float, default=150)
    parser.add_argument("--load", type=float, default=10000)
    args = parser.parse_args()
    grid = axes(POTS if args.preset == "full" else (50,))
    total = math.prod(map(len, grid))
    if args.count:
        print(total)
        return
    stop = args.stop if args.stop is not None else total
    if not args.output or not 0 <= args.start < stop <= total:
        parser.error("Provide an output directory and a nonempty valid range")
    if args.hz <= 0 or args.seconds * args.hz < 13:
        parser.error("Tone must have at least 13 cycles")
    if args.source <= 0 or args.load <= 0 or args.workers <= 0 or args.timeout <= 0:
        parser.error("Fixtures and runtime limits must be positive")
    stimulus = (args.family, None, None, None, None) if args.family == "ac" else (
        args.family, args.hz, args.dbu, args.seconds, min(2e-6, 1/(400*args.hz)))
    args.detector_transformer = "ap2623"
    manifest = {**signature(args, stimulus), "grid": args.preset,
                "detector_transformer": args.detector_transformer}
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = args.output / "matrix.json"
    text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    if metadata.exists() and metadata.read_text() != text:
        parser.error("Existing results use a different grid, circuit, simulator or stimulus")
    metadata.write_text(text)
    archive_models(args)
    jobs = ((i, control_at(i, grid)) for i in range(args.start, stop))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda job: run_case(args, job, stimulus), jobs))
    writer(args.output / f"summary-{args.start}-{stop}.csv", rows)
    valid = sum(r["solver"] == "complete" for r in rows)
    if args.family == "tone":
        settled = sum(r.get("settled_half_window_0_1db", False) for r in rows)
        print(f"{settled}/{valid} valid tone rows within late-window drift limit")
    print(f"{valid}/{len(rows)} valid {args.family} rows, IDs {args.start} through {stop-1} of {total}")
    if valid != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
