# Hey Atlas wake-word model

`hey_atlas.onnx` detects the spoken English phrase **Hey Atlas**. It is an
unmodified third-party openWakeWord model by Brian Kelley (`briankelley`),
bundled for this project's noncommercial personal and Academy demonstrations.

- Source: [atlas-voice-training](https://github.com/briankelley/atlas-voice-training)
- Release: [hey_atlas-v1](https://github.com/briankelley/atlas-voice-training/releases/tag/hey_atlas-v1)
- [Original ONNX download](https://github.com/briankelley/atlas-voice-training/releases/download/hey_atlas-v1/hey_atlas.onnx)
- Retrieved: 2026-09-29; GitHub asset ID: `434409795`; size: 205430 bytes.
- SHA-256 (matches the GitHub release API's asset digest):
  `ea196d0e182fad1b09fb6c58376c2a079675798688aac3766c312475cf4113e6`

## Attribution and noncommercial-use notice

The author's [license notice](https://github.com/briankelley/atlas-voice-training#license)
states that ACAV100M training features are licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), and that
trained models inherit a noncommercial restriction. MUSAN data is listed as
CC BY 4.0. The repository's Apache 2.0 license describes its training scripts
and configuration; do not describe this model as unrestricted Apache 2.0.
Preserve this attribution, source links and restriction when copying the model.
The owner selected it for noncommercial use. No model modifications were made.

## Runtime and verification

The shared listener resolves `WAKE_WORD=hey_atlas` relative to its own source
file, so it works independently of the launch directory. Detection runs on
the Pi with ONNX/CPU through the existing openWakeWord installation. There
is no runtime model download or training dependency.

The author's release reports 81% accuracy, 62% recall and 55% precision;
these are upstream results, not measurements on this Pi or the owner's voice.
Start with the existing detection threshold of 0.5. Model loading and synthetic
audio checks do not verify spoken detection. Local test results so far: the
2026-09-29 guided test gave three detections in a 25-second "Hey Atlas" window
and none in a 20-second negative window, and a full Atlas-triggered
conversation was verified; counted recall and false-activation rates are still
open. Latest results: `docs/SWS_project_status.md`.
