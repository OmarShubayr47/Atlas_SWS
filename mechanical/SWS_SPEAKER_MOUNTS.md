# SWS lid speaker grilles and clearance envelopes

Updated: 2026-10-11 (Asia/Riyadh). Status: **Designed prototype; CAD checks passed; physical fit unverified**. Owner: codex-pc, T-005. The 2026-10-11 revision below supersedes the earlier envelope height and absence of supports.

The owner uses two speakers from [AliExpress item 1005006494531366](https://ar.aliexpress.com/item/1005006494531366.html?gatewayAdapt=glo2ara#nav-specification) and requested lid slots at top left/right, above the controls. The owner supplied **35 × 25 mm** and subsequently **6.2 mm depth** in this session. These are owner-provided housing dimensions, not measurements or drawing dimensions independently verified by the agent. Protrusions, sound-outlet registration, mounting features and wire exits remain unspecified.

The listing was not inspected: web retrieval failed, a focused item-ID search returned no results, and browser navigation was rejected by site-safety policy. No alternate browser/domain route was attempted. Existing records identify the 3525/2535 cavity-box family; family codes alone were not used to establish dimensions, impedance or rating. No electrical architecture or BOM variant was changed.

## 2026-10-10 grille geometry and checks

Source: `mechanical/sws_enclosure_prototype.fs`, synchronized with live Feature Studio 1 in Onshape `Test Pi`. +Y is the upper/vent edge confirmed by the owner. Lid outline94.9 ×62.8 mm, thickness2, outer R4.2; seating-lip inner outline87.3 ×55.2 mm, inner R0.4. Existing controls and cradles retain their positions.

| Feature | Dimensions / coordinates, mm |
|---|---|
| Left speaker reference | Centre(−23.5,13.5); x−41…−6, y1…26 |
| Right speaker reference | Centre(23.5,13.5); x6…41, y1…26 |
| Speaker depth reference | 6.2 below lid underside Z; zZ−6.2…Z |
| Each acoustic grille | Five horizontal rounded slots, each27 ×2.4, R1.0, 4 mm row pitch |
| Acoustic slot bounds | Left x−37…−10; right x10…37; overall y4.3…22.7 |
| Central cooling vents | Two rounded3 ×16, R1.0, centred(−3,15) and(3,15); y7…23 |

The acoustic slots cut through the 2 mm lid. They are a trial grille layout within each housing footprint, **not housing-through cutouts or a manufacturer-specified outlet**. Exact outlet alignment may require revising the pattern when the speaker face is available. Slot web thickness is1.60 mm; reference housing borders are4.0 mm at the sides and3.3 mm at top/bottom. R1.0 avoids the zero-length straight sides that the rounded-prism helper would create at a radius equal to half the slot height.

Two options were added: `Paired speaker grilles - owner 35 x 25 footprint` defaults true; `Show speaker clearance envelopes - 35 x 25 x 6.2` defaults false. The boxes are clearance references, not detailed speaker models or printable holders. With grilles disabled, the original nine rectangular3 ×16 vents return and no speaker boxes are created. Envelopes are checked before deletion when their display is disabled.

## Clearance and assembly verification

- Onshape Feature Studio Commit/regeneration succeeded. Saved instance: lid offset0, mounts shown, reference base hidden, paired grilles enabled, speaker boxes hidden; 11 prototype parts.
- Visible-envelope previews regenerated13 parts at offsets0 and10. Kernel checks found no solid interference between the two boxes and the sleeve/lid/main cradles, between the boxes, or against the centred base reference. Intended contact with the lid underside is allowed. Original-nine-vent fallback regenerated11 parts; previews were cancelled and the saved settings restored.
- At the saved nominal geometry, boxes leave2.65 mm to the lip inner X boundary and1.60 mm to its upper Y boundary. The left box is1.00 mm above the encoder-cradle projection; the right box is4.00 mm above the power-cradle projection. The installed knob projection ends at y−2, leaving3 mm to the boxes. These are nominal geometry calculations without mounting stock or tolerances.
- With Z50, box bottoms are z43.8 and the base posts end at z7, leaving36.8 mm vertically. This excludes the absent Pi/HAT/cooler and does not establish electronics clearance.
- The existing [SWS assembled prototype - corrected base](https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/9c422f5d3ebeb2f67e4b2f27) updated automatically, retaining12 instances and12 mate features. Native whole-assembly interference detection reports **No interferences**. Actual speakers and hidden reference boxes are not assembly instances; their separate envelope checks are described above. Base source and assembly mates were unchanged.
- Live source copied back from Feature Studio 1 matches the repository snapshot after newline normalization. Read-only delegated review checked bounds, slot radii, nominal clearances and airflow limits. `git diff --check` checks repository formatting.

Local proof images are in `C:/Users/pc/.codex/visualizations/2026/10/10/01a123ec-18a7-7892-9e00-2948d22e6c0b/`: `sws-speaker-grilles-top.jpg`, `sws-speaker-grilles-assembled.jpg`, `sws-speaker-clearance-check.jpg` and `sws-speaker-assembly-check.jpg`. They are not synchronized by Git; the live model and this record are shared references.

## Cooling and remaining mechanical work

The ten acoustic slots provide approximately639.42 mm² of geometric opening. Speaker boxes behind them occupy those footprints, so these openings must not be counted as free cooling vents. The two central rounded vents provide approximately94.28 mm², compared with432 mm² from the former nine rectangular vents. Airflow and temperature with the final Pi/HAT/cooler, wiring and speaker installation remain untested; additional ventilation may be required.

Prior 2026-10-10 state: no speaker pockets, keepers, screw bosses or wire holes had been added. The 2026-10-11 shelves below supersede that absence of supports. Positive retention remains **Under Evaluation** pending actual frame bearing surfaces, mounting features, outlet and wire-exit information. A holder must bear on the housing/frame and keep the diaphragm/outlet clear. The reference boxes have no fitting allowance and cannot establish tolerance, print fit, speaker retention, acoustics, load strength or wire bend clearance.

No print, fabrication, physical fit, acoustic, thermal or hardware test was performed. T-005 remains in progress.

## 2026-10-11 speaker shelves and rightward wiring

The owner supplied a PCB layout image showing the speaker outputs on the right, the same side as Pi USB/Ethernet, and explicitly confirmed **keep the two upper corners; route both wire pairs right**. The image establishes that routing intent, not component heights or a measured mechanical registration. The grille centres and control layout remain unchanged.

Feature Studio 1 now adds two shelves integral with the sleeve, so no separate shelf parts or assembly mates are needed. Each speaker is inserted from above with the lid removed. These trial seats and low walls locate the nominal housing; they do not establish positive retention against lifting, shock or vibration.

| Current geometry | Dimensions / coordinates, mm |
|---|---|
| Housing envelope | 35 ×25 ×6.2; centres x±23.5, y13.5 |
| Housing height | zH−6.6…H−0.4; H is sleeve height, independent of lid display offset |
| Assembled face gap | 0.4 below lid underside; nominal seat zH−6.6 |
| Shelf floor | Width38; y0.7…29.5; zH−8.6…H−6.6; 2 thick, R0.6 |
| Side walls and upper stop | Side thickness1.2, height3.2 above seat; side clearance0.3 per side; upper clearance0.3 |
| Local lower stop | 6 wide at the inner end of each shelf; lower clearance0.3; avoids the encoder cradle |
| Rightward floor notch | xcx+15…cx+19.2, y10.5…16.5; open through floor toward +X |
| Underside support ribs | Two per shelf at cx±10; 2 wide, approximately6 deep |
| Rib wire relief | Open-bottom corridor y10.5…16.5, 6 wide ×4 high through each rib; 2.1 stock remains above |

The shelf extends to the upper sleeve wall and joins it with 0.1 nominal overlap. A tongue connects each local lower stop into the floor. The rightward notch allows leads to descend beneath the seat; the rib reliefs leave space for the left wire pair to continue toward the right-side PCB pads. Actual wire diameter, insulation, bend radius, exit location, strain relief and clearance past the HAT remain unverified. These are open routing clearances, not a fully retained wire channel.

The first shelf revision compiled but failed Part Studio regeneration with a non-manifold Boolean: side walls and the upper stop touched only along an edge above the floor. Extending the side walls to y26.4 and spanning the stop across the full floor width provides real overlap and resolves that failure.

**Current CAD evidence:** default saved offset0 / mounts shown / base reference hidden / grilles, shelves and port windows enabled / speaker envelopes hidden regenerates11 parts. Visible-envelope configurations at offsets0 and10 regenerate13 parts. Kernel checks report no solid penetration of the housing boxes into the sleeve/shelves, lid, control cradles or base reference; intended shelf contact is allowed. Base/sleeve minimum gap remains0.20 and power/reset cradle gap0.60. Live454-line Feature Studio source copied back equals the repo source after newline normalization. Native complete-assembly detection reports **No interferences**, with12 instances and12 mate features unchanged.

At H50, speaker seat is z43.4, floor bottom41.4 and rib bottom35.4. The Pi/HAT/cooler and actual speakers/wires are absent from the assembly. These heights and checks do not prove electronics-stack clearance, housing bearing suitability, printed strength, acoustics or thermal performance. The left shelf floor retains0.7 nominal plan gap to the encoder-cradle projection. The existing acoustic/free-vent area calculation above is unchanged; shelves and installed electronics require thermal testing.

The new **Speaker support shelves - trial fit** option defaults true. Shelves are created only while paired grilles are enabled. Speaker boxes remain fixed to the sleeve when the lid is shown exploded. Pi access windows are recorded separately in `mechanical/SWS_PORT_OPENINGS.md`.

Local proofs in the visualization directory above: `sws-speaker-shelves-internals.jpg`, `sws-speaker-shelf-underside.jpg`, `sws-pi-port-openings-assembled.jpg`, `sws-shelves-ports-assembly-check.jpg`. No physical test or fabrication performed.

## Exact next action

Obtain the speaker face/outlet location, bearing/mounting features, protrusions and wire-exit envelope. Confirm the trial shelf bearing and routing, then design positive retention and strain relief. Establish the Pi/HAT/cooler stack and cable-plug envelopes, add base fastening and repeat CAD checks. Confirm fit, outlet alignment, retention, strength and temperature with actual components and an owner-authorised print.
