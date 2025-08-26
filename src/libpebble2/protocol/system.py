__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import (
    BinaryArray,
    Boolean,
    Embed,
    FixedString,
    Int16,
    Optional,
    PascalString,
    Uint8,
    Uint16,
    Uint32,
    Uint64,
    Union,
)

# Time manipulation

__all__ = [
    "AppVersionRequest",
    "AppVersionResponse",
    "BLEControl",
    "FirmwareUpdateStartResponse",
    "GetTimeRequest",
    "GetTimeResponse",
    "Model",
    "ModelError",
    "ModelRequest",
    "ModelResponse",
    "PhoneAppVersion",
    "Ping",
    "PingPong",
    "Pong",
    "Reset",
    "SetLocaltime",
    "SetUTC",
    "SystemMessage",
    "TimeMessage",
    "WatchFirmwareVersion",
    "WatchModel",
    "WatchVersion",
    "WatchVersionRequest",
    "WatchVersionResponse",
]


class GetTimeRequest(PebblePacket):
    """Represents a request to get the current time from a Pebble device."""


class GetTimeResponse(PebblePacket):
    """
    Represents the response packet for retrieving the current time from the Pebble device.

    Attributes:
        time (Uint32): The current time value returned by the device, typically as a Unix timestamp.
    """

    time = Uint32()


class SetLocaltime(PebblePacket):
    """
    Represents a packet to set the local time on the Pebble device.

    Attributes:
        time (Uint32): The local time to set, represented as a 32-bit unsigned integer (typically a
            Unix timestamp).
    """

    time = Uint32()


class SetUTC(PebblePacket):
    """
    Represents a packet for setting the UTC time on a Pebble device.

    Attributes:
        unix_time (Uint32): The current Unix timestamp.
        utc_offset (Int16): The offset from UTC in minutes.
        tz_name (PascalString): The name of the time zone.
    """

    unix_time = Uint32()
    utc_offset = Int16()
    tz_name = PascalString()


class TimeMessage(PebblePacket):
    """
    Represents a time-related message packet for Pebble devices.

    This class encapsulates messages sent to or received from the Pebble system endpoint (0x0B)
    regarding time operations. The type of message is determined by the `kind` field, which
    selects the appropriate message structure via a union:

    - 0x00: GetTimeRequest
    - 0x01: GetTimeResponse
    - 0x02: SetLocaltime
    - 0x03: SetUTC

    Attributes:
        kind (Uint8): The type of time message.
        message (Union): The message payload, determined by `kind`.

    Meta:
        endpoint (int): The protocol endpoint for system time messages (0x0B).
    """

    class Meta:
        """
        Meta class containing protocol metadata for the system, specifically the endpoint
        identifier.

        Attributes:
            endpoint (int): The protocol endpoint value used for system messages.
        """

        endpoint = 0x0B

    kind = Uint8()
    message = Union(
        kind,
        {0x00: GetTimeRequest, 0x01: GetTimeResponse, 0x02: SetLocaltime, 0x03: SetUTC},
    )


# Phone app version


class AppVersionRequest(PebblePacket):
    """Represents a request packet to retrieve the version information of a Pebble app."""


class AppVersionResponse(PebblePacket):
    """
    Represents a response packet containing version information for a Pebble application.

    Attributes:
        protocol_version (Uint32): Protocol version (unused as of v3.0).
        session_caps (Uint32): Session capabilities (unused as of v3.0).
        platform_flags (Uint32): Flags indicating platform-specific features.
        response_version (Uint8): Version of the response format (default is 2).
        major_version (Uint8): Major version number of the application.
        minor_version (Uint8): Minor version number of the application.
        bugfix_version (Uint8): Bugfix version number of the application.
        protocol_caps (Uint64): Protocol capabilities supported by the application.
    """

    protocol_version = Uint32()
    session_caps = Uint32()
    platform_flags = Uint32()
    response_version = Uint8(default=2)
    major_version = Uint8()
    minor_version = Uint8()
    bugfix_version = Uint8()
    protocol_caps = Uint64()


