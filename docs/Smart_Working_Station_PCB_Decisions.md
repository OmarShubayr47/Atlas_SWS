# Smart Working Station --- PCB Decisions & Architecture

## 1. PCB Purpose

The custom PCB will be a **Raspberry Pi 5 HAT PCB** for the Smart
Working Station.

The HAT will provide the project's custom hardware, audio circuitry,
physical controls, GPIO routing, and expansion interfaces while the
Raspberry Pi 5 remains the main computer.

## 2. Raspberry Pi 40-Pin Interface

-   Use a **female 40-pin header** on the HAT.
-   The HAT mates directly with the Raspberry Pi 5's male 40-pin GPIO
    header.
-   Route required GPIOs through PCB traces to onboard components.
-   Keep unused GPIOs accessible through spare headers/test points where
    practical.
-   Expose useful buses such as GPIO, 5 V, 3.3 V, GND, I²C, UART, and
    I²S.

## 3. Audio System

### Amplifier

Selected IC: **MAX98357AETE+T**.

Reason: - 16-pin TQFN package. - More practical for our custom PCB than
the WLP variant. - Suitable for the indoor workstation. - The
wider-temperature automotive variant is unnecessary.

### Stereo configuration

Use **2 × MAX98357AETE+T**: - Amplifier 1 → Left speaker - Amplifier 2 →
Right speaker

The two amplifiers will share the required I²S signals and use
channel-selection configuration for left/right stereo.

### Speaker

Current speaker family: two thin notebook-style 3525/2535 cavity-box
speakers. Supplier options include 4 Ω / 8 Ω and 2 W / 3 W variants.

The exact ordered impedance, power rating, dimensions, and pin/wire
configuration must be verified before final electrical assumptions or PCB
manufacturing.

## 4. Speaker Connector

An earlier prototype recommendation used a 2-position screw terminal block.
That recommendation is retained here only as superseded history.

### HAT decision

Use **four bare solder pads** on the HAT:

```text
SPKR_L_P
SPKR_L_N
SPKR_R_P
SPKR_R_N
```

Speaker wires are soldered directly to these pads. Do not re-add screw
terminals unless the project owner explicitly reverses this decision.

### Critical rule

MAX98357A outputs are differential/bridge-tied.

**Never connect OUT− to GND.**

Each speaker connects between its amplifier's OUT+ and OUT−.

## 5. I²S Audio Interface

The HAT routes a shared I²S bus to both MAX98357A amplifiers:

-   BCLK → GPIO18 / physical pin 12
-   LRCLK / WS → GPIO19 / physical pin 35
-   DIN → GPIO21 / physical pin 40

Amplifier enable/channel selection uses `AMP_EN` on GPIO26 / physical pin
37. Overlay resolved (verified 2026-09-20): `dtoverlay=hifiberry-dac`
replaced `googlevoicehat-soundcard`. It outputs I²S only; AMP_EN is driven
by software. GPIO16 is free; GPIO20 stays claimed by the overlay and must not
be allocated.

Bench findings (2026-09-22) that affect this design:
- The bench breakouts appear to have an onboard SD pull-up, so bench
  channel-select voltages do not validate R1 = 210 kΩ on the bare-chip HAT.
- AMP_EN is shared: one shorted SD pin silences both channels and loads
  GPIO26. Continuity-check SD–GND on every fabricated board before power-up.

Under evaluation (2026-09-22): the projector's built-in speakers over HDMI
audio as an alternative or additional output, because they may be louder.
The HAT audio design is unchanged until a loudness test decides.

## 6. Physical Controls

### AI Assistant Button

A K6-6271D04 momentary LED tact switch mounted off-board and connected to
bare HAT wiring pads.

Expected function: 1. User presses the AI button. 2. Voice input becomes
active. 3. USB microphone captures the command. 4. Speech-to-text / AI
processing occurs. 5. Response is played through the speakers.

Button: GPIO22 / physical pin 15. LED: GPIO24 / physical pin 18. The LED
resistor remains a bench-verification item.

### Volume Control

Use a **rotary encoder with an integrated push switch**.

Functions: - Rotate clockwise → volume up. - Rotate counter-clockwise →
volume down. - Press → mute/unmute.

Reason: the audio path is digital I²S, so software/digital volume
control is more appropriate than an analog potentiometer.

Target part: ALPS EC11E18244AU, mounted off-board. GPIO5/GPIO6 carry the
quadrature phases and GPIO13 carries the mute push switch. Re-run calibration
with the actual ALPS part; KY-040 bench results do not automatically transfer.

### Power Button

Use the Raspberry Pi 5's **J2 external power-button connection**.

Architecture:

``` text
External momentary POWER button → dedicated two-wire pair → Pi 5 J2
```

The switch contacts do not pass through the HAT and do not consume a GPIO.
Only the separate power-indicator LED is represented on the HAT circuitry.

### Restart Button

Use the TS365ZJ momentary button on GPIO27 / physical pin 13, mounted
off-board and wired to HAT pads.

`software/restart_button.py` requires an approximately 2-second hold and was
verified by a live Pi reboot on 2026-09-21. A systemd unit is still required
for automatic startup after reboot.

## 7. Microphone

The previous **INMP441 I²S microphone has been dropped**.

New decision: use a **USB microphone**.

The HAT does not need an INMP441 interface.

## 8. Camera

The Raspberry Pi Camera Module 3 has been **dropped from the project**.

Therefore: - No camera connector is required. - No camera-related PCB
circuitry is required. - Computer vision/OpenCV hardware is not part of
the current HAT design.

## 9. Touch System

The project uses a 32-inch PCAP capacitive touch foil with an
**ILITEK2510 USB controller**.

