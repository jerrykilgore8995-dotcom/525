"""Run a bounded 1 kHz validation matrix and publish raw operating evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from itertools import product
import math
import shutil
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
HZ = 1000
SECONDS = .05
WINDOW_CYCLES = 12
SAMPLES_PER_CYCLE = 256
SAMPLES = WINDOW_CYCLES * SAMPLES_PER_CYCLE
HARMONICS = [(tuple(math.cos(math.tau*k*n/SAMPLES_PER_CYCLE) for n in range(SAMPLES_PER_CYCLE)),
              tuple(math.sin(math.tau*k*n/SAMPLES_PER_CYCLE) for n in range(SAMPLES_PER_CYCLE)))
             for k in range(1, 21)]
STAGES = ("out", "a1", "a2", "a3")
HARMONIC_FIELDS = [f"h{k}_dbc" for k in range(2, 21)]
METRIC_FIELDS = ["out_dbu", "gain_db", "stage_a1_gain_db", "stage_a1_gr_db", "thd_pct",
                 "thdn_pct", "phase_relative_to_source_deg", "gate_min_v", "detector_mean_v",
                 "first_to_last_a1_gain_db"] + [f"{s}_peak_v" for s in STAGES] + HARMONIC_FIELDS
FIELDS = ("opamp", "detector_opamp", "mode", "ceiling_index", "input_dbu", "load_ohm",
          "max_step_s", "solver") + tuple(METRIC_FIELDS)


def db(value):
    return 20 * math.log10(max(1e-15, value))


def read_samples(path):
    # ngspice uses adaptive timesteps. Resample the last integral-cycle window
    # with explicit interpolation, keeping the original waveform in the trace.
    end = SECONDS
    step = 1 / (HZ * SAMPLES_PER_CYCLE)
    start = end - SAMPLES * step
    previous = None
    columns = [[] for _ in range(8)]
    n = 0
    with path.open() as stream:
        next(stream)
        for line in stream:
            row = tuple(map(float, line.split()))
            if not all(map(math.isfinite, row)) or len(row) != 9:
                raise ValueError("Invalid waveform row")
            while previous is not None and n < SAMPLES and start + n*step <= row[0]:
                t = start + n*step
                width = row[0] - previous[0]
                fraction = (t - previous[0]) / width if width else 1
                for column, lo, hi in zip(columns, previous[1:], row[1:]):
                    column.append(lo + (hi-lo)*fraction)
                n += 1
            previous = row
    if n != SAMPLES:
        raise ValueError(f"Waveform ended after {n}/{SAMPLES} requested samples")
    return columns


def spectrum(samples):
    n = len(samples)
    cycles = n // SAMPLES_PER_CYCLE
    if cycles * SAMPLES_PER_CYCLE != n:
        raise ValueError("Expected a whole number of cycles")
    folded = [sum(samples[i::SAMPLES_PER_CYCLE]) for i in range(SAMPLES_PER_CYCLE)]
    return [complex(sum(v*c for v,c in zip(folded, cos)),
                    -sum(v*s for v,s in zip(folded, sin))) * (2/n)
            for cos, sin in HARMONICS]


def measurements(path):
    source, output, a1, a2, a3, gate, detector, a1_plus = read_samples(path)
    hs = spectrum(output)
    primary = abs(hs[0])
    src_h1 = spectrum(source)[0]
    stage1 = abs(spectrum(a1)[0]) / max(1e-15, abs(spectrum(a1_plus)[0]))
    mean = sum(output)/len(output)
    residual = sum((x - mean)**2 for x in output)/len(output) - .5*primary**2
    half = SAMPLES//2
    ratio_start = abs(spectrum(a1[:half])[0]) / max(1e-15, abs(spectrum(a1_plus[:half])[0]))
    ratio_end = abs(spectrum(a1[half:])[0]) / max(1e-15, abs(spectrum(a1_plus[half:])[0]))
    return {
        "out_dbu": db(primary / (.775*math.sqrt(2))),
        "gain_db": db(primary / abs(src_h1)),
        "stage_a1_gain_db": db(stage1),
        "thd_pct": 100 * math.sqrt(sum(abs(c)**2 for c in hs[1:])) / max(primary, 1e-15),
        "thdn_pct": 100 * math.sqrt(max(0, 2*residual)) / max(primary, 1e-15),
        "phase_relative_to_source_deg": math.degrees(math.atan2((hs[0]/src_h1).imag, (hs[0]/src_h1).real)),
        "gate_min_v": min(gate),
        "detector_mean_v": sum(detector)/len(detector),
        "first_to_last_a1_gain_db": db(ratio_end / max(ratio_start, 1e-15)),
        **{f"{name}_peak_v": max(map(abs, waveform)) for name,waveform in zip(STAGES, (output,a1,a2,a3))},
        **{field: db(abs(h)/max(primary, 1e-15)) for field,h in zip(HARMONIC_FIELDS, hs[1:])},
    }


def run_case(spec, args):
    amp, detector, mode, ceiling, level, load, max_step = spec
    row = dict(zip(FIELDS, (*spec, "solver_error")))
    name = f"{amp}-{detector}-{mode}-c{ceiling}-{level:+}dBu-{load}R-{max_step:g}"
    keep = args.keep_all or (mode == "C" and ceiling == 8 and level == 4 and load == 10000)
    with tempfile.TemporaryDirectory(prefix="vintage-525c-") as tmp:
        waveform = Path(tmp)/"wave.dat"
        deck_path = args.output/"decks"/(name+".cir")
        log_path = args.output/"logs"/(name+".log")
        output_path = args.output/"waveforms"/(name+".dat")
        parameters = ["--opamp", amp, "--detector-opamp", detector, "--mode", mode,
                      "--ceiling", str(ceiling), "--dbu", str(level), "--load", str(load),
                      "--max-step", str(max_step), "--seconds", str(SECONDS),
                      "--input", ".9", "--transient", "--trace", str(waveform)]
        run = subprocess.run(["python3", "fixture.py", *parameters], cwd=ROOT,
                             check=True, text=True, capture_output=True)
        deck_path.write_text(run.stdout.replace(str(waveform), "wave.dat"))
        transient = Path(tmp)/"circuit.cir"
        transient.write_text(run.stdout)
        with log_path.open("w") as stream:
            try:
                result = subprocess.run([args.ngspice, "-b", str(transient)], cwd=ROOT, stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=args.timeout)
                if result.returncode == 0 and waveform.exists():
                    try:
                        row.update(measurements(waveform))
                        row["solver"] = "complete"
                    except ValueError as error:
                        stream.write(f"\n{error}\n")
                    if keep:
                        shutil.copyfile(waveform, output_path)
            except subprocess.TimeoutExpired:
                row["solver"] = "timeout"
    return row


def cases():
    for amp,detector in (("2520","2520"), ("990","990"), ("990","2520")):
        for mode,ceiling,level in product(("C","L"), (0,8,10), (-40,-18,4,18)):
            yield amp,detector,mode,ceiling,level,10000,2e-6
        for mode in ("C","L","OFF"):
            for load in (600, 10000):
                for step in (2e-6,1e-6):
                    yield amp,detector,mode,8,4,load,step


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=lambda p: Path(p).resolve())
    parser.add_argument("--ngspice", default="ngspice")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--keep-all", action="store_true")
    parser.add_argument("--pair", choices=("2520/2520", "990/990", "990/2520"))
    parser.add_argument("--retry-from", type=Path, help="Re-evaluate incomplete cases from another metrics.csv")
    args = parser.parse_args()
    for sub in ("decks", "logs", "waveforms"):
        (args.output/sub).mkdir(parents=True, exist_ok=True)
    selected = list(dict.fromkeys(cases()))
    if args.pair:
        selected = [spec for spec in selected if "/".join(spec[:2]) == args.pair]
    previous_rows = []
    if args.retry_from:
        if args.output == args.retry_from.resolve().parent:
            parser.error("use a separate directory to retain the original runs")
        with args.retry_from.open() as stream:
            previous_rows = list(csv.DictReader(stream))
        incomplete = {tuple(r[k] for k in FIELDS[:7]) for r in previous_rows
                      if r["solver"] != "complete"}
        selected = [spec for spec in selected if tuple(map(str, spec)) in incomplete]
    if not selected:
        parser.error("no cases selected")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda spec: run_case(spec, args), selected))
    baseline = {(r["opamp"], r["detector_opamp"], r["mode"]): float(r["stage_a1_gain_db"])
                for r in previous_rows + rows if r["solver"] == "complete"
                and int(r["ceiling_index"]) == 0 and int(r["input_dbu"]) == -40}
    for row in rows:
        key = tuple(row[k] for k in ("opamp","detector_opamp","mode"))
        if row["solver"]=="complete" and key in baseline:
            row["stage_a1_gr_db"] = baseline[key] - row["stage_a1_gain_db"]
    with (args.output/"metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{sum(r['solver']=='complete' for r in rows)} / {len(rows)} complete waveform evaluations")


if __name__ == "__main__":
    main()
