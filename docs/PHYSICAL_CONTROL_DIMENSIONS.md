# Smart Working Station — Physical Control Dimensions

Date: 2026-10-10 (Asia/Riyadh)

All dimensions are in millimetres. Source: the owner's supplied 2026-10-09 design handoff from component PDFs, reproduced in the 2026-10-10 chat. The PDFs have not been re-inspected for this file. These are recorded drawing dimensions, not measurements of actual components.

**2026-10-10 follow-up:** the original handoff tables below are preserved. Codex subsequently inspected rendered local PDFs: PTT p1, Power p1, reset p1 (drawing) and p5 (travel), Encoder p2–3 (dimensions/mounting) and extracted its p1–2 specification text. New drawing findings and clarifications are listed below; no actual component was measured.

## PTT — K6-6271D04

Source path supplied by owner: `C:/Users/pc/Downloads/PTT.pdf`.

| Feature | Dimension |
|---|---|
| Square cap | 12.2 × 12.2; ±0.2 on cap size |
| Cap top to housing bottom | 11.9 ±0.3 |
| Lead extension below housing | Approximately 3.3–3.7 |

## Power — TM-001-D1-03

Source path supplied by owner: `C:/Users/pc/Downloads/Power.pdf`.

| Feature | Dimension |
|---|---|
| Outer cap/rim diameter | Ø9.8 ±0.1 |
| Raised face diameter | Ø8.2 ±0.1 |
| Housing bottom to rim top | 8.3 ±0.2 |
| LED lead extension | 5.6 ±0.2 |

## Restart — TS365ZJ

Source path supplied by owner: `C:/Users/pc/Downloads/reset.pdf`.

| Feature | Dimension |
|---|---|
| Body width | 7.3 ±0.3 |
| Terminal span | 8.3 ±0.3 |
| Actuator section | Approximately 2.9/3.0 × 1.5; confirm the drawing's two width references before modelling |
| Actuation travel | 0.25 ±0.10 |
| Listed height variants | 4.3, 4.5, 5, 6, 7, or 8 |

**Actual switch height variant: unknown.** Measure or identify it before finalising the enclosure support and actuator clearance. Body width and terminal span are not panel cutout dimensions.

## Encoder and push switch — ALPS EC11E18244AU

Source path supplied by owner: `C:/Users/pc/Downloads/Encoder.pdf`.

| Feature | Dimension |
|---|---|
| Shaft diameter | Ø6 |
| D-shaft flat-to-opposite-tangent dimension | 4.5 |
| Shaft length from front housing face | 20 |
| Body face dimensions | 11.7 × 12 |
| Body depth | 4.5 |
| Push travel | 0.5 ±0.3 |

No threaded panel-mount nut is shown in the recorded drawing findings. A mechanical support is needed. Shaft tolerances, knob dimensions and knob retention details are not supplied.

## Proposed enclosure openings — fit allowances

These are prototype design choices, not manufacturer-specified panel cutouts or physically verified fits.

| Control | Proposed opening |
|---|---|
| PTT | 12.8 × 12.8 square |
| Power cap | Ø10.4 |
| Encoder shaft | Ø6.5 |
| Restart | Ø6.6 proposed printed-plunger guide; actual height variant and support remain unresolved |

### Calculated clearance before print error

For centred parts, clearance per side is half the difference between opening size and part size. The calculations below assume the CAD opening prints exactly to size; printed error and misalignment reduce the available clearance.

| Control | Nominal clearance per side | At largest recorded part size |
|---|---|---|
| PTT cap | (12.8 − 12.2) / 2 = 0.30 | (12.8 − 12.4) / 2 = 0.20 |
| Power outer rim | (10.4 − 9.8) / 2 = 0.30 | (10.4 − 9.9) / 2 = 0.25 |
| Encoder shaft | (6.5 − 6.0) / 2 = 0.25 | Unknown: shaft tolerance not supplied |

The power opening is larger than the entire rim. It does not retain the switch; an internal support must do that. The encoder shaft opening also does not retain its body.