class PhoneAppVersion(PebblePacket):
    """
    Represents a packet for requesting or responding with the phone app version in the Pebble
    protocol.

    This packet uses a union to differentiate between request and response types based on the
    `kind` field.

    Attributes:
        kind (Uint8): Indicates the type of message (0x00 for request, 0x01 for response).
        message (Union): Contains either an AppVersionRequest or AppVersionResponse, depending
            on `kind`.

    Meta:
        endpoint (int): Protocol endpoint identifier (0x11).
    """

    class Meta:
        """
        Meta class containing protocol endpoint information for system messages.

        Attributes:
            endpoint (int): The protocol endpoint identifier for system messages.
        """

        endpoint = 0x11

    kind = Uint8()
    message = Union(
        kind,
        {
            0x00: AppVersionRequest,
            0x01: AppVersionResponse,
        },
    )


# System message


class FirmwareUpdateStartResponse(PebblePacket):
    """
    Represents the response packet for initiating a firmware update on the Pebble device.

    Attributes:
        response (Uint8): Status code indicating the result of the firmware update start request.
    """

    response = Uint8()


class SystemMessage(PebblePacket):
    """
    Represents a system message packet for Pebble devices.

    This class defines the structure and types of system messages exchanged with Pebble devices,
    including firmware update notifications, reconnect commands, and MAP status changes.

    Attributes:
        command (Uint8): The command identifier for the system message. Defaults to 0x00.
        message_type (Uint8): The type of system message, as defined by the `Type` enum.
        extra_data (Union): Additional data associated with certain message types, such as
            `FirmwareUpdateStartResponse` for message_type 0x0A.

    Inner Classes:
        Meta: Metadata for the packet, including endpoint and endianness.
        Type (IntEnum): Enumeration of possible system message types.

    Message Types:
        - NewFirmwareAvailable (0x00): Indicates new firmware is available.
        - FirmwareUpdateStart (0x01): Signals the start of a firmware update.
        - FirmwareUpdateComplete (0x02): Indicates firmware update completion.
        - FirmwareUpdateFailed (0x03): Indicates firmware update failure.
        - FirmwareUpToDate (0x04): Indicates firmware is up to date.
        - StopReconnecting (0x06): Command to stop reconnecting.
        - StartReconnecting (0x07): Command to start reconnecting.
        - MAPDisabled (0x08): Indicates MAP is disabled.
        - MAPENabled (0x09): Indicates MAP is enabled.
        - FirmwareUpdateStartResponse (0x0A): Response to firmware update start, with extra data.

    Note:
        The `extra_data` field is only populated for specific message types (e.g., 0x0A).
    """

    class Meta:
        """
        Meta class containing protocol configuration for system messages.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x12).
            endianness (str): Byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0x12
        endianness = "<"

    class Type(IntEnum):
        """
        Enumeration of system protocol message types related to firmware updates and MAP
        (Message Access Profile) status.

        Members:
            NewFirmwareAvailable (0x00): Indicates that a new firmware version is available.
            FirmwareUpdateStart (0x01): Signals the start of a firmware update process.
            FirmwareUpdateComplete (0x02): Indicates successful completion of a firmware update.
            FirmwareUpdateFailed (0x03): Indicates that the firmware update process has failed.
            FirmwareUpToDate (0x04): Indicates that the firmware is already up to date.
            StopReconnecting (0x06): Command to stop attempting to reconnect.
            StartReconnecting (0x07): Command to start attempting to reconnect.
            MAPDisabled (0x08): Indicates that MAP (Message Access Profile) is disabled.
            MAPENabled (0x09): Indicates that MAP (Message Access Profile) is enabled.
            FirmwareUpdateStartResponse (0x0A): Response to the start of a firmware update.
        """

        NewFirmwareAvailable = 0x00
        FirmwareUpdateStart = 0x01
        FirmwareUpdateComplete = 0x02
        FirmwareUpdateFailed = 0x03
        FirmwareUpToDate = 0x04
        StopReconnecting = 0x06
        StartReconnecting = 0x07
        MAPDisabled = 0x08
        MAPENabled = 0x09
        FirmwareUpdateStartResponse = 0x0A

    command = Uint8(default=0x00)
    message_type = Uint8(enum=Type)
    extra_data = Union(
        message_type,
        {
            0x0A: FirmwareUpdateStartResponse,
        },
        accept_missing=True,
    )


# BLE control


class BLEControl(PebblePacket):
    """
    Represents a BLE (Bluetooth Low Energy) control packet for Pebble devices.

    Attributes:
        opcode (Uint8): The operation code for the BLE control packet. Defaults to 0x4.
        discoverable (Boolean): Indicates whether the device should be discoverable.
        duration (Uint16): The duration (in seconds) for which the device remains discoverable.

    Meta:
        endpoint (int): The protocol endpoint for BLE control packets (0x33).
        endianness (str): The byte order used for serialization ("<" for little-endian).
    """

    class Meta:
        """
        Meta class containing protocol configuration for system messages.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x33).
            endianness (str): Byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0x33
        endianness = "<"

    opcode = Uint8(default=0x4)
    discoverable = Boolean()
    duration = Uint16()


