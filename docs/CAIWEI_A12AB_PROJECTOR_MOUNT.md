# CAIWEI A12AB Projector Mount — Sourcing and Preliminary Workshop Concept

Status: **Under Evaluation**  
Last updated: 2026-09-30  
Owner-confirmed projector: **CAIWEI A12AB**

This document records the evidence needed to select a commercial projector
mount and fabricate the supporting steel/aluminum structure. It is not a
fabrication drawing and does not authorize an order or workshop fabrication.

## 1. Confirmed project facts

- The project owner confirmed on 2026-09-30 that the received projector is a
  CAIWEI A12AB. A user-supplied underside photo independently shows the label
  fields **`Model: A12`**, **`Series: AB`**, and **`Version: M`**. This
  supersedes the earlier `model unconfirmed` status.
- The underside photo shows four raised threaded mounting bosses and a
  ceiling-mount instruction pictogram. It also shows a ventilation grille
  close to the lower-right boss. The photo has no dimensional scale, so it
  does not establish hole spacing, thread size, or safe screw depth.
- Actual-project measurement at zoom 100%: throw ratio **1.28–1.36** (about
  1.32), native 1920×1080 panel, and a 32-inch image needs approximately
  **0.91–0.96 m lens-to-table optical distance**.
- Focus at this short distance is still untested and remains the mount
  geometry go/no-go test.
- The requested concept places the projector around **2.00 m above the floor**
  with approximately **0.10–0.20 m horizontal offset/reach**, projecting onto
  the table.

## 2. External product evidence and limitations

The external A12AB listings are inconsistent. CAIWEI's product page is titled
`A12AB` but its specification table calls the model `900DAB`. It lists a net
weight of 9.7 lb (about 4.4 kg), body size 12.64 × 9.92 × 5.12 in (about
321 × 252 × 130 mm), and desktop/ceiling/tripod installation. A separate
seller listing for the A12/900D family states that the bottom has four M4
mounting holes. The real-unit photo confirms four bosses, but **M4 remains an
external claim** until checked with a thread gauge or known screw.

Sources checked 2026-09-30:

- CAIWEI product page: <https://www.caiweiinc.com/products/a12ab-native-1080p-1100-ansi-lumen-outdoor-movie-daylight-projectors/>
- A12AB-family seller listing stating four bottom M4 holes:
  <https://uquid.com/shop/product/caiwei-a12ab-video-projector-android-system-wifi-beamer-7200-lumens-lamp-brightness-home-theater-projector-for-mobile-phone-ships-from-russian-federation-color-900dab-iOVATxejZxpcX>
- CAIWEI contact page: <https://www.caiweiinc.com/contact-us/>
- CAIWEI/EUG small mount listing (3 kg rating):
  <https://www.machineryoffers.com/offer/32041-New-Arrival-360-Degree-Adjustable-Projector-Ceiling-Mount-Stand-Wall-Projector-Bracket-Metal-Mount.html>
- CAIWEI/EUG product catalogue, including the TR01 20 kg stand listing:
  <https://eug.goldsupplier.com/product.html>
- Saudi local 15 kg universal mount listing:
  <https://www.noon.com/saudi-en/ceiling-projector-mount-white/N23033121A/p/>
- Saudi local NCTS CM100180 four-arm, 30 kg listing:
  <https://saudi.microless.com/product/ncts-cm100180-universal-projector-mount-100-180cm-four-adjustable-arms-height-adjustment-retractable-column-quick-release-connector-full-motion-design-up-to-66lbs-30kg-support-ncts-cm100180/>

The A12AB manual describes normal desktop and ceiling projection but does not
explicitly approve operating the chassis with the **lens pointing vertically
down**. Image rotation or `360° inversion` is not evidence that the cooling
system supports every physical orientation. CAIWEI must confirm lens-down
operation before the direct-down design is fabricated or used.

## 3. Commercial mount decision

### Rejected

- **CAIWEI/EUG 230 mm mini aluminum mount:** rated 3 kg. This is below the
  official A12AB-page mass of about 4.4 kg and must not be used.
- **Tray mounts rated 3.5 kg:** also below the external projector mass and
  unsuitable for an overhead public demonstration.
- A single 1/4-inch camera screw or an adhesive attachment is not acceptable
  for this overhead installation.

### Candidate specification

Use a commercial **universal four-arm projector mount head** meeting all of
the following, then attach its upper/base plate to the fabricated stand:

- Safe working load at least **10 kg**; 15 kg or greater preferred.
- Four adjustable arms able to reach the actual A12AB hole pattern.
- M4 projector screws and spacers after the real thread/depth measurement.
- Positive mechanical locks for pitch, roll, and yaw; friction alone is not
  acceptable.
- A quick-release plate is desirable for service, but it must also have a
  locking screw or pin.
- A separate rated safety tether from the projector/chassis to the stand.
- No arm, plate, or spacer may block an intake/exhaust vent or rest on the
  adjustable height foot.

