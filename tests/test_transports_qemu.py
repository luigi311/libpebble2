from libpebble2.communication.transports.qemu import (
    MessageTargetQemu,
    MessageTargetWatch,
    QemuTransport,
)
from libpebble2.communication.transports.qemu.protocol import QemuPacket, QemuRawPacket, QemuSPP


class DummySock:
    def __init__(self):
        self.sent = []
        self._open = True

    def send(self, b):
        self.sent.append(b)

    def recv(self, n):
        return b""

    def close(self):
        self._open = False


def test_qemu_send_watch_frames_chunking(monkeypatch):
    qt = QemuTransport()
    qt.socket = DummySock()
    qt._connected = True
    # Message to watch -> should be wrapped in QemuSPP
    msg = b"a" * 10
    qt.send_packet(msg, target=MessageTargetWatch())
    assert qt.socket.sent
    pkt = QemuPacket.parse(qt.socket.sent[0])[0]
    assert isinstance(pkt.data, QemuSPP)
    assert pkt.data.payload == msg


def test_qemu_send_raw_to_qemu():
    qt = QemuTransport()
    qt.socket = DummySock()
    qt._connected = True
    qt.send_packet(b"\x01\x02", target=MessageTargetQemu(protocol=7, raw=True))
    pkt = QemuRawPacket.parse(qt.socket.sent[0])[0]
    assert pkt.protocol == 7 and pkt.data == b"\x01\x02"


def test_qemu_read_from_assembled_data_without_socket():
    qt = QemuTransport()
    qt.socket = DummySock()
    qt._connected = True
    # Prepare inbound packet (to watch)
    outbound = QemuPacket(data=QemuSPP(payload=b"xyz")).serialise()
    qt.assembled_data = outbound
    target, payload = qt.read_packet()
    assert isinstance(target, MessageTargetWatch)
    assert payload.endswith(b"xyz")
