import subprocess
import numpy as np
import wave
import os

RAW_FILE = "capture.raw"
WAV_FILE = "speech_test.wav"
RECORD_SECONDS = 4
SAMPLERATE = 48000

print(f"--- Recording {RECORD_SECONDS} seconds of RAW PCM... Talk/clap now! ---")

# Record raw PCM (no WAV header) directly from HW 2,0
cmd = f"arecord -D hw:2,0 -c 2 -r {SAMPLERATE} -f S32_LE -t raw -d {RECORD_SECONDS} {RAW_FILE}"
subprocess.run(cmd, shell=True, check=True)

print("--- Processing 24-bit MEMS audio data ---")

# Read raw bytes
with open(RAW_FILE, "rb") as f:
    raw_data = f.read()

# Convert raw bytes into 32-bit integer array
data32 = np.frombuffer(raw_data, dtype=np.int32)

# De-interleave: Extract Left channel (even indices)
left_channel = data32[0::2]

# INMP441 alignment fix: 
# Shift right by 14 bits to convert 24-bit MSB aligned values to 16-bit signed PCM
pcm16 = (left_channel >> 14).astype(np.int16)

# Print real audio signal metrics
peak = np.max(np.abs(pcm16))
rms = np.sqrt(np.mean(np.square(pcm16.astype(np.float64))))
print(f"Signal Peak: {peak} / 32767 | Signal RMS: {rms:.1f}")

# Write clean Mono WAV file
with wave.open(WAV_FILE, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLERATE)
    wf.writeframes(pcm16.tobytes())

print(f"Saved clean audio to '{WAV_FILE}'")

# Clean up temporary raw file
if os.path.exists(RAW_FILE):
    os.remove(RAW_FILE)
