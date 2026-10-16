"""Circuit templates: parameters, formulas and drawings.

Each template takes named values (as said by the user, parsed by values.py),
computes everything else deterministically, and draws the circuit with
schemdraw. Rules every template follows:

  - Nothing that belongs in a datasheet is invented. If a value such as an
    LED's forward voltage was not given, a typical value is used AND recorded
    as an assumption, which is printed on the drawing and returned to the
    assistant so it says so aloud.
  - Chosen component values are snapped to E-series preferred values (the
    ones you can buy), and the result is recomputed with the snapped value,
    so the drawing shows what the real circuit will do, not the ideal.
  - Design rules of thumb (forced beta of 10, 2x resistor power margin) are
    labelled as rules, not presented as data.

Adding a template = one compute function, one draw function, one Template()
entry in TEMPLATES.
"""
import math
import re
from dataclasses import dataclass, field
from typing import Callable

import schemdraw.elements as elm

from . import values as V
from .values import BadValue, fmt


@dataclass(frozen=True)
class Param:
    name: str
    unit: str          # a values.UNIT_NAMES key, "choice" or "text"
    help: str
    default: str | None = None
    assumption: str | None = None   # recorded when the default is used
    optional: bool = False          # may be absent (an alternative input)
    choices: tuple = ()


@dataclass
class Result:
    values: dict                    # every value the drawing shows
    derived: list = field(default_factory=list)       # [(label, text)]
    assumptions: list = field(default_factory=list)
    notes: list = field(default_factory=list)


@dataclass(frozen=True)
class Template:
    name: str
    title: str
    description: str
    params: tuple
    compute: Callable
    draw: Callable

    def signature(self) -> str:
        names = [p.name + ("?" if (p.optional or p.default) else "") for p in self.params]
        return f"{self.name}({', '.join(names)})"


def resolve(t: Template, inputs: dict) -> tuple[dict, list]:
    """Parse the given inputs; fill defaults (recording assumptions)."""
    by_lower = {p.name.lower(): p for p in t.params}
    given = {}
    for key, raw in (inputs or {}).items():
        p = by_lower.get(str(key).strip().lower())
        if p is None:
            raise BadValue(f"{t.name} has no parameter '{key}'. Its parameters are "
                           f"{', '.join(p.name for p in t.params)}.")
        if raw is None or str(raw).strip().lower() in ("", "none", "remove"):
            continue
        given[p.name] = raw
    vals, assumptions = {}, []
    for p in t.params:
        if p.name in given:
            raw = given[p.name]
        elif p.default is not None:
            raw = p.default
            if p.assumption:
                assumptions.append(p.assumption)
        elif p.optional:
            continue
        else:
            raise BadValue(f"Missing {p.name}: {p.help}.")
        if p.unit == "choice":
            text = str(raw).strip().lower()
            if text not in p.choices:
                raise BadValue(f"{p.name} must be one of {', '.join(p.choices)}.")
            vals[p.name] = text
        elif p.unit == "text":
            vals[p.name] = re.sub(r"[^\w ]", "", str(raw)).strip()[:16] or p.default
        else:
            vals[p.name] = V.parse(raw, p.unit)
            if vals[p.name] <= 0 and p.unit != "":
                raise BadValue(f"{p.name} must be greater than zero.")
    return vals, assumptions


def _power_note(p_watts: float, name: str) -> str:
    # Rule of thumb: run a resistor at no more than half its rating.
    if p_watts <= 0.125:
        return f"{name} dissipates {fmt(p_watts, 'W')}: a 0.25 W resistor has at least 2x margin."
    return f"{name} dissipates {fmt(p_watts, 'W')}: use a resistor rated {fmt(2 * p_watts, 'W')} or more."


# --- voltage divider ----------------------------------------------------------

def _divider(v, assumptions):
    vin, r1 = v["Vin"], v["R1"]
    notes = []
    if "R2" in v:
        r2 = v["R2"]
        if "Vout" in v:
            notes.append("R2 was given, so the requested Vout was not used.")
    elif "Vout" in v:
        target = v["Vout"]
        if not 0 < target < vin:
            raise BadValue("The output voltage must be between 0 and Vin.")
        r2 = V.nearest(r1 * target / (vin - target), "E24")
        notes.append(f"R2 is the nearest E24 value for a {fmt(target, 'V')} target.")
    else:
        raise BadValue("Give R2, or the output voltage you want (Vout).")
    vout = vin * r2 / (r1 + r2)
    i = vin / (r1 + r2)
    notes += [_power_note(i * i * r1, "R1"), _power_note(i * i * r2, "R2"),
              "Vout is unloaded: anything connected across R2 pulls it lower."]
    return Result({"Vin": vin, "R1": r1, "R2": r2, "Vout": vout},
                  [("Vout", fmt(vout, "V")), ("Divider current", fmt(i, "A"))],
                  assumptions, notes)


