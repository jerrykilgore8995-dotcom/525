"""Measure coherent two-tone products of the connected vintage 525C circuit."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path
import subprocess

import numpy as np

from verify import PAIRS, ROOT, archive_models, solve_deck, writer


MODES = (("C", 200), ("C", 68), ("C", 30), ("C", 20), ("L", 200), ("OFF", 200))
STIMULI = {"smpte": (60, 7000, 4), "ccif": (19000, 20000, 1)}
END = .4
WINDOW = .1
RATE = 480000
LEVELS = (-18, 4)


def db(x):
    return 20 * np.log10(max(abs(x), 1e-15))


def measure(args, case):
    (mode, resistor), stimulus, dbu = case
    f1, f2, ratio = STIMULI[stimulus]
    p2 = .775*np.sqrt(2)*10**(dbu/20)/np.hypot(ratio, 1)
    amp, detector = args.pair.split("/")
    name = f"{mode}-{resistor}-{stimulus}-{dbu:+}dBu"
    dest = args.output / name
    dest.mkdir(exist_ok=True)
    raw = dest / "imd.dat"
    step = 1/(400*f2)
    cmd = ["python3", "fixture.py", "--opamp", amp, "--detector-opamp", detector,
           "--detector-transformer", "ap2623", "--mode", mode, "--comp-r44", str(resistor),
           "--input", ".5", "--output", ".75", "--ceiling", "8", "--load", str(args.load),
           "--seconds", str(END), "--max-step", str(step), "--transient", "--trace",
           str(raw.relative_to(args.output))]
    original = subprocess.check_output(cmd, cwd=ROOT, text=True)
    lines = []
    for line in original.splitlines():
        if line.startswith("VIN "):
            line = (f"Vtone1 mix 0 SIN(0 {ratio*p2:.15g} {f1})\n"
                    f"Vtone2 src mix SIN(0 {p2:.15g} {f2})")
        if line.startswith("tran "):
            lines.append("save v(src) v(oh)")
        if line.startswith("fourier "):
            continue
        if line.startswith("wrdata "):
            lines.append("set numdgt=16")
            line = f"wrdata {raw.relative_to(args.output)} v(src) v(oh)"
        lines.append(line)
    status, data = solve_deck(args, dest, raw, "\n".join(lines) + "\n", 3)
    row = {"id": name, "pair": args.pair, "mode": mode, "r44_ohm": resistor,
           "stimulus": stimulus, "input_dbu": dbu, "load_ohm": args.load, "solver": status}
    if data is None:
        return row
    if data[-1,0] < END - 1e-8 or np.any(np.diff(data[:,0]) <= 0):
        return {**row, "solver": "incomplete_trace"}
    n = round(RATE*WINDOW)
    wave = np.interp(END-WINDOW+np.arange(n)/RATE, data[:,0], data[:,2])
    spectrum = np.fft.rfft(wave)*2/n
    fundamental = abs(spectrum[round(f2*WINDOW)])
    row["f1_out_dbu"] = db(spectrum[round(f1*WINDOW)]/(.775*np.sqrt(2)))
    row["f2_out_dbu"] = db(fundamental/(.775*np.sqrt(2)))
    # Keep the individual products so the host can compare the same convention.
    offsets = (-3, -2, -1, 1, 2, 3)
    products = ([f2+m*f1 for m in offsets] if stimulus == "smpte" else
                [f2-f1, 2*f1-f2, 2*f2-f1, 3*f1-2*f2, 3*f2-2*f1])
    amplitudes = [abs(spectrum[round(hz*WINDOW)])/max(fundamental,1e-15) for hz in products]
    row["products_rss_pct_of_f2"] = 100*np.linalg.norm(amplitudes)
    row.update({f"product_{i}_hz": hz for i,hz in enumerate(products,1)})
    row.update({f"product_{i}_dbc": db(a) for i,a in enumerate(amplitudes,1)})
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pair", choices=PAIRS, required=True)
    p.add_argument("--output", type=lambda path: Path(path).resolve(), required=True)
    p.add_argument("--ngspice", default="ngspice")
    p.add_argument("--load", type=int, choices=(600,10000), default=10000)
    p.add_argument("--stimuli", choices=tuple(STIMULI), nargs="+", default=tuple(STIMULI))
    p.add_argument("--modes", choices=("C","L","OFF"), nargs="+", default=("C","L","OFF"))
    p.add_argument("--timeout", type=int, default=200)
    p.add_argument("--workers", type=int, default=2)
    args=p.parse_args()
    archive_models(args)
    cases = list(product((mode for mode in MODES if mode[0] in args.modes), args.stimuli, LEVELS))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows=list(pool.map(lambda case: measure(args, case), cases))
    writer(args.output/"summary.csv", rows)
    done=sum(r["solver"]=="complete" for r in rows)
    print(f"{done}/{len(rows)} two-tone traces measured")
    if done!=len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