## First modelling pass

Status: **Designed prototype** in Onshape; physical fit remains unverified. Internal supports are still open. See the existing-model audit below; the following is the general modelling sequence, not a request to recreate the existing model.

1. Establish the enclosure/panel outline and which face carries the controls. Use actual enclosure geometry or explicitly proposed prototype dimensions.
2. Create separate parameters for `ptt_opening = 12.8`, `power_opening = 10.4`, and `encoder_opening = 6.5`. Keep control spacing and panel thickness separate from component dimensions.
3. Sketch only these three openings initially. Leave restart geometry unresolved rather than selecting a height variant.
4. Design supports that transfer press forces from the component housing into the enclosure. Capture the encoder body against rotation as well as axial movement. Do not rely on soldered wires or switch terminals as structural members.
5. Resolve support depth from panel thickness, desired cap exposure, actual housing geometry and actuator motion. The supplied overall heights alone do not establish a usable mounting ledge or support footprint.
6. Include the encoder's recorded maximum push travel of 0.8 and restart's maximum travel of 0.35 in the motion check. Neither travel is a prescribed resting gap. Ensure the panel/knob/actuator does not preload the switches or prevent full movement.
7. Check lead space, insulated solder joints, wire bends and strain relief. Lead extensions alone do not specify the full wiring clearance.

## Required physical checks before final enclosure

- Measure actual cap, shaft, housing and lead envelopes; identify TS365ZJ height and clarify its actuator width references.
- Confirm the encoder knob's fit, retention, diameter and clearance during push travel.
- Check a small fit coupon using the selected print process and intended panel thickness before committing to a full enclosure print; printing remains a separate owner-authorised action.
- Check free button movement and repeated encoder rotation/push with supported housings and strain-relieved wiring.
- Record measured dimensions and fit results in `docs/decisions_pi5.md`; update this sheet with their provenance.

Continuing work: `coordination/tasks/T-005-control-panel.md`. Projector stand work remains in T-003.

## PDF re-inspection findings — 2026-10-10

- **Restart:** the table on reset p1 resolves the two actuator widths: A = 3.0 for H = 4.3, 4.5 or 5; A = 2.9 for H = 6, 7 or 8. The orthogonal actuator dimension is 1.5 ±0.1. The actual purchased H is still unknown. Travel 0.25 ±0.10 appears on p5.
- **Encoder:** Encoder p2 specifies shaft Ø6 with tolerance +0/−0.05, and flat-to-opposite-tangent 4.5 with +0/−0.1. Thus the proposed Ø6.5 opening has 0.25 mm radial clearance at the largest specified shaft diameter, before print error. The flat section is 10 mm long; the existing knob socket is 9 mm deep. Check its entrance/shoulder interaction and full push travel on real hardware.
- **Encoder mounting pattern:** Encoder p3 shows mounting tabs at 12.5 ±0.05 mm centre spacing; slot dimensions are 1.5 (+0.1/0) × 2.6 (+0.1/0). Five electrical terminal holes are Ø1 (+0.1/0); D/E are spaced 5 mm on a row 7 mm from the tab row, A/C/B span 5 mm on the opposite row 7.5 mm away. View is explicitly from the mounting side: do not mirror it accidentally. These are carrier-board hole dimensions, not panel openings or a ready-made printed-body pocket.
- **PTT and power:** reviewed cap/rim dimensions match the supplied handoff. Both drawings show through-hole terminals and cap-over-housing construction. Neither drawing supplies a complete dimensioned housing pocket suitable for claiming a snug printed retainer. Do not obtain missing housing dimensions by scaling the drawing image.

The first **Proposed** support route was a small rigid carrier under each control. Adjustable cradle prototypes have since been added in the latest revision below; positive housing/tab keepers and physical fit remain open.

## Existing Onshape model audit and change — 2026-10-10

Document title displayed by Onshape: **Test Pi**. Part Studio: **SWS enclosure + knob prototype**, with four parts; it is not four separate Part Studios.

