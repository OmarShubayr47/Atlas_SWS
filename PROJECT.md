# Smart Working Station — Project Map

Revision: 2026-10-16

## Purpose

Build a practical projected physical workstation controlled through a 32-inch PCAP touch surface and voice interaction, using a Raspberry Pi 5 and a custom stereo-audio HAT. Computer vision and the camera are removed from current scope.

## Current stage

Advanced prototyping and integration. Details and labels: `docs/SWS_project_status.md`.

- Pi 5, 4 GB, and 32 GB microSD are in use.
- Voice assistant pipeline was verified end to end on the Pi with Hey Jarvis (2026-09-22), then with the new Hey Atlas default (2026-09-29). The Atlas-triggered conversation produced a full reply through the projector. Counted recognition reliability and physical PTT regression remain open.
- Projected status panel (Chromium kiosk) works on the projector, verified.
- Projector received: **CAIWEI A12AB** (owner-confirmed 2026-09-30), not the ordered WiMiUS P62 Pro. Native 1920×1080, throw ratio 1.28–1.36, and overscan fixed by CVT timing are all measured. Focus at ~1 m is untested and is the go/no-go for the mount geometry. Mount sourcing and the preliminary workshop concept are in `docs/CAIWEI_A12AB_PROJECTOR_MOUNT.md` / T-003.
- Since 2026-10-01 the assistant, UI server, restart button and kiosk run as systemd user services with crash and hang recovery (tested). The 2026-10-01 owner test verified push-to-talk, the volume knob, an Arabic command, and voice-driven schematics and file viewer. Short audio cutouts during replies were measured (bursty speech delivery); a jitter-buffer fix is Proposed.
- Custom HAT schematic/layout are designed and under instructor review, not fabricated or verified.
- ILITEK2510 PCAP controller is untested.
- HAT amplifier power architecture is a fabrication blocker. The I2S overlay is resolved: `hifiberry-dac` leaves GPIO16 free, but GPIO20 is still claimed.
- Mechanical: enclosure, control cradles, speaker mounts, port openings and a rack carrier are Designed in Onshape with CAD interference checks passing. The encoder knob bore was selected by a printed coupon; all other physical fit, retention and load capacity remain Under Evaluation.

## Architecture

```text
Projector + PCAP touch + USB microphone
                 -> Raspberry Pi 5
                 -> application / voice assistant
                 -> I2S
                 -> custom HAT with 2 x MAX98357AETE+T
                 -> independent left and right speakers
```


## Important paths

- `software/` — Pi application code (voice assistant, UI server/kiosk, restart button, tools).
- `tests/` — hardware diagnostic and bench scripts.
- `docs/` — project status, PCB design decisions, projector mount and control-dimension records.
- `docs/SWS_project_status.md` — detailed status and open items.
- `docs/Smart_Working_Station_PCB_Decisions.md` — HAT PCB design decisions.
- `docs/CAIWEI_A12AB_PROJECTOR_MOUNT.md` — projector mount sourcing and geometry (T-003).
- `docs/PHYSICAL_CONTROL_DIMENSIONS.md` — owner-supplied control drawing dimensions, proposed openings and mounting checks (T-005; physical fit remains unverified).
- `mechanical/sws_enclosure_prototype.fs` — Onshape Feature Studio 1 source: rounded enclosure, four-control layout, cradle/reset prototypes, upper speaker shelves with rightward wire relief, Pi access windows and CAD interference/base-fit checks. Positive keepers, physical fit and base retention remain open (T-005).
- `mechanical/SWS_ASSEMBLY.md` — live Onshape assembly with the actual corrected base, lid/supports, nominal installed knob and separate test articles; mate/datums, passing static interference check and remaining physical checks (T-005).
- `mechanical/SWS_SPEAKER_MOUNTS.md` — paired upper grilles, owner-provided35 ×25 ×6.2 mm envelopes, sleeve-integral shelves/rightward wire relief, passing CAD checks and remaining retention/thermal checks (T-005).
- `mechanical/SWS_PORT_OPENINGS.md` — official Pi 5 geometry registration, trial USB/Ethernet/USB-C/dual-HDMI/microSD/power-button access windows and required physical plug/stack checks (T-005).
- `mechanical/sws_rack_enclosure_carrier.fs`, `mechanical/SWS_RACK_CARRIER.md` — current120 ×90 ×8 full-enclosure carrier with exactly two horizontal insertion sticks on ONE vertical centreline (61 pitch), bolted braces and removable case clamps. Owner selected A1/PLA; current CAD/mesh checks pass. Source/export/print records are under `mechanical/print_jobs/20261013/`; hardware, real rack/plug fit and load capacity remain Under Evaluation (T-006). Former `sws_pi_rack_carrier.fs` is a Superseded experimental Pi-base/sliding-shelf snapshot.
- `academy/SmartWorkingStation_OmarShubayr/` — Academy deliverable folder; preserve required Arabic `اقرأني.txt` files.
- `academy/SmartWorkingStation_OmarShubayr/قطع المشروع/ملف المشروع.xlsx` — official project workbook. Edit it at the XML level or in Excel, never by saving with openpyxl (that drops the Academy logo).

## Development environment

- Target: Raspberry Pi 5 / Raspberry Pi OS.
- Primary language: Python.
- Use a project virtual environment when appropriate.
- Use `.env` for secrets/configuration; never copy its contents into documentation or commit it.
- Resolve ALSA devices by stable name, not card index.
- Use one shared, lazily-created PyAudio instance per process.

Install, service and test commands are in `README.md`.

## Current priority order

Two parallel tracks; full lists are in `docs/SWS_project_status.md`. The owner has not yet ranked one track against the other.

**PCB track (fabrication blockers):** amp power rail off the 40-pin header, GAIN_SEL two-amp bench A/B, R5/R6 values, multimeter pinout checks, SD–GND continuity check rule.

**Pi track (from the Pi handoff of 2026-09-22, updated 2026-10-16):**
1. Replace faulty bench amp U1 → check SD–GND → restore U2 via 210 kΩ → stereo test.
2. ~1 m focus test (go/no-go for mount geometry), then cause of focus gradient.
3. PCAP touch enumeration, then touch → UI mapping (the display is rotated 180°; touch must use the same rotation).
4. ~~systemd autostart for assistant, UI, and restart button~~ — done 2026-10-01 (plus the kiosk); physical restart-button tiers still pending.
5. Voice follow-ups: jitter buffer for the reply cutouts, Arabic STT check, sentence-by-sentence TTS, fix or shelve Realtime. (~~Encoder volume~~ done 2026-10-01; ~~reconcile `mic_stream.py`~~ checked 2026-09-22.)

**Mechanical track:** enclosure base retention and housing keepers; owner-authorised empty fit and inert-load proof of the rack carrier before any electronics go on it.

**Then:** formal deliverables/BOM synchronization and mechanical integration.

## Non-negotiable constraints

- Do not reintroduce camera/OpenCV as a current subsystem without explicit owner approval.
- MAX98357A outputs are bridge-tied: OUTN is not ground and left/right outputs must not be commoned.
- Do not treat designed hardware as tested or approved.
- Do not invent electrical or compatibility facts.
- Do not alter official Academy requirements or identity fields without explicit instruction.