def _draw_divider(d, r):
    v = r.values
    src = elm.SourceV().up().length(d.unit * 2).label(f"Vin\n{fmt(v['Vin'], 'V')}", loc="top")
    elm.Line().right(d.unit * 0.75)
    elm.Resistor().down().label(f"R1\n{fmt(v['R1'], 'Ω')}", loc="bottom")
    mid = d.here
    elm.Dot()
    elm.Resistor().down().label(f"R2\n{fmt(v['R2'], 'Ω')}", loc="bottom")
    elm.Line().left().tox(src.start)
    elm.Ground().at(src.start)
    elm.Line().right(d.unit * 0.6).at(mid)
    elm.Dot(open=True).label(f"Vout\n{fmt(v['Vout'], 'V')}", loc="right")


# --- LED + series resistor ----------------------------------------------------

def _led(v, assumptions):
    vs, vf = v["Vs"], v["Vf"]
    if vs <= vf:
        raise BadValue(f"The supply ({fmt(vs, 'V')}) must be above the LED's forward "
                       f"voltage ({fmt(vf, 'V')}).")
    notes = []
    if "R" in v:
        r = v["R"]
    else:
        ideal = (vs - vf) / v["If"]
        r = V.next_higher(ideal, "E24")
        notes.append(f"R is the next E24 value above (Vs - Vf) / If = {fmt(ideal, 'Ω')}, "
                     "so the current stays at or below the target.")
    i = (vs - vf) / r
    notes.append(_power_note(i * i * r, "R"))
    return Result({"Vs": vs, "Vf": vf, "R": r, "I": i},
                  [("R", fmt(r, "Ω")), ("LED current", fmt(i, "A"))],
                  assumptions, notes)


def _draw_led(d, r):
    v = r.values
    elm.Vdd().label(f"Vs = {fmt(v['Vs'], 'V')}")
    elm.Resistor().down().label(f"R\n{fmt(v['R'], 'Ω')}", loc="bottom")
    elm.LED().down().label(f"LED\nVf {fmt(v['Vf'], 'V')}", loc="bottom")
    elm.Ground()


# --- RC filters -----------------------------------------------------------------

def _rc(v, assumptions):
    have = {k for k in ("R", "C", "fc") if k in v}
    notes = []
    if {"R", "C"} <= have:
        rr, cc = v["R"], v["C"]
        if "fc" in have:
            notes.append("R and C were both given, so the requested fc was not used.")
    elif {"fc", "R"} <= have:
        rr = v["R"]
        cc = V.nearest(1 / (2 * math.pi * rr * v["fc"]), "E12")
        notes.append("C is the nearest E12 value for the requested cutoff.")
    elif {"fc", "C"} <= have:
        cc = v["C"]
        rr = V.nearest(1 / (2 * math.pi * cc * v["fc"]), "E24")
        notes.append("R is the nearest E24 value for the requested cutoff.")
    else:
        raise BadValue("Give two of: R, C and the cutoff frequency fc.")
    fc = 1 / (2 * math.pi * rr * cc)
    notes.append("First order: 20 dB per decade beyond fc. Load the output with "
                 "much more than R, or the cutoff moves.")
    return Result({"R": rr, "C": cc, "fc": fc},
                  [("Cutoff fc (-3 dB)", fmt(fc, "Hz")), ("Time constant RC", fmt(rr * cc, "s"))],
                  assumptions, notes)


def _draw_rc(d, r, highpass):
    v = r.values
    elm.Dot(open=True).label("Vin", loc="left")
    if highpass:
        elm.Capacitor().right().label(f"C\n{fmt(v['C'], 'F')}")
    else:
        elm.Resistor().right().label(f"R\n{fmt(v['R'], 'Ω')}")
    node = d.here
    elm.Dot()
    if highpass:
        elm.Resistor().down().label(f"R\n{fmt(v['R'], 'Ω')}", loc="bottom")
    else:
        elm.Capacitor().down().label(f"C\n{fmt(v['C'], 'F')}", loc="bottom")
    elm.Ground()
    elm.Line().right(d.unit * 0.6).at(node)
    elm.Dot(open=True).label("Vout", loc="right")


