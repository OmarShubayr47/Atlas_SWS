"""Phase 4: value parsing, template formulas (checked against hand
calculation), rendering, revision storage and the voice tools."""
import json
import math

import pytest

from schematic import render, store, templates, values as V
from schematic.values import BadValue
from tools import registry, safety, view


# --- values ------------------------------------------------------------------

@pytest.mark.parametrize("text,unit,expected", [
    ("4.7k", "Ω", 4700), ("4k7", "Ω", 4700), ("4.7 kΩ", "Ω", 4700),
    ("4.7 kilo ohm", "Ω", 4700), ("1 meg", "Ω", 1e6), ("2R2", "Ω", 2.2),
    ("100n", "F", 1e-7), ("0.1uF", "F", 1e-7), ("100 nano farads", "F", 1e-7),
    ("5V", "V", 5), ("20mA", "A", 0.02), ("20 milliamps", "A", 0.02),
    ("4,7k", "Ω", 4700), ("4,700", "Ω", 4700), ("1kHz", "Hz", 1000), (11, "", 11),
])
def test_parse(text, unit, expected):
    assert V.parse(text, unit) == pytest.approx(expected)


@pytest.mark.parametrize("text,unit", [("5V", "Ω"), ("20mA", "V"), ("abc", "Ω"), ("", "V")])
def test_parse_refuses(text, unit):
    with pytest.raises(BadValue):
        V.parse(text, unit)


def test_format_and_series():
    assert V.fmt(4700, "Ω") == "4.7 kΩ"
    assert V.fmt(0.00034, "A") == "340 µA"
    assert V.fmt(1591.5, "Hz") == "1.59 kHz"
    assert V.nearest(4600) == 4700 and V.nearest(19410) == 20000
    assert V.next_higher(301) == 330 and V.next_higher(300) == 300
    assert V.next_lower(325) == 300
    assert V.nearest(4780, "E96") == 4750


# --- formulas (hand-checked) ------------------------------------------------------

def compute(name, inputs):
    t = templates.get(name)
    vals, assumptions = templates.resolve(t, inputs)
    return t.compute(vals, assumptions)


def test_divider():
    r = compute("voltage_divider", {"Vin": "5 V", "R1": "10k", "R2": "4.7k"})
    assert r.values["Vout"] == pytest.approx(5 * 4.7 / 14.7)        # 1.599 V
    assert dict(r.derived)["Vout"] == "1.6 V" and not r.assumptions


def test_divider_from_target_snaps_to_e24():
    r = compute("voltage_divider", {"Vin": "5 V", "Vout": "3.3 V"})
    assert r.values["R2"] == 20000                                 # ideal 19.4k
    assert r.values["Vout"] == pytest.approx(5 * 20 / 30)          # 3.333 V
    assert any("R1 = 10 kΩ" in a for a in r.assumptions)


def test_led_defaults_are_assumptions():
    r = compute("led_resistor", {"Vs": "5 V"})
    assert r.values["R"] == 300 and r.values["I"] == pytest.approx(0.01)
    assert len(r.assumptions) == 2                                 # If and Vf
    with pytest.raises(BadValue):
        compute("led_resistor", {"Vs": "1.5 V"})                   # below Vf


def test_rc_filters():
    low = compute("rc_lowpass", {"R": "1k", "C": "100n"})
    assert low.values["fc"] == pytest.approx(1 / (2 * math.pi * 1e3 * 1e-7))
    high = compute("rc_highpass", {"fc": "1 kHz", "C": "100n"})
    assert high.values["R"] == 1600
    assert high.values["fc"] == pytest.approx(994.7, abs=0.1)
    with pytest.raises(BadValue):
        compute("rc_lowpass", {"R": "1k"})                          # only one of three


def test_opamps():
    assert compute("opamp_noninverting", {"gain": "11", "Rg": "1k"}).values["Rf"] == 10000
    with pytest.raises(BadValue):
        compute("opamp_noninverting", {"gain": "1", "Rg": "1k"})
    assert compute("opamp_inverting", {"Rf": "100k", "Rin": "10k"}).values["gain"] == -10