- Part Studio URL: https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/8d015e88aea66245a409c790
- Feature Studio 1 URL: https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/81ef44886bc683ad50e48164
- Source saved after the change: `mechanical/sws_enclosure_prototype.fs` (FeatureScript 3083).
- Existing sleeve: 94.9 × 62.8, 2 mm walls; lid: 2 mm thick with a 3 mm lip. Current height parameter is 50 mm from base underside to lid underside in assembled position.
- Original control centres before the later layout revision below: PTT (−28, −12), encoder (0, −12), power (28, −12), relative to model origin. The original openings already matched the proposed handoff values.
- Existing knob: Ø20 × 14, 9 mm deep D socket with 0.2 mm diametral allowance. Existing separate coupon contains 6.1/6.2/6.3 mm D bores. These are prototype fit choices, not Verified dimensions of printed parts.
- Change: added `lidOffset` display parameter, default 10 mm, allowed 0–30 mm. Zero shows the lid seated at the sleeve top. Part names now reflect lid offset and knob diameter.
- Verification: Onshape Commit succeeded; default 10 mm regenerated with four parts, then 0 mm was accepted and showed a seated lid with four parts. Current saved instance is at 0 mm. No physical assembly, support or hardware fit was tested.
- Still open: switch supports, restart recess, sleeve port cutouts, base retention, enclosure fastening, actual HAT/cooler/cable clearances and ventilation performance. Earlier source comments call the base tested; this session did not independently verify that base.

## Rounded enclosure and base fit audit — 2026-10-10

Owner requested smoother enclosure edges aligned with the base and a base-fit check. Status: **Designed prototype; CAD checks passed**. No physical fit was Tested.

The original base sketch and corrected-base Feature Studio 2 were inspected. Both specify a 90.5 × 58.4 outline with R2 corners and a 2 mm plate. The corrected source adds four Ø2.5 posts extending 5 mm above the plate, at centres (−39, −24.5), (−39, 24.5), (19, −24.5), (19, 24.5) after centring the outline. The original base studios were preserved.

| Contour | Overall dimensions | Corner radius | CAD allowance |
|---|---|---|---|
| Centred base reference | 90.5 × 58.4 | 2.0 | Reference reconstructed from inspected CAD |
| Sleeve cavity | 90.9 × 58.8 | 2.2 | 0.20 per side around base |
| Sleeve/lid outside | 94.9 × 62.8 | 4.2 | 2.00 sleeve wall |
| Lid lip outside | 90.3 × 58.2 | 1.9 | 0.30 per side inside cavity |
| Lid lip inside | 87.3 × 55.2 | 0.4 | 1.50 lip wall |

All these rounded outlines share corner centres at x = ±43.25, y = ±27.20, so the stated clearances and wall thicknesses also hold around the curved corners. A 0.6 mm fillet rounds the lid's top exterior perimeter; the underside seating face and control openings retain their geometry.

Feature Studio 1 reconstructs a temporary centred corrected-base reference, checks collision against sleeve and lid, and measures base-to-sleeve distance. The optional **Show centred base fit reference** checkbox retains one additional part for inspection (a fifth part in this rounded revision, sixth after adding the reset cap below); it is not a linked copy of the base studio. Update the reference if the base changes.

**Observed Onshape result:** no collision; minimum sleeve gap 0.19999999999999057 mm (0.20 mm within numerical precision). Assembled offset 0 and exploded offset 10 mm regenerated successfully. Enabling the reference produced five parts; cancelling the preview restored the saved 0 mm / reference-hidden instance with four parts. At the current 50 mm height, post tops at z7 are 40 mm below the lip bottom at z47. This checks these CAD envelopes only, not installed electronics or wiring.

**Fit conclusion:** the centred base can enter the sleeve in nominal CAD. The sleeve is open underneath and has no retaining shoulder, clips or fasteners, so it does not yet hold the base. The 0.20 mm print allowance remains unverified. Next integration action: design base retention/fastening while preserving the insertion clearance, then check an owner-authorised printed fit. No fabrication was performed or approved here.

