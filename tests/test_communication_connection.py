import struct
import threading
import time

from libpebble2.communication import PebbleConnection
from libpebble2.communication.transports import BaseTransport, MessageTarget, MessageTargetWatch
from libpebble2.exceptions import ConnectionError
from libpebble2.protocol.base import PebblePacket
from libpebble2.protocol.system import (
    ModelResponse,
    WatchFirmwareVersion,
    WatchModel,
    WatchVersion,
    WatchVersionResponse,
)
from libpebble2.util.hardware import PebbleHardware


class DummyTransport(BaseTransport):
    def __init__(self):
        self._connected = False
        self._in = []
        self._sent = []
        self.must_initialise = False

    @property
    def connected(self):
        return self._connected

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def read_packet(self):
        if not self._in:
            raise ConnectionError("no data")
        return self._in.pop(0)

    def send_packet(self, message, target=None):
        self._sent.append((target, message))


def frame(pkt: PebblePacket) -> bytes:
    return pkt.serialise_packet()


def test_pump_reader_and_pending_bytes_parsing():
    t = DummyTransport()
    pc = PebbleConnection(t)
    pc.connect()
    # Build a watch version response
    wvr = WatchVersion(
        data=WatchVersionResponse(
            running=WatchFirmwareVersion(
                timestamp=0,
                version_tag="v3.1.2",
                git_hash="deadbeef",
                is_recovery=False,
                hardware_platform=PebbleHardware.SNOWY_DVT,
                metadata_version=0,
            ),
            recovery=WatchFirmwareVersion(
                timestamp=0,
                version_tag="v0",
                git_hash="00000000",
                is_recovery=False,
                hardware_platform=0,
                metadata_version=0,
            ),
            bootloader_timestamp=0,
            board="",
            serial="",
            bt_address=b"\x00" * 6,
            resource_crc=0,
            resource_timestamp=0,
            language="en",
            language_version=0,
            capabilities=0,
            is_unfaithful=None,
        )
    )
    framed = frame(wvr)
    # Chop the frame to force pending_bytes path: deliver first half, then second
    half = len(framed) // 2
    t._in.append((MessageTargetWatch(), framed[:half]))
    t._in.append((MessageTargetWatch(), framed[half:]))

    # Register a waiter first so the incoming reply is captured, then pump.

    out = {}

    def _read_major():
        out["major"] = pc.firmware_version.major

    th = threading.Thread(target=_read_major, daemon=True)
    th.start()
    time.sleep(0.01)  # tiny yield to ensure the waiter is set up
    pc.pump_reader()
    pc.pump_reader()
    th.join(timeout=1)
    assert out.get("major") == 3
    assert pc.watch_platform == "basalt"


def test_send_and_read_queues_before_send():
    t = DummyTransport()
    pc = PebbleConnection(t)
    pc.connect()

    # Queue a response to be read from endpoint after send
    model_bytes = struct.pack(">I", 14)  # BobbySilver
    resp = WatchModel(command=1, data=ModelResponse(data=model_bytes, length=len(model_bytes)))
    t._in.append((MessageTargetWatch(), frame(resp)))

    holder = {}

    def get_model():
        holder["model"] = pc.watch_model

    th = threading.Thread(target=get_model, daemon=True)
    th.start()
    time.sleep(0.01)
    pc.pump_reader()
    th.join(timeout=1)
    assert "model" in holder
    from libpebble2.protocol.system import Model

    assert holder["model"] == 14 or holder["model"] == Model.BobbySilver


def test_run_sync_handles_decode_error_and_disconnect(caplog):
    t = DummyTransport()
    pc = PebbleConnection(t, log_packet_level=None, log_protocol_level=None)
    pc.connect()

    # Force a bad payload that triggers PacketDecodeError in _handle_watch_message
    t._in.append((MessageTargetWatch(), b"\x00\x00\xff\xffBAD"))
    # Ensure disconnect breaks loop
    t._in.append((MessageTarget(), b"nope"))  # not watch -> broadcast transport; still fine

    # then connection error
    def feeder():
        try:
            pc.run_sync()
        except Exception as e:
            raise AssertionError("run_sync must not raise") from e

    # Trigger reader once; after first read, PacketDecodeError is swallowed, then no more data -> ConnectionError
    thread = threading.Thread(target=feeder, daemon=True)
    # Arrange read_packet to raise ConnectionError after consuming the queued item
    orig = t.read_packet

    def rp():
        if t._in:
            return orig()
        raise ConnectionError("gone")

    t.read_packet = rp
    thread.start()
    time.sleep(0.05)
    assert not thread.is_alive()  # loop exited
