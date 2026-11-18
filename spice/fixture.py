"""Render a complete vintage 525C deck. Run ngspice from this directory."""
import argparse
from pathlib import Path


MODELS = {
    "2520": "DOA2520_10P",
    "2520-q9": "DOA2520_Q9_TEST",
    "2520-drawing": "DOA2520_DRAWN",
    "990": "JE990_15",
}


def deck(args):
    opamp = MODELS[args.opamp]
    detector = MODELS[args.detector_opamp or args.opamp]
    mode = {"C": 0, "L": 1, "OFF": 2}[args.mode]
    peak = .775 * 2**.5 * 10**(args.dbu / 20)
    yield "Vintage 525C engineering fixture, provisional device and winding parameters"
    yield ".include device-models.lib"
    yield ".include discrete-opamps.lib"
    yield ".include magnetics.lib"
    yield ".include 525c.lib"
    for name, model in (("ACTIVE_DOA", opamp), ("DETECTOR_DOA", detector)):
        yield f".subckt {name} ip im out vp vn com"
        yield f"Xstage ip im out vp vn com {model}"
        yield f".ends {name}"
    yield "VPLUS p 0 15"
    yield "VMINUS n 0 -15"
    if args.burst_dbu is None:
        yield f"VIN src 0 DC 0 AC 1 SIN(0 {peak:.12g} {args.hz})"
    else:
        burst_peak = .775 * 2**.5 * 10**(args.burst_dbu / 20)
        yield f"VPHASE carrier 0 DC 0 AC 1 SIN(0 1 {args.hz})"
        yield (f"BINPUT src 0 V=v(carrier)*ternary_fcn(time<{args.burst_start:.9g},"
               f"{peak:.12g},ternary_fcn(time<{args.burst_stop:.9g},{burst_peak:.12g},{peak:.12g}))")
    yield f"RSRC src ip {args.source}"
    yield "VSTRAP edge7 edge8 0"
    yield "VLAMP aux0 0 0"
    yield "VSECONDARY ol 0 0"
    yield f"RLOAD oh ol {args.load}"
    yield "X525 0 oh ol pin4 ip 0 edge7 edge8 test aux0 aux0 p 0 n COMP525C"
    yield (f"+ inp={args.input} outp={args.output} ceiling_index={args.ceiling} "
           f"r1pos={args.release[0]} r2pos={args.release[1]} mode={mode} ds={args.deess}")
    yield ".options method=gear maxord=2"
    if args.diagnostic_tolerances:
        yield ".options reltol=1e-3 vntol=1e-6 chgtol=1e-12"
    else:
        yield ".options reltol=1e-4"
    yield ".control"
    yield "op"
    yield "print v(x525.pos_rail) v(x525.neg_rail) v(x525.a1_out) v(x525.a2_out) v(x525.a3_out)"
    yield "print v(x525.fet_gate) v(x525.detector_control) i(vplus) i(vminus)"
    contact_mark = 2 * args.ceiling
    for deck_name in ("a", "b"):
        yield f"print @r.x525.rs5{deck_name}{contact_mark}[resistance]"
    if args.ac:
        yield "ac dec 48 20 40000"
        yield "print vdb(oh) vp(oh)"
    if args.transient:
        step = args.max_step or 1/(args.hz*500)
        start = args.seconds / 2
        yield f"tran {step:.8g} {args.seconds} 0 {step:.8g}"
        yield f"meas tran out_rms RMS v(oh) from={start:.8g} to={args.seconds:.8g}"
        yield f"meas tran control_min MIN v(x525.detector_control) from={start:.8g} to={args.seconds:.8g}"
        if args.burst_dbu is None:
            yield f"fourier {args.hz} v(oh)"
        if args.trace:
            yield "set wr_singlescale"
            yield "set wr_vecnames"
            yield (f"wrdata {args.trace} v(src) v(oh) v(x525.a1_out) v(x525.a2_out) "
                   "v(x525.a3_out) v(x525.fet_gate) v(x525.detector_control) v(x525.a1_plus)")
    yield "quit"
    yield ".endc"
    yield ".end"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opamp", choices=tuple(MODELS), default="2520")
    parser.add_argument("--detector-opamp", choices=tuple(MODELS),
                        help="Override only the vintage detector amplifier for substitution diagnostics")
    parser.add_argument("--mode", choices=("C", "L", "OFF"), default="C")
    parser.add_argument("--input", type=float, default=.5)
    parser.add_argument("--output", type=float, default=.75)
    parser.add_argument("--ceiling", type=int, choices=range(11), default=5)
    parser.add_argument("--release", choices=("00", "10", "01", "11"), default="00")
    parser.add_argument("--deess", type=int, choices=(0, 1), default=0)
    parser.add_argument("--source", type=float, default=150)
    parser.add_argument("--load", type=float, default=10000)
    parser.add_argument("--dbu", type=float, default=4)
    parser.add_argument("--hz", type=float, default=1000)
    parser.add_argument("--seconds", type=float, default=.1)
    parser.add_argument("--burst-dbu", type=float, help="Switch the continuous carrier to this level during the burst")
    parser.add_argument("--burst-start", type=float, default=.02)
    parser.add_argument("--burst-stop", type=float, default=.05)
    parser.add_argument("--ac", action="store_true")
    parser.add_argument("--max-step", type=float, help="Maximum transient timestep in seconds")
    parser.add_argument("--diagnostic-tolerances", action="store_true",
                        help="Use relaxed tolerances for first-pass stability diagnostics")
    parser.add_argument("--trace", type=Path, help="Write raw transient nodes to this path (without spaces)")
    parser.add_argument("--transient", action="store_true")
    args = parser.parse_args()
    if not (0 <= args.input <= 1 and 0 <= args.output <= 1):
        parser.error("input and output are positions from 0 to 1")
    if not (args.source > 0 and args.load > 0 and args.hz > 0 and args.seconds > 0):
        parser.error("source, load, frequency and runtime must be positive")
    if args.burst_dbu is not None and (not args.transient
                                      or not 0 < args.burst_start < args.burst_stop < args.seconds):
        parser.error("burst needs --transient and start/stop inside the run")
    if args.max_step is not None and args.max_step <= 0:
        parser.error("--max-step must be positive")
    if args.trace is not None and (not args.transient or any(c.isspace() for c in str(args.trace))):
        parser.error("--trace requires --transient and a path without spaces")
    print("\n".join(deck(args)))


if __name__ == "__main__":
    main()
