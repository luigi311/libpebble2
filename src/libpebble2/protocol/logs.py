__author__ = "katharine"

from .base import PebblePacket
from .base.types import UUID, Boolean, FixedString, Uint8, Uint16, Uint32, Union

__all__ = [
    "AppLogMessage",
    "AppLogShippingControl",
    "LogDumpShipping",
    "LogMessage",
    "LogMessageDone",
    "NoLogMessages",
    "RequestLogs",
]

# Flash log messages


class RequestLogs(PebblePacket):
    """
    Represents a request to retrieve logs from a Pebble device.

    Attributes:
        generation (Uint8): The generation identifier for the log request.
        cookie (Uint32): A unique identifier used to track the log request.
    """

    generation = Uint8()
    cookie = Uint32()


class LogMessage(PebblePacket):
    """
    Represents a log message packet from a Pebble device.

    Attributes:
        cookie (Uint32): Unique identifier for the log message.
        timestamp (Uint32): Timestamp when the log message was generated.
        level (Uint8): Severity level of the log message.
        length (Uint8): Length of the log message string.
        line (Uint16): Line number in the source file where the log was generated.
        filename (FixedString): Name of the source file (up to 16 characters).
        message (FixedString): The log message content, with length specified by `length`.
    """

    cookie = Uint32()
    timestamp = Uint32()
    level = Uint8()
    length = Uint8()
    line = Uint16()
    filename = FixedString(16)
    message = FixedString(length)


class LogMessageDone(PebblePacket):
    """
    Represents a packet indicating that a log message transmission is complete.

    Attributes:
        cookie (Uint32): A unique identifier for the log message transaction.
    """

    cookie = Uint32()


class NoLogMessages(PebblePacket):
    """
    Represents a packet indicating that there are no log messages available.

    Attributes:
        cookie (Uint32): A unique identifier for the log request.
    """

    cookie = Uint32()


class LogDumpShipping(PebblePacket):
    """
    Represents a packet for log dump shipping in the Pebble protocol.

    This class handles communication with the log dump endpoint (2002) and supports
    multiple command types, each with its own associated data structure.

    Attributes:
        command (Uint8): The command identifier for the packet.
        data (Union): The data associated with the command. The structure of `data` depends on the
            value of `command`:
            - 0x10: Uses the `RequestLogs` structure.
            - 0x80: Uses the `LogMessage` structure.
            - 0x81: Uses the `LogMessageDone` structure.
            - 0x82: Uses the `NoLogMessages` structure.

    Meta:
        endpoint (int): The protocol endpoint for log dump shipping (2002).
    """

    class Meta:
        """
        Meta class containing protocol endpoint information for log-related operations.

        Attributes:
            endpoint (int): The protocol endpoint identifier for logs.
        """

        endpoint = 2002

    command = Uint8()
    data = Union(
        command,
        {
            0x10: RequestLogs,
            0x80: LogMessage,
            0x81: LogMessageDone,
            0x82: NoLogMessages,
        },
    )


# App log messages


class AppLogShippingControl(PebblePacket):
    """
    Represents a packet to control the shipping of application logs on a Pebble device.

    Attributes:
        enable (Boolean): Indicates whether log shipping is enabled or disabled.

    Meta:
        endpoint (int): The protocol endpoint for app log shipping control (2006).
        register (bool): Whether to register this packet type (False).
    """

    class Meta:
        """
        Meta class containing protocol configuration for logs.

        Attributes:
            endpoint (int): The protocol endpoint identifier (2006).
            register (bool): Indicates whether the protocol should be registered (False).
        """

        endpoint = 2006
        register = False

    enable = Boolean()


class AppLogMessage(PebblePacket):
    """
    Represents a log message packet sent from a Pebble app.

    Attributes:
        uuid (UUID): The unique identifier of the app sending the log message.
        timestamp (Uint32): The timestamp of the log message.
        level (Uint8): The log level (e.g., info, warning, error).
        message_length (Uint8): The length of the log message.
        line_number (Uint16): The line number in the source file where the log was generated.
        filename (FixedString): The name of the source file (max 16 characters).
        message (FixedString): The log message content, with length specified by `message_length`.
    """

    class Meta:
        """
        Meta class containing protocol endpoint information for log-related operations.

        Attributes:
            endpoint (int): The protocol endpoint identifier for logs.
        """

        endpoint = 2006

    uuid = UUID()
    timestamp = Uint32()
    level = Uint8()
    message_length = Uint8()
    line_number = Uint16()
    filename = FixedString(16)
    message = FixedString(message_length)
