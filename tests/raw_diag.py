import subprocess
import numpy as np

print("Capturing 1 second of raw hardware frames...")
subprocess.run("arecord -D hw:2,0 -c 2 -r 48000 -f S32_LE -d 1 raw.pcm", shell=True, check=True)

raw_bytes = open("raw.pcm", "rb").read()
data = np.frombuffer(raw_bytes, dtype=np.int32)

left = data[0::2]
right = data[1::2]

print("\n--- SAMPLE INSPECTION (First 5 Left Channel Frames) ---")
for i in range(min(5, len(left))):
    val = int(left[i]) & 0xFFFFFFFF
    print(f"Decimal: {left[i]:<12} | Hex: 0x{val:08X} | Binary: {val:032b}")

print("\n--- SIGNAL STATUS ---")
if len(left) == 0:
    print("STATUS: NO DATA RECORDED.")
elif np.all(left == left[0]):
    print("STATUS: DEAD LINE. Data pin is locked at a fixed voltage level.")
else:
    # Check if bit 30 (0x40000000) is set across all samples
    bit30_set = np.all((left.astype(np.uint32) & 0x40000000) != 0)
    if bit30_set:
        print("STATUS: FLOATING / UNGROUNDED. Bit 30 is stuck HIGH. Check L/R pin and SD jumper wire.")
    else:
        print("STATUS: DYNAMIC SIGNAL DETECTED. Data stream is active.")
