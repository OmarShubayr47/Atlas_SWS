# Smart Working Station — Project Status

Detailed status of the Smart Working Station: hardware baseline, HAT PCB design, Pi software, mechanical design and open items. Status labels: Designed / Implemented / Tested / Verified / Under Evaluation. Task IDs (T-001 … T-006) and references to `docs/decisions_pi5.md` point to records kept in the private working repository.

## Project scope (current)

Projected touch interface + voice assistant workstation. **Computer vision and the camera are fully removed from the project** — no object recognition, no illumination subsystem (it existed only to serve the camera). The system is now: projector (visual) + PCAP touch (input) + custom audio HAT (voice out, stereo) + USB mic (voice in) + Raspberry Pi 5.


## Hardware baseline (actual)

| Item | Status |
|---|---|
| Raspberry Pi 5, 4GB RAM | In use (BOM baseline was 8GB — not acquired) |
| 32GB microSD | In use (BOM baseline was 128GB A2 — not acquired) |
| Projector: **CAIWEI A12AB** (received 2026-09; owner-confirmed 2026-09-30; NOT the ordered WiMiUS P62 Pro) | Received and tested. Board `5605RX58ZXW_hand`, Android 9, fw V1.00.1A20240626; EDID is a generic template and does not independently identify the model. WiMiUS specs do not apply. **Measured:** native 1920×1080 panel; throw ratio 1.28–1.36 (~1.32) at zoom 100% → 32" image needs D ≈ 91–96 cm; TV-timing overscan ~4–5% **fixed** by sending CVT 1920×1080@59 via a kanshi profile (`software/ui/kanshi-projector.conf`). Digital zoom % is not a linear width scale; measure the image if zoom is used. Focus softens toward the top (optical; cause open). **Untested:** focus at ~1 m, the go/no-go for mount geometry. T-003 covers the commercial mount and fabricated stand. |
| PCAP touch foil, 32", Ilitek 2510 USB controller | Untested |
| USB microphone (Corsair) | Working; resolved by card name, never by hard-coded index. **Keep its USB cable away from mains/power leads:** 60 Hz pickup once made speech detection fail (fixed by re-routing, 2026-09-21). |
| Bench amps (MAX98357A WLP breakouts) | U1 **faulty** (SD shorted to GND on the module), removed. U2 tested as a single mono amp, with SD wired direct to GPIO26 for now (210 kΩ removed). GPIO26 survived ~1 min driving into U1's short (read-back verified). |
| Bench encoder (KY-040) | Tested: full-step, 4 edges/click, rest state 3, direction inverted. Values do not carry over to the HAT's ALPS EC11. |
| Speaker drivers ×2 | 3525/2535 cavity box speakers, notebook-computer style, ultra-thin, rated 4Ω/8Ω, 2W/3W |

## PCB — MAX98357A Stereo HAT (schematic + layout complete)

**Status: Designed, submitted for instructor review. NOT fabricated, NOT ordered, NOT tested. Treat as "Selected/Designed," not "Approved."**

### Audio — 2× MAX98357AETE+T (TQFN-16), true stereo

- Shared I2S bus: `DIN`→GPIO21/pin40, `BCLK`→GPIO18/pin12, `LRCLK`→GPIO19/pin35 — both ICs listen to the same bus.
- Channel select + enable: single shared GPIO26/pin37 (`AMP_EN`).
  - **U1 (left):** `SD_MODE` tied direct to `AMP_EN`.
  - **U2 (right):** `SD_MODE` tied to `AMP_EN` through **R1 = 210kΩ** (derived from datasheet formula at VDDIO=3.3V: `R_SMALL(kΩ) = 94.0×VDDIO − 100 = 210.2kΩ`, standard E96 value).
  - GPIO high → left channel active + right channel active via divider. GPIO low → both amps shutdown.
- Gain: `GAIN_SLOT` on both ICs tied to shared net `GAIN_SEL`. **Not yet populated** — footprint has unpopulated pads for GND (12dB) or 5V (6dB); floating = 9dB with zero rework. **Open item: run a real two-amp bench A/B test before populating** — single-channel bench testing earlier gave working results at 6dB (GAIN tied to VDD), which contradicts the datasheet-power-table-based 12dB recommendation. Trust the bench result over the table inference once tested.
- Decoupling: 10µF + 100nF per IC at VDD pins (7,8). EP (pin 17, exposed thermal pad) tied to GND plane on both ICs — confirmed in layout.
- Outputs: `OUTP`/`OUTN` per channel are bridge-tied differential — **never ground OUTN**. **Final decision: routed to 4 bare pads** (`SPKR_L_P`, `SPKR_L_N`, `SPKR_R_P`, `SPKR_R_N`), not screw terminals as originally recommended for prototype serviceability — deliberate trade-off, confirmed by the project owner.
- **Open item — power rail:** VDD currently modeled as a generic +5V net. Per the project's own PCB safety rules, final design should NOT route high-current audio power through the Pi's 40-pin header 5V pins — needs a dedicated external DC input (screw terminal, reverse-polarity FET, fuse) added in a later power-architecture pass. Not yet done in the current schematic.

