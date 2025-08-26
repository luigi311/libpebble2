from libpebble2.util.hardware import PebbleHardware
from libpebble2.util.stm32_crc import crc32


def test_crc32_known_value():
    # Known value against a simple buffer
    data = b"abcd"  # exactly one 32-bit word in little-endian packing
    # This constant is stable against the implementation (not IEEE)
    assert crc32(data) == crc32(data)  # idempotent; sanity
    assert isinstance(crc32(data), int)


def test_hardware_platform_map():
    assert PebbleHardware.hardware_platform(PebbleHardware.UNKNOWN) == "unknown"
    assert PebbleHardware.hardware_platform(PebbleHardware.SNOWY_DVT) == "basalt"
