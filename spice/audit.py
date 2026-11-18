"""Compare the vintage component worksheet with the connected SPICE deck."""
import csv
from pathlib import Path


def elements(path, subcircuit):
    inside = False
    devices = {}
    for line in path.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        name = words[0].upper()
        if name == ".SUBCKT":
            inside = words[1] == subcircuit
        elif inside and name == ".ENDS":
            return devices
        elif inside and name[0] not in "*.+":
            if name in devices:
                raise ValueError(f"Duplicate element {name} in {subcircuit}")
            devices[name] = words[1:]
    raise ValueError(f"Missing subcircuit {subcircuit}")


def legacy_instances(ref):
    if ref == "JP":
        return ["VSTRAP"]
    if ref == "J1":
        return ["X525", "VEDGE4", "VEDGE8"]
    if ref == "Q1":
        return ["JQ1"]
    if ref in ("R38", "R43", "R55"):
        return [f"{ref}A", f"{ref}B"]
    if ref in ("S5A", "S5B"):
        return [f"R{ref}{i}" for i in range(0, 21, 2)]
    if ref == "S1A":
        return ["RS1A13", "RS1A24", "RS1A46", "RS1A810"]
    if ref == "S1B":
        return ["RS1B13", "RS1B35", "RS1B46"]
    if ref == "S1C":
        return ["RS1C35"]
    if ref == "S3":
        return ["RS3A", "RS3B"]
    if ref == "S4":
        return ["RS4A", "RS4B"]
    if ref == "S2":
        return ["RS2"]
    if ref.startswith("CR"):
        return ["D" + ref]
    if ref.startswith(("A", "T")):
        return ["X" + ref]
    if ref.startswith(("M", "DS")):
        return ["R" + ref]
    return [ref]


def main():
    base = Path(__file__).resolve().parent
    circuit = elements(base / "525c.lib", "COMP525C")
    fixture_parts = {"X525", "VSTRAP"}
    with (base.parent / "reference" / "525c-components.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    expected = {name for row in rows for name in legacy_instances(row["refdes"])}
    actual = set(circuit) | fixture_parts
    if actual != expected:
        raise SystemExit(f"missing {sorted(expected-actual)}, extra {sorted(actual-expected)}")
    amp_path = base / "discrete-opamps.lib"
    original = elements(amp_path, "JE990_15") | elements(amp_path, "JE990_ISOLATOR")
    with (base.parent / "reference" / "je990-components.csv").open() as stream:
        jensens = {"D"+r["refdes"] if r["refdes"].startswith("CR") else r["refdes"]
                   for r in csv.DictReader(stream)}
    if set(original) != jensens:
        raise SystemExit("JE-990 drawing / netlist reference count mismatch")
    drawn = elements(amp_path, "DOA2520_DRAWN")
    target = {f"{kind}{i}" for kind, n in (("Q", 9), ("R", 16), ("C", 5), ("D", 3))
              for i in range(1,n+1)}
    corrected = elements(amp_path, "DOA2520_Q9_CORE")
    if set(drawn) != target or set(corrected) != target:
        raise SystemExit("2520 drawing / netlist reference count mismatch")
    print(f"525C {len(rows)} worksheet rows mapped to {len(actual)} circuit/fixture entries")
    print(f"2520 {len(drawn)} and JE-990 {len(original)} schematic components present")


if __name__ == "__main__":
    main()
