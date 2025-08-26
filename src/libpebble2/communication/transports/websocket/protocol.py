__author__ = "katharine"

from enum import IntEnum

from libpebble2.protocol.base import PebblePacket
from libpebble2.protocol.base.types import (
    BinaryArray,
    FixedString,
    PascalString,
    Uint8,
    Uint32,
    Union,
)


class WebSocketRelayFromWatch(PebblePacket):
    """
    Represents a relay packet received from a Pebble watch over a WebSocket connection.

    This class is used to encapsulate the binary payload sent from the watch, allowing
    for structured access and manipulation of the data.

    Attributes:
        payload (BinaryArray): The binary data received from the watch.
    """

    payload = BinaryArray()


class WebSocketRelayToWatch(PebblePacket):
    """
    Represents a relay packet sent to the Pebble watch over a WebSocket transport.

    Attributes:
        payload (BinaryArray): The binary payload to be relayed to the watch.
    """

    payload = BinaryArray()


class WebSocketPhoneAppLog(PebblePacket):
    """
    Represents a Pebble packet for logging phone app events over a WebSocket transport.

    Attributes:
        payload (FixedString): The log message or data sent from the phone app.
    """

    payload = FixedString()


class WebSocketPhoneServerLog(PebblePacket):
    """
    Represents a Pebble packet for logging messages from the phone server over a WebSocket
    transport.

    Attributes:
        payload (BinaryArray): The binary data payload of the log message.
    """

    payload = BinaryArray()


class WebSocketInstallBundle(PebblePacket):
    """
    Represents a Pebble packet for installing a bundle over a WebSocket transport.

    Attributes:
        pbw (BinaryArray): The binary array containing the bundle data to be installed.
    """

    pbw = BinaryArray()


class WebSocketInstallStatus(PebblePacket):
    """
    Represents the status of an install operation communicated over a WebSocket transport.

    Attributes:
        status (Uint32): The status code of the install operation.

    Classes:
        StatusCode (IntEnum): Enumeration of possible install status codes.
            Success (0x00): Indicates the install operation was successful.
            Failed (0x01): Indicates the install operation failed.
    """

    class StatusCode(IntEnum):
        """
        Enumeration of status codes for WebSocket protocol communication.

        Attributes:
            Success (int): Indicates a successful operation (value: 0x00).
            Failed (int): Indicates a failed operation (value: 0x01).
        """

        Success = 0x00
        Failed = 0x01

    status = Uint32()


class WebSocketPhoneInfoRequest(PebblePacket):
    """
    Represents a request packet for phone information over a WebSocket transport.

    Attributes:
        version (Uint8): The protocol version of the request. Defaults to 0x00.
    """

    version = Uint8(default=0x00)


class WebSocketInstallPhoneInfoResponse(PebblePacket):
    """
    Represents a response packet for installing phone information over a WebSocket transport.

    Attributes:
        payload (BinaryArray): The binary payload containing phone information data.
    """

    payload = BinaryArray()


class WebSocketConnectionStatusUpdate(PebblePacket):
    """
    Represents a packet indicating the status update of a WebSocket connection.

    Attributes:
        status (Uint8): The status code of the connection, represented as an unsigned 8-bit integer.

    Inner Classes:
        StatusCode (IntEnum): Enumeration of possible connection statuses.
            Connected (0xFF): Indicates the connection is established.
            Disconnected (0x00): Indicates the connection is closed.
    """

    class StatusCode(IntEnum):
        """
        Enumeration representing the status codes for WebSocket connection states.

        Attributes:
            Connected (int): Indicates that the connection is established (value: 0xFF).
            Disconnected (int): Indicates that the connection is closed or lost (value: 0x00).
        """

        Connected = 0xFF
        Disconnected = 0x00

    status = Uint8()


class WebSocketProxyConnectionStatusUpdate(PebblePacket):
    """
    Represents a packet indicating the status update of a WebSocket proxy connection.

    Attributes:
        status (int): The connection status code, represented as an unsigned 8-bit integer.
            Possible values are defined in the StatusCode enum:
                - StatusCode.Connected (0xFF): Connection is established.
                - StatusCode.Disconnected (0x00): Connection is closed or disconnected.

    Classes:
        StatusCode (IntEnum): Enum representing possible connection status codes.
    """

    class StatusCode(IntEnum):
        """
        Enumeration representing the status codes for WebSocket connection states.

        Attributes:
            Connected (int): Indicates that the WebSocket is connected (value: 0xFF).
            Disconnected (int): Indicates that the WebSocket is disconnected (value: 0x00).
        """

        Connected = 0xFF
        Disconnected = 0x00

    status = Uint8()


class WebSocketProxyAuthenticationRequest(PebblePacket):
    """
    Represents a proxy authentication request packet for WebSocket communication.

    Attributes:
        token (PascalString): The authentication token used for proxy authentication.
    """

    token = PascalString()


class WebSocketProxyAuthenticationResponse(PebblePacket):
    """
    Represents a response packet for proxy authentication over a WebSocket transport.

    Attributes:
        status (Uint8): The status code of the authentication response, indicating success
            or failure.

    Classes:
        StatusCode (IntEnum): Enumeration of possible authentication status codes.
            Success (0x00): Authentication succeeded.
            Failed (0x01): Authentication failed.
    """

    class StatusCode(IntEnum):
        """
        Enumeration of status codes for WebSocket protocol communication.

        Attributes:
            Success (int): Indicates a successful operation (value: 0x00).
            Failed (int): Indicates a failed operation (value: 0x01).
        """

        Success = 0x00
        Failed = 0x01

    status = Uint8()


