"""Engineering values: parse what was said, print it back, snap to E-series.

Parsing accepts the forms people say and models write:
    "4.7k", "4k7" (RKM code), "4.7 kΩ", "4.7 kilo ohm", "10M", "1 meg",
    "100n", "0.1uF", "100 nF", "2R2", "5", "5V", "3.3 v", "20mA", "1e-6",
    "4,7k" (decimal comma), "4,700" (thousands separator)
Prefix case matters the way it does on a schematic: m = milli, M = mega.
A value with the WRONG unit ("5 V" for a resistor) is refused, not guessed.

E-series values are the IEC 60063 preferred numbers; resistor values are
snapped to them because those are the values one can actually buy.
"""
import math
import re

PREFIX = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3,
          "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9}
# Spoken prefixes. "mega" before "meg" so the longer word wins.
_PREFIX_WORDS = (("mega", "M"), ("meg", "M"), ("kilo", "k"), ("milli", "m"),
                 ("micro", "u"), ("nano", "n"), ("pico", "p"))
# Unit names that may END a value, per quantity; matched case-insensitively,
# longest first. "r" for ohms allows "10R".
UNIT_NAMES = {
    "Ω": ("ohms", "ohm", "Ω", "Ω", "r"),
    "F": ("farads", "farad", "f"),
    "V": ("volts", "volt", "v"),
    "A": ("amperes", "ampere", "amps", "amp", "a"),
    "Hz": ("hertz", "hz"),
    "H": ("henries", "henry", "h"),
    "": (),
}

E12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)
E24 = (1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6,
       3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1)
E96 = tuple(v / 100 for v in (
    100, 102, 105, 107, 110, 113, 115, 118, 121, 124, 127, 130, 133, 137, 140,
    143, 147, 150, 154, 158, 162, 165, 169, 174, 178, 182, 187, 191, 196, 200,
    205, 210, 215, 221, 226, 232, 237, 243, 249, 255, 261, 267, 274, 280, 287,
    294, 301, 309, 316, 324, 332, 340, 348, 357, 365, 374, 383, 392, 402, 412,
    422, 432, 442, 453, 464, 475, 487, 499, 511, 523, 536, 549, 562, 576, 590,
    604, 619, 634, 649, 665, 681, 698, 715, 732, 750, 768, 787, 806, 825, 845,
    866, 887, 909, 931, 953, 976))
SERIES = {"E12": E12, "E24": E24, "E96": E96}

_NUMBER = re.compile(r"^([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([pnuµμmkKMG]?)$")
_RKM = re.compile(r"^([0-9]+)([pnuµμmkKMGR])([0-9]+)$")


class BadValue(ValueError):
    """A value that cannot be understood; the message is meant to be spoken."""


def _strip_unit(s: str, unit: str, raw: str) -> str:
    """Remove a trailing unit name; refuse one belonging to another quantity."""
    low = s.lower()
    for quantity, names in UNIT_NAMES.items():
        for name in sorted(names, key=len, reverse=True):
            n = name.lower()
            # The unit must follow a digit or a prefix, so "4k7" never loses
            # its last character and a bare "m" is never read as a unit.
            if len(s) > len(n) and low.endswith(n) and re.search(r"[0-9pnuµμmkKMG]$", s[: -len(n)]):
                if quantity != unit:
                    raise BadValue(f"'{raw}' is in {quantity or 'another unit'}, "
                                   f"not {unit or 'a plain number'}.")
                return s[: -len(n)]
    return s


def parse(text, unit: str) -> float:
    """Parse a value in `unit` (a key of UNIT_NAMES). Raises BadValue."""
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    raw = str(text or "").strip()
    s = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", raw)   # 4,700 -> 4700
    s = s.replace(",", ".").replace(" ", "")          # 4,7k  -> 4.7k
    for word, sym in _PREFIX_WORDS:
        s = re.sub(word, sym, s, flags=re.IGNORECASE)
    s = _strip_unit(s, unit, raw)
    m = _RKM.match(s)
    if m:
        mult = 1.0 if m.group(2) == "R" else PREFIX[m.group(2)]
        return float(f"{m.group(1)}.{m.group(3)}") * mult
    m = _NUMBER.match(s)
    if not m:
        raise BadValue(f"I couldn't read '{raw}' as a value in {unit or 'a number'}.")
    return float(m.group(1)) * PREFIX[m.group(2)]


def fmt(value: float, unit: str = "", digits: int = 3) -> str:
    """Engineering format: 4700 Ω -> '4.7 kΩ', 0.00034 A -> '340 µA'."""
    if value == 0 or not math.isfinite(value):
        return f"{value:g} {unit}".strip()
    exp3 = int(math.floor(math.log10(abs(value)) / 3)) * 3
    exp3 = max(-12, min(9, exp3))
    mant = value / 10 ** exp3
    decimals = max(0, digits - 1 - int(math.floor(math.log10(abs(mant)))))
    text = f"{mant:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    prefix = {-12: "p", -9: "n", -6: "µ", -3: "m", 0: "", 3: "k", 6: "M", 9: "G"}[exp3]
    return f"{text} {prefix}{unit}".strip()


def _candidates(value: float, series: str):
    decade = 10 ** math.floor(math.log10(value))
    for d in (decade / 10, decade, decade * 10):
        for b in SERIES[series]:
            yield b * d


def _check(value: float) -> None:
    if not value > 0 or not math.isfinite(value):
        raise BadValue("A component value must be a positive number.")


def nearest(value: float, series: str = "E24") -> float:
    """Closest preferred value (geometrically: same ratio up or down)."""
    _check(value)
    best = min(_candidates(value, series), key=lambda c: abs(math.log(c / value)))
    return float(f"{best:.6g}")


def next_higher(value: float, series: str = "E24") -> float:
    """Smallest preferred value >= value (e.g. a current-limiting resistor)."""
    _check(value)
    return float(f"{min(c for c in _candidates(value, series) if c >= value * (1 - 1e-9)):.6g}")


def next_lower(value: float, series: str = "E24") -> float:
    """Largest preferred value <= value (e.g. a base resistor: more current)."""
    _check(value)
    return float(f"{max(c for c in _candidates(value, series) if c <= value * (1 + 1e-9)):.6g}")
