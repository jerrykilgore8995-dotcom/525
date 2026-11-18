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
    limit = {}
    limit_paths = (summaries / "limit-band.csv", summaries / "limit-settling" / "summary.csv",
                   EVIDENCE / "limit-settling" / "summary.csv")
    for path in limit_paths:
        for row in read(path):
            # The local retry CSV omitted fixture columns preserved in its deck directory names.
            row.setdefault("pair", "2520/2520")
            if "load_ohm" not in row and "load" not in row:
                row["load_ohm"] = "10000"
            if (row.get("mode", "L") != "L" or row["hz"] not in ("100", "1000", "5000", "10000")
                    or row.get("load_ohm", row.get("load")) != "10000"
                    or row.get("deess", row.get("ds")) != "0"
                    or row["solver"] != "complete" or row["settled_half_window_0_1db"] != "True"):
                continue
            key = row["pair"], row["hz"], row["input_dbu"]
            limit[key] = {**row, "mode": "L", "r44_ohm": 200, "origin": path.parent.name}
    harmonics.extend(limit.values())
    write("harmonics.csv", ("pair","mode","r44_ohm","hz","input_dbu","gain_db","phase_deg","a1_gain_db","thd_k2_k20_pct",
                            *(f"k{k}_dbc" for k in range(2,21)), "origin"), harmonics)
    write("release.csv", ("pair","r44_ohm","hz","release","gain_t63_2_ms","origin"), releases)
    attacks = {}
    paths = [(summaries / name / "summary.csv", .9) for name in ("attack-final", "attack-limit")]
    paths.extend((EVIDENCE / name / "summary.csv", .5) for name in
                 ("mod-8-attack", "mod-12-retry", "mod-finer-20", "mod-finer-30"))
    for path, default_input in paths:
        for row in read(path):
            if row["solver"] != "complete" or not row["crest_10_90_us"]:
                continue
            row.setdefault("input_position", default_input)
            row.setdefault("r44_ohm", 200)
            key = (row["pair"], row["mode"], float(row["r44_ohm"]), float(row["drive_dbu"]))
            previous = attacks.get(key)
            if previous is None or float(row["max_step_s"]) < float(previous["max_step_s"]):
                attacks[key] = {**row, "origin": path.parent.name}
    write("attack.csv", ("pair","mode","r44_ohm","input_position","drive_dbu",
                         "crest_t10_us","crest_10_90_us","max_step_s","origin"), attacks.values())
    generate(ROOT / "calibration")


if __name__ == "__main__":
    main()
