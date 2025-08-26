from libpebble2.protocol.base import PebblePacket
from libpebble2.protocol.base.types import (
    BinaryArray,
    FixedList,
    FixedString,
    PascalList,
    Uint8,
    Uint16,
    Union,
)


class A(PebblePacket):
    v = Uint8()


class B(PebblePacket):
    v = Uint16()


class U(PebblePacket):
    k = Uint8()
    data = Union(k, {1: A, 2: B})


def test_union_parse_and_serialise():
    p = U(k=1, data=A(v=7))
    raw = p.serialise()
    assert raw == b"\x01\x07"

    p2, n = U.parse(raw)
    assert p2.k == 1 and p2.data.v == 7 and n == len(raw)

    p3 = U(data=B(v=513))
    raw3 = p3.serialise()
    assert raw3 == b"\x02\x02\x01"  # k inferred, then B serialized


class Inner(PebblePacket):
    n = Uint8()
    s = FixedString(3)


class WithEmbedAndLists(PebblePacket):
    count = Uint8()
    items = FixedList(Inner, count=count)
    blob = BinaryArray()


def test_embed_and_lists():
    i1 = Inner(n=1, s="xy")
    i2 = Inner(n=2, s="ab")
    w = WithEmbedAndLists(items=[i1, i2], blob=b"\x00\x01")
    raw = w.serialise()
    # count is inferred to 2; each Inner is 1+3 bytes = 4
    assert raw[:1] == b"\x02"
    w2, n = WithEmbedAndLists.parse(raw)
    assert len(w2.items) == 2 and w2.items[0].s == "xy"
    assert w2.blob == b"\x00\x01"


class PLElem(PebblePacket):
    val = Uint8()


class WithPascalList(PebblePacket):
    count = Uint8()
    items = PascalList(PLElem, count=count)


def test_pascal_list_encodes_lengths():
    w = WithPascalList(items=[PLElem(val=1), PLElem(val=255)])
    raw = w.serialise()
    # bytes: count=2, each element serialised with length byte (1) followed by payload(1)
    assert raw[0] == 2 and raw[1] == 1 and raw[3] == 1
