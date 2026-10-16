# SWS complete-enclosure rack carrier

Updated: 2026-10-13 (Asia/Riyadh), T-006, codex-pc. **Designed prototype; nominal CAD and mesh checks passed. Physical fit, printed strength and load capacity remain Under Evaluation.**

The latest owner instruction is to carry the complete SWS case, Pi 5, cooler, HAT, controls and two speakers. The rack has ONE vertical column of two slots. Exactly two horizontal insertion sticks are stacked vertically on the same centreline; there is no requirement for side-by-side rack holes. This supersedes the bare-Pi/sliding-base experiments and the pending clarification record of 12 October. Printer/material: owner selected Bambu A1 and PLA.

## Live design and sources

- [SWS rack shelf - Pi and enclosure](https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/f900d3c6b9a067747d351fc8).
- [Pi rack carrier - temporary source](https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/2917103e6e442aee150600d9), feature type `SWS complete enclosure rack`, identifier `piRackCarrier` preserved.
- Current source: `mechanical/sws_rack_enclosure_carrier.fs`. The former `sws_pi_rack_carrier.fs` is explicitly marked Superseded and preserves an experimental Pi-base/sliding-shelf variant; it is not live.
- Existing T-005 enclosure, corrected Pi base and detailed enclosure assembly are preserved. This rack studio uses external enclosure/control envelopes, not the actual electronics or detailed assembly.

## Dimensions and load path

All values in mm. +Y points into the rack; Z0 is platform underside.

| Feature | Current default / provenance |
|---|---|
| Rack slots | Owner: 5 wide x24.8 vertical, clear edge gap36.2; derived pitch61 |
| Slot arrangement | One column, X0; insertion reference centres Z26/87 |
| Opposed faces | Owner described matching holes on the opposite side |
| Span | Owner51.3 interpreted as outside opposing-face span; datums still unconfirmed |
| Rack references | Assumed2 mm sheet and capsule ends; width/profile/interior unknown |
| Two insertion sticks | Both X0, horizontal inY, centres Z26/87; 4.2 wide x10 high bar section |
| Reach | 60 fromY34 to tipY94; overall stick71.8 including bolted root |
| Retaining holes | AxisX, diameter3, centreY90.5; centre inset3.5 gives2 material from rim to tip |
| Stick roots | Uniform4.2 thickness, root20 high,1.5 fillets; .2 trial clearance in central-spine windows |
| Platform | 120 x90 x8, R4 corners, four front/rear stops plus four lateral stops2.5 high |
| Arm pair | Two separate8 mm thick triangular arms, printed flat onYZ faces; transverse M4 joints |
| Platform-to-arm screws | Four4.4 clearance holes,9 diameter flush-head recesses; arms have flat open-sided nut seats |
| Rear keeper | 18 wide x3 thick; two4.8 x10.6 openings at sameX0/Z26,87 |
| Clamps | Front/rear120 mm bars,6 thick with integral2 mm feet; four10 OD x54 spacers,4.4 through bores |
| Payload reference | Enclosure94.9 x62.8 x52 at X0/Y-14/Z8; separate knob/control envelopes |

The arms bolt to the two independent stick roots and central spine. The shelf bolts onto the arms. Four low side stops prevent sideways escape; two removable top clamps contact the lid perimeter at X+/-42.5, leaving nominal controls/grilles/vents clear. Clamp columns stand outside the case at X+/-55, Y-50/20. Their physical plug-boot clearance, bearing pads and tightening load still need checking. Do not overtighten against the thin printed lid. Existing base retention/control/speaker keepers remain open T-005 items; rack clamps do not validate those internal joints.

The insertion position is centred in the slots; it does not remain suspended at that height without seating. In the assumed capsule slots the4.2 x10 bars can settle approximately6.26 before their lower corners bear. Loaded seating, actual end shape and any internal folds must be checked on the real rack. Root clearance is0.2 inY/Z; X is established by the clamped arm/stick/spine stack, so assemble with bolts loose first and validate the printed stack. Two retained metal pins through the tip holes keep the rear keeper captured; their end retention/head geometry must be selected and checked. The drawing3 mm hole does not establish a fit for a nominal3 mm bolt/pin. Use a separate upright restraint through the spine anchors as a secondary restraint. Hardware is absent from collision checks.

## Estimated mass and provisional design load

These are conservative planning allocations, not measured component specifications:

| Item | Allocation, g |
|---|---:|
| Pi 5 | 55 |
| Cooler | 35 |
| HAT | 50 |
| Controls | 20 |
| Two speakers | 30 |
| Wires and enclosure fasteners | 25 |
| Printed case, lid, base, supports and knob | 90 |
| **Estimated system payload** | **305** |
| **Payload allowance** | **500** |

