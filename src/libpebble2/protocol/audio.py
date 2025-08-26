__author__ = "katharine"

from .base import PebblePacket
from .base.types import BinaryArray, PascalList, Uint8, Uint16, Union

__all__ = ["AudioStream", "DataTransfer", "EncoderFrame", "StopTransfer"]


class EncoderFrame(PebblePacket):
    """
    Represents a single frame of encoded audio data.

    Attributes:
        data (BinaryArray): The binary audio data for this frame.
    """

    data = BinaryArray()


class DataTransfer(PebblePacket):
    """
    Represents a data transfer packet for audio frames.

    Attributes:
        frame_count (Uint8): The number of audio frames included in the transfer.
        frames (PascalList[EncoderFrame]): A list of encoded audio frames, with the number of
            frames specified by `frame_count`.
    """

    frame_count = Uint8()
    frames = PascalList(EncoderFrame, count=frame_count)


class StopTransfer(PebblePacket):
    """
    Represents a packet to signal the stopping of an audio transfer.

    This class is used in the Pebble protocol to indicate that an ongoing audio data transfer should
    be terminated. It does not contain any additional fields or methods.
    """


class AudioStream(PebblePacket):
    """
    Represents an audio stream packet for Pebble communication.

    This packet is used to transfer audio data or control commands between devices.
    It contains a packet ID to determine the type of data, a session ID to identify the audio
    session, and a union field 'data' that varies depending on the packet ID:
        - If packet_id == 0x02: contains a DataTransfer payload.
        - If packet_id == 0x03: contains a StopTransfer payload.

    Attributes:
        packet_id (Uint8): Identifier for the type of packet.
        session_id (Uint16): Unique identifier for the audio session.
        data (Union): Payload data, type depends on packet_id.

    Meta:
        endpoint (int): Protocol endpoint for audio stream packets (0x2710).
        endianness (str): Byte order for serialization ("<" for little-endian).
    """

    class Meta:
        """Meta information for AudioStream, including endpoint and endianness."""

        endpoint = 0x2710
        endianness = "<"

    packet_id = Uint8()
    session_id = Uint16()
    data = Union(
        packet_id,
        {
            0x02: DataTransfer,
            0x03: StopTransfer,
        },
    )