# --- op-amp amplifiers -----------------------------------------------------------

_OPAMP_NOTE = ("Op-amp part and supply are not specified: check its output swing, "
               "input range and bandwidth for your signal.")


def _noninv(v, assumptions):
    notes = []
    if "Rf" in v and "Rg" in v:
        rf, rg = v["Rf"], v["Rg"]
    elif "gain" in v and ("Rg" in v or "Rf" in v):
        g = v["gain"]
        if g <= 1:
            raise BadValue("A non-inverting amplifier's gain is above 1. For a gain of "
                           "exactly 1 use a voltage follower.")
        if "Rg" in v:
            rg = v["Rg"]
            rf = V.nearest((g - 1) * rg, "E24")
            notes.append("Rf is the nearest E24 value for the requested gain.")
        else:
            rf = v["Rf"]
            rg = V.nearest(rf / (g - 1), "E24")
            notes.append("Rg is the nearest E24 value for the requested gain.")
    else:
        raise BadValue("Give Rf and Rg, or the gain plus one of them.")
    gain = 1 + rf / rg
    notes.append(_OPAMP_NOTE)
    return Result({"Rf": rf, "Rg": rg, "gain": gain},
                  [("Gain 1 + Rf/Rg", f"{gain:.3g} ({20 * math.log10(gain):.1f} dB)")],
                  assumptions, notes)


def _draw_noninv(d, r):
    v = r.values
    op = elm.Opamp(leads=True).flip()          # + input on top
    elm.Line().left(d.unit * 0.4).at(op.in2)
    elm.Dot(open=True).label("Vin", loc="left")
    elm.Line().down(d.unit * 0.6).at(op.in1)
    fb = d.here
    elm.Dot()
    elm.Resistor().right().tox(op.out).label(f"Rf\n{fmt(v['Rf'], 'Ω')}", loc="bottom")
    elm.Line().up().toy(op.out)
    elm.Resistor().down().at(fb).label(f"Rg\n{fmt(v['Rg'], 'Ω')}", loc="bottom")
    elm.Ground()
    elm.Line().right(d.unit * 0.5).at(op.out)
    elm.Dot(open=True).label("Vout", loc="right")


def _inv(v, assumptions):
    notes = []
    if "Rf" in v and "Rin" in v:
        rf, rin = v["Rf"], v["Rin"]
    elif "gain" in v and ("Rin" in v or "Rf" in v):
        g = abs(v["gain"])
        if g == 0:
            raise BadValue("The gain cannot be zero.")
        if "Rin" in v:
            rin = v["Rin"]
            rf = V.nearest(g * rin, "E24")
            notes.append("Rf is the nearest E24 value for the requested gain.")
        else:
            rf = v["Rf"]
            rin = V.nearest(rf / g, "E24")
            notes.append("Rin is the nearest E24 value for the requested gain.")
    else:
        raise BadValue("Give Rf and Rin, or the gain plus one of them.")
    gain = -rf / rin
    notes.append(f"Input impedance is Rin = {fmt(rin, 'Ω')}.")
    notes.append(_OPAMP_NOTE)
    return Result({"Rf": rf, "Rin": rin, "gain": gain},
                  [("Gain -Rf/Rin", f"{gain:.3g} ({20 * math.log10(abs(gain)):.1f} dB, inverted)")],
                  assumptions, notes)


def _draw_inv(d, r):
    v = r.values
    op = elm.Opamp(leads=True)                 # - input on top
    elm.Dot().at(op.in1)
    elm.Resistor().left().at(op.in1).label(f"Rin\n{fmt(v['Rin'], 'Ω')}")
    elm.Dot(open=True).label("Vin", loc="left")
    elm.Line().left(d.unit * 0.3).at(op.in2)
    elm.Ground()
    elm.Line().up(d.unit * 0.6).at(op.in1)
    elm.Resistor().right().tox(op.out).label(f"Rf\n{fmt(v['Rf'], 'Ω')}")
    elm.Line().down().toy(op.out)
    elm.Line().right(d.unit * 0.5).at(op.out)
    elm.Dot(open=True).label("Vout", loc="right")


# --- NPN low-side switch -----------------------------------------------------------

