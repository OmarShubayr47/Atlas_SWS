# SWS assembled prototype — corrected base

Date: 2026-10-10 (Asia/Riyadh). Status: **Designed CAD assembly; static interference check passed; physical fit unverified**.

Owner requested assembly of the existing enclosure and control prototypes with the corrected base. Codex-pc assembled the existing solids in Onshape without changing either source Part Studio or Feature Studio. Read-only delegated review checked the instance count, placement assumptions and limits of the evidence.

## Live model and sources

- Document: `Test Pi`, workspace `Main`.
- Assembly: [SWS assembled prototype - corrected base](https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/9c422f5d3ebeb2f67e4b2f27). This was the previously empty `Assembly 1` tab.
- Prototype source: [SWS enclosure + knob prototype](https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/8d015e88aea66245a409c790), Feature Studio 1; repo snapshot `mechanical/sws_enclosure_prototype.fs`.
- Actual base source: [Pi 5 base - corrected mounting posts](https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/7b4d3d159734797cdebf903c), Feature Studio 2.

The prototype source remains at lid offset0, mounts shown, reconstructed base reference hidden. The assembly inserts the **actual corrected-base source part**, not the reconstructed reference. The prototype source has 11 solids; the assembly has 12 instances. Changes to the source geometry or parameters require review of the assembly datums and another interference check.

## Instances and layout

| Main assembly — nine instances | Placement |
|---|---|
| Pi 5 base - corrected 58 x 49 mm posts | Centred inside the sleeve, plate underside at z0, posts facing upward |
| SWS sleeve | Source pose; height50 |
| SWS lid with integral mounting posts | Source pose; underside z50, top z52 |
| Encoder cradle | Source pose below encoder at (−28, −12) |
| PTT cradle | Source pose below PTT at (0, −12) |
| Power cradle | Source pose below power at (28, −10) |
| Reset A cradle | Source pose below reset at (28, −22) |
| Printed reset cap | Source seated pose, fixed for presentation |
| EC11 D-shaft knob | Centred over encoder; nominal socket entrance/underside z60.5 |

Three test articles remain separate beside the enclosure: the spare reset B access guide, its cradle and the D-shaft fit coupon. The spare guide/cradle remain together at their source positions near x104; the coupon retains its source position. They are not joined to the enclosure or included in its physical parts stack.

The actual switches, encoder body/shaft, wires, fasteners, Pi, HAT and cooler are absent from this assembly. Open PTT/power apertures therefore do not show the actual button caps.

## Constraints and datums

All values are millimetres. Six explicit mate connectors, four Fastened mates and two Groups are saved: **12 mate features**. No instance Fix flags remain.

| Feature | Definition |
|---|---|
| Mate connector 1 | Owned by corrected base, created at its instance source origin; Move X45.25, Y29.20, Z0 to the plate underside centre |
| Mate connector 2 | Assembly origin connector, referenced to Origin Z axis; no Move |
| Fastened 1 | Base centre connector1 to assembly connector2; centred base pose |
| Mate connector 3 | Owned by knob, source-origin Move X70, Y0, Z0; socket entrance centre |
| Mate connector 4 | Owned by lid, source-origin Move X−28, Y−12, Z60.5; nominal knob entrance target |
| Group 1 | Corrected base, sleeve, lid, all four main cradles and reset cap: eight members, preserving the aligned poses |
| Fastened 2 | Knob connector3 to lid connector4 |
| Group 2 | Spare reset B guide and its cradle |
| Mate connector 5 / Fastened 3 | Spare guide source-origin connector to assembly connector2 |
| Mate connector 6 / Fastened 4 | Coupon source-origin connector to assembly connector2 |

The corrected-base outline is 0..90.5 × 0..58.4 in its source, so centring corresponds to the expected translation (−45.25, −29.20, 0). The shell-hidden view confirms the plate below the controls and posts facing upward; the bottom view confirms the base inside the sleeve outline.

The origin connector2 displays negative primary Z. Fastened3 and Fastened4 required the primary-axis flip to retain the spare module/coupon's upright source orientation. Initial temporary Fix flags caused warnings about multiple fixed parts and combining fixed parts with an origin mate; replacing them with these mates cleared the warning indicators. Final visible instance/mate tooltip titles contained no warning/error indicators.

Groups and Fastened mates are static CAD positioning constraints. They do not design a physical joint or simulate the cap's actuation, encoder rotation or push travel. The base still requires actual retention/fastening.

## Nominal knob height

The installed knob position is a drawing-based trial pose, not a measured hardware fit. With lid underside Z50 and encoder seat drop5:

- Rear bearing seat: 50 − 5 = z45.
- Assumed encoder front face: 45 + recorded body depth4.5 = z49.5.
- Recorded shaft length20 gives nominal tip z69.5.
- Knob socket ceiling is 9 above its underside, giving underside z60.5 and top z74.5.
- Nominal underside-to-lid-top gap is 8.5; maximum recorded push travel0.8 would leave 7.7 before other effects.

For this assumed seating datum and full nominal socket insertion, **knob underside = Z − encoder seat drop + 15.5**. Connector4 is an explicit numerical datum; it is not automatically linked to feature parameters. Update it if enclosure height, lid offset, encoder seat depth, socket depth or the confirmed shaft/housing relationship changes. The actual shoulder, seating datum, flat orientation, socket engagement and retention still require confirmation.