### Physical controls — all wired as bare solder pads, off-board

All four controls use EasyEDA's "Convert to PCB: No" component setting — this keeps them fully documented in the schematic (BOM, ERC, net connections) while the PCB carries only bare pads that get wired to the real switches by hand-soldered leads. Real switches sit wherever the enclosure design eventually puts them, not fixed to the HAT's position.

| Control | Part | Pads on HAT | Notes |
|---|---|---|---|
| AI assistant / PTT button | K6-6271D04 (LED tact switch, green) | `AI_BTN`, `AI_LED_A`, shared `GND_BUS` | Single button does both wake-word-equivalent trigger AND PTT — same GPIO22 as existing working code. **LED polarity: pin 5 = cathode(−), pin 6 = anode(+)** — this was corrected mid-design after being initially read backwards from a similar-looking sibling part; verify with a multimeter before final soldering. LED driven from GPIO24 through R6 (200Ω placeholder — datasheet gave no Vf table, value unverified until bench-tested with the real part). |
| Restart button | TS365ZJ | `RESTART_BTN`, `GND_BUS` | **Pins 1 & 3 are the actual switch contacts; pins 2 & 4 are tied to the metal shell only** — not part of the switching path. Wiring the wrong pair (as done with a similar-looking part earlier) means the button never registers. GPIO27, software does `sudo reboot`. Rated 50,000 cycles — fine for infrequent use. |
| Power button | TM-001-D1-03 (Blue LED variant) | LED only: `PWR_LED_A`, `PWR_LED_K` | **Switch contacts are NOT on the HAT at all** — wired with their own dedicated 2-wire pair directly to the Raspberry Pi's J2 pads (confirmed via Pi's own documentation: J2 sits between the RTC battery connector and board edge; bridging it with a normally-open momentary switch reproduces the built-in power button). No GPIO, no software involvement. LED: pin5=anode(+), pin6=cathode(−); Vf is 3.0V nominal/3.6V max — **too high for 3.3V GPIO logic**, so it's wired always-on across the 5V rail through R5 (~200Ω placeholder) rather than GPIO-driven — simple power-good indicator, not a software status light. |
| Rotary encoder (volume + mute) | ALPS EC11E18244AU | `ENC_A`, `ENC_B`, `ENC_BTN`, shared `GND_BUS` | Pins A/B = quadrature phases, C = common (→GND), D/E = independent push-switch (mute). **Pull-ups must be 1kΩ, not 10kΩ** — datasheet specifies 1mA minimum operating current on the sliding contacts; 10kΩ at 3.3V only delivers ~0.33mA, below spec, causes unreliable contact. 1kΩ gives ~3.3mA, correct for both phases and the switch (R2/R3/R4). Debounce is handled in **software** (≥5ms window, same pattern as the existing PTT debounce), not hardware RC — the datasheet's actual bounce spec doesn't line up cleanly with easy RC component values. **Firmware note: only phase A aligns with detent stability points, not phase B** — worth knowing before assuming a rotation-counting bug if it feels "off by half a step." GPIO5/6/13. |

