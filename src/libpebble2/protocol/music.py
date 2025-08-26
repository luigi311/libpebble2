__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import Optional, PascalString, Uint8, Uint16, Uint32, Union

__all__ = [
    "MusicControl",
    "MusicControlGetCurrentTrack",
    "MusicControlNextTrack",
    "MusicControlPause",
    "MusicControlPlay",
    "MusicControlPlayPause",
    "MusicControlPreviousTrack",
    "MusicControlUpdateCurrentTrack",
    "MusicControlVolumeDown",
    "MusicControlVolumeUp",
]


class MusicControlPlayPause(PebblePacket):
    """
    Represents a packet to control the play/pause functionality of music playback on a Pebble
    device.
    """


class MusicControlPlay(PebblePacket):
    """
    Represents a packet to control the play functionality of music playback on a Pebble
    device.
    """


class MusicControlPause(PebblePacket):
    """
    Represents a packet to control the pause functionality of music playback on a Pebble
    device.
    """


class MusicControlNextTrack(PebblePacket):
    """
    Represents a packet to control the next track functionality of music playback on a Pebble
    device.
    """


class MusicControlPreviousTrack(PebblePacket):
    """
    Represents a packet to control the previous track functionality of music playback on a Pebble
    device.
    """


class MusicControlVolumeUp(PebblePacket):
    """
    Represents a packet to control the volume up functionality of music playback on a Pebble
    device.
    """


class MusicControlVolumeDown(PebblePacket):
    """
    Represents a packet to control the volume down functionality of music playback on a Pebble
    device.
    """


class MusicControlGetCurrentTrack(PebblePacket):
    """Represents a packet to request the current track information from a Pebble device."""


class MusicControlUpdateCurrentTrack(PebblePacket):
    """
    Represents a packet for updating the current music track information on a Pebble device.

    Attributes:
        artist (PascalString): The name of the artist.
        album (PascalString): The name of the album.
        title (PascalString): The title of the track.
        track_length (Optional[Uint32]): The length of the track in seconds, if available.
        track_count (Optional[Uint16]): The total number of tracks in the album, if available.
        current_track (Optional[Uint16]): The index of the current track, if available.
    """

    artist = PascalString()
    album = PascalString()
    title = PascalString()
    track_length = Optional(Uint32())
    track_count = Optional(Uint16())
    current_track = Optional(Uint16())


class MusicControlUpdatePlayStateInfo(PebblePacket):
    class State(IntEnum):
        Paused = 0x00
        Playing = 0x01
        Rewinding = 0x02
        Fastforwarding = 0x03
        Unknown = 0x04

    class Shuffle(IntEnum):
        Unknown = 0x00
        Off = 0x01
        On = 0x02

    class Repeat(IntEnum):
        Unknown = 0x00
        Off = 0x01
        One = 0x02
        All = 0x03

    state = Uint8(enum=State)
    track_position = Uint32()
    play_rate = Uint32()
    shuffle = Uint8(enum=Shuffle)
    repeat = Uint8(enum=Repeat)


class MusicControlUpdateVolumeInfo(PebblePacket):
    volume_percent = Uint8()


class MusicControlUpdatePlayerInfo(PebblePacket):
    package = PascalString()
    name = PascalString()


class MusicControl(PebblePacket):
    """
    Represents a music control packet for Pebble devices.

    This class encapsulates commands sent to or received from the Pebble music endpoint (0x20).
    The packet structure is determined by the `command` field, which selects the appropriate
    data structure for the `data` field using a union.

    Attributes:
        command (Uint8): The command identifier specifying the music control action.
        data (Union): The payload associated with the command, mapped as follows:
            0x01: MusicControlPlayPause
            0x02: MusicControlPause
            0x03: MusicControlPlay
            0x04: MusicControlNextTrack
            0x05: MusicControlPreviousTrack
            0x06: MusicControlVolumeUp
            0x07: MusicControlVolumeDown
            0x08: MusicControlGetCurrentTrack
            0x10: MusicControlUpdateCurrentTrack
            0x11: MusicControlUpdatePlayStateInfo
            0x12: MusicControlUpdateVolumeInfo
            0x13: MusicControlUpdatePlayerInfo

    Meta:
        endpoint (int): The protocol endpoint for music control (0x20).
        endianness (str): Byte order for serialization ("<" for little-endian).
    """

    class Meta:
        """
        Meta class defines protocol-specific metadata for music communication.

        Attributes:
            endpoint (int): The protocol endpoint identifier for music messages.
            endianness (str): Byte order used for encoding/decoding messages ("<" for little-endian).
        """

        endpoint = 0x20
        endianness = "<"

    command = Uint8()
    data = Union(
        command,
        {
            0x01: MusicControlPlayPause,
            0x02: MusicControlPause,
            0x03: MusicControlPlay,
            0x04: MusicControlNextTrack,
            0x05: MusicControlPreviousTrack,
            0x06: MusicControlVolumeUp,
            0x07: MusicControlVolumeDown,
            0x08: MusicControlGetCurrentTrack,
            0x10: MusicControlUpdateCurrentTrack,
            0x11: MusicControlUpdatePlayStateInfo,
            0x12: MusicControlUpdateVolumeInfo,
            0x13: MusicControlUpdatePlayerInfo,
        },
    )
