"""Compare a legacy detector ratio to the schematic-supported 1:1:1 AP2623 candidate."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
from types import SimpleNamespace

from control_grid import measure
from fixture import DETECTOR_TURNS
from verify import MODES, PAIRS, archive_models, envelope_case, writer


LEVELS = (-40, -24, -18, -12, -6, 0, 4, 8, 12, 18)


def evaluate(args, trial):
    kind, mode, stimulus = trial
    local = SimpleNamespace(**vars(args), kind=kind, mode=mode)
    if kind == "tone":
        return measure(local, (16, 0, 90, 75, "reference", stimulus))
    frequency, step = stimulus
    return envelope_case(local, (local.pair, mode, frequency, "00", step))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", choices=PAIRS, required=True)
    parser.add_argument("--detector-transformer", choices=tuple(DETECTOR_TURNS), required=True)
    parser.add_argument("--output", type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    args.load = 10000
    archive_models(args)
    trials = list(product(("tone",), MODES, LEVELS))
    trials += list(product(("attack",), MODES, product((1000, 10000), (2.5e-7, 1.25e-7))))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda trial: evaluate(args, trial), trials))
    for row in rows:
        row["detector_transformer"] = args.detector_transformer
    writer(args.output / "summary.csv", rows)
    waveforms = sum(row["solver"] in ("complete", "insufficient_gr") for row in rows)
    print(f"{args.pair} {args.detector_transformer}: {waveforms}/{len(rows)} valid waveforms")
    if waveforms != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
