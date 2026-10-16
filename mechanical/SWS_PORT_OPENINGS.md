# SWS enclosure Pi 5 port access openings

Date: 2026-10-11 (Asia/Riyadh). Status: **Designed prototype; live FeatureScript regenerated; physical connector and cable fit unverified**. Owner: codex-pc, T-005.

The owner requested access for HDMI, USB and the other Pi ports in the existing sleeve. The owner also confirmed that both upper-corner speakers must route their wires toward +X, the USB/Ethernet side shown in the PCB image. Speaker shelves and wire relief are recorded separately in `SWS_SPEAKER_MOUNTS.md`; the image does not establish connector or PCB dimensions.

## Source evidence and registration

Primary references are the official Raspberry Pi [Pi 5 mechanical drawing, RP-008347-DS-1](https://pip-assets.raspberrypi.com/categories/892-raspberry-pi-5/documents/RP-008347-DS-1-raspberry-pi-5-mechanical-drawing.pdf) and [Pi 5 STEP geometry archive, RP-010083-CA-1](https://pip-assets.raspberrypi.com/categories/892-raspberry-pi-5/documents/RP-010083-CA-1-rpi-5%203D%20STEP%20-%20No%20Graphics%20small%20file.zip), retrieved on 2026-10-11. The archive contains `rpi-5b_no_graphics.step` and its license. Its STEP header identifies a FreeCAD/Open CASCADE export dated 2026-05-27. These reference files are not measurements of the owner's board.

The drawing gives an 85 × 56 mm PCB with Ø2.7 primary mounting holes at PCB coordinates (3.5,3.5), (61.5,3.5), (3.5,52.5) and (61.5,52.5). The existing corrected base uses a 2 mm plate and 5 mm posts, giving a nominal **PCB underside seat at z7 mm**. Translation by x−42.5 and y−28 registers these holes to the existing base posts at (−39,−24.5), (19,−24.5), (−39,24.5) and (19,24.5).

The STEP PCB lowerface is z0.03 and its upperface is z1.306. Setting the model's lowerface on z7 therefore requires z+6.97. Its modeled PCB thickness, 1.276 mm, is reference geometry rather than a verified physical board thickness. Assembly placements were traversed through the STEP hierarchy; connector front-face boundary vertices and the onboard power actuator's circle supplied the bounds below. Full component bounds include leads and mounting lugs, which were not treated as mating-face heights.

The drawing treats its dimensions as approximate, subject to tolerances and change, and unsuitable as production data. It also omits some components and calls for checking the physical board. The STEP and drawing have small nominal datum differences: the lower USB stack centre is y29.0 in STEP versus y29.1 in the drawing, and Ethernet is y10.25 versus y10.2. The prototype uses the STEP geometry with explicit access allowances; it does not resolve manufacturing tolerances.

## Nominal connector references

All coordinates are in enclosure millimetres with PCB underside seated at z7. +X is the right USB/Ethernet side; −Y is the USB-C/HDMI edge; −X is the microSD/onboard-power side.

| Reference | Nominal transformed geometry |
|---|---|
| Lower USB stack frontface | x45.50; y−6.250…8.250; z8.876…24.496 |
| Upper USB stack frontface | x45.28; y11.750…26.250; z8.881…24.331 |
| Ethernet frontface | x45.55; y−25.535…−9.965; z8.486…21.426 |
| USB-C frontface | y−29.20; x−35.77…−26.83; z8.406…11.566 |
| Micro-HDMI at PCB x25.8 | y−29.630; x−20.084…−13.316; z8.271…11.440 |
| Micro-HDMI at PCB x39.2 | y−29.630; x−6.684…0.084; z8.271…11.440 |
| Pi onboard power actuator | x−42.95; centre y−9.6, z10.006; circular frontface Ø1.8 |
| MicroSD socket body, including mouth region | x−40.25…−28.85; y−5.89…6.06; z5.55…6.97 |

The microSD socket is below the PCB and inset from its left edge. Its body bounds do not establish card insertion/removal travel or finger clearance. The onboard power actuator is recessed from the sleeve's outer left face by approximately 4.5 mm. Its access is separate from the lid's main power control.

## Implemented sleeve openings

Source: `sws_enclosure_prototype.fs`, synchronized with Feature Studio 1 in Onshape `Test Pi`. `Pi port access windows - trial plug fit` defaults true. Each opening is a rounded rectangle with **R0.8 mm** corners cut through the 2 mm sleeve wall. These are proposed prototype access openings, not manufacturer panel cutouts.

| Sleeve face / opening | Horizontal centre | Z centre | Width × height | Default bounds |
|---|---|---|---|---|
| Right, lower USB stack | y1 | 16.69 | 16.5 × 18 | y−7.25…9.25; z7.69…25.69 |
| Right, upper USB stack | y19 | 16.69 | 16.5 × 18 | y10.75…27.25; z7.69…25.69 |
| Right, Ethernet | y−17.75 | 14.96 | 17.6 × 15 | y−26.55…−8.95; z7.46…22.46 |
| Front, USB-C | x−31.3 | 10 | 12 × 8 | x−37.3…−25.3; z6…14 |
| Front, both micro-HDMI ports | x−10 | 10 | 26 × 8 | x−23…3; z6…14 |
| Left, shared microSD/onboard-power service access | y−1.5 | 9 | 23 × 10 | y−13…10; z4…14 |

Widths in the table run along Y on right/left faces and along X on the front. The shared HDMI opening avoids a thin web between adjacent plug mouldings. The right-side openings retain nominal webs of 1.50 mm between USB windows and 1.70 mm between Ethernet and the lower USB window. Actual cable housings, latch access, printed strength and access through these recesses remain untested.

`Pi PCB underside seat - match base posts` (`piSeat`) defaults **7 mm**, with an allowed 5–12 mm parameter range. The code computes `dz = piSeat − 7` and shifts **only the port windows vertically** by this amount. It does not alter the corrected base posts, move a Pi/HAT/cooler or change any electronics model. A different value must match the actual chosen mounting stack; changing this parameter alone does not create that stack.

The sleeve's outer right face is x47.45 and its front face is y−31.4. Nominal connector fronts are approximately 1.8–2.2 mm behind these faces, so cable mouldings and seating depth matter in addition to connector metal dimensions. Rounded window corners also reduce clearance locally. No print or cable insertion test establishes fit yet.

## Scope and verification

Internal GPIO, MIPI and PCIe ribbon connections do not automatically require exterior wall holes. Their cables need a defined route before adding further openings. The HAT DC-input connector location and envelope remain unresolved; no geometry has been invented for it.

The live FeatureScript compiled/regenerated with the new openings and saved **11 prototype parts**. A copy of the live source matched the repository source after newline normalization. The default PCB seat remains z7. This records source/regeneration verification only; the updated whole-assembly interference result is recorded by the main continuation in `SWS_ASSEMBLY.md` and the T-005 handoff. No actual Pi, HAT, cooler, connector, cable, speaker or printed enclosure was tested.

Reference values and opening choices are also recorded in the small machine-readable `pi5-port-reference.json`. The downloaded official files and extraction script remain in the local visualization directory and are not repository binaries.

## Exact next action

Confirm the installed Pi's underside seat and the Pi/HAT/cooler stack; identify the HAT DC-input connector and cable route. Check actual USB, Ethernet, USB-C and micro-HDMI plugs for full insertion, moulding clearance and latch access, and confirm microSD removal/onboard-button reach. Revise the prototype openings as required before an owner-authorised print or fabrication, then verify physical fit and strength.
