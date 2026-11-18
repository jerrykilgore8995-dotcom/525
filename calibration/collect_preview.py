"""Import measured rows into small versioned tables for the native build."""
import csv
import re
from pathlib import Path

from generate_preview import generate

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, fields, rows):
    with (ROOT / "calibration" / name).open("w", newline="") as stream:
        out = csv.DictWriter(stream, fields, extrasaction="ignore", lineterminator="\n")
        out.writeheader()
        out.writerows(rows)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-dir", required=True, type=Path)
    args = parser.parse_args()
    summaries = args.summary_dir
    curves = {}
    for name in ("gain-C-fixed", "gain-L-fixed", "mod-screen", "mod-four",
                 "mod-aligned", "mod-hybrid", "mod-hybrid-four"):
        for row in read(EVIDENCE / name / "points.csv"):
            if row["solver"] != "complete":
                continue
            resistor = int(float(row.get("r44_ohm") or 200))
            if resistor not in (200, 68, 30, 20):
                continue
            row["r44_ohm"] = resistor
            key = tuple(row[k] for k in ("pair","mode","r44_ohm","input_position","ceiling_mark","input_dbu"))
            curves[key] = {**row, "origin": name}
    for path in sorted(summaries.glob("525C-Mod-*-curves-points.csv")):
        for row in read(path):
            if row["solver"] != "complete" or row["stable"] != "True":
                continue
            row["r44_ohm"] = int(float(row["r44_ohm"]))
            key = tuple(row[k] for k in ("pair","mode","r44_ohm","input_position","ceiling_mark","input_dbu"))
            curves.setdefault(key, {**row, "origin": path.stem})
    write("curves.csv", ("pair","mode","r44_ohm","input_position","ceiling_mark","input_dbu",
                         "a1_gain_db","out_dbu","stable","origin"), curves.values())
    harmonics = []
    releases = []
    for path in sorted(summaries.glob("525C-Mod-*-summary.csv")):
        match = re.fullmatch(r"525C-Mod-(2520|990)-(200|68|30|20)-(harmonics|release)-summary.csv", path.name)
        if match is None:
            continue
        amp, resistor, kind = match.groups()
        for row in read(path):
            if row["solver"] != "complete":
                continue
            if kind == "harmonics" and row["deess"] == "0" and row["settled_half_window_0_1db"] == "True":
                harmonics.append({**row, "origin": path.stem})
            elif kind == "release" and row["gain_t63_2_ms"]:
                releases.append({**row, "origin": path.stem})
    write("harmonics.csv", ("pair","r44_ohm","hz","input_dbu","thd_k2_k20_pct",
                            *(f"k{k}_dbc" for k in range(2,21)), "origin"), harmonics)
    write("release.csv", ("pair","r44_ohm","hz","release","gain_t63_2_ms","origin"), releases)
    generate(ROOT / "calibration")


if __name__ == "__main__":
    main()
