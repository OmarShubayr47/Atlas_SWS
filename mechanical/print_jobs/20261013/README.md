# T-006 print preparation — 13 October 2026

Current geometry: TWO horizontal insertion sticks in ONE vertical column, 61 pitch / 60 reach, complete-case carrier. Source `../../sws_rack_enclosure_carrier.fs` matches the live Onshape editor. This package contains 13 separate structural parts; no rack/enclosure reference solids or test coupon are included.

## Files and checks

- `centred_stl/rack_01.stl` through `rack_13.stl`: the print files. One translated part each, centred at 128/128 on its individual A1 plate, bed Z0. Rotation and scale unchanged from the native export.
- `stl/`: native Onshape fine binary mm export of the same 13 parts, with descriptive part names, in the source's checked print orientations. Original export coordinates are spread on a display grid; do not print them as a single build plate. (Left out of the public Atlas_SWS copy, since `centred_stl/` holds the same geometry.)
- `mesh_checks.json`: source/translated SHA256, dimensions and triangle counts; 13 finite/closed edge-topology meshes, all individual dimensions within 240 mm, passed.
- The downloaded ZIP `SWS-rack-two-stacked-sticks-20261013.zip` is kept locally only; ZIP files are excluded by the repository's ignore rule. STLs and manifests are Git-synchronized.
- Mesh utility: `mechanical/tools/check_rack_stls.py` (standard-library Python). Run from repository root with `python mechanical/tools/check_rack_stls.py`.

| Part | Quantity | Print orientation / bounds, mm |
|---|---:|---|
| 01 platform | 1 | Flat underside down, 120 x 90 x 10.5 including stops |
| 02 central spine | 1 | Broad side down, 13.6 x 134 x 4.2 |
| 03/04 arms | 1 each | Broad side down, 90 x 134 x 8 |
| 05 keeper | 1 | Broad face down, 18 x 81 x 3 |
| 06-09 spacers | 4 | Upright, 10 x 10 x 54; consider brim |
| 10 front clamp | 1 | Wide top face down, 120 x 15 x 8 including feet |
| 11 rear clamp | 1 | Wide top face down, 120 x 13 x 8 |
| 12/13 insertion sticks | 1 each | Broad side down, 71.8 x 20 x 4.2 |

Bambu A1 and PLA selected by owner. Nozzle 0.4 and Generic PLA are provisional configuration assumptions. Proposed first-slice settings: 0.20 layers, 6 walls, 100% rectilinear infill, parts individually. A 40% gyroid profile is an alternate proposal, not validated for the 2 kg design target. Do not reorient the sticks upright. Small transverse platform holes in the side-printed arms still need slicer/physical inspection.

## Slicer status

Installed Bambu Studio observed: 02.07.01.62. Isolated preparation utility `mechanical/tools/prepare_bambu_profiles.py` reads only static official vendor profiles and resolves inheritance/G-code includes; it never reads user/printer account data. Profile preparation initially encountered Windows access denied during Program Files path resolution; an escalated retry was requested. At this record's initial write, profile generation and Bambu CLI slicing were pending. No successful slice is claimed from CAD or mesh checks. Subsequent result must be appended here before describing this package as slicer-verified.

No printer command, printing or fabrication was performed. Geometry/mesh checks do not establish actual printed strength, fit, thermal behaviour or load capacity. See the [mechanical record](../../SWS_RACK_CARRIER.md) for the full hardware/empty-fit/inert-load procedure. 2 kg is an untested total-load design target. Verify actual nozzle/filament/bed, clearances and secure retention before owner-authorised print/installation.

## Subsequent result and enclosure-preservation update

The escalated static-profile preparation retry returned "aborted by user after 1188.6 s", with no exit code/success output; no generated profiles were observed. It was not an automatic-approval-review rejection. No Bambu CLI slice was completed; slicing remains unverified. Utility syntax compilation passed. The CAD/closed-mesh/bounds checks above remain valid; use the oriented separate STLs and verify in the owner's A1/PLA slicer before fabrication.

Owner subsequently required the original button/speaker/air openings be preserved. Actual enclosure source is unchanged. Display-only reference pockets were added to the rack preview; the 13 structural STL geometries/rotations remain unchanged. Current rack source (346 lines) matches the live editor.

The subsequent 0.6-to-2 mm upper-border correction changes only the metal-rack reference plates (excluded from exports); all 13 printable STL geometries and their previous mesh checks remain unchanged. Source is 347 lines; actual rack/printed strength and slicer validation remain open.