## Verification and limits

- All 12 instances inserted and saved; main parts aligned, separate test articles retained beside them.
- Native Onshape interference detection on the entire saved assembly: **No interferences**. Include standard content and Show top level only were both unchecked; there is no standard content/subassembly in this model.
- Corrected base inspected with the sleeve hidden and from below with sleeve restored. Current nominal outlines provide 0.20 mm base/sleeve clearance; the earlier FeatureScript reference check measured that gap. The assembly check confirms absence of solid penetration, not a new minimum-distance measurement.
- Whole assembly visibility restored, connectors hidden and isometric view restored at the end.
- Repository formatting checked with `git diff --check`; no source/runtime tests are applicable to this documentation and assembly-only change.

Local proof images are in `C:/Users/pc/.codex/visualizations/2026/10/10/01a123ec-18a7-7892-9e00-2948d22e6c0b/`: `sws-assembled-corrected-base.jpg`, `sws-assembly-internals.jpg`, `sws-assembly-base-underside.jpg` and `sws-assembly-interference-check.jpg`. These local images are not synchronized by Git; the live assembly and this record are the shared reference.

No physical fit, travel, wiring, load, thermal or hardware test was performed. No printing/fabrication was performed or authorized. Static clearance checks exclude absent component housings, terminals, wires and electronics, and do not establish assembly/disassembly access.

## Exact next action

Obtain actual control housing/terminal/encoder shoulder measurements and identify TS365ZJ height. Adjust trial seats/pockets, add positive housing/tab keepers and inward reset-cap retention, and confirm no switch preload/full travel. Select fasteners and wire routing/strain relief; design base retention and review Pi/HAT/cooler/port integration. For speakers, establish outlet, bearing/mounting and wire-exit features, then design positive retention and review cooling. Recheck the assembly after those geometry changes, then perform owner-authorised physical fit testing when components are available. T-005 remains in progress for those tasks.

## 2026-10-10 speaker-grille revision

Feature Studio 1 and the prototype source were subsequently updated with paired upper acoustic grilles for the owner's35 ×25 ×6.2 mm speakers, plus two central cooling vents. This supersedes the original lid vent pattern shown in the earlier proof images. The existing assembly updated automatically; all12 instances and12 mate features retain their placements. Actual corrected-base source and assembly mates were unchanged. Native interference detection on the complete updated assembly again reports **No interferences**.

The saved prototype source remains offset0 / mounts shown / base reference hidden, now with speaker grilles enabled and optional speaker envelopes hidden. It still has11 solids; the two temporary reference boxes are not assembly instances. Separate FeatureScript checks of those boxes against lip, cradles and base reference passed. Live source matches the repo snapshot. `mechanical/SWS_SPEAKER_MOUNTS.md` records dimensions, pattern, checks, reduced free ventilation and remaining outlet/retention/wiring/thermal work. Speakers are not physically mounted by the grille slots.

New local proofs: `sws-speaker-grilles-top.jpg`, `sws-speaker-grilles-assembled.jpg`, `sws-speaker-clearance-check.jpg`, `sws-speaker-assembly-check.jpg` in the same visualization directory. Whole visibility and isometric view restored. No physical test or fabrication performed.

## 2026-10-11 speaker-shelf and Pi-port revision

Feature Studio 1 now adds speaker shelves integral with the sleeve, low locating walls, underside support ribs and rightward wire relief. Owner explicitly kept the two upper corners and both wire pairs routing to the right-side PCB pads. The speaker reference boxes now sit at zH−6.6…H−0.4, fixed to the sleeve when the lid is displayed exploded. The assembled0.4 face gap is a trial allowance. See `mechanical/SWS_SPEAKER_MOUNTS.md`.

The sleeve now has trial windows for right-side USB/Ethernet, front USB-C/dual micro-HDMI and left microSD/onboard-power-button access. Official Pi 5 geometry is registered to the default PCB underside seat z7; the seat parameter changes only window heights. See `mechanical/SWS_PORT_OPENINGS.md` for sizes and physical limitations.

The source remains11 solids at saved offset0 / mounts shown / base reference and speaker boxes hidden / grilles, shelves and ports enabled. Live454-line source copied back matches the repository. The assembly updates automatically and retains all12 instances and12 mate features; actual corrected-base source and mates were unchanged. Native interference detection selected the complete assembly, with Include standard content and Show top level only unchecked, and reports **No interferences**. This includes the newly integral shelves and the corrected base; actual Pi/HAT/cooler, speakers, controls, plugs and wires remain absent. Separate kernel housing-envelope checks passed at offsets0 and10.

Local proofs: `sws-speaker-shelves-internals.jpg`, `sws-speaker-shelf-underside.jpg`, `sws-pi-port-openings-assembled.jpg` and `sws-shelves-ports-assembly-check.jpg`. Whole assembly visibility and isometric view restored. No physical fit, load, acoustic, thermal, wiring or fabrication test performed. Confirm the actual electronics stack, cable plugs and speaker bearing/exit geometry, design positive keepers/base fastening/strain relief, then update and recheck the assembly before owner-authorised physical testing.
