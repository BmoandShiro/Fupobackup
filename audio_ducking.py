# audio_ducking.py
import time
import pyaudio
import numpy as np
import threading
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


def smooth_adjust_volume(target_volume, volume, step=0.05, delay=0.1):
    current_volume = volume.GetMasterVolumeLevelScalar()
    while current_volume > target_volume:
        current_volume -= step
        if current_volume <= target_volume:
            current_volume = target_volume
        volume.SetMasterVolumeLevelScalar(current_volume, None)
        time.sleep(delay)






def restore_original_volume(volume, original_db):
    volume.SetMasterVolumeLevel(original_db, None)

def get_microphone_level(stream, chunk_size=5000):
    data = np.frombuffer(stream.read(chunk_size), dtype=np.int16)
    return np.average(np.abs(data))

def monitor_and_adjust_volume(volume, threshold_db, volume_level_db, stop_event):
    audio_interface = pyaudio.PyAudio()
    stream = audio_interface.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    original_volume_level = volume.GetMasterVolumeLevelScalar()  # Get the current volume level
    reduce_volume_level = original_volume_level / 2
    volume_adjusted = False

    try:
        while not stop_event.is_set():
            level = get_microphone_level(stream)

            # Debug statement to monitor microphone level
            print(f"Microphone Level: {level} dB")

            if level > threshold_db and not volume_adjusted:
                volume.SetMasterVolumeLevelScalar(reduce_volume_level, None)  # Set to target volume level
                volume_adjusted = True

            elif level <= threshold_db and volume_adjusted:
                volume.SetMasterVolumeLevelScalar(original_volume_level, None)  # Restore original volume level
                volume_adjusted = False

    finally:
        stream.stop_stream()
        stream.close()
        audio_interface.terminate()



        

def _get_endpoint_volume():
    """Get IAudioEndpointVolume for default speakers. Prefer EndpointVolume (modern pycaw)."""
    device = AudioUtilities.GetSpeakers()
    volume = getattr(device, "EndpointVolume", None)
    if volume is not None:
        return cast(volume, POINTER(IAudioEndpointVolume))
    if getattr(device, "Activate", None) is not None:
        iface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(iface, POINTER(IAudioEndpointVolume))
    return None


def print_audio_device_info():
    device = AudioUtilities.GetSpeakers()
    volume = _get_endpoint_volume()
    if volume is None:
        print("Could not get volume interface.")
        return
    device_name = getattr(device, "FriendlyName", None) or getattr(device, "GetDeviceFriendlyName", lambda: "Unknown")()
    device_id = getattr(device, "GetId", lambda: "")()
    print(f"Default Audio Playback Device: {device_name}")
    print(f"Device ID: {device_id}")


if __name__ == "__main__":
    threshold_db = 30  # Adjust this threshold to your preference

    volume = _get_endpoint_volume()
    if volume is None:
        print("Could not get volume interface (pycaw). Check EndpointVolume / Activate.")
        raise SystemExit(1)

    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_and_adjust_volume, args=(volume, threshold_db, 0.5, stop_event))

    monitor_thread.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        stop_event.set()
        monitor_thread.join()