class AppConfigSetup(PebblePacket):
    """
    Represents a packet for setting up application configuration via Pebble communication protocol.

    This class is a placeholder for the AppConfigSetup packet structure, used in the websocket
    transport layer. It inherits from PebblePacket and may be extended to include specific
    fields or methods for configuration setup.

    Attributes:
        (No attributes defined yet)
    """


class AppConfigResponse(PebblePacket):
    """
    Represents a response packet containing application configuration data.

    Attributes:
        length (Uint32): The length of the configuration data.
        data (FixedString): The configuration data as a fixed-length string, determined by `length`.
    """

    length = Uint32()
    data = FixedString(length=length)


class AppConfigCancelled(PebblePacket):
    """
    Represents a packet indicating that an app configuration process was cancelled.

    This class is used within the Pebble communication protocol to signal that the
    app configuration has been aborted or cancelled by the user or system.
    """


class AppConfigURL(PebblePacket):
    """
    Represents a Pebble packet containing an application configuration URL.

    Attributes:
        length (Uint32): The length of the configuration URL string.
        data (FixedString): The configuration URL string, with its length specified by `length`.
    """

    length = Uint32()
    data = FixedString(length=length)


class WebSocketPhonesimAppConfig(PebblePacket):
    """
    Represents a configuration packet for the WebSocket Phonesim application.

    Attributes:
        command (Uint8): The command identifier for the configuration packet.
        config (Union): The configuration data, determined by the value of `command`.
            - 0x01: AppConfigSetup
            - 0x02: AppConfigResponse
            - 0x03: AppConfigCancelled
    """

    command = Uint8()
    config = Union(
        command,
        {
            0x01: AppConfigSetup,
            0x02: AppConfigResponse,
            0x03: AppConfigCancelled,
        },
    )


class WebSocketPhonesimConfigResponse(PebblePacket):
    """
    Represents a response packet for the WebSocket Phonesim configuration.

    Attributes:
        command (Uint8): The command identifier for the configuration response.
        config (Union): The configuration data associated with the command. If the command is 0x01,
            the configuration is represented by an AppConfigURL instance.
    """

    command = Uint8()

    config = Union(command, {0x01: AppConfigURL})


class WebSocketRelayQemu(PebblePacket):
    """
    Represents a relay packet for WebSocket communication with QEMU.

    Attributes:
        protocol (Uint8): The protocol identifier for the packet.
        data (BinaryArray): The binary data payload of the packet.
    """

    protocol = Uint8()
    data = BinaryArray()


class InsertPin(PebblePacket):
    """
    Represents a Pebble packet for inserting a pin via the websocket protocol.

    Attributes:
        json (FixedString): The JSON string containing the pin data to be inserted.
    """

    json = FixedString()


class DeletePin(PebblePacket):
    """
    Represents a packet for deleting a pin on a Pebble device.

    Attributes:
        uuid (FixedString): The UUID of the pin to be deleted, represented as a fixed-length string
            of 36 characters.
    """

    uuid = FixedString(36)


class WebSocketTimelinePin(PebblePacket):
    """
    Represents a Pebble packet for timeline pin operations over a WebSocket transport.

    Attributes:
        command (Uint8): The command identifier specifying the type of timeline pin operation.
        data (Union): The payload associated with the command.
            - If command is 0x01, data is an InsertPin instance.
            - If command is 0x02, data is a DeletePin instance.
    """

    command = Uint8()
    data = Union(command, {0x01: InsertPin, 0x02: DeletePin})


class WebSocketTimelineResponse(PebblePacket):
    """
    Represents a response packet for a timeline operation over a WebSocket transport.

    Attributes:
        status (WebSocketTimelineResponse.Status): The status of the timeline operation.
            - Succeeded (0x00): The operation was successful.
            - Failed (0x01): The operation failed.
    """

    class Status(IntEnum):
        """
        Enumeration representing the status of a WebSocket protocol operation.

        Attributes:
            Succeeded (int): Indicates the operation was successful (value: 0x00).
            Failed (int): Indicates the operation failed (value: 0x01).
        """

        Succeeded = 0x00
        Failed = 0x01

    status = Uint8(enum=Status)


to_watch: dict[int, type[PebblePacket]] = {
    0x01: WebSocketRelayToWatch,
    0x04: WebSocketInstallBundle,
    0x06: WebSocketPhoneInfoRequest,
    0x09: WebSocketProxyAuthenticationRequest,
    0x0A: WebSocketPhonesimAppConfig,
    0x0B: WebSocketRelayQemu,
    0x0C: WebSocketTimelinePin,
}

from_watch: dict[int, type[PebblePacket]] = {
    0x00: WebSocketRelayFromWatch,
    0x01: WebSocketRelayToWatch,
    0x02: WebSocketPhoneAppLog,
    0x03: WebSocketPhoneServerLog,
    0x05: WebSocketInstallStatus,
    0x06: WebSocketPhoneInfoRequest,
    0x07: WebSocketConnectionStatusUpdate,
    0x08: WebSocketProxyConnectionStatusUpdate,
    0x09: WebSocketProxyAuthenticationResponse,
    0x0A: WebSocketPhonesimConfigResponse,
    0x0C: WebSocketTimelineResponse,
}

endpoints: dict[type[PebblePacket], int] = {v: k for k, v in to_watch.items()}
endpoints.update({v: k for k, v in from_watch.items()})
