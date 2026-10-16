# Smart Working Station (Atlas)

A projected interactive workstation. A Raspberry Pi 5 projects a user interface onto a flat work surface. A 32-inch PCAP touch foil will turn that surface into a touchscreen. A voice assistant called **Atlas**, started by the wake word "Hey Atlas" or a push-to-talk button, answers questions about the project, opens files and drawings on the projected surface, and draws template schematics by voice.

Tuwaiq Academy — تصميم وتصنيع الحلول الهندسية V5 · Omar Shubayr

> This public repository is a curated snapshot of the project. The dated engineering decision log, internal coordination files and competition material are kept in a separate private working repository.

## Status (2026-10-16)

Labels follow the project's evidence rule: **Designed** (drawn or specified), **Implemented** (built or coded), **Tested** (checked in isolation), **Verified** (confirmed working in the real system).

| Subsystem | Status |
|---|---|
| Voice assistant (wake word / PTT → speech-to-text → LLM with restricted project tools → streamed speech) | **Verified** end to end on the Pi with "Hey Atlas" and a full spoken reply from the projector (2026-09-29). Owner test 2026-10-01 verified push-to-talk, the volume knob, an Arabic command, and voice-driven schematics and file viewer. Open: short audio cutouts during replies (cause measured: bursty speech delivery; jitter-buffer fix proposed) and counted wake-word reliability |
| Always-on services | **Tested**: assistant, UI server, restart button and kiosk run as systemd user services, restart after a crash or hang, and start on a cold boot |
| Projected UI and file viewer (Chromium kiosk) | **Verified** on the projector: status panel, and files and schematics opened by voice. Touch-ready zoom and pan; touch input itself not yet connected |
| Template schematics by voice | **Tested** with unit tests and a spoken owner test: 8 circuit templates; every value is computed in Python and snapped to standard E-series values |
| Restart button (GPIO27) | **Verified** reboot (2026-09-21). Two-tier hold (2 s restarts the software, 8 s reboots) is unit-tested; physical tier test pending |
| Projector (CAIWEI A12AB, 1920×1080) | **Tested**: native resolution, throw ratio 1.28–1.36, overscan fixed with computer (CVT) timing. Focus at ~1 m and the projector mount are under evaluation |
| Audio output | Projector speakers over HDMI **Verified** for a full reply. The permanent design is the custom HAT with 2 × MAX98357A (stereo); one bench amplifier tested in mono |
| Custom HAT PCB (2 × MAX98357AETE+T, controls) | **Designed**, under instructor review; not fabricated. Open before fabrication: dedicated amplifier power input, gain selection bench test, LED resistor values |
| Enclosure, controls, speaker mounts and rack carrier | **Designed** in Onshape with CAD interference checks passing; carrier parts exported as STL for a Bambu A1. Encoder knob bore selected by a printed test coupon. Physical fit and load capacity under evaluation |
| PCAP touch foil (ILITEK 2510 USB) | Not yet tested |

Detailed status and open items: [`docs/SWS_project_status.md`](docs/SWS_project_status.md).

## Architecture

```text
USB microphone ──► Raspberry Pi 5 ──► I2S ──► HAT: 2 × MAX98357A ──► left / right speakers
PCAP touch foil ─►   (Python)     ──► HDMI ─► projector (UI + speech today)
Buttons / encoder ─► GPIO
```

- **Wake word / PTT:** openWakeWord ("Hey Atlas") runs on the Pi, or the button on GPIO22. Both feed one shared turn path, and the microphone is claimed so the two cannot collide.
- **Speech pipeline:** webrtcvad detects end of speech → cloud STT → LLM with an allowlist of typed tools → cloud TTS streamed to the speakers.
- **Tools, never a shell:** the assistant can read project files (`.env` is always denied), show files on the projector, create notes in `~/SWS_Workspace` (create-only: no overwrite, delete or run) and draw template schematics. Path checks live in `software/tools/safety.py`.
- **UI:** the assistant posts state events to a loopback-only server (`software/ui/server.py`). A Chromium kiosk subscribes over Server-Sent Events, so the display can never stall the assistant.
- **Separate processes:** the restart button and the UI server run apart from the assistant, so a hung assistant cannot take them down.

## Repository layout