# Firmware/hardware version


class WatchVersionRequest(PebblePacket):
    """Represents a request for the watch version information."""


class WatchFirmwareVersion(PebblePacket):
    """
    Represents the firmware version information of a Pebble watch.

    Attributes:
        timestamp (Uint32): The timestamp of the firmware build.
        version_tag (FixedString): The version tag string (up to 32 characters).
        git_hash (FixedString): The git hash of the firmware source (up to 8 characters).
        is_recovery (Boolean): Indicates if the firmware is a recovery build.
        hardware_platform (Uint8): The hardware platform identifier.
        metadata_version (Uint8): The version of the firmware metadata.
    """

    timestamp = Uint32()
    version_tag = FixedString(32)
    git_hash = FixedString(8)
    is_recovery = Boolean()
    hardware_platform = Uint8()
    metadata_version = Uint8()


class WatchVersionResponse(PebblePacket):
    """
    Represents the response packet containing version and system information from a Pebble watch.

    Attributes:
        running (WatchFirmwareVersion): The currently running firmware version.
        recovery (WatchFirmwareVersion): The recovery firmware version.
        bootloader_timestamp (int): Timestamp of the bootloader build (Unix epoch).
        board (str): Board identifier string (max 9 characters).
        serial (str): Serial number string (max 12 characters).
        bt_address (bytes): Bluetooth MAC address (6 bytes).
        resource_crc (int): CRC32 of the resource bundle.
        resource_timestamp (int): Timestamp of the resource bundle (Unix epoch).
        language (str): Language code (max 6 characters).
        language_version (int): Version of the language pack.
        capabilities (int): Bitfield representing device capabilities (64-bit, little-endian).
        is_unfaithful (bool, optional): Indicates if the device is "unfaithful"
            (special diagnostic flag).
    """

    running = Embed(WatchFirmwareVersion)
    recovery = Embed(WatchFirmwareVersion)
    bootloader_timestamp = Uint32()
    board = FixedString(9)
    serial = FixedString(12)
    bt_address = BinaryArray(6)
    resource_crc = Uint32()
    resource_timestamp = Uint32()
    language = FixedString(6)
    language_version = Uint16()
    capabilities = Uint64(endianness="<")
    is_unfaithful = Optional(Boolean())


class WatchVersion(PebblePacket):
    """
    Represents a Pebble protocol packet for querying or responding with the watch firmware version.

    Attributes:
        Meta (class): Contains metadata for the packet, including the endpoint value (0x10).
        command (Uint8): The command identifier for the packet.
        data (Union): The payload of the packet, which is determined by the command value:
            - 0x00: WatchVersionRequest
            - 0x01: WatchVersionResponse
    """

    class Meta:
        """
        Meta class defines protocol metadata for the system, specifying the endpoint identifier
        used for communication.

        Attributes:
            endpoint (int): The unique identifier for the system protocol endpoint.
        """

        endpoint = 0x10

    command = Uint8()
    data = Union(
        command,
        {
            0x00: WatchVersionRequest,
            0x01: WatchVersionResponse,
        },
    )


# Ping, pong.


class Ping(PebblePacket):
    """
    Represents a Ping packet in the Pebble protocol.

    Attributes:
        idle (Boolean): Indicates whether the Pebble device is idle.
    """

    idle = Boolean()


class Pong(PebblePacket):
    """Represents a Pong packet in the Pebble protocol."""


