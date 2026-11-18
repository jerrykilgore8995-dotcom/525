"""Measure one row of the independent 525 IN × OUT harmonic grid."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from reference_matrix import MODES, axes, control_at, run_case, signature
from verify import PAIRS, RELEASE, archive_models, writer

FREQUENCIES = (100, 1000, 5000, 10000)
LEVELS = (-30, -18, 4, 10, 18, 24)
GRID = axes(range(101))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=int, choices=range(101), required=True)
    parser.add_argument("--outs", type=int, nargs="+", default=list(range(0, 101, 10)))
    parser.add_argument("--hz", type=int, choices=FREQUENCIES, required=True)
    parser.add_argument("--dbu", type=float, required=True)
    parser.add_argument("--pair", choices=PAIRS, default=PAIRS[0])
    parser.add_argument("--slot", type=int, choices=range(6), default=0)
    parser.add_argument("--ceiling", type=int, choices=range(11), default=8)
    parser.add_argument("--release", choices=RELEASE, default="00")
    parser.add_argument("--ds", type=int, choices=(0, 1), default=0)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=lambda x: Path(x).resolve(), required=True)
    args = parser.parse_args()
    if args.workers < 1 or any(not 0 <= out <= 100 for out in args.outs):
        parser.error("Use positive workers and OUT positions from 0 to 100")
    args.source = 150
    args.load = 10000
    args.detector_transformer = "ap2623"
    seconds = max(.8 if args.hz == 100 else .16, .04 + (2.5 if args.release in ("01", "11") else 0))
    stimulus = ("tone", args.hz, args.dbu, seconds, min(5e-6, 1 / (400 * args.hz)))
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {**signature(args, stimulus), "detector_transformer": args.detector_transformer}
    metadata = args.output / "matrix.json"
    serialized = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if metadata.exists() and metadata.read_text() != serialized:
        parser.error("The output directory contains a different circuit or stimulus")
    metadata.write_text(serialized)
    archive_models(args)

    def measure(output):
        index = args.input
        for digit, radix in ((output, 101), (PAIRS.index(args.pair), len(PAIRS)),
                             (args.slot, len(MODES)), (RELEASE.index(args.release), len(RELEASE)),
                             (args.ds, 2), (args.ceiling, 11)):
            index = index * radix + digit
        row = run_case(args, (index, control_at(index, GRID)), stimulus)
        row["max_step_s"] = stimulus[-1]
        row["tone_seconds"] = seconds
        print(f"IN {args.input}% OUT {output}%: {row['solver']}, settled {row.get('settled_half_window_0_1db', False)}",
              flush=True)
        return row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(measure, sorted(set(args.outs))))
    writer(args.output / "harmonic-pots.csv", rows)
    settled = sum(row.get("settled_half_window_0_1db", False) for row in rows)
    print(f"{settled}/{len(rows)} settled; inspect individual rows before fitting")
    if settled != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