The case-plastic estimate derives from approximately67.5 cm3 of current CAD plastic, allocating90 g. Current carrier solid-volume estimate is212 g without the optional fit piece (222 g with it), using1.24 g/cm3 from the official [Bambu PLA Basic TDS](https://store.bblcdn.com/s7/default/b189de92249a4b9ebed28b8ea1f080f0/Bambu_PLA_Basic_Technical_Data_Sheet.pdf). Density is a planning assumption for the owner's unspecified PLA; slice supports and hardware change mass.

**Total rack-load DESIGN TARGET: 2 kg including carrier and payload. This is not a verified/rated capacity or an established safety factor.** It allows for uncertainty beyond the approximately0.3 kg contents and approximately0.21 kg solid carrier. A geometry-only static screen gives about0.95 N.m at2 kg with centreY-14 relative to rack faceY34.2, or1.56 N.m at the front case edge. A20 mm-wide unperforated8 mm shelf strip with37.35 mm side overhang gives approximately3.44 MPa under the entire2 kg off-centre load; this ignores holes/recesses, contact, layer bonding, stress concentrations, creep and temperature and does not establish strength. Physical centred and off-centre proof tests are required.

Proposed hardware for review, not purchased or fit-tested: three M4x30 transverse joints; front platform bolts approximatelyM4x20 and rear approximatelyM4x40; four approximatelyM4x80 clamp bolts; compatible washers/locking nuts; two retained metal pins fitting the3 mm trial holes; independent upright restraint. Flat nut-seat underhead paths are9.3 mm(front) and26.6 mm(rear) before washers/nuts/thread projection. Verify actual hardware/head/capture clearances and lengths before assembly.

## Print preparation and verification

Owner printer/material: A1, PLA. Official [A1 specification](https://us.store.bambulab.com/products/a1) gives256 x256 x256 build space. Each part is independently checked within240 mm bounds. The print-layout grid is an export/display layout, NOT a single A1 build plate.

13 structural parts: platform, spine, two arms, keeper, four spacers, two clamps and two insertion sticks. Optional empty fit coupon is separate and disabled in the saved assembled view so it cannot be mistaken for a third attachment stick.

- Platform: flat underside on bed; local stops grow upward.
- Spine, two arms and BOTH sticks: their broad side faces on bed. Bar length/bending lies in layer planes.
- Keeper: broad face on bed. Clamps: wide top face down, feet upward. Spacers: upright.
- `Print layout` removes all7 reference bodies and applies/checks rotations. All parts begin atZ0.
- Proposed first slice:0.20 layers,6 walls,100% rectilinear infill.40% gyroid is an alternate profile, not approved for the rack load target. A0.4 nozzle and Generic PLA profile are assumptions until actual nozzle/filament are checked.

Live source Commit/regeneration and full editor copy-back matched exactly (347 lines). Default assembled view has20 parts (13 structural +7 reference); print layout has13, optional coupon adds one. Collision guards test printed parts against enclosure/controls/rack and one another, allowing intended contact. No hardware, full insertion motion, actual electronics or elastic deflection is checked. These checks apply to the current61/51.3/4.2 default; the full parameter space is not verified.

Fine binary mm STLs were exported individually through Onshape to `mechanical/print_jobs/20261013/stl/`. `mechanical/tools/check_rack_stls.py` confirms13 closed edge-topology meshes, finite vertices, bed-levelZ0 and maximum individual footprint90 x134 or120 x90 (spacers54 tall). It only translates each STL to the centre of its individual256 mm plate; original rotations and scale are preserved in `centred_stl/`. `mesh_checks.json` records bounds, triangle counts and hashes. Slicer result is recorded separately in the print-job README/handoff; CAD/mesh success alone is not physical printability verification.

Proof screenshots are local in the current Codex visualization directory: `sws-rack-two-stacked-sticks.jpg` and `sws-rack-two-sticks-print-layout.jpg`.

## Exact next physical action

After owner-authorised printing, first test an empty insertion stick through both actual faces, then the two-stick empty carrier, rear keeper, retained pins and independent restraint. Verify60 reach/61 pitch, internal clearance, loaded seating, hardware access and all capture points. Use inert weights over a catch surface; increase load gradually to the intended total load, check centred/off-centre loading, permanent deformation, joint movement and creep before adding electronics. Confirm real assembled mass, plug access, cable strain relief and warm operating conditions. PLA temperature/long-term creep and daily retention need review; no load rating is established by this record. No fabrication or physical test has been performed by Codex.


## Preserved enclosure openings — owner reminder, 2026-10-13

ActualT-005 enclosure source remains unchanged at2d5a114: PTT12.8 x12.8, power10.4 diameter, encoder6.5 diameter, reset guide6.6 diameter; each speaker grille five27 x2.4 rounded slots, plus two3 x16 central cooling vents, same original positions. Two35 x25 x6.2 speaker supports and all trial Pi port windows are preserved. The rack preview now mirrors those lid openings as DISPLAY-ONLY shallow reference pockets after the full-envelope collision guards run; it is still not the actual detailed case. No structural rack or enclosure print geometry changed, so the previously checked13 STL exports remain applicable. Final source347 lines matches live editor.

## Upper reference-plate edge revision — 2026-10-13

Owner highlighted the0.6 mm stock above a rounded slot and requested+1.4 to leave2 mm. That thin strip belongs to the displayed metal-rack face references: former topZ100 minus upper capsule tipZ99.4. Reference tops now follow26 +pitch +12.4 +2, givingZ101.4 at pitch61 and2 mm stock at any pitch. Sheet depth remains the assumed2 mm. Both reference parts are clearly labelled REFERENCE ONLY / not print parts. This does not alter or strengthen the actual iron rack.

Printable keeper already has4.7 mm above its rectangular slot; central-spine upper window has2.8 mm stock. Their geometry and all13 structural STL files are unchanged. Default20-part live regeneration passed;347-line full editor copy-back matches repo. References were temporarily isolated for inspection then full view restored. No physical/load/slicer verification added. Local proof:`sws-rack-reference-2mm-top-edge.jpg` in current Codex visualization directory.