Mute is implemented entirely in software (read the encoder's push-switch GPIO, scale the digital audio stream to silence) — no hardware mute circuit on SD_MODE.

### GPIO allocation table (final)

| GPIO | Physical pin | Function |
|---|---|---|
| 18 | 12 | I2S_BCLK (shared bus) |
| 19 | 35 | I2S_LRCLK (shared bus) |
| 21 | 40 | I2S_DIN (shared bus) |
| 26 | 37 | AMP_EN (shared amp enable + L/R select) |
| 22 | 15 | AI_BTN / PTT (single button, dual-purpose) |
| 24 | 18 | AI_LED (PTT status LED, software-driven) |
| 5 | 29 | ENC_A |
| 6 | 31 | ENC_B |
| 13 | 33 | ENC_BTN (mute) |
| 27 | 13 | RESTART_BTN |
| 2, 3 | 3, 5 | I2C — reserved, unused |
| 14, 15 | 8, 10 | UART — reserved, unused |
| 0, 1 | 27, 28 | HAT ID EEPROM only — never repurpose |
| 16 | 36 | Free since the switch to `hifiberry-dac` (verified 2026-09-20) |
| 20 | 38 | **Still claimed** by `hifiberry-dac` (I2S0_SDI0) — do not allocate |
| 17 | 11 | Drives an LED in legacy `voice_control.py` — not in the HAT design; unaccounted for |

**Power button is not a GPIO net at all** — wired directly to Pi's J2 pads, entirely separate from this table and from the HAT board.

**Overlay — resolved (verified 2026-09-20):** `googlevoicehat-soundcard` hard-claimed GPIO16 as its own SD_MODE and never drove GPIO26. It was replaced by `dtoverlay=hifiberry-dac`, which outputs I2S only: GPIO16 is free, GPIO20 stays claimed (I2S0_SDI0), and AMP_EN (GPIO26) is driven by software (`software/common/amp_enable.py`). The ALSA card name changed; `AMP_NAME_HINT` defaults to "hifiberry".

### Bench findings the PCB side needs (from the Pi, 2026-09-22)

- Bench breakouts appear to have an onboard SD pull-up, so bench channel-select voltages do **not** validate the bare-chip HAT's R1 = 210 kΩ.
- Shared AMP_EN: one shorted SD silences both channels and loads GPIO26. **Continuity-check SD–GND on every fabricated board before power-up.**
- Route the mic/USB cable away from mains and power leads (including the projector's) in the enclosure.
- A speaker solder joint already caused one silent bench session. The Pi side suggests weighing screw terminals again before fabrication. The owner's current decision is still bare pads; this is flagged for the owner, not changed.

## Software — voice assistant

**Operational output selection (2026-09-27, codex-pi):** the owner requested projector HDMI speech for the current session/setup. The existing assistant now uses `PLAYBACK_PCM="plug:'hdmi:CARD=vc4hdmi0,DEV=0'"` and `SPEECH_GAIN_DB=0` in the Pi-local, untracked `.env`. The earlier values of these two keys and the previous HDMI mixer level are preserved in `scratch/hdmi-output-before-20260927.json` (no credentials). HDMI-A-1 is connected; ALSA identifies its output as `vc4hdmi0`, device 0. One replacement assistant and its persistent HDMI player were observed running; WebUI health returned 200. **Implemented; audible projector speech and comfortable volume await owner confirmation.** Projector volume about 30% was requested, not measured or remotely set. HAT wiring, boot overlay, CVT display timing, and the final HAT/BOM audio architecture remain unchanged. See `coordination/tasks/T-001-hdmi-playback.md`.

**Resume note, same day:** after a Pi reboot at 18:55, the application and UI needed starting again. Two detached assistant launches failed capture-device lookup despite successful independent ALSA/helper checks; root cause remains open. The unchanged assistant succeeded in a managed terminal, with one assistant and a RUNNING HDMI stream. WebUI and kiosk were restored. This is manual runtime startup, not installed autostart; listening confirmation is still pending.

**Latest runtime check, 19:29 same day:** another boot at 19:25:55 stopped the applications again. At the owner's request, `./software/ui/run_kiosk.sh` restored the WebUI (HTTP 200) and Chromium. A compositor screenshot of HDMI-A-1 verifies the full turquoise UI at the existing 1920×1080@59 Hz setting. Wall visibility/focus awaits owner confirmation. The voice assistant is currently stopped; earlier assistant PIDs are historical. Autostart remains unimplemented.

**Physical discrepancy, 19:31:** owner sees a small/blurry Pi desktop on the wall, while a fresh HDMI-A-1 capture still shows the UI and its processes remain running. Projected WebUI is **not Verified** in this session. Output enabled/DPMS On; cause unresolved. Next check: whether moving the Pi mouse moves the projected pointer, to distinguish a frozen image from a live desktop.

**2026-09-28 runtime:** owner reconfirmed the earlier tested +12 dB projector speech setting; Pi-local `.env` now has `SPEECH_GAIN_DB=12` with the existing HDMI-A-1 playback override. Kiosk and UI server are running (HTTP 200), and a Pi HDMI capture shows the turquoise page. The owner reports the projector remote and its own Menu button are unresponsive; wall image is not verified. Corsair microphone is absent from USB/ALSA, so the assistant is stopped and projector speech cannot yet be tested. Physical projector control recovery and microphone reconnection are the next checks. No autostart service exists.

**2026-09-29 runtime:** the Corsair mic is present again. One managed-terminal assistant completed a full Atlas-triggered conversation, and the owner heard the entire reply from the projector at comfortable volume. HDMI-A-1 speech with the saved +12 dB gain is **Verified for that turn**; T-001 is done. The HDMI path now holds GPIO26 low and does not enable the MAX amp. The first date answer had a wrong weekday; each later LLM request receives the Pi's current local date/time, but a date-question retest is still open. The assistant remained running in one managed terminal at the last check, with no autostart. The physical WebUI/projector control issue is still open.

**2026-09-30 follow-up:** the owner reports that Atlas's spoken replies cut out repeatedly during the previous day's integrated test, roughly every 0.5 seconds by estimate. Cause and cadence are unmeasured; reliable playback across turns is **Under Evaluation**. In that test the turquoise UI and an Atlas turn were visible on the projector. Two physical PTT triggers reached the assistant: the first yielded no transcript; the second produced a transcript and generated a reply, but the owner did not confirm completed speech or UI display. Full PTT regression remains open. The restart-button dry run had no confirmed physical hold. The owner now reports nothing connected to the Pi and plans to prepare Windows-side changes, push them, then request a Pi pull and Academy retest. The earlier full projector reply remains Verified for its specific turn; do not generalize it to uninterrupted playback.

**2026-10-01 — always-on services and physical controls (T-004, Pi Claude Code):** the assistant, UI server, restart button and kiosk now run as **systemd user services** (`software/deploy/install_services.sh`, linger on), restart on crash (tested: 5.2 s) and on hang via a watchdog (tested: 65 s). The assistant waits for a missing mic instead of exiting. PTT: press while listening = finish, while thinking/speaking = stop. The encoder is the speech volume (software gain on the active output; mute = exact zeros), the AI LED on GPIO24 mirrors the state, and the restart button is tiered (2 s + release = restart software, 8 s = reboot). Every reply now logs delivery statistics for the cutout investigation; `tests/playback_continuity_test.py` is ready but not yet run. **Before any manual run: `systemctl --user stop sws-assistant`** (otherwise GPIO/mic/HDMI conflict). Logs: `journalctl --user-unit=sws-assistant`. Physical tests of the buttons, knob and LED, and a full reboot, are pending. See the 2026-10-01 decision-log entry.

**2026-10-01 owner test (21:25–21:57):**
- **Verified:** PTT (start, finish, stop), the volume knob (a small response delay, accepted for now), an Arabic command, and schematics and the file viewer driven by voice.
- **Cutout cause measured:** bursty TTS delivery. 26 of 28 replies had silence inserted mid-reply (median 170 ms, max 2.98 s). A jitter-buffer fix in `keepalive_output.py` is Proposed; it would also shorten the knob delay.
- **Problems found (open):**
  - the assistant answered "what files can you access" with only the 3 workspace files, although it can open the whole project
  - it described a single-LED drawing as two LEDs with separate resistors (overclaim)
  - "move it to the middle" was handled as a scroll instead of fit
  - the caption sat at the right edge of the wall image
  - the first PDF open was not seen on the wall
- **Still pending:** the restart-button tiers and a full reboot.

See the "Owner hardware test" decision-log entry.

**Latest owner preference, 2026-09-27:** use the WebUI on the projector and always route the current assistant's speech to the projector speakers, at home and at the Academy. Keep the saved HDMI override across launches. Do not run the white-edge/overscan diagnostic as a routine launch step. The configured output is HDMI-A-1 (`vc4hdmi0`); moving locations does not require an output change if the same Pi HDMI port is used. This operational preference does not authorize HAT/BOM redesign or installation of autostart services.

**OpenAI HTTP pipeline (`voice_assistant.py`) — verified end to end 2026-09-22 with the previous Hey Jarvis model:** wake word or PTT (GPIO22) → local PyAudio/webrtcvad capture → `gpt-4o-mini-transcribe` → `gpt-5.4-mini` (reasoning_effort low) with **read-only project tools** (confined to `~/sws`, `.env` denied; `software/tools/`) → `gpt-4o-mini-tts`, voice `sage`, **streamed** as raw PCM to one amp. Measured ~3.6 s from end of speech to first sound (+0.8 s silence wait); per-stage timings are printed. The older `arecord` → Groq → gTTS description is superseded for this entry point. **Risk:** mini-transcribe accuracy on Arabic is unverified; revert with `STT_MODEL=gpt-4o-transcribe` in `.env` if worse.

**DNS fix (verified 2026-09-22):** a 5 s first-lookup stall was fixed system-wide with `ipv4.dns-options single-request-reopen` on all three saved NetworkManager connections; an in-app `RES_OPTIONS` fallback remains in `voice_assistant.py`.

**Projected status panel (verified 2026-09-22):** Chromium kiosk (`software/ui/run_kiosk.sh`) fed by a loopback-only SSE server (`software/ui/server.py`) through a fire-and-forget client (`software/common/ui_events.py`), so the display can never stall the assistant. Turquoise HUD theme; states shown by shape, motion and label, not colour alone. Since 2026-10-01 it runs as the `sws-ui`/`sws-kiosk` services, shows "assistant offline" when the assistant's heartbeat stops, shows restart-button banners, and its volume bar follows the knob. Not yet: touch input.

**Fallback path (`voice_control.py`):** the Groq-based implementation is **silent on current hardware** (it doesn't drive AMP_EN). Update or retire it.

**Triggers and microphone handoff:**
- openWakeWord is implemented.
- **2026-09-29 — Hey Atlas Implemented / Tested; full conversation Verified:** all three entry points and the shared listener default to the bundled `hey_atlas` ONNX model. No Pi-local wake-word override was present; existing model overrides remain available. The Corsair mic is enumerated again. A 25-second guided Atlas window produced three detections and three microphone handoffs; a 20-second prompted negative window produced zero activations. Positive attempt count is uncertain, so recall and false-activation rate remain Under Evaluation. Later, the owner asked "Tell me about our project" after the Atlas trigger; the main assistant transcribed it, read project files through its restricted tools, generated a reply and played it to completion. The owner confirmed hearing the full answer from the projector. The previous 2026-09-22 end-to-end result used Hey Jarvis. Physical PTT regression remains open. See T-002 and `software/models/README.md`.
- **2026-10-12 — «يا أطلس» requested as a second wake word:** measured 0 of 26 detections with the `hey_atlas` model (max score 0.02; control "Hey Atlas" 3 of 6). A dedicated `ya_atlas` model must be trained off-Pi: Colab notebook prepared in `training/ya_atlas/` (owner to run; not yet run). Gate: 22 real clips ready, 1 h room audio still to record. Tool: `tests/wake_phrase_scores.py`.
- Wake word and the GPIO22 AI/PTT button feed one shared assistant-turn path.
- The enqueuing trigger claims the shared `busy` state so the wake-word listener cannot immediately reopen the microphone.
- Use one shared, lazily-created PyAudio instance per process. Per-stream `terminate()` calls previously caused a C-level `SIGABRT` and made the USB microphone disappear from the bus. **Open discrepancy (Pi, 2026-09-22):** `software/common/mic_stream.py` lacks the shared-PyAudio fix an earlier entry describes; reconcile.

**Audio/config state:**
- ALSA devices resolve by stable card/device name through the existing audio-device helper; do not restore hard-coded card indexes.
- `.env` is the configuration/secret source of truth, with `load_dotenv(override=True)` intentional. Do not restore stale shell API-key exports.

**Realtime path (`voice_realtime.py`):** OpenAI Realtime model `gpt-realtime-2.1`, speech-to-speech, voice `sage`. Transport/auth/model setup has been tested. Full end-to-end hardware validation after the shared-PyAudio fix is still open, so this path is not yet Verified.

**Restart control:** `software/restart_button.py` is separate from the assistant and uses GPIO27. The 2-second-hold reboot was verified by a live Pi reboot on 2026-09-21. Since 2026-10-01 (owner decision) it is **tiered** — 2 s and release restarts the SWS software, 8 s reboots — and runs as `sws-restart.service`. The tiers are unit-tested in dry run; the physical switch test is pending.

**Controlled actions:** read-only file tools are implemented (see above). Since 2026-10-01 (T-004 phases 3–4, owner decision) the allowlist also includes:

- **Viewer:** `open_file`, `control_view` and `close_view`. Project or workspace files (text, images/SVG, PDF pages) are shown on the projector. The UI server re-checks every path and serves files under a CSP. Zoom and pan respond to pointer input, so they are touch-ready.
- **Create-only file tools:** `create_note`, `create_text_file` and `show_workspace`. Writes go only into `~/SWS_Workspace`, with no overwrite, delete or run. Because nothing destructive exists yet, no confirmation gate is needed yet.
- **Template schematics:** `create_schematic`, `modify_schematic` and `list_schematic_templates`, implemented in `software/schematic/` with schemdraw 0.23. There are 8 templates. Every value is computed in Python and snapped to E-series values. Values not given (such as LED Vf) are printed as labelled assumptions. Each change saves a new revision.
- **Tested:** 77 unit tests pass. Projector-output screenshots show text, a PDF page, the file list and an inverted schematic. Five typed requests through the real LLM tool loop each picked the right tool, in 2.4–5.5 s.
- **Pending:** a spoken end-to-end test and the owner's verification on the wall.

Actions with side effects must use an allowlist, never unrestricted shell access, and destructive or costly actions need explicit confirmation. The voice-to-3D-print pipeline remains an open design item.

**Pi configuration outside git:** `dtoverlay=hifiberry-dac`; `~/.config/kanshi/config` = `software/ui/kanshi-projector.conf` (keeps overscan off — do not remove; the desktop Screen Configuration tool can overwrite it); DNS option on all saved connections; sudo still has the cloud-init `NOPASSWD:ALL` rule (broader than needed); `.env` holds `OPENAI_API_KEY` and `GROQ_API_KEY` (names only here, never values).


## Sourcing

All BOM sourced through LCSC going forward. TQFN package chosen for the amps partly for hand-solder practicality vs. WLP, but the exposed thermal pad still makes hand-soldering genuinely hard — **JLCPCB SMT assembly (pulls directly from LCSC part numbers) is worth pricing out** rather than assuming hand-assembly, especially since LCSC sourcing already sets this up cleanly.

## Open items

Two parallel tracks. The order within each track is its owner's; the owner has not ranked the tracks against each other.

### PCB track (fabrication blockers)

1. **GAIN_SEL** — bench-test both gain options with two real amps and speakers before populating the resistor footprint.
2. **Power rail architecture** — move amp VDD off the 40-pin header 5V pins to a dedicated protected DC input (Stage 5, not yet done).
3. **R5/R6 LED resistor values** — placeholders pending real-part bench measurement.
4. **Multimeter-verify every switch/encoder pinout before final soldering** — two pinout surprises already caught during design (Restart button's shell-ground pins, PTT LED polarity); don't assume a third similar-looking part matches without checking.
5. **SD–GND continuity check** on every fabricated board before power-up (bench finding above).
6. **Speaker outputs** — owner to reconfirm bare pads vs screw terminals given the bench solder-joint failure.
7. ~~Confirm the I2S overlay choice~~ — resolved 2026-09-20 (`hifiberry-dac`; GPIO16 free, GPIO20 claimed).

### Pi track (from the Pi handoff, 2026-09-22)

1. Replacement U1 → check SD–GND first → U2 back through 210 kΩ → `tests/stereo_test.py`.
2. ~1 m focus test (~91–96 cm for 32") — go/no-go for the mount geometry. Then complete T-003: measure the actual four-hole pattern/weight/center of gravity, obtain CAIWEI approval for lens-down operation, select a universal four-arm mount rated ≥10 kg, and obtain workshop approval for the braced/anchored stand. (~~Measure throw ratio~~ — done: 1.28–1.36.)
3. Cause of the focus gradient (level/square the projector).
4. PCAP touch foil enumeration, then touch → UI mapping.
5. ~~systemd autostart for assistant, UI and restart button~~ — implemented 2026-10-01 as user services (plus the kiosk); crash and hang recovery tested. A full-reboot check is pending (T-004).
6. Verify Arabic STT on gpt-4o-mini-transcribe (revert via `STT_MODEL` if worse).
7. Encoder → volume inside the assistant — **implemented 2026-10-01** as software speech volume (`common/speech_volume.py`). The HDMI `hdmi:` PCM has no softvol stage, so mixer controls cannot change projector speech. Mute writes exact zeros, which satisfies "mute must be true silence"; the hifiberry `Master` floor is −50 dB, not off (measured 2026-09-22). The physical knob test is pending (T-004).
8. Speak sentence-by-sentence while the LLM writes (next latency lever).
9. `voice_control.py` is silent on current hardware (no AMP_EN) — update or retire.
10. ~~`mic_stream.py` lacks the shared-PyAudio fix~~ — checked 2026-09-22: the Pi/repo copy already has it (one process-wide PyAudio instance, never terminated mid-run). Only reconcile if a PC-side copy differs.
11. `voice_realtime.py` — fix or shelve (full Realtime hardware validation still open).
12. Narrow sudo to `/sbin/reboot` only.
13. ~~Confirm projector model~~ — owner confirmed **CAIWEI A12AB** on 2026-09-30, and the real underside label reads `Model: A12`, `Series: AB`, `Version: M`. The same photo confirms four raised mounting bosses but has no scale; T-003 still needs boss spacing, thread, screw depth, weight, center of gravity, and vent clearance.
14. **Projector speakers over HDMI — WORKS, tested 2026-09-22:** speech is clear at projector volume 50% with `PLAYBACK_PCM` + `common/keepalive_output.py` (one stream held open; per-reply streams made the projector re-train the link and swallow replies) and `SPEECH_GAIN_DB=12`. No display trade-off: the PC timing keeps working. **Still open:** the loudness comparison against the bench amp, and the owner's architecture decision. The HAT design and BOM stay unchanged.
    `voice_realtime.py` and `voice_control.py` still open a stream per reply, so they would be silent on HDMI.
15. `/etc/asound.conf` hard-codes the ALSA default by index (`hw:0,0` playback, `hw:1,0` capture, 2026-09-05); the amp is now card 2, so anything using `default` hits the wrong card. The assistant is unaffected (resolves by name). Fix by name or remove the file — found 2026-09-22.
16. **TTS delivery gaps** (the measured cause of the cutouts, 2026-10-01): implement the `KeepAliveOutput` jitter buffer. It prebuffers about 0.5–1 s, feeds speech at real time with a small lead, and applies the volume at feed time. Afterwards, re-measure the gap statistics and the knob delay, and run `tests/playback_continuity_test.py` once to rule out a downstream cause.
17. Fix the problems found in the 2026-10-01 owner test:
    - the "3 files" answer
    - the single-LED overclaim; add a parallel-LED template
    - "middle" handled as scroll instead of fit
    - ~~caption at the right edge~~ and ~~first PDF open not seen~~ — one cause, fixed 2026-10-11 (CSS grid column grew to the footer ticker's width; files were centred off-screen). Tested by HDMI capture; wall check pending.
18. **Journal is RAM-only** (Raspberry Pi OS `Storage=volatile`): reboots wipe `journalctl`. Copy measurements out before rebooting, or log reply stats to `scratch/` (Proposed). Cold-boot autostart of all four services Tested by log 2026-10-11.

### Mechanical controls (updated 2026-10-13)

- Owner-supplied drawing dimensions are recorded in `docs/PHYSICAL_CONTROL_DIMENSIONS.md` (2026-10-09 handoff, supplied 2026-10-10). Local PDFs were subsequently inspected; findings are separately attributed. Components have not been measured.
- Prototype openings remain **Proposed**: PTT 12.8 × 12.8, power Ø10.4, encoder Ø6.5 mm. Independent housing supports are required; wires must not carry pressing forces.
- T-005 covers Onshape `SWS enclosure + knob prototype` (11 parts with mounting prototypes). Feature Studio 1 source is saved in `mechanical/sws_enclosure_prototype.fs`; assembled offset0 and exploded offset10 regenerate. Saved instance is assembled, mounts shown, base reference hidden. Positive housing keepers, actual port/cable fit and base retention remain open; prototype port windows are now Designed. TS365ZJ actuator-width variants were clarified from its PDF, but actual height is still unknown. The Ø20 ×14 knob and 9 mm socket are Designed prototypes; print and physical fit remain unverified.
- Owner-requested smoothing is **Designed**: sleeve/lid outside corners R4.2 follow the inspected R2 base with a 2 mm wall and 0.20 mm base clearance; lid top perimeter has a 0.6 mm fillet. Onshape's centred base-reference check reports no collision and 0.20 mm minimum sleeve gap. Lip clearance is 0.30 mm per side. This establishes nominal CAD insertion only: the open-bottom sleeve still needs base retention/fastening, and printed fit remains unverified. Original base studios were preserved. Next mechanical integration action is to design that retention before final printing.
- Owner layout is **Designed** with vents above controls: encoder (−28, −12), PTT (0, −12), power (28, −10), reset (28, −22). Reset A has a proposed Ø6.6 guide and separate Ø6 printed-cap prototype with Ø8.5 flange. Cap guide clearance is 0.30 mm radial; it projects1 mm above the lid, leaving0.65 mm after recorded maximum travel. Actual restart H, contact height, inward cap retention and physical sliding/return checks remain open.
- Latest mounting revision is **Designed prototype; CAD checks passed**: four removable cradles with rectangular housing pockets, bearing seats, terminal reliefs, open wire chambers and Ø6 trial round wire exits. Lid posts and Ø2.4 clearance / Ø1.8 pilot holes provide a trial screw attachment; fasteners and strength remain unverified. Intended press path is housing → cradle seat/columns/fasteners → lid; positive housing/tab keepers are still needed. PTT/power pockets and seat depths are adjustable trial values, not confirmed component fits. Owner-confirmed spare reset B is a separate two-part module with Ø4 recessed access, alongside cap option A. Onshape collision guards pass; minimum power/reset cradle gap0.60 mm and base/sleeve gap0.20 mm. See dimension sheet for defaults, drawing provenance and physical checks. Next: confirm actual housings/TS365ZJ H, update pockets/seats and add keepers before physical testing.
- Owner-requested assembled view is **Designed; static CAD check passed** in Onshape `SWS assembled prototype - corrected base`: 12 instances, comprising nine main parts and three separate test articles. The actual corrected-base source is centred in the sleeve with posts upward; the lid, cradles and reset cap retain seated poses. Knob underside z60.5 is a nominal drawing-based installation pose, requiring confirmed encoder seating/engagement. Six connectors, four Fastened mates and two Groups anchor the layout without Fix flags or visible mate warnings. Native whole-assembly interference detection reports **No interferences** among modelled solids. Sources unchanged. See `mechanical/SWS_ASSEMBLY.md` for the live link, datums and evidence. Actual controls/electronics/wires are absent; physical fit, motion, fasteners, keepers and base retention remain open.

- Speaker-grille continuation, 2026-10-10: **Designed prototype; CAD checks passed**. Owner supplied35 ×25 ×6.2 mm for each of two speakers from AliExpress item1005006494531366; these dimensions were not independently measured/drawing-verified. Feature Studio 1 now cuts five rounded27 ×2.4 mm slots at each upper corner, with two central3 ×16 mm cooling vents. Optional speaker clearance boxes check against lip, controls and the base reference without solid interference. Saved model retains11 parts; the updated12-instance assembly reports **No interferences**. Source is synchronized with the repo. Retention remains **Under Evaluation**: outlet registration, bearing/mounting features, protrusions and wire exits are unknown. Speakers cover the acoustic-slot footprints; free central vent area is approximately94.28 mm² versus432 mm² before, and thermal performance requires testing. See `mechanical/SWS_SPEAKER_MOUNTS.md`. Next: obtain those remaining features, design holders/wire relief and review electronics/cooling before physical validation. No fabrication or hardware test performed; electrical architecture/BOM variant unchanged.

- Speaker/port continuation, 2026-10-11: **Designed prototype; CAD checks passed**. Owner confirmed keeping both upper corners and routing both wire pairs to the right-side HAT pads shown in the supplied PCB image. Sleeve-integral2 mm shelves, low locating walls, support ribs and +X notches/open-bottom6 ×4 rib reliefs support that trial arrangement; speaker face gap is0.4 beneath the assembled lid. Positive retention, bearing surfaces, wire fit/strain relief and strength remain Under Evaluation. Added rounded Pi USB/Ethernet windows on the right, USB-C/shared dual-micro-HDMI window on the front and shared microSD/onboard-power-button access on the left, using official Pi 5 STEP/drawing datums and prototype allowances. Windows assume PCB underside at z7; the new seat parameter moves windows only and must match actual posts. Default11 parts and visible-envelope0/10 configurations13 parts regenerate; source matches live Feature Studio. The12-instance/12-mate assembly again reports **No interferences**. Actual Pi/HAT/cooler/components, cables and wires are absent; no physical test or fabrication performed. See `mechanical/SWS_PORT_OPENINGS.md` and the updated speaker record. Next: establish the actual electronics stack, cable plugs and speaker bearing/exit geometry, add retention/fastening and perform owner-authorised fit/thermal testing. Electrical/BOM architecture unchanged.

- Rack revision,2026-10-13 (T-006): **Designed prototype; current default CAD/mesh checks passed; physical fit/load capacity Under Evaluation**. Latest owner clarification supersedes bare-Pi/sliding-base variants: carry the COMPLETE SWS enclosure/electronics on A1/PLA and use exactly TWO horizontal insertion sticks in ONE vertical slot column, not side-by-side rack holes. Both sticksX0, centresZ26/87, pitch61,60 reach,Ø3 transverse tip holes with2 mm rim-to-tip stock. Current120 ×90 ×8 cradle has two separate8 mm braces, flat nut seats, low lateral/corner stops, four54 mm spacers and two removable lid-perimeter clamps. `sws_rack_enclosure_carrier.fs` matches live347-line source; assembled20 parts and oriented print13 parts regenerate with modeled-solid collision guards. Individual fine-mm STLs and13 closed-mesh/bounds checks saved under `mechanical/print_jobs/20261013/`; slicer outcome is recorded in that job/handoff. Planning payload305 g, allowance500 g, carrier solid PLA estimate212 g; total rack-load DESIGN TARGET2 kg is untested, not a rating. Rack51.3 datum/interior, slot seating, selectedM4 hardware/retained pins, plug boots, internal enclosure retention, creep/temperature and centred/off-centre proof tests remain open. Existing enclosure/corrected base preserved; former source is a Superseded experimental snapshot. Next: owner-authorised empty fit/hardware checks and inert-load proof before electronics. See `mechanical/SWS_RACK_CARRIER.md` and `coordination/handoffs/20261013-T-006-full-enclosure-rack.md`.
- Encoder fit,2026-10-13: owner printed the coupon and selected the middle bore. Source identifies it asØ6.2 D-bore (0.20 diametral allowance, nominal D flat-to-opposite tangent4.7). Live knob instance already has0.20 allowance; **Selected by owner coupon fit**, production knob push travel/retention remains untested.
- Rack-reference edge correction,2026-10-13: highlighted0.6 mm stock belongs to the assumed metal-rack reference plates. Extended their top edges1.4 to leave2 above the upper rounded slots; both labelled reference-only/not printable. Printable keeper already has4.7 above its opening and spine window2.8;13 structural STL files remain unchanged. Current347-line source matches live;20-part default regeneration passed. This reference edit does not establish real metal or printed strength.

### Documentation track

- **Expo 2030 deck (presentation 2026-10-14):** slide-12 projector screenshots captured 2026-10-11 in `Expo2030_Presentaion/screenshots/` (status panel, voice-opened divider schematic, zoomed PDF). They were inserted on 2026-10-11 (PC, `build_expo.py`), with captions. The status panel was then retaken at 21:09 (Ohm's law turn, same filename) and the deck rebuilt with it the same evening (PC; handoff `coordination/handoffs/20261011-expo-slide12-screenshots-pc.md` done). 2026-10-13 (PC): the owner's desk photo (`camera_photo.jpg`) fills the fourth frame. Morph zoom slides 12–16 zoom into each picture and back out. The team slide is removed and the contents renumbered 01–06; the problem and idea slides are rewritten; «جهاز الإسقاط» is now «البروجكتر»; the data counter shows 28 analysed replies (was 77 tests); the deck now has 18 slides. Still needed: slide 8's Expo track and challenge (the alignment slide).
- **Display rotated 180° (2026-10-11)** for the projector stand: `transform 180` in the kanshi profile. Touch mapping must use the same rotation.
- **Public showcase repo `Atlas_SWS` (2026-10-16, PC):** the Academy form asks for a project link. This repo stays private; `scripts/export_public_repo.py` builds a curated copy with fresh history (agent files, Expo deck, legacy/ESP32 docs, decision log, wake-word training, Academy build tools and the duplicate STL folder are left out). README and PROJECT map refreshed to 2026-10-16.

- **Academy package** (`academy/SmartWorkingStation_OmarShubayr/`, built by `python academy/build_submission.py`), prepared 2026-09-22, refreshed 2026-10-01. The workbook is filled (name, description, category إلكترونيات, 21-part BOM, HAT parts cross-checked against the EasyEDA BOM). The idea PDF is regenerated with current progress. EasyEDA schematic/layout JSON, BOM CSV and Gerber zip (2026-09-27) are in `PCB/`. **Missing:** schematic PDF, PCB pictures/3D, datasheets, project photos, and 3D design.
- ~~Formal BOM update~~ — done in the Academy workbook 2026-09-22: the actual Pi 5 4 GB / 32 GB, the received Caiwei projector (cost delta unknown), no PAM8403, no 3.5mm mic, no camera. Camera-era files stay in `docs/legacy-camera/` as history.
- **Master instructions** — several sections still describe the pre-2026-09-22 state (see the banner at the top of that file); fold in the items above.
