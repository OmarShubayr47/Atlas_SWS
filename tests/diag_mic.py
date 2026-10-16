import subprocess
import numpy as np
import wave
import os

print("--- STEP 1: Capturing 3 seconds of raw 32-bit I2S data directly via ALSA ---")
cmd = "arecord -D hw:2,0 -c 2 -r 48000 -f S32_LE -d 3 raw_capture.raw"
subprocess.run(cmd, shell=True)

if not os.path.exists("raw_capture.raw"):
    print("Error: Capture failed. Check ALSA connection.")
    exit(1)

# Read raw bytes into numpy array
raw_bytes = open("raw_capture.raw", "rb").read()
data = np.frombuffer(raw_bytes, dtype=np.int32)

print("\n--- STEP 2: Channel RMS Power Diagnostics ---")
left = data[0::2]
right = data[1::2]

rms_left = np.sqrt(np.mean(np.square(left.astype(np.float64))))
rms_right = np.sqrt(np.mean(np.square(right.astype(np.float64))))

print(f"Left Channel RMS Level  : {rms_left:.2f}")
print(f"Right Channel RMS Level : {rms_right:.2f}")

active_channel = left if rms_left >= rms_right else right
channel_name = "LEFT" if rms_left >= rms_right else "RIGHT"
print(f"--> Active mic signal detected on: {channel_name} channel")

print("\n--- STEP 3: Generating Shift Bit Test Files ---")
# Try different bit-shifts to find the clean 24-bit to 16-bit window
for shift in [8, 12, 14, 16]:
    shifted = active_channel >> shift
    clipped = np.clip(shifted, -32768, 32767).astype(np.int16)
    
    fname = f"test_shift_{shift}.wav"
    wf = wave.open(fname, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(48000)
    wf.writeframes(clipped.tobytes())
    wf.close()
    print(f"Generated: {fname}")

print("\nDone! Test files created.")