def _npn(v, assumptions):
    vin, vbe, beta = v["Vin"], v["Vbe"], v["beta"]
    if vin <= vbe:
        raise BadValue("The drive voltage must be above VBE.")
    ib_target = v["Ic"] / beta
    rb = V.next_lower((vin - vbe) / ib_target, "E24")
    ib = (vin - vbe) / rb
    notes = [f"Rb is the next E24 value below (Vin - VBE) / (Ic / beta), so the base "
             f"gets at least {fmt(ib_target, 'A')}.",
             "Check the GPIO can supply Ib (see the Raspberry Pi GPIO documentation).",
             "Choose a transistor rated well above Ic and Vcc."]
    if ib > 5e-3:
        # A design judgement, not a datasheet limit: several mA is a lot to
        # ask of a logic pin, and a MOSFET's gate draws no steady current.
        notes.insert(1, f"Ib of {fmt(ib, 'A')} is a lot for a logic pin: for a load "
                        "this size a logic-level N-MOSFET is usually the better switch.")
    if v["load"] in ("relay", "motor"):
        notes.append("The flyback diode is required: it clamps the coil's voltage "
                     "spike when the transistor switches off.")
    return Result(dict(v, Rb=rb, Ib=ib),
                  [("Rb", fmt(rb, "Ω")), ("Base current", fmt(ib, "A")),
                   ("Load current", fmt(v["Ic"], "A"))],
                  assumptions, notes)


def _draw_npn(d, r):
    v = r.values
    elm.Vdd().label(f"Vcc = {fmt(v['Vcc'], 'V')}")
    kind = v["load"]
    # Load labels go on the LEFT (loc="top" for a downward element): the
    # flyback diode sits on the right.
    if kind == "relay":
        load = elm.Inductor().down().length(d.unit * 1.2).label("Relay\ncoil", loc="top")
    elif kind == "motor":
        load = elm.Motor().down().length(d.unit * 1.2).label("M", loc="top")
    elif kind == "lamp":
        load = elm.Lamp().down().label("Lamp", loc="top")
    else:
        load = elm.Resistor().down().label("Load", loc="top")
    elm.Line().down(d.unit * 0.3)
    # .right(): standard orientation (base left, collector up, emitter down).
    # Without it schemdraw rotates the transistor to the current drawing
    # direction, which after the load is "down".
    q = elm.BjtNpn(circle=True).right().anchor("collector")
    elm.Ground().at(q.emitter)
    elm.Line().left(d.unit * 0.3).at(q.base)
    elm.Resistor().left().label(f"Rb\n{fmt(v['Rb'], 'Ω')}")
    elm.Dot(open=True).label(f"GPIO\n{fmt(v['Vin'], 'V')}", loc="left")
    if kind in ("relay", "motor"):
        elm.Dot().at(load.start)
        elm.Line().right(d.unit * 0.8).at(load.start)
        elm.Diode().down().reverse().toy(load.end).label("D1\nflyback", loc="bottom")
        elm.Line().left().tox(load.end)
        elm.Dot().at(load.end)


# --- push button with pull-up ---------------------------------------------------------

def _pullup(v, assumptions):
    i = v["Vcc"] / v["R"]
    notes = ["Released reads HIGH; pressed reads LOW.",
             "Debounce in software (at least 5 ms, the project convention).",
             "If the switch datasheet gives a minimum contact current, size R so "
             "Vcc/R exceeds it (the HAT's EC11 encoder needs 1 kΩ for this reason)."]
    return Result(dict(v), [("Current when pressed", fmt(i, "A"))], assumptions, notes)


def _draw_pullup(d, r):
    v = r.values
    elm.Vdd().label(fmt(v["Vcc"], "V"))
    elm.Resistor().down().label(f"R\n{fmt(v['R'], 'Ω')}", loc="bottom")
    node = d.here
    elm.Dot()
    elm.Button().down().label("S1", loc="bottom")
    elm.Ground()
    elm.Line().right(d.unit * 0.8).at(node)
    elm.Dot(open=True).label(str(v["pin"]).upper(), loc="right")


# --- registry -------------------------------------------------------------------------

_LED_I = ("LED current 10 mA assumed: use the current your LED's datasheet "
          "recommends.")
_LED_VF = ("Forward voltage 2.0 V assumed (typical red LED; blue and white are "
           "nearer 3 V): check the LED's datasheet.")
_GPIO = "Drive voltage 3.3 V assumed (a Raspberry Pi GPIO pin)."

