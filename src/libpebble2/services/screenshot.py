__author__ = "katharine"

from typing import cast
from libpebble2.communication import PebbleConnection
from libpebble2.events import BaseEventQueue
from libpebble2.events.mixin import EventSourceMixin
from libpebble2.exceptions import ScreenshotError
from libpebble2.protocol.screenshots import (
    ScreenshotHeader,
    ScreenshotRequest,
    ScreenshotResponse,
)


class Screenshot(EventSourceMixin):
    """
    Takes a screenshot from the watch.

    Args:
        pebble (PebbleConnection): The pebble of which to take a screenshot.
    """

    def __init__(self, pebble: PebbleConnection) -> None:
        self._pebble = pebble
        super().__init__()

    def grab_image(self) -> list[bytearray]:
        """
        Takes a screenshot. Blocks until completion.

        While this method is executing, "progress" events will periodically be emitted with the
        following signature: ::
           (downloaded_so_far, total_size)

        Returns:
            list[bytearray]: A list of bytearrays, one per row of the image. Each bytearray contains
            RGB triples for each pixel in that row.

        Raises:
            ScreenshotError: If the screenshot request fails.
        """
        # We have to open this queue before we make the request, to ensure we don't miss
        # the response.
        queue = self._pebble.get_endpoint_queue(ScreenshotResponse)
        self._pebble.send_packet(ScreenshotRequest())
        return self._read_screenshot(queue)

    def _read_screenshot(self, queue: BaseEventQueue) -> list[bytearray]:
        packet = cast("ScreenshotResponse", queue.get())
        data = cast("bytes", packet.data)
        header = ScreenshotHeader.parse(data)[0]
        if header.response_code != ScreenshotHeader.ResponseCode.OK:
            queue.close()
            msg = f"Screenshot failed: {header.response_code!s}"
            raise ScreenshotError(msg)
        data = header.data
        expected_size = self._get_expected_bytes(header)
        while len(data) < expected_size:
            next_chunk = cast("ScreenshotResponse", queue.get())
            data += cast(bytes, next_chunk.data)
        queue.close()
        return self._decode_image(header, data)

    @classmethod
    def _get_expected_bytes(cls, header: ScreenshotHeader) -> int:
        version = cast("int", header.version)
        width = cast("int", header.width)
        height = cast("int", header.height)
        if version == 1:
            return (width * height) // 8
        if version == 2:
            return width * height

        msg = f"Unknown screenshot version: {header.version}"
        raise ScreenshotError(msg)

    @classmethod
    def _decode_image(cls, header: ScreenshotHeader, data: bytes) -> list[bytearray]:
        if header.version == 1:
            return cls._decode_1bit(header, data)
        if header.version == 2:
            return cls._decode_8bit(header, data)

        msg = f"Unknown screenshot version: {header.version}"
        raise ScreenshotError(msg)

    @classmethod
    def _decode_1bit(cls, header: ScreenshotHeader, data: bytes) -> list[bytearray]:
        output = []
        width = cast("int", header.width)
        height = cast("int", header.height)
        row_bytes = width // 8
        for row in range(height):
            row_values = []
            for column in range(width):
                pixel = (data[row * row_bytes + column // 8] >> (column % 8)) & 1
                row_values.extend([pixel * 255] * 3)
            output.append(bytearray(row_values))
        return output

    @classmethod
    def _decode_8bit(cls, header: ScreenshotHeader, data: bytes) -> list[bytearray]:
        output = []
        width = cast("int", header.width)
        height = cast("int", header.height)
        for row in range(height):
            row_values = []
            for column in range(width):
                pixel = data[row * width + column]
                row_values.extend(
                    [
                        ((pixel >> 4) & 0b11) * 85,
                        ((pixel >> 2) & 0b11) * 85,
                        ((pixel >> 0) & 0b11) * 85,
                    ]
                )
            output.append(bytearray(row_values))
        return output
