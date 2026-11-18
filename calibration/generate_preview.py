"""Render calibrated data into a header with no runtime file dependencies."""
import csv
from pathlib import Path


def generate(folder):
    def read(name):
        with (folder / name).open(newline="") as stream:
            return list(csv.DictReader(stream))

    def number(value):
        return format(float(value), ".10g")

    def row(values):
        return "    {" + ", ".join(map(number, values)) + "},\n"

    def amp(r):
        return int(r["pair"].startswith("990/"))

    def resistor(r):
        return (200, 68, 30, 20).index(int(float(r["r44_ohm"])))

    gain = [row((amp(r), 4 if r["mode"] == "L" else resistor(r), r["input_position"],
                 int(r["ceiling_mark"])//2, r["input_dbu"], r["a1_gain_db"]))
            for r in read("curves.csv") if r["stable"] == "True"]
    harmonic = [row((amp(r), 4 if r["mode"] == "L" else resistor(r), r["hz"], r["input_dbu"], r["gain_db"], r["phase_deg"], r["a1_gain_db"],
                     *(10**(float(r[f"k{k}_dbc"])/20) for k in range(2,21))))
                for r in read("harmonics.csv")]
    release = [row((amp(r), resistor(r), r["hz"], ("00","10","01","11").index(r["release"]),
                    r["input_position"], float(r["gain_t63_2_ms"])*.001)) for r in read("release.csv")]
    attack = [row((amp(r), 4 if r["mode"] == "L" else resistor(r), r["drive_dbu"], r["crest_10_90_us"]))
              for r in read("attack.csv")]
    declarations = (
        ("AttackPoint", "int amp, slot; double level, spanUs;", "attack", attack),
        ("GainPoint", "int amp, slot; double input; int ceiling; double level, gain;", "gain", gain),
        ("HarmonicPoint", "int amp, slot, hz; double level, gainDb, phaseDeg, a1GainDb, magnitude[19];", "harmonics", harmonic),
        ("ReleasePoint", "int amp, slot, hz, setting; double input, seconds;", "release", release),
    )
    with (folder / "PreviewData.h").open("w") as stream:
        stream.write("#pragma once\n\nnamespace vintage525::data {\n")
        for name, fields, variable, values in declarations:
            if not values:
                raise ValueError(f"No data for {name}")
            stream.write(f"struct {name} {{ {fields} }};\ninline constexpr {name} {variable}[] = {{\n")
            stream.writelines(values)
            stream.write("};\n")
        stream.write("}\n")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parent)
