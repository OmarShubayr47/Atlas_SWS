"""Prepare isolated, full Bambu Studio CLI profiles from installed vendor data.

Reads only the static Program Files BBL profiles, never user/printer credentials.
The CLI requires full settings: resolve both `inherits` and G-code `include`
templates before export. Proposed settings are not hardware/strength approval.
Outputs are confined to mechanical/print_jobs/20261013/profiles/.

Reference: https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path


VENDOR_ROOT = Path("C:/Program Files/Bambu Studio/resources/profiles/BBL")
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "print_jobs/20261013/profiles"
MACHINE = "Bambu Lab A1 0.4 nozzle"
PROCESS = "0.20mm Standard @BBL A1"
FILAMENT = "Generic PLA @BBL A1"
TEMPLATE_METADATA = {"name", "type", "from", "inherits", "include", "instantiation", "setting_id"}


class VendorProfiles:
    def __init__(self):
        self.root = VENDOR_ROOT.resolve(strict=True)
        self.sources = {}
        self.cache = {}

    def flatten(self, kind, name, active=()):
        if kind not in {"machine", "process", "filament"}:
            raise ValueError(f"Unsupported profile kind: {kind}")
        if not isinstance(name, str) or not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise ValueError("Profile reference must be a local vendor profile name")
        path = (self.root / kind / f"{name}.json").resolve(strict=True)
        path.relative_to(self.root)
        if path in active:
            raise ValueError(f"Profile inheritance/include cycle: {path.name}")
        if path in self.cache:
            return copy.deepcopy(self.cache[path])

        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError(f"Vendor profile is not an object: {path.name}")
        self.sources[str(path.relative_to(self.root)).replace("\\", "/")] = hashlib.sha256(raw).hexdigest()
        chain = active + (path,)
        merged = {}
        if data.get("inherits"):
            merged.update(self.flatten(kind, data["inherits"], chain))
        includes = data.get("include", [])
        if not isinstance(includes, list):
            raise ValueError(f"Vendor include is not a list: {path.name}")
        for included_name in includes:
            template = self.flatten(kind, included_name, chain)
            # Templates supply settings/G-code, not identity or preset metadata.
            merged.update({key: value for key, value in template.items() if key not in TEMPLATE_METADATA})
        merged.update({key: value for key, value in data.items() if key != "include"})
        self.cache[path] = copy.deepcopy(merged)
        return merged


def proposed_process(base, density, pattern, label):
    profile = copy.deepcopy(base)
    profile.update({
        "name": f"SWS Proposed 0.20mm 6 walls {label} @BBL A1",
        "from": "User",
        "inherits": PROCESS,
        "instantiation": "true",
        "layer_height": "0.2",
        "wall_loops": "6",
        "sparse_infill_density": density,
        "sparse_infill_pattern": pattern,
        "description": "Proposed SWS rack prototype settings; fit, strength, PLA creep and load capacity unverified.",
    })
    profile.pop("setting_id", None)
    return profile


def validate(machine, filament, profiles):
    if machine.get("name") != MACHINE or machine.get("nozzle_diameter") != ["0.4"]:
        raise ValueError("Expected installed A1 0.4 mm machine profile")
    if machine.get("printable_area") != ["0x0", "256x0", "256x256", "0x256"]:
        raise ValueError("Unexpected A1 printable area; review vendor profile before export")
    if str(machine.get("printable_height")) != "256":
        raise ValueError("Unexpected A1 printable height")
    for field in ("machine_start_gcode", "machine_end_gcode", "change_filament_gcode"):
        if not isinstance(machine.get(field), str) or not machine[field].strip():
            raise ValueError(f"Missing resolved A1 G-code template: {field}")
    if filament.get("name") != FILAMENT or filament.get("filament_type") != ["PLA"]:
        raise ValueError("Expected installed Generic PLA A1 profile")
    for profile in profiles:
        if profile.get("layer_height") != "0.2" or profile.get("wall_loops") != "6":
            raise ValueError("Proposed layer-height/wall overrides failed")
        if MACHINE not in profile.get("compatible_printers", []):
            raise ValueError("Process is not marked compatible with A1 0.4")
    if profiles[0].get("sparse_infill_density") != "40%" or profiles[0].get("sparse_infill_pattern") != "gyroid":
        raise ValueError("Proposed 40% gyroid overrides failed")
    if profiles[1].get("sparse_infill_density") != "100%" or profiles[1].get("sparse_infill_pattern") != "rectilinear":
        raise ValueError("Proposed solid first-slice overrides failed")


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Parse the written output again; never report success for malformed JSON.
    if json.loads(path.read_text(encoding="utf-8")) != data:
        raise ValueError(f"Profile output failed round-trip: {path.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bambu-version", default="not supplied", help="Observed installed executable version for provenance")
    args = parser.parse_args()
    vendor = VendorProfiles()
    machine = vendor.flatten("machine", MACHINE)
    process = vendor.flatten("process", PROCESS)
    filament = vendor.flatten("filament", FILAMENT)
    gyroid = proposed_process(process, "40%", "gyroid", "40pct gyroid")
    # Rectilinear is used for 100% infill; 40% gyroid is the alternate proposal.
    # Without explicit per-part settings, use this solid profile for all parts in
    # the conservative first slice so hanger/keeper/pins are not sliced sparsely.
    solid = proposed_process(process, "100%", "rectilinear", "100pct solid")
    validate(machine, filament, [gyroid, solid])
    outputs = {
        "a1_04_machine_full.json": machine,
        "generic_pla_a1_filament_full.json": filament,
        "sws_020_6walls_40gyroid_proposed.json": gyroid,
        "sws_020_6walls_100solid_proposed.json": solid,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        path = OUTPUT_ROOT / name
        write_json(path, data)
        print(f"Prepared {path}: {len(data)} keys")
    manifest = {
        "date": "2026-10-13",
        "timezone": "Asia/Riyadh",
        "status": "Proposed settings; slice/physical print and load checks required",
        "observed_bambu_studio_version": args.bambu_version,
        "vendor_root": str(vendor.root),
        "cli_reference": "https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage",
        "source_sha256": dict(sorted(vendor.sources.items())),
        "output_sha256": {name: hashlib.sha256((OUTPUT_ROOT / name).read_bytes()).hexdigest() for name in outputs},
        "first_slice_process": "sws_020_6walls_100solid_proposed.json",
        "alternative_process": "sws_020_6walls_40gyroid_proposed.json",
        "proposed_overrides": {"layer_height": "0.2", "wall_loops": "6"},
        "first_slice_scope": "100% rectilinear infill for all parts; no per-part settings are encoded by this utility",
        "assumptions": ["A1 with 0.4 mm nozzle", "Generic PLA until actual filament is identified"],
        "limits": "Presets do not verify actual nozzle, filament, bed type, print orientation, fit, strength, creep or load capacity. No printer command is sent.",
    }
    write_json(OUTPUT_ROOT / "profile_manifest.json", manifest)
    print(f"Validated {len(outputs)} full profiles and manifest; {len(vendor.sources)} static vendor sources")


if __name__ == "__main__":
    main()