The CAIWEI/EUG catalogue contains a `TR01` stand listing rated 20 kg and older
universal ceiling-bracket listings, but the available pages do not certify
A12AB hole-pattern compatibility or 90° lens-down locking. They are not a
single-item recommendation without written confirmation from CAIWEI. The
locally listed 15 kg Noon mount and 30 kg NCTS four-arm mount are purchase
candidates only after their arm span, supplied M4 hardware, and usable angle
are confirmed.

## 4. Projection geometry

For a 32-inch 16:9 image:

```text
image width  = 0.708 m
image height = 0.398 m
throw ratio  = 1.28–1.36 (measured on the project unit)
required lens-to-table distance = 0.708 × (1.28–1.36)
                                = 0.907–0.963 m
```

Therefore, if the **lens optical center** is exactly 2.00 m above the floor,
the table surface would need to be about **1.04–1.09 m above the floor** to
obtain a 32-inch image at zoom 100%.

If the table is 0.75 m high, a 2.00 m lens height gives 1.25 m throw and an
estimated 41.5–44.2-inch diagonal at zoom 100%. Digital zoom could reduce the
visible image, but it reduces effective resolution and its percentage is not
linear on this unit. Final geometry must therefore be based on the actual
table height and a physical image measurement.

Always dimension from the **lens optical center to the table surface**, not
from the floor to the projector enclosure.

## 5. Recommended workshop structure

The preferred structure is a rigid, braced frame attached to the workstation,
not a light free-standing photography tripod. A two-post portal frame is the
most stable option. If access requires one side to remain open, use a single
post with a triangulated cantilever and bolt it to the workstation frame or a
properly engineered outrigger base.

Preliminary material starting points for workshop review:

- Steel option: 40 × 40 × 3 mm square hollow section for the 2 m column and
  boom, with welded/bolted diagonal gusseting.
- Aluminum option: 45 × 45 mm or 50 × 50 mm industrial T-slot extrusion with
  a diagonal brace and proper joining plates; do not use 20 × 20 extrusion.
- Mount adapter plate: drill only after the commercial mount's base pattern is
  measured. Use through-bolts, washers, and prevailing-torque locknuts.
- The requested 0.10–0.20 m reach is a starting requirement, not a final boom
  length. The A12AB body is roughly 0.32 m long externally, and the lens is
  not at the body center. Measure the post-to-lens and center-of-gravity reach
  before cutting material.

For preliminary loading, treat the projector plus mount as at least 6 kg and
use a minimum factor of safety of 3 for the frame, joints, base, fasteners,
and tether. With a 0.25 m center-of-gravity offset, the service moment is
about 15 N·m and the preliminary design moment is about 45 N·m. A workshop
engineer/instructor must review the real base anchorage and joint design;
section size alone does not prevent tipping or joint slip.

## 6. Direct-down orientation gate

Before using the direct-down arrangement, obtain written CAIWEI confirmation
that the A12AB may operate continuously with its lens axis vertical and ask
for required vent clearances. The actual unit's underside label gives
`service@caiwei.net`; CAIWEI's website also publishes `sales@caiwei.net` and
WhatsApp `+86 18028568605`.

Suggested message:

> We have a CAIWEI A12AB projector and need to project vertically downward
> onto a horizontal worktable. Is continuous operation with the lens pointing
> straight down approved for cooling and optical safety? Please provide the
> four mounting-hole spacing, screw thread and maximum screw engagement depth,
> required ventilation clearance, and the exact compatible CAIWEI/EUG mount
> model and load rating.

If CAIWEI does not approve vertical operation, keep the projector in its
normal horizontal/ceiling-approved orientation and turn the beam downward
with a rigidly mounted **front-surface optical mirror**. That alternative
needs a separate optical-path and mirror-size prototype; a household
back-surface mirror may produce a double image.

## 7. Physical measurements required before ordering or cutting

1. Retake the complete underside photo with a ruler in frame. The existing
   photo confirms the A12/AB/M label and four bosses but has no scale.
2. Measure all four mounting-hole center coordinates from one datum edge.
3. Confirm the thread with an M4 gauge/screw and measure safe engagement
   depth; do not bottom a screw inside the projector.
4. Weigh the actual projector and identify its center of gravity with all
   cables disconnected.
5. Measure floor-to-table height, desired projected rectangle, table-edge to
   image-center distance, and obstruction-free post location.
6. Temporarily support the projector so the lens-to-table optical path is
   0.91–0.96 m; verify full-field focus and record the measured image size.
7. Identify intake/exhaust vents and required access to focus, controls,
   power, HDMI, USB, and the main switch.
8. Check the Academy AV store/workshop for a universal four-arm mount marked
   at least 10 kg and containing M4 hardware. Record its manufacturer/model,
   load label, arm span, angle range, and base-hole pattern.
9. Have the workshop instructor approve the frame, base anchorage, locking
   method, tether point, cable strain relief, and overhead-use risk control.

Do not order or fabricate until items 1–6 resolve compatibility and geometry.