## Owner control layout and reset cap — 2026-10-10

Owner requested encoder at bottom left, PTT in the middle, power at bottom right and reset below power. Owner confirmed vents remain above controls, and preferred a printed cap for the small reset switch if feasible. Top view uses +Y toward the vents and −Y toward the lower control edge. This revision supersedes the original control centres above.

| Control | Centre (x, y) | Proposed opening |
|---|---|---|
| Encoder | (−28, −12) | Ø6.5 shaft |
| PTT | (0, −12) | 12.8 × 12.8 |
| Power | (28, −10) | Ø10.4 cap |
| Reset | (28, −22) | Ø6.6 guide for printed Ø6 stem |

The reset cap is a new separate solid shown seated in the guide. **Designed prototype:** Ø6 stem, Ø8.5 × 1 flange, 4 mm overall height and 0.5 mm top-edge fillet. The stem overlaps the flange by 0.1 mm. With the flange top at lid underside Z, the cap top is Z+3; the 2 mm lid leaves 1 mm projection. The flange underside is Z−1, the proposed contact face for the switch actuator. No switch height variant or carrier depth was assumed, and no reset carrier was added.

Calculated nominal clearances: stem-to-guide radial gap 0.30 mm; flange overlap beyond guide 0.95 mm; flange-to-lip gap 1.35 mm (1.05 after 0.30 lateral play); power-to-reset aperture web 3.50 mm. Maximum recorded reset travel 0.35 mm leaves 0.65 mm cap projection. The 0.5 mm top fillet remains above the lid at that travel. The Ø20 encoder knob clears PTT by 11.60 mm and the lip inner boundary by at least 5.60 mm. Vents stay above all controls. These checks cover nominal apertures/cap/knob envelopes, not switch housings or future carriers.

**Required before functional use:** identify actual TS365ZJ H; design an aligned carrier with contact height that avoids preload and supports pressing loads; retain the cap against inward escape; check tilt, sliding friction, spring return, full travel and housing/wiring clearances on physical parts. The flange prevents outward escape through the lid, but the switch/carrier is still needed underneath. These CAD choices do not establish physical fit or authorize printing.

That layout revision had five parts: sleeve, lid, encoder knob, reset cap and fit coupon. Source was synchronized in `mechanical/sws_enclosure_prototype.fs`; assembled offset 0 and exploded offset 10 previews regenerated. Base check reported no collision and 0.20 mm minimum sleeve gap. Screenshot: `sws-four-control-layout.jpg` in the current Codex visualization workspace. The latest mounting revision below supersedes this part count.

## Removable cradles and separate reset B — 2026-10-10

Owner requested square locating pockets with round wire exits and a spare reset option separate from the enclosure. Owner confirmed a **recessed-hole test module** for that spare, alongside the existing printed-cap option A. Status: **Designed prototypes; CAD checks passed; physical fit/retention unverified**.

Feature Studio 1 now generates four separate main control cradles and lid-mounted posts. Each cradle has a 1.6 mm housing-bearing seat, a 3 mm high rectangular pocket wall, an open wiring chamber and a second 1.6 mm plate with a round wire exit. The seat and lower plate are joined by side columns. The clear chamber height is 6.4 mm. Small terminal reliefs pass through the upper seat; the central round exit passes through the lower plate only, preserving the housing-bearing surface. Insulated solder joints, wire bends, a grommet and strain relief are not modelled or validated.

Intended pressing load path: **housing → upper seat → cradle columns/fasteners → lid posts → lid**. Soldered wires and terminals must not be structural supports. The two mounting holes per cradle are Ø2.4 clearance with matching Ø1.8 blind post pilots, a trial 2 mm screw scheme. Actual fastener type, length, head clearance, pilot fit and printed strength remain unselected/unverified. There is no positive housing keeper or encoder-tab clamp yet: pockets locate bodies and seats support downward loads, but the components could lift out. Final keepers require confirmed housing/contact geometry.

