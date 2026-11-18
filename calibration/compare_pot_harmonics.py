"""Compare compiled VST3 output against independent SPICE pot sweeps."""
import argparse
import csv
from pathlib import Path

PROFILES = (("C", 200), ("C", 68), ("C", 30), ("C", 20), ("L", 200), ("OFF", 200))


def read(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def controls(row, spice=False):
    return (int(row["hz"]), float(row["input_dbu"]),
            int(row["input_pct"]), int(row["output_pct"]), int(row["ceiling"]),
            int(row["release"][0]) + 2*int(row["release"][1]) if spice else int(row["release"]),
            int(row["deess"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vst3_csv", type=Path)
    parser.add_argument("reference_csv", type=Path, nargs="+")
    args = parser.parse_args()
    rendered = {(int(r["amp"]), int(r["slot"]), *controls(r)): r for r in read(args.vst3_csv)}
    rows = []
    for path in args.reference_csv:
        for reference in read(path):
            if reference["solver"] != "complete" or reference["settled_half_window_0_1db"] != "True":
                continue
            condition = controls(reference, spice=True)
            if float(reference["out_dbu"]) < -80:
                print(f"{condition}: below the output floor for relative harmonic comparisons")
                continue
            amp = int(reference["pair"].startswith("990/"))
            slot = PROFILES.index((reference["mode"], int(reference["r44"])))
            measured = rendered.get((amp, slot, *condition))
            if measured is None:
                print(f"{condition}: missing binary result")
                continue
            harmonic_errors = []
            reference_power = 0
            for order in range(2, 21):
                field = f"k{order}_dbc"
                if not measured.get(field):
                    continue
                dbc = float(reference[field])
                reference_power += 10 ** (dbc / 10)
                if dbc >= -100:
                    error = 100 * abs(10 ** ((float(measured[field])-dbc)/20)-1)
                    harmonic_errors.append(error)
                    if error > 10:
                        print(f"{condition}: K{order} differs by {error:.2f}% ({dbc:.2f} dBc reference)")
            reference_thd = 100 * reference_power ** .5
            error = 100 * abs(float(measured["vst3_thd_pct"])/reference_thd-1)
            rows.append((condition, error, harmonic_errors))
    for category, selected in (
        ("anchors", [r for r in rows if not (r[0][2] % 10 or r[0][3] % 10)]),
        ("holdouts", [r for r in rows if r[0][2] % 10 or r[0][3] % 10]),
    ):
        if not selected:
            continue
        thd = [error for _, error, _ in selected]
        harmonics = [error for _, _, values in selected for error in values]
        print(f"{category}: THD {sum(x <= 10 for x in thd)}/{len(thd)} within 10%, "
              f"max {max(thd):.2f}%; individual harmonics ≥−100 dBc "
              f"{sum(x <= 10 for x in harmonics)}/{len(harmonics)} within 10%, "
              f"max {max(harmonics, default=0):.2f}%")


if __name__ == "__main__":
    main()