def test_npn_switch():
    r = compute("npn_switch", {"Vcc": "12 V", "Ic": "80 mA"})
    assert r.values["Rb"] == 300                                   # 325 -> next lower E24
    assert r.values["Ib"] == pytest.approx(2.6 / 300)
    assert any("MOSFET" in n for n in r.notes)                     # Ib > 5 mA
    assert any("flyback" in n for n in r.notes)
    small = compute("npn_switch", {"Vcc": "5 V", "Ic": "20 mA", "load": "lamp"})
    assert not any("MOSFET" in n for n in small.notes)


def test_pullup_and_param_errors():
    assert compute("button_pullup", {"pin": "GPIO22"}).values["pin"] == "GPIO22"
    with pytest.raises(BadValue):
        compute("voltage_divider", {"Vin": "5 V", "Rx": "1k"})      # unknown name
    with pytest.raises(BadValue):
        compute("voltage_divider", {"R2": "1k"})                    # Vin missing


@pytest.mark.parametrize("name", list(templates.TEMPLATES))
def test_every_template_renders(name):
    defaults = {"voltage_divider": {"Vin": "5", "R2": "1k"}, "led_resistor": {"Vs": "5"},
                "rc_lowpass": {"R": "1k", "C": "1u"}, "rc_highpass": {"R": "1k", "C": "1u"},
                "opamp_noninverting": {"Rf": "10k", "Rg": "1k"},
                "opamp_inverting": {"Rf": "10k", "Rin": "1k"},
                "npn_switch": {"Vcc": "5", "Ic": "20m"}, "button_pullup": {}}
    t = templates.get(name)
    vals, assumptions = templates.resolve(t, defaults[name])
    svg = render.render(t, t.compute(vals, assumptions), t.title)
    assert svg.startswith(b"<svg") and t.title.encode() in svg
    assert b"Liberation Sans" in svg


# --- storage and tools ---------------------------------------------------------------

def test_store_revisions_never_overwrite(tmp_path):
    spec = {"template": "led_resistor", "title": "LED for 5 V", "inputs": {}}
    p1, n1 = store.save(tmp_path, spec, b"<svg/>")
    p2, n2 = store.save(tmp_path, spec, b"<svg>2</svg>")
    assert (n1, n2) == (1, 2) and p1.read_bytes() == b"<svg/>"
    assert store.latest(tmp_path, "led for 5 v")[0]["revision"] == 2
    assert store.latest(tmp_path, "5_V")[0]["revision"] == 2         # partial
    assert store.latest(tmp_path, "")[1] == p2                       # newest
    assert store.latest(tmp_path, "nope") is None


@pytest.fixture
def workspace_root(tmp_path, monkeypatch):
    monkeypatch.setattr(safety, "WORKSPACE_ROOT", (tmp_path / "ws").resolve())
    seen = []
    monkeypatch.setattr(view.ui_events, "publish",
                        lambda event_type, **f: seen.append({"type": event_type, **f}))
    return tmp_path / "ws", seen


def test_voice_tools_create_and_modify(workspace_root):
    root, events = workspace_root
    out = registry.dispatch("create_schematic", json.dumps(
        {"template": "voltage_divider", "values": {"Vin": "5 V", "R2": "4.7k"},
         "title": "Sensor divider"}))
    assert "Vout 1.6 V" in out and "Assumed: R1 = 10 kΩ" in out
    folder = root / "schematics" / "Sensor_divider"
    assert (folder / "r1.svg").is_file() and (folder / "r1.json").is_file()
    assert events[-1]["kind"] == "image" and events[-1]["invert"] is True

    out = registry.dispatch("modify_schematic", {"name": "", "values": {"r2": "10k"}})
    assert "revision 2" in out and "Vout 2.5 V" in out
    spec = json.loads((folder / "r2.json").read_text())
    assert spec["inputs"]["R2"] == "10k" and (folder / "r1.svg").is_file()

    assert view.friendly_name(folder / "r2.svg") == "Sensor divider — revision 2"
    from tools import workspace
    listing = workspace.show_workspace("schematics")
    assert "r2.svg" in listing and "r1.svg" not in listing          # newest only
    assert events[-1]["items"][0]["name"] == "Sensor divider — revision 2"

    assert "Unknown template" in registry.dispatch(
        "create_schematic", {"template": "flux_capacitor", "values": {}})
    assert "is in V, not Ω" in registry.dispatch(
        "create_schematic", {"template": "voltage_divider", "values": {"Vin": "5", "R2": "5V"}})
