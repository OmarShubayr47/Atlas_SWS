import pyaudio
import numpy as np
import wave

FORMAT = pyaudio.paInt32
CHANNELS = 2
RATE = 48000
CHUNK = 1024
RECORD_SECONDS = 3

p = pyaudio.PyAudio()

# Open Google VoiceHAT capture
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                input=True, input_device_index=0, frames_per_buffer=CHUNK)

print("Recording 3 seconds... Talk into the microphone!")
frames_left = []

for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK, exception_on_overflow=False)
    raw32 = np.frombuffer(data, dtype=np.int32)
    
    # Extract Left channel (even indices)
    left = raw32[0::2]
    
    # INMP441 outputs 24-bit data in MSB format.
    # Mask out the floating MSB driver bit (0x40000000) and shift right by 14
    # To fix sign-extension for 16-bit PCM:
    shifted = ((left & 0x00FFFFFF) >> 8).astype(np.int16)
    
    frames_left.append(shifted.tobytes())

print("Recording done. Saving to clean_test.wav...")

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open("clean_test.wav", "wb")
wf.setnchannels(1)
wf.setsampwidth(2)
wf.setframerate(RATE)
wf.writeframes(b"".join(frames_left))
wf.close()

print("File saved! Testing direct ALSA playback...")
