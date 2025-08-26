__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import UUID, FixedString, Int32, Uint8, Uint32, Union

__all__ = [
    "AppMetadata",
    "AppRunState",
    "AppRunStateRequest",
    "AppRunStateStart",
    "AppRunStateStop",
]

# App run state


class AppRunStateStart(PebblePacket):
    """
    Represents a packet indicating the start of an app run state on the Pebble device.

    Attributes:
        uuid (UUID): The universally unique identifier of the app being started.
    """

    uuid = UUID()


class AppRunStateStop(PebblePacket):
    """
    Represents a packet indicating that an app should stop running on the Pebble device.

    Attributes:
        uuid (UUID): The universally unique identifier of the app to stop.
    """

    uuid = UUID()


class AppRunStateRequest(PebblePacket):
    """
    Represents a request packet to query the run state of an app on the Pebble device.

    This class is used to initiate communication with the Pebble device to determine
    whether a specific app is currently running. It does not contain any additional
    fields or methods beyond those inherited from PebblePacket.
    """


class AppRunState(PebblePacket):
    """
    Represents the run state of an application on a Pebble device.

    This packet is used to communicate application state changes such as start, stop, or request
    state. The packet structure is defined by the endpoint 0x34 and uses little-endian byte order.

    Attributes:
        command (Uint8): The command identifier indicating the type of state change.
        data (Union): The associated data for the command, which varies depending on the command
            value:
            - 0x01: AppRunStateStart
            - 0x02: AppRunStateStop
            - 0x03: AppRunStateRequest

    Meta:
        endpoint (int): The protocol endpoint for app run state packets (0x34).
        endianness (str): Byte order used for serialization ("<" for little-endian).
    """

    class Meta:
        """
        Meta class containing protocol configuration for the application.

        Attributes:
            endpoint (int): The protocol endpoint identifier.
            endianness (str): The byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0x34
        endianness = "<"

    command = Uint8()
    data = Union(
        command,
        {
            0x01: AppRunStateStart,
            0x02: AppRunStateStop,
            0x03: AppRunStateRequest,
        },
    )


# App fetch


class AppFetchRequest(PebblePacket):
    class Meta:
        endpoint = 0x1771
        endianness = "<"

    command = Uint8(default=0x01)
    uuid = UUID()
    app_id = Int32()


class AppFetchStatus(IntEnum):
    Start = 0x01
    Busy = 0x02
    InvalidUUID = 0x03
    NoData = 0x04


class AppFetchResponse(PebblePacket):
    class Meta:
        endpoint = 0x1771
        endianness = "<"
        register = False

    command = Uint8(default=0x01)
    response = Uint8(enum=AppFetchStatus)


class AppMetadata(PebblePacket):
    """This represents an entry in the appdb."""

    class Meta:
        """Meta class containing protocol configuration for AppMetadata."""

        endianness = "<"

    uuid = UUID()
    flags = Uint32()
    icon = Uint32()
    app_version_major = Uint8()
    app_version_minor = Uint8()
    sdk_version_major = Uint8()
    sdk_version_minor = Uint8()
    app_face_bg_color = Uint8()
    app_face_template_id = Uint8()
    app_name = FixedString(96)
