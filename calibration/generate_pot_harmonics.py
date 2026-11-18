"""Build a sparse measured harmonic table from SPICE CSVs."""
import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = (("C", 200), ("C", 68), ("C", 30), ("C", 20), ("L", 200), ("OFF", 200))


def generate(files, target):
    anchors = {}
    for path in files:
        with path.open(newline="") as stream:
            for row in csv.DictReader(stream):
                if (row["solver"] != "complete" or row["settled_half_window_0_1db"] != "True"
                        or not row.get("out_dbu") or float(row["out_dbu"]) < -80):
                    continue
                inp, out = int(row["input_pct"]), int(row["output_pct"])
                if inp % 10 or out % 10:
                    continue
                amp = int(row["pair"].startswith("990/"))
                slot = PROFILES.index((row["mode"], int(row["r44"])))
                key = (amp, slot, int(row["ceiling"]), int(row["release"][0]) + 2*int(row["release"][1]),
                       int(row["deess"]), int(row["hz"]), float(row["input_dbu"]), inp, out)
                anchors[key] = [float(row[f"k{k}_dbc"]) for k in range(2, 21)]
    if not anchors:
        raise ValueError("No valid measured harmonic anchors")
    lines = ["#pragma once", "", "namespace vintage525::data {",
             "struct PotHarmonicPoint {",
             "    int amp, slot, ceiling, release, deess, hz;",
             "    double level;",
             "    int input, output;",
             "    double dbc[19];",
             "};", "inline constexpr PotHarmonicPoint potHarmonics[] = {"]
    for key, values in sorted(anchors.items()):
        metadata = ", ".join(f"{v:g}" for v in key)
        harmonics = ", ".join(f"{v:.6f}" for v in values)
        lines.append(f"    {{{metadata}, {{{harmonics}}}}},")
    lines.extend(("};", "}", ""))
    target.write_text("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, default=ROOT / "PotHarmonicData.h")
    args = parser.parse_args()
    generate(args.csv, args.output)
