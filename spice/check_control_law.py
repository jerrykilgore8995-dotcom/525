"""Compare the 525C circuit's loaded OUT/CEILING law to independent SPICE traces."""
import argparse
import csv
from pathlib import Path
import subprocess

import numpy as np

from control_grid import REFERENCE
from verify import AC_PROBES_HZ, writer


LADDER_OHM = (8200, 6800, 5100, 4300, 3300, 2700, 2200, 1600, 1300, 1100)


def small_signal_tap(mark, out_pct, hz):
    """A1 output to A2 non-inverting pin, treating both op-amp pins as ideal."""
    jw = 2j * np.pi * hz
    z_input = 1 / (1 / 62000 + jw * 47e-12)
    z_branch = z_input + 1 / (jw * 5e-6) + .02
    z_shunt = 1 / (1 / 3300 + 1 / z_branch)
    fraction = out_pct / 100
    r_upper = max(1e-6, 1000 * (1 - fraction))
    r_lower = max(1e-6, 1000 * fraction)
    r_th = r_upper * r_lower / (r_upper + r_lower)
    series = sum(LADDER_OHM[mark // 2:]) + .02
    return r_lower / (r_upper + r_lower) * z_shunt / (z_shunt + series + r_th) * z_input / z_branch


def digital_taps(executable, rows, frequencies, sample_rate):
    controls = {(int(r["ceiling_mark"]), int(r["output_pct"])) for r in rows}
    requests = list(sorted((mark, out, hz) for mark, out in controls for hz in frequencies))
    stimulus = "".join(f"{out / 100} {mark // 2} {sample_rate} {hz}\n"
                       for mark, out, hz in requests)
    result = subprocess.run([str(executable.resolve())], input=stimulus, text=True,
                            capture_output=True, check=True)
    data = np.atleast_2d(np.loadtxt(result.stdout.splitlines()))
    if data.shape != (len(requests), 2) or not np.isfinite(data).all():
        raise ValueError("Invalid impulse-response result")
    return dict(zip(requests, data[:, 0] + 1j*data[:, 1]))


def record_error(row, prefix, hz, error):
    row[f"{prefix}gain_error_db_{hz}hz"] = 20 * np.log10(abs(error))
    row[f"{prefix}phase_error_deg_{hz}hz"] = np.degrees(np.angle(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--dsp", type=Path, help="Executable that measures the C++ impulse response")
    parser.add_argument("--sample-rate", type=int, default=44100)
    args = parser.parse_args()
    with args.summary.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows = [r for r in rows if r["solver"] == "complete"]
    anchors = {(r["pair"], r["mode"], r["deess"]): r for r in rows
               if r["ceiling_mark"] == "16" and r["region"] == "reference"}
    digital_hz = [hz for hz in AC_PROBES_HZ if 2 * hz < args.sample_rate]
    taps = digital_taps(args.dsp, rows, digital_hz, args.sample_rate) if args.dsp else {}
    report = []
    for r in rows:
        key = r["pair"], r["mode"], r["deess"]
        ref = anchors[key]
        mark, out_pct = int(r["ceiling_mark"]), int(r["output_pct"])
        row = {field: r[field] for field in ("id", "pair", "mode", "ceiling_mark", "deess",
                                             "input_pct", "output_pct", "region")}
        for hz in AC_PROBES_HZ:
            gain, phase = f"gain_db_{hz}hz", f"phase_deg_{hz}hz"
            actual = 10**(float(r[gain]) / 20) * np.exp(1j * np.radians(float(r[phase])))
            base = 10**(float(ref[gain]) / 20) * np.exp(1j * np.radians(float(ref[phase])))
            relative = 1 if r["mode"] == "OFF" else small_signal_tap(mark, out_pct, hz) / small_signal_tap(16, REFERENCE[1], hz)
            record_error(row, "", hz, base * relative / actual)
            if taps and hz in digital_hz:
                tap = taps[mark, out_pct, hz]
                relative = 1 if r["mode"] == "OFF" else tap / taps[16, REFERENCE[1], hz]
                record_error(row, "dsp_", hz, base * relative / actual)
                record_error(row, "tap_", hz, tap / small_signal_tap(mark, out_pct, hz))
        report.append(row)
    if not report:
        raise SystemExit("No completed data to compare")
    writer(args.results, report)
    for region in ("reference", "input", "output", "holdout"):
        # OUT=0 uses a 1 µΩ numerical floor. Exclude its near-null signal from
        # relative error maxima while retaining the error in the output CSV.
        subset = [r for r in report if r["region"] == region and r["output_pct"] != "0"]
        if subset:
            gain = max(abs(r[f"gain_error_db_{hz}hz"]) for r in subset for hz in AC_PROBES_HZ)
            phase = max(abs(r[f"phase_error_deg_{hz}hz"]) for r in subset for hz in AC_PROBES_HZ)
            print(f"{region}: {len(subset)} rows, max {gain:.4f} dB and {phase:.4f} degrees")
    if taps:
        subset = [r for r in report if r["output_pct"] != "0"]
        for prefix in ("dsp_", "tap_"):
            gain = max(abs(r[f"{prefix}gain_error_db_{hz}hz"]) for r in subset for hz in digital_hz)
            phase = max(abs(r[f"{prefix}phase_error_deg_{hz}hz"]) for r in subset for hz in digital_hz)
            print(f"{prefix} worst absolute errors at {args.sample_rate} Hz: {gain:.4f} dB, {phase:.4f} degrees")
            if gain > .25 or phase > 3:
                raise SystemExit("Output stage exceeds the sampled control-law limit")


if __name__ == "__main__":
    main()
