from libpebble2.protocol.screenshots import ScreenshotHeader, ScreenshotResponse
from libpebble2.services.screenshot import Screenshot


def wrap(b):
    return ScreenshotResponse(data=b)


def test_screenshot_decode_v1(fake_pebble):
    # Build a 8x1 image, version 1: header then 1 byte of data (8 pixels, 1-bit)
    header = ScreenshotHeader(
        response_code=ScreenshotHeader.ResponseCode.OK,
        version=1,
        width=8,
        height=1,
        data=b"",
    ).serialise()
    # pixels 1010_0001 -> bytes LSB-first per column index
    payload = bytes([0b10000101])
    fake_pebble.queue_for(ScreenshotResponse, [wrap(header), wrap(payload)])

    s = Screenshot(fake_pebble)
    rows = s.grab_image()
    # a single row, 8 pixels expanded to RGB (3 bytes each)
    assert len(rows) == 1
    assert len(rows[0]) == 8 * 3


def test_screenshot_decode_v2(fake_pebble):
    header = ScreenshotHeader(
        response_code=ScreenshotHeader.ResponseCode.OK,
        version=2,
        width=2,
        height=1,
        data=b"",
    ).serialise()
    # two 8-bit pixels (RR GG BB as 2-bit fields): 0b rrggbb
    # choose values so mapping to 0..255 visible
    payload = bytes([0b11110000, 0b00001111])
    fake_pebble.queue_for(ScreenshotResponse, [wrap(header), wrap(payload)])
    s = Screenshot(fake_pebble)
    rows = s.grab_image()
    assert len(rows) == 1 and len(rows[0]) == 2 * 3
