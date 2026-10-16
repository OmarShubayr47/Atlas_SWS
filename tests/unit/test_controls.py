"""Phase 1/2 logic: speech volume, the output gain stage, the keep-alive
player's reply statistics and cancel, liveness, sd_notify, restart tiers.

These run without hardware. The keep-alive tests play into ALSA's "null"
device, which accepts audio and discards it at the real-time rate.
"""
import json
import socket
import threading
import time

import numpy as np
import pytest

from common import keepalive_output, liveness, sd_notify, speech_volume


# --- speech volume ------------------------------------------------------------

def make_volume(tmp_path, **kw):
    return speech_volume.SpeechVolume(state_path=tmp_path / "volume.json", **kw)


def test_volume_steps_and_clamps(tmp_path):
    vol = make_volume(tmp_path)
    assert vol.level_db() == 0.0 and vol.percent() == 100
    vol.step(-3)
    assert vol.level_db() == -6.0
    vol.step(+10)                       # cannot go above the verified level
    assert vol.level_db() == 0.0
    vol.step(-100)                      # bottom step
    assert vol.level_db() == vol.min_db and vol.percent() == 0
    assert vol.silent() and vol.gain_db() is None   # 0 % is silence


def test_mute_and_unmute_by_turning(tmp_path):
    vol = make_volume(tmp_path)
    vol.step(-2)
    assert vol.toggle_mute() is True
    assert vol.silent() and vol.gain_db() is None
    vol.step(+1)                        # turning unmutes from the remembered level
    assert not vol.muted() and vol.level_db() == -2.0


def test_level_is_saved_and_reloaded_but_mute_is_not(tmp_path, monkeypatch):
    monkeypatch.setattr(speech_volume, "SAVE_DELAY_S", 0.05)
    vol = make_volume(tmp_path)
    vol.step(-4)
    vol.toggle_mute()
    time.sleep(0.3)
    data = json.loads((tmp_path / "volume.json").read_text())
    assert data["level_db"] == -8.0 and "saved" in data
    again = make_volume(tmp_path)
    assert again.level_db() == -8.0 and not again.muted()


def test_corrupt_state_file_is_ignored(tmp_path):
    (tmp_path / "volume.json").write_text("{not json")
    assert make_volume(tmp_path).level_db() == 0.0


# --- gain stage ---------------------------------------------------------------

class FixedVolume:
    def __init__(self, db):
        self.db = db

    def gain_db(self):
        return self.db


def tone(n=2400, amp=0.25):
    t = np.arange(n) / 24000
    return (np.sin(2 * np.pi * 440 * t) * amp * 32767).astype("<i2").tobytes()


def rms(pcm):
    x = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    return np.sqrt(np.mean(x ** 2))


def test_gain_stage_realigns_split_samples():
    stage = keepalive_output.GainStage()
    pcm = tone(100)
    out = stage.process(pcm[:51]) + stage.process(pcm[51:])
    assert out == pcm                   # 0 dB, no volume: bit-exact


def test_gain_stage_mute_is_exact_zeros():
    stage = keepalive_output.GainStage(12.0, FixedVolume(None))
    out = stage.process(tone())
    assert out == bytes(len(out)) and len(out) == len(tone())


def test_gain_stage_attenuation_matches_db():
    pcm = tone()
    out = keepalive_output.GainStage(0.0, FixedVolume(-6.0)).process(pcm)
    ratio_db = 20 * np.log10(rms(out) / rms(pcm))
    assert ratio_db == pytest.approx(-6.0, abs=0.1)


# --- keep-alive player (ALSA null device) ---------------------------------------

def test_reply_stats_and_no_gaps_when_fed_fast(capsys):
    out = keepalive_output.KeepAliveOutput("null")
    out.begin()
    for _ in range(10):                 # 1 s of audio, delivered at once
        out.write(tone())
    out.drain()
    line = [ln for ln in capsys.readouterr().out.splitlines() if "Reply audio" in ln][-1]
    assert "Reply audio 1.00 s" in line and "gaps 0 (0 ms)" in line


def test_gaps_counted_when_delivery_is_slower_than_playback(capsys):
    out = keepalive_output.KeepAliveOutput("null")
    out.begin()
    for _ in range(4):                  # 0.1 s of audio every 0.3 s
        out.write(tone())
        time.sleep(0.3)
    out.drain()
    line = [ln for ln in capsys.readouterr().out.splitlines() if "Reply audio" in ln][-1]
    gaps = int(line.split("gaps ")[1].split(" ")[0])
    assert gaps >= 3


def test_cancel_discards_until_next_begin(capsys):
    out = keepalive_output.KeepAliveOutput("null")
    out.begin()
    out.write(tone())
    out.cancel()
    assert "[CANCELLED]" in capsys.readouterr().out
    out.write(tone())                   # ignored: still the cancelled reply
    t0 = time.monotonic()
    out.drain()                         # returns at once after a cancel
    assert time.monotonic() - t0 < 0.1
    out.begin()                         # the next reply plays normally
    out.write(tone())
    out.drain()
    assert "Reply audio 0.10 s" in capsys.readouterr().out


# --- liveness ------------------------------------------------------------------

def test_liveness_turn_stall_and_wake_word_stall():
    live = liveness.Liveness(turn_stall_s=0.1, wake_word_stall_s=0.1)
    assert live.healthy()               # idle, nothing watched
    live.turn_started()
    time.sleep(0.15)
    assert not live.healthy()           # no progress
    live.turn_progress()
    assert live.healthy()
    live.turn_finished()
    live.wake_word_progress()
    time.sleep(0.15)
    assert not live.healthy()           # listener stopped reading
    live.wake_word_progress()
    assert live.healthy()


# --- sd_notify -----------------------------------------------------------------

def test_sd_notify_noop_without_systemd(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert sd_notify.notify("READY=1") is False


def test_sd_notify_sends_datagram(tmp_path, monkeypatch):
    path = str(tmp_path / "notify.sock")
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(path)
        monkeypatch.setenv("NOTIFY_SOCKET", path)
        assert sd_notify.notify("WATCHDOG=1") is True
        assert server.recv(64) == b"WATCHDOG=1"
    monkeypatch.setenv("WATCHDOG_USEC", "60000000")
    assert sd_notify.watchdog_interval_s() == 30.0


# --- restart button tiers ------------------------------------------------------

class FakeButton:
    is_pressed = True


def test_restart_tiers(monkeypatch, capsys):
    import restart_button as rb
    monkeypatch.setattr(rb, "REBOOT_HOLD_S", 0.3)
    tiers = rb.TieredRestart(FakeButton(), dry_run=True, reboot_allowed=True)

    tiers.on_press()                    # released early: nothing
    tiers.on_release()
    assert "released early" in capsys.readouterr().out

    tiers.on_press()                    # held, then released: software restart
    tiers.on_held()
    tiers.on_release()
    time.sleep(0.4)                     # reboot timer must NOT fire
    out = capsys.readouterr().out
    assert "systemctl --user restart" in out and "/sbin/reboot" not in out

    tiers.on_press()                    # held through the reboot time
    tiers.on_held()
    time.sleep(0.5)
    out = capsys.readouterr().out
    assert "would now run: sudo -n /sbin/reboot" in out
    tiers.on_release()                  # releasing after a reboot does nothing more
    assert "systemctl" not in capsys.readouterr().out