| Path | Purpose |
|---|---|
| `software/voice_assistant.py` | Main assistant (OpenAI HTTP pipeline) |
| `software/voice_realtime.py` | Experimental speech-to-speech path (OpenAI Realtime); not yet validated |
| `software/voice_control.py` | Older Groq-based fallback; silent on current hardware (does not drive AMP_EN) |
| `software/restart_button.py` | Restart-button daemon (GPIO27: hold 2 s + release → restart the software; hold 8 s → orderly reboot) |
| `software/common/` | Hardware and audio helpers: mic stream, VAD recorder, wake word, amp enable, audio-device lookup by name, encoder, volume, UI events |
| `software/tools/` | Tools the LLM may call, and their path-safety checks |
| `software/schematic/` | Template schematics: value parsing / E-series, 8 circuit templates (schemdraw), SVG rendering, revisions |
| `software/ui/` | UI server, kiosk launcher, web page and file viewer, kanshi display profile |
| `software/deploy/` | systemd user units and `install_services.sh` |
| `software/models/` | Bundled Hey Atlas wake-word model, with its source and noncommercial-use notice |
| `tests/` | Hardware diagnostics and bench tests (mic, amp, encoder, buttons, projector patterns, latency); unit tests in `tests/unit/` |
| `mechanical/` | Onshape FeatureScript sources (`.fs`), design records for the enclosure, controls, speaker mounts, port openings and rack carrier, and STL print files |
| `academy/SmartWorkingStation_OmarShubayr/` | Tuwaiq Academy deliverable folder: idea PDF, project workbook, PCB schematic/layout (EasyEDA JSON), BOM and Gerber files |
| `docs/` | Project status, PCB design decisions, projector mount and control-dimension records |

## GPIO map (HAT design)

| GPIO | Pin | Function |
|---|---|---|
| 18 / 19 / 21 | 12 / 35 / 40 | I2S BCLK / LRCLK / DIN |
| 26 | 37 | AMP_EN (amp enable + left/right select) |
| 22 | 15 | AI / push-to-talk button |
| 24 | 18 | AI button LED |
| 5 / 6 | 29 / 31 | Encoder A / B (volume) |
| 13 | 33 | Encoder push (mute) |
| 27 | 13 | Restart button |

The power button is not a GPIO: it is wired to the Pi 5 J2 pads. GPIO20 is claimed by the `hifiberry-dac` overlay; GPIO0/1 are reserved for the HAT EEPROM.

## Running on the Pi

Everything starts at boot as systemd **user** services and restarts itself if it crashes or hangs:

```bash
software/deploy/install_services.sh             # once: install, enable, start
systemctl --user status 'sws-*'                 # sws-ui, sws-assistant, sws-restart, sws-kiosk
journalctl --user-unit=sws-assistant -f         # live assistant log
software/deploy/install_services.sh --uninstall # remove the services again
```

For a manual test run, stop the service first. Otherwise two copies fight over the GPIO pins, the microphone and the HDMI audio device:

```bash
systemctl --user stop sws-assistant
.venv/bin/python software/voice_assistant.py
systemctl --user start sws-assistant
```

Python dependencies are in `requirements.txt`. Unit tests: `.venv/bin/python -m pytest tests/unit -q`.

**Configuration** lives in `.env` (never committed). Required: `OPENAI_API_KEY`. The Groq fallback also needs `GROQ_API_KEY`. Optional overrides include `STT_MODEL`, `CHAT_MODEL`, `TTS_MODEL`, `TTS_VOICE`, `WAKE_WORD`, `MIC_NAME_HINT`, `AMP_NAME_HINT`, `PLAYBACK_PCM`, `SPEECH_GAIN_DB` and the `*_PIN` settings. Audio devices are found by name, never by ALSA card number.

`WAKE_WORD` defaults to `hey_atlas` in all three assistant entry points. The
[bundled model](software/models/README.md) is a third-party model used for
noncommercial personal and Academy demonstrations. Detection stays on-device.
Set `WAKE_WORD=hey_jarvis` to select the previous installed model, or
`WAKE_WORD_ENABLED=0` for button-only use; restart the assistant after a
configuration change. Software checks: `.venv/bin/python tests/test_wake_word.py`
(no microphone or cloud calls).

**Pi system configuration outside this repo:** `dtoverlay=hifiberry-dac` in the boot config. The display profile `software/ui/kanshi-projector.conf` is installed to `~/.config/kanshi/config`; it sends CVT timing so the projector does not overscan, and rotates the image 180° for the projector stand.