TEMPLATES = {t.name: t for t in (
    Template(
        "voltage_divider", "Voltage divider",
        "Two resistors that scale a voltage down. Give R2 or the Vout you want.",
        (Param("Vin", "V", "the input voltage"),
         Param("R1", "Ω", "the top resistor", default="10k",
               assumption="R1 = 10 kΩ chosen (no value was given)."),
         Param("R2", "Ω", "the bottom resistor", optional=True),
         Param("Vout", "V", "the output voltage you want", optional=True)),
        _divider, _draw_divider),
    Template(
        "led_resistor", "LED with current-limiting resistor",
        "Series resistor for an LED from a supply; computes R or checks one.",
        (Param("Vs", "V", "the supply voltage"),
         Param("If", "A", "the LED current", default="10 mA", assumption=_LED_I),
         Param("Vf", "V", "the LED forward voltage", default="2.0 V", assumption=_LED_VF),
         Param("R", "Ω", "an existing resistor to check", optional=True)),
        _led, _draw_led),
    Template(
        "rc_lowpass", "RC low-pass filter",
        "First-order low-pass. Give two of R, C and the cutoff fc.",
        (Param("R", "Ω", "the series resistor", optional=True),
         Param("C", "F", "the capacitor to ground", optional=True),
         Param("fc", "Hz", "the cutoff frequency", optional=True)),
        _rc, lambda d, r: _draw_rc(d, r, highpass=False)),
    Template(
        "rc_highpass", "RC high-pass filter",
        "First-order high-pass. Give two of R, C and the cutoff fc.",
        (Param("R", "Ω", "the resistor to ground", optional=True),
         Param("C", "F", "the series capacitor", optional=True),
         Param("fc", "Hz", "the cutoff frequency", optional=True)),
        _rc, lambda d, r: _draw_rc(d, r, highpass=True)),
    Template(
        "opamp_noninverting", "Non-inverting op-amp amplifier",
        "Gain 1 + Rf/Rg. Give Rf and Rg, or the gain and one of them.",
        (Param("Rf", "Ω", "the feedback resistor", optional=True),
         Param("Rg", "Ω", "the resistor to ground", optional=True),
         Param("gain", "", "the voltage gain wanted", optional=True)),
        _noninv, _draw_noninv),
    Template(
        "opamp_inverting", "Inverting op-amp amplifier",
        "Gain -Rf/Rin. Give Rf and Rin, or the gain and one of them.",
        (Param("Rf", "Ω", "the feedback resistor", optional=True),
         Param("Rin", "Ω", "the input resistor", optional=True),
         Param("gain", "", "the voltage gain wanted (its size)", optional=True)),
        _inv, _draw_inv),
    Template(
        "npn_switch", "NPN transistor switch",
        "A GPIO switching a relay, motor, lamp or other load through an NPN "
        "transistor; computes the base resistor.",
        (Param("Vcc", "V", "the load's supply voltage"),
         Param("Ic", "A", "the load current"),
         Param("load", "choice", "what is being switched", default="relay",
               assumption="Load type 'relay' assumed (with flyback diode).",
               choices=("relay", "motor", "lamp", "load")),
         Param("Vin", "V", "the drive voltage", default="3.3 V", assumption=_GPIO),
         Param("Vbe", "V", "base-emitter voltage", default="0.7 V",
               assumption="VBE 0.7 V assumed (typical silicon): check VBE(sat) in "
                          "the transistor's datasheet."),
         Param("beta", "", "forced beta", default="10",
               assumption="Forced beta of 10 (a design rule that keeps the switch "
                          "saturated; the datasheet hFE is not used).")),
        _npn, _draw_npn),
    Template(
        "button_pullup", "Push button with pull-up resistor",
        "A push button to a GPIO input with a pull-up resistor.",
        (Param("Vcc", "V", "the logic supply", default="3.3 V",
               assumption="3.3 V logic assumed (Raspberry Pi GPIO)."),
         Param("R", "Ω", "the pull-up resistor", default="10k",
               assumption="Pull-up 10 kΩ chosen (no value was given)."),
         Param("pin", "text", "the GPIO label, e.g. GPIO22", default="GPIO")),
        _pullup, _draw_pullup),
)}


def get(name: str) -> Template:
    t = TEMPLATES.get(str(name or "").strip().lower())
    if t is None:
        raise BadValue(f"Unknown template '{name}'. Available: {', '.join(TEMPLATES)}.")
    return t


def summary() -> str:
    """One line per template, for the tool description and the user."""
    return "; ".join(t.signature() for t in TEMPLATES.values())