| Prototype | Trial pocket (x × y) | Seat below lid/guide underside | Cradle plate footprint | Mount centre spacing |
|---|---|---|---|---|
| PTT | 8.6 × 8.6 | 8.0 | 26 × 16 | 20 |
| Power | 8.4 × 8.4 | 6.0 | 24 × 14 | 18 |
| Encoder | 12.3 × 12.6 | 5.0 | 28 × 24 | 22 |
| Reset A | 9.2 × 4.8 | 9.1 | 24 × 9 | 19 |
| Spare reset B | 9.2 × 4.8 | 8.5 | 24 × 9 | 19 |

All pocket, seat and wire-exit values are independently editable feature parameters. Round wire exits default to Ø6, adjustable Ø3–7. **PTT/power pocket dimensions and all seat depths are trial design choices, not dimensions established by the PDFs or physical measurement.** The encoder pocket gives 0.30 mm per side against the recorded 11.7 × 12 body, before print error; tab slots are trial 1.8 × 2.9. Check the encoder's front shoulder/shaft section against the Ø6.5 panel opening, and the knob through the full 0.8 mm push travel.

Reset A seat drop 9.1 is a trial setup based on the largest listed H8 plus the cap underside offset1 and a nominal 0.1 contact gap; it **does not select the actual switch variant**. Reset B guide-to-seat drop8.5 similarly gives a nominal 0.5 recess for H8. Actual H, actuator registration, preload, contact gap and inward cap retention remain unresolved.

**Spare reset B:** two independent solids, positioned away from the enclosure at x104. A 24 × 16 × 2 rounded guide has a Ø4 recessed tool-access hole and two underside mounting posts; its separate cradle uses the same trial reset pocket/terminal reliefs and round wire exit. Neither solid is joined to the main lid, sleeve or reset A cap. This allows comparison of the printed-cap option and recessed access without changing the main lid.

Additional drawing findings from rendered pages, used only for trial terminal reliefs:

- PTT PCB pattern has six Ø1.2 holes. Outer switch rows span 5.1 ±0.1 in x and 5.0 ±0.1 in y; middle LED holes span 5.7 ±0.1. Reliefs are Ø1.8; do not reverse the two x spans. Drawing also shows a separate small locating-hole reference not used by this prototype.
- Power PCB pattern has six Ø1.0 holes, outer row span4.5 ±0.1, middle LED span5.4 ±0.1 and outer row separation6.5 ±0.1. Reliefs are Ø1.6.
- Reset p1 adds cover depth3.6 ±0.2 and side/base depth reference4.2 ±0.2. These, body width7.3 ±0.3 and terminal span8.3 ±0.3 are distinct envelopes. Trial reliefs use shell row span7 and signal row span5, separated2.5, with Ø1.8 shell / Ø1.6 signal reliefs.

Pattern orientation and origin registration to actual housings/actuators still need confirmation. These relief holes are mechanical clearances, not electrical pin assignments or soldering instructions. No missing housing dimensions were estimated from image scale.

**CAD verification:** Onshape Commit and regeneration succeeded: 11 parts with main mounts shown and base reference hidden; 12 with the base reference visible; seven with main mounts hidden. Assembled offset0 and exploded offset10 passed. Saved instance restored to offset0, mounts shown, base reference hidden. `evCollision` guards reject solid interference between cradles, sleeve/lid posts, base reference and spare guide/cradle, while allowing intended seat/post contact. Feature info reports no solid interference, power/reset minimum gap0.5999999999999963 mm (0.60 nominal), and base/sleeve minimum gap0.19999999999999057 mm (0.20 nominal).

Read-only review caught initial post/wall overlaps; mount spacings were widened. An encoder terminal relief tangent to the outer wall caused a non-manifold Boolean failure; additional Y stock removed that tangency, including across the stated encoder pocket-depth bounds. Final kernel regeneration passed at default dimensions; the entire parameter combination space was not tested. Screenshots are in the current Codex visualization workspace.

