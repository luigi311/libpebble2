__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import BinaryArray, Uint8, Uint32

__all__ = ["ScreenshotHeader", "ScreenshotRequest", "ScreenshotResponse"]


class ScreenshotRequest(PebblePacket):
    """
    Represents a request packet for capturing a screenshot from a Pebble device.

    Attributes:
        Meta (class): Contains metadata for the packet, including endpoint and registration status.
        _command (Uint8): The command byte for the screenshot request, defaults to 0x00.
    """
    class Meta:
        """
        Meta class containing configuration for the screenshots protocol.

        Attributes:
            endpoint (int): The protocol endpoint identifier.
            register (bool): Indicates whether the protocol should be registered.
        """
        endpoint = 8000
        register = False

    _command = Uint8(default=0x00)


class ScreenshotResponse(PebblePacket):
    """
    Represents a response packet for screenshot data from a Pebble device.

    Attributes:
        data (BinaryArray): The binary data of the screenshot image.

    Meta:
        endpoint (int): The protocol endpoint for screenshot responses (8000).
    """
    class Meta:
        """
        Meta class containing protocol configuration for screenshots.

        Attributes:
            endpoint (int): The protocol endpoint identifier for screenshot operations.
        """
        endpoint = 8000

    data = BinaryArray()


class ScreenshotHeader(PebblePacket):
    """
    Represents the header information for a Pebble screenshot packet.

    Attributes:
        response_code (ResponseCode): The response code indicating the status of the screenshot
            request.
        version (int): The version of the screenshot protocol.
        width (int): The width of the screenshot in pixels.
        height (int): The height of the screenshot in pixels.
        data (bytes): The binary data associated with the screenshot header.

    Classes:
        ResponseCode (IntEnum): Enum representing possible response codes:
            OK (0): The request was successful.
            MalformedCommand (1): The command was malformed.
            OutOfMemory (2): The device ran out of memory.
            AlreadyInProgress (3): A screenshot operation is already in progress.
    """
    class ResponseCode(IntEnum):
        """
        Enumeration of possible response codes for screenshot-related commands.

        Attributes:
            OK (int): Command was successful.
            MalformedCommand (int): The command was malformed or invalid.
            OutOfMemory (int): The device ran out of memory while processing the command.
            AlreadyInProgress (int): A screenshot operation is already in progress.
        """
        OK = 0
        MalformedCommand = 1
        OutOfMemory = 2
        AlreadyInProgress = 3

    response_code = Uint8(enum=ResponseCode)
    version = Uint32()
    width = Uint32()
    height = Uint32()
    data = BinaryArray()