class PingPong(PebblePacket):
    """
    Represents a PingPong packet for Pebble protocol communication.

    This packet is used for sending and receiving ping/pong messages between devices.
    It contains a command identifier, a cookie for tracking requests, and a message
    field that is a union type, which can be either a Ping or Pong message depending
    on the command value.

    Attributes:
        command (Uint8): The command type (0 for Ping, 1 for Pong).
        cookie (Uint32): A unique identifier for the ping/pong exchange.
        message (Union): The message payload, which is either a Ping or Pong object
            depending on the value of `command`.

    Meta:
        endpoint (int): The protocol endpoint for PingPong packets (2001).
    """

    class Meta:
        """
        Meta class containing protocol configuration for the system module.

        Attributes:
            endpoint (int): The protocol endpoint identifier for system messages.
        """

        endpoint = 2001

    command = Uint8()
    cookie = Uint32()
    message = Union(
        command,
        {
            0: Ping,
            1: Pong,
        },
    )


# Reset


class Reset(PebblePacket):
    """
    Represents a packet for system reset operations on a Pebble device.

    This packet can be used to send various reset-related commands to the device,
    such as performing a standard reset, dumping the core, factory resetting, or
    executing a PRF operation.

    Attributes:
        command (Reset.Command): The specific reset command to execute.

    Inner Classes:
        Meta: Metadata for the packet, including endpoint and endianness.
        Command (IntEnum): Enumeration of possible reset commands:
            - Reset: Perform a standard reset (0x00)
            - DumpCore: Dump the device core (0x01)
            - FactoryReset: Perform a factory reset (0x02)
            - PRF: Execute a PRF operation (0x03)
    """

    class Meta:
        """
        Meta class containing protocol configuration for the system.

        Attributes:
            endpoint (int): The protocol endpoint identifier.
            endianness (str): Byte order used for serialization ("<" for little-endian).
        """

        endpoint = 2003
        endianness = "<"

    class Command(IntEnum):
        """
        An enumeration of system command codes.

        Attributes:
            Reset (int): Command to reset the system (0x00).
            DumpCore (int): Command to dump the system core (0x01).
            FactoryReset (int): Command to perform a factory reset (0x02).
            PRF (int): Command for PRF operation (0x03).
        """

        Reset = 0x00
        DumpCore = 0x01
        FactoryReset = 0x02
        PRF = 0x03

    command = Uint8(enum=Command)


# Watch colour (on top of the former factory/system settings endpoints)


class Model(IntEnum):
    """Enumeration of Pebble device models."""

    Unknown = 0
    TintinBlack = 1
    TintinWhite = 2
    TintinRed = 3
    TintinOrange = 4
    TintinGrey = 5
    BiancaSilver = 6
    BiancaBlack = 7
    TintinBlue = 8
    TintinGreen = 9
    TintinPink = 10
    SnowyBlack = 11
    SnowyWhite = 12
    SnowyRed = 13
    BobbySilver = 14
    BobbyBlack = 15
    BobbyGold = 16


class ModelRequest(PebblePacket):
    """
    Represents a request packet for querying the model information from a Pebble device.

    Attributes:
        _key (PascalString): The key used for the request, defaults to "mfg_color".
    """

    _key = PascalString(default="mfg_color")


class ModelResponse(PebblePacket):
    """
    Represents a response packet containing model information from a Pebble device.

    Attributes:
        length (Uint8): The length of the data array.
        data (BinaryArray): The binary data array containing model information, with size
            specified by 'length'.
    """

    length = Uint8()
    data = BinaryArray(length=length)


class ModelError(PebblePacket):
    """Represents an error packet related to the Pebble device model."""


class WatchModel(PebblePacket):
    """
    Represents a Pebble watch model packet for communication with the system endpoint.

    This packet supports multiple commands:
        - 0x00: ModelRequest
        - 0x01: ModelResponse
        - 0xFF: ModelError

    Attributes:
        command (Uint8): The command identifier.
        data (Union): The payload, which varies depending on the command value.

    Meta:
        endpoint (int): The protocol endpoint for watch model operations (5001).
    """

    class Meta:
        """
        Meta class containing protocol configuration for the system module.

        Attributes:
            endpoint (int): The protocol endpoint identifier for system messages.
        """

        endpoint = 5001

    command = Uint8()
    data = Union(
        command,
        {
            0x00: ModelRequest,
            0x01: ModelResponse,
            0xFF: ModelError,
        },
    )