**Exact next physical/design action:** obtain actual housing, shoulder, actuator and terminal measurements; identify TS365ZJ H; update pockets/seats and add positive housing/tab keepers plus cap inward retention. Select and test fasteners and wire/strain-relief arrangements. Then perform owner-authorised fit/travel/load checks. Base retention, Pi/HAT/cooler/port integration and ventilation remain open. No print, fabrication or hardware test was performed.

## Assembly with the actual corrected base — 2026-10-10

Owner requested all existing CAD parts assembled with the corrected base. Onshape [SWS assembled prototype - corrected base](https://cad.onshape.com/documents/0f32fa900cd7f2bfc7a2c41b/w/de06d0f74d2d731a40355f14/e/9c422f5d3ebeb2f67e4b2f27) now contains 12 instances: nine main assembly parts and three separate test articles. The actual corrected-base source is inserted and centred, posts upward. Lid/supports/reset cap are seated; the knob is above the encoder opening at nominal underside z60.5. The spare reset B guide/cradle and coupon remain beside the enclosure. Feature Studio/Part Studio sources remain unchanged at the saved 11-part prototype state with reference base hidden.

Native whole-assembly interference detection reports **No interferences** among the modelled solids. Base placement was also viewed with the sleeve hidden and from below. The knob pose assumes the encoder rear housing bears on its seat z45, front face z49.5, shaft tip z69.5 and full nominal 9 mm socket insertion; this is not hardware verification. Its datum must be updated when confirmed seating/shaft/socket geometry changes. Static Groups/Fastened mates hold cap and knob for presentation and do not validate movement, retention or real joints. Actual switches/encoder, wiring, fasteners, Pi/HAT/cooler are absent.

See `mechanical/SWS_ASSEMBLY.md` for sources, instance/mate definitions, update instructions, proof images and exact next physical/design action. T-005 remains in progress; no print, fabrication or physical test was performed.

## Speaker supports and Pi access revision — 2026-10-11

The latest source adds sleeve-integral shelves for the owner's35 ×25 ×6.2 speakers at the upper corners, with rightward wire notches and relief beneath the support ribs. Owner confirmed both wire pairs route to the right-side PCB pads. The current speaker envelopes sit0.4 below the assembled lid, fixed to sleeve height when the lid is shown exploded. See `mechanical/SWS_SPEAKER_MOUNTS.md` for current dimensions and retention/strength/thermal limits; this supersedes the prior absence of speaker supports.

Pi port windows are now Designed using official Raspberry Pi 5 geometry and trial plug allowances: right USB/Ethernet, front USB-C and shared dual micro-HDMI, left shared microSD/onboard power-button access. `mechanical/SWS_PORT_OPENINGS.md` records their registration and sizes. The default PCB underside seat is z7 from the existing2 mm base plate/5 mm posts. The new seat parameter shifts window heights only; it does not move the actual base posts or electronics.

Control pockets, seats, terminal reliefs and Ø6 wire exits are unchanged. Default11 parts and13-part visible-speaker-envelope configurations at lid offsets0/10 regenerate without solid penetration; base gap remains0.20 and power/reset cradle gap0.60. The actual corrected-base assembly remains12 instances/12 mate features and reports No interferences. These checks exclude actual Pi/HAT/cooler, component housings, cables and wires. Control keepers, TS365ZJ H, base fastening and physical fit/travel/wiring/thermal validation remain open. No fabrication or hardware test performed.

## Owner encoder coupon fit — 2026-10-13

Owner reports printing the test part and finding the **middle bore the best fit**. The saved Feature Studio1 coupon is labelled left-to-right6.1/6.2/6.3; its middle D-bore has0.20 mm diametral allowance, nominalØ6.2 and4.7 flat-to-opposite-tangent dimension. This is an owner-reported physical coupon result, **Selected**, not a measurement of the shaft. Live production knob instance was inspected and already uses0.20 allowance, so no enclosure source change was needed. The production knob itself, retention, full encoder push travel, seating and surrounding clearances have not been physically tested. Owner also identified A1/PLA for the rack prints; coupon print settings were not independently verified.
