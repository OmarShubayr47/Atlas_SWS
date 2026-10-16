import pyaudio
import numpy as np
import wave

FORMAT = pyaudio.paInt32
CHANNELS = 2
RATE = 48000
CHUNK = 1024
RECORD_SECONDS = 5
OUTPUT_FILENAME = "clean_mic.wav"

audio = pyaudio.PyAudio()

# Find Google VoiceHAT card (Card 2)
device_index = None
for i in range(audio.get_device_count()):
    dev = audio.get_device_info_by_index(i)
    name = dev['name'].lower()
    if dev['maxInputChannels'] > 0 and ('googlevoice' in name or 'voicehat' in name or 'hw:2,0' in name or 'plughw:2,0' in name):
        device_index = i
        print(f"Using Capture Hardware: {dev['name']} (Index {i})")
        break

if device_index is None:
    # Fallback to explicit ALSA hardware address if PyAudio string lookup fails
    print("Selecting ALSA plughw:2,0 directly...")
    device_index = 2

print(f"\n---> Speaking into the microphone for {RECORD_SECONDS} seconds...")

stream = audio.open(format=FORMAT, 
                    channels=CHANNELS,
                    rate=RATE, 
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=CHUNK)

frames = []

for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK, exception_on_overflow=False)
    
    # 1. Convert raw bytes to 32-bit signed integers
    audio_data = np.frombuffer(data, dtype=np.int32)
    
    # 2. Extract Left channel (even indices [0::2])
    left_channel = audio_data[0::2]
    
    # 3. Bit-shift 14 bits to convert 24-bit MSB-aligned data into clean 16-bit range
    shifted = left_channel >> 14
    
    # 4. Clip to 16-bit signed boundaries to prevent overflow static
    clipped = np.clip(shifted, -32768, 32767).astype(np.int16)
    
    frames.append(clipped.tobytes())

print("---> Recording finished!")

stream.stop_stream()
stream.close()
audio.terminate()

# Write mono 16-bit PCM WAV file
wf = wave.open(OUTPUT_FILENAME, 'wb')
wf.setnchannels(1)
wf.setsampwidth(2)
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print(f"Clean audio file written to: {OUTPUT_FILENAME}")
