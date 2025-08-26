import sys
import threading
import time
import types
import uuid

import pytest
from libpebble2.exceptions import TimeoutError
from libpebble2.protocol.system import WatchFirmwareVersion, WatchVersionResponse


class FakeQueue:
    """Minimal queue for endpoint queues used by services."""

    def __init__(self, items):
        self._items = list(items)
        self.closed = False

    def get(self, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._items:
                return self._items.pop(0)
            time.sleep(0.001)
        raise TimeoutError()

    def close(self):
        self.closed = True

    def __iter__(self):
        while True:
            yield self.get()


class FakePebble:
    """
    Just enough of PebbleConnection to be useful in service tests.
    - register_endpoint stores callbacks by type
    - get_endpoint_queue returns injected queues
    - send_and_read can be stubbed per test.
    """

    def __init__(self):
        self._handlers = {}
        self._queues = {}
        self._next_handle = 1
        self.sent_packets = []
        self._send_and_read_script = []  # list of (expect_cls, return_obj)
        self._lock = threading.Lock()
        # minimal watch info defaults
        self.watch_info = WatchVersionResponse(
            running=WatchFirmwareVersion(
                timestamp=0,
                version_tag="v3.0.0".ljust(32, "\x00"),
                git_hash="deadbeef",
                is_recovery=False,
                hardware_platform=0,
                metadata_version=0,
            ),
            recovery=WatchFirmwareVersion(
                timestamp=0,
                version_tag="v3.0.0".ljust(32, "\x00"),
                git_hash="deadbeef",
                is_recovery=False,
                hardware_platform=0,
                metadata_version=0,
            ),
            bootloader_timestamp=0,
            board="".ljust(9, "\x00"),
            serial="".ljust(12, "\x00"),
            bt_address=b"\x00" * 6,
            resource_crc=0,
            resource_timestamp=0,
            language="en".ljust(6, "\x00"),
            language_version=0,
            capabilities=0,
            is_unfaithful=None,
        )

    # API used by services
    def register_endpoint(self, packet_cls, handler):
        handle = self._next_handle
        self._next_handle += 1
        self._handlers[packet_cls] = (handle, handler)
        return handle

    def unregister_endpoint(self, handle):
        for k, (h, _) in list(self._handlers.items()):
            if h == handle:
                del self._handlers[k]

    def get_endpoint_queue(self, packet_cls):
        return self._queues.pop(packet_cls)

    def queue_for(self, packet_cls, items):
        """Helper used in tests to prime a queue for a packet type."""
        from libpebble2.protocol.base import PebblePacket

        # items should be PebblePacket instances of the outer wrapper (e.g., GetBytes)
        assert all(isinstance(x, PebblePacket) for x in items)
        self._queues[packet_cls] = FakeQueue(items)

    def send_packet(self, pkt):
        self.sent_packets.append(pkt)

    def send_and_read(self, pkt, expect_cls, timeout=15):
        with self._lock:
            if not self._send_and_read_script:
                raise AssertionError("send_and_read script exhausted")
            exp, ret = self._send_and_read_script.pop(0)
            assert exp is expect_cls
            # We still record what was sent to let tests assert flow
            self.sent_packets.append(pkt)
            return ret

    def script_send_and_read(self, steps):
        """steps: list of (expect_cls, return_pkt)."""
        self._send_and_read_script = list(steps)

    # Helpers for tests to invoke registered handler
    def fire(self, packet):
        """Call the handler registered for type(packet)."""
        t = type(packet)
        # Find a handler for the exact class
        if t in self._handlers:
            self._handlers[t][1](packet)
            return
        # Or for its base in case registration was for outer envelope
        for k, (_, h) in self._handlers.items():
            if isinstance(packet, k):
                h(packet)
                return
        raise AssertionError(f"No handler for {t}")


@pytest.fixture
def fake_pebble():
    return FakePebble()


@pytest.fixture
def patch_websocket(monkeypatch):
    """Provide a fake websocket module before importing transport."""
    fake = types.SimpleNamespace(
        WebSocketException=Exception,
        ABNF=types.SimpleNamespace(OPCODE_BINARY=2, OPCODE_CLOSE=8),
    )

    class _WS:
        def __init__(self):
            self.connected = True
            self._in = []
            self.sent = []

        def send_binary(self, data):
            self.sent.append(data)

        def recv_data(self):
            if not self._in:
                raise AssertionError("No recv_data scripted")
            return self._in.pop(0)

        def close(self):
            self.connected = False

    fake._instance = _WS()

    def create_connection(url):
        return fake._instance

    fake.create_connection = create_connection
    sys.modules["websocket"] = fake
    return fake


@pytest.fixture
def patch_serial(monkeypatch):
    """Provide a fake serial module before importing transport."""

    class _Conn:
        def __init__(self, device, speed):
            self.device = device
            self.speed = speed
            self._buf = bytearray()
            self.is_open = True

        def read(self, n):
            # return exactly n or less (simulate blocking read returning requested length)
            if n <= len(self._buf):
                out = bytes(self._buf[:n])
                del self._buf[:n]
                return out
            out = bytes(self._buf)
            self._buf.clear()
            return out

        def write(self, b):
            self._written = b

        def close(self):
            self.is_open = False

    fake = types.SimpleNamespace(Serial=_Conn, SerialException=Exception)
    sys.modules["serial"] = fake
    return fake


@pytest.fixture
def any_uuid():
    return uuid.UUID("01234567-89ab-4cde-8123-456789abcdef")
