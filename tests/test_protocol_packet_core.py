import struct
import uuid

import pytest
from libpebble2.exceptions import IncompleteMessage
from libpebble2.protocol.base import PebblePacket
from libpebble2.protocol.base.types import FixedString, Uint8, Uint16


class Demo(PebblePacket):
    class Meta:
        endpoint = 0x99AA
        endianness = "<"

    a = Uint8()
    b = Uint16()
    s = FixedString(4)


def test_serialise_roundtrip_and_repr_eq():
    pkt = Demo(a=1, b=513, s="hi")
    raw = pkt.serialise()
    assert raw == b"\x01\x01\x02hi\x00\x00"

    framed = pkt.serialise_packet()
    #  length (= len(raw)) + endpoint
    assert framed[:4] == struct.pack("!HH", len(raw), 0x99AA)

    parsed, n = Demo.parse(raw)
    assert n == len(raw)
    assert parsed == pkt
    assert parsed != Demo(a=1, b=513, s="bye")
    assert "Demo(" in repr(pkt)
    assert "a=1" in repr(pkt)


def test_parse_message_dispatch_and_incomplete():
    pkt = Demo(a=2, b=3, s="four")
    framed = pkt.serialise_packet()
    # incomplete
    with pytest.raises(IncompleteMessage):
        PebblePacket.parse_message(framed[:3])
    # complete -> returns registered class and length
    parsed, length = PebblePacket.parse_message(framed)
    assert isinstance(parsed, Demo)
    assert length == len(framed)