Decision: - Use the supplied/existing USB touch controller. - Do **not**
design a custom capacitive touch controller. - The controller remains an
external USB device.

## 10. Projector

The projector is external to the HAT.

Received projector (2026-09): **CAIWEI A12AB** (owner-confirmed 2026-09-30). It is not
the WiMiUS P62 Pro that was ordered. Measured: native 1920×1080, throw ratio
1.28–1.36 (a 32" image needs ~91–96 cm), overscan fixed by CVT timing.
Focus at ~1 m is untested.

*Superseded:* "WiMiUS P62 Pro, selected and ordered; throw ratio unmeasured"
(the text below this line is kept as history).

Its throw ratio remains unmeasured and must be calculated from real delivery
measurements before final mount geometry or touch/projector mapping.

The HAT does not need projector electronics.

## 11. PCB Contents

### On the HAT

-   2 × MAX98357AETE+T
-   Four left/right speaker solder pads
-   Female 40-pin Raspberry Pi header
-   Bare wiring pads for off-board AI/PTT, encoder/mute, and restart controls
-   AI and power-indicator LED circuitry/pads
-   I²S routing
-   GPIO routing
-   Spare GPIO/test points
-   Audio decoupling and grounding
-   Power distribution
-   Future expansion headers

### External

-   Raspberry Pi 5
-   USB microphone
-   PCAP touch foil + ILITEK2510 controller
-   Projector
-   Two speakers
-   AI/PTT, restart, power, and encoder controls
-   Dedicated power-switch wiring to Raspberry Pi 5 J2
-   Raspberry Pi power supply

## 12. Power Architecture

Power architecture is **not yet finalized**.

It must account for: - Raspberry Pi 5 - 2 × MAX98357A - USB microphone -
USB touch controller - Other possible USB peripherals

The HAT should not blindly route all high-current audio power through
weak GPIO/header paths.

Stage 5 will determine: - 5 V distribution - Amplifier supply -
Raspberry Pi power arrangement - Current requirements - Protection -
Grounding - Decoupling - Connector ratings - Power trace sizing

## 13. Development Stages

### Stage 1 --- MAX98357A Stereo Amplifier

Design and verify: - 2 × MAX98357AETE+T - Official reference circuit -
Power supply - Decoupling - I²S - Left/right selection - Gain
configuration - Shutdown/enable - Speaker outputs - Speaker connectors -
Grounding - Thermal/layout considerations

Use the official MAX98357A documentation as the primary source. Do not
blindly copy values from random breakout boards.

### Stage 2 --- Raspberry Pi HAT Interface

Design: - Female 40-pin header - 5 V - 3.3 V - GND - I²S - GPIO
routing - I²C - UART - Spare GPIO/test points

Create a GPIO allocation table before routing.

### Stage 3 --- Physical Controls

Add: - AI assistant button - Rotary encoder - Encoder push switch for
mute - Restart button - POWER button via J2 - Status LEDs if useful

### Stage 4 --- External Interfaces

Plan convenient connections for: - USB microphone - PCAP/ILITEK2510
touch controller - Projector - Left speaker - Right speaker - Future
peripherals

### Stage 5 --- Power Architecture

Finalize: - 5 V distribution - Amplifier supply - Pi power
considerations - Current capacity - Protection - Decoupling -
Grounding - Power trace sizing

### Stage 6 --- Final HAT PCB

Workflow:

``` text
Schematic
↓
Component / footprint verification
↓
PCB placement
↓
Power routing
↓
I²S / signal routing
↓
GPIO routing
↓
Ground plane
↓
DRC
↓
3D inspection
↓
Manufacturing files
↓
PCB fabrication
↓
Assembly
↓
Testing
```

## 14. Final Decision Table

  Item                   Decision
  ---------------------- -------------------------------------------
  PCB type               Raspberry Pi 5 HAT
  Pi connection          Female 40-pin header
  Amplifier              MAX98357A
  Confirmed IC           **MAX98357AETE+T**
  Number of amps         2
  Audio                  Stereo
  Speaker target         3525/2535 family, 2 units; exact variant to verify
  Speaker connection     Four bare solder pads
  Microphone             USB microphone
  Camera                 Dropped
  AI button              K6-6271D04 off-board → GPIO22
  AI LED                 Off-board switch LED → GPIO24
  Volume                 ALPS EC11E18244AU → GPIO5/GPIO6
  Mute                   Encoder push switch → GPIO13
  Power button           External momentary button → Pi 5 J2
  Restart                TS365ZJ → GPIO27 → 2 s hold → orderly reboot
  Touch                  External ILITEK2510 USB controller
  Projector              External CAIWEI A12AB; throw ratio 1.28–1.36
  Power architecture     Dedicated protected amplifier input still open
  PCB software           EasyEDA
  Development strategy   Stage-by-stage design and testing

## 15. Immediate Next Step

The schematic and layout are complete and under instructor review. Do not
restart Stage 1 unless a review finding requires redesign.

Before fabrication:

1.  Resolve instructor feedback.
2.  Finalize the dedicated protected amplifier-power input.
3.  Bench-test final `GAIN_SEL` population with both amplifiers and the real
    speakers.
4.  Bench-test R5/R6 LED resistor values.
5.  Verify every physical control pinout with a multimeter.
6.  ~~Install and measure the final generic I²S overlay/GPIO behavior.~~
    Done 2026-09-20 (`hifiberry-dac`).
7.  Re-run ERC/DRC, footprint, exposed-pad, clearance, trace-width, and
    mechanical checks.
8.  Decide hand assembly versus JLCPCB SMT assembly.
9.  Generate manufacturing outputs only after the blocking items are closed.
