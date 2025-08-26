__author__ = "katharine"

from enum import IntEnum
from typing import ClassVar

from .base import PebblePacket
from .base.types import (
    UUID,
    BinaryArray,
    Field,
    FixedList,
    FixedString,
    Uint8,
    Uint16,
    Uint32,
    Union,
)

__all__ = [
    "AppMessage",
    "AppMessageACK",
    "AppMessageNACK",
    "AppMessagePush",
    "AppMessageTuple",
    "StockAppSetIcon",
    "StockAppSetTitle",
]


class AppMessageTuple(PebblePacket):
    """Represents a tuple in an AppMessage dictionary."""

    class Type(IntEnum):
        """
        An enumeration representing the possible types of AppMessage values.

        Attributes:
            ByteArray (int): Represents a byte array type (value: 0).
            CString (int): Represents a C-style string type (value: 1).
            Uint (int): Represents an unsigned integer type (value: 2).
            Int (int): Represents a signed integer type (value: 3).
        """

        ByteArray = 0
        CString = 1
        Uint = 2
        Int = 3

    key = Uint32()
    type = Uint8(enum=Type)
    length = Uint16()
    data = BinaryArray(length=length)


class AppMessagePush(PebblePacket):
    """
    Represents a packet for pushing an app message to a Pebble device.

    Attributes:
        uuid (UUID): The unique identifier of the target application.
        count (Uint8): The number of key-value pairs in the dictionary.
        dictionary (FixedList[AppMessageTuple]): A fixed-size list of app message tuples
            containing key-value pairs.
    """

    uuid = UUID()
    count = Uint8()
    dictionary: ClassVar[Field[list[AppMessageTuple]]] = FixedList(AppMessageTuple, count=count)


class AppMessageACK(PebblePacket):
    """
    Represents an acknowledgment packet for an AppMessage in the Pebble protocol.

    This class is used to indicate successful receipt or processing of an AppMessage.
    It inherits from PebblePacket and does not add any additional fields or methods.
    """


class AppMessageNACK(PebblePacket):
    """
    Represents a negative acknowledgment (NACK) packet for Pebble app messages.

    This class is used to indicate that an app message sent to the Pebble device was not accepted
    or processed successfully.

    Attributes:
        (Inherited from PebblePacket)
    """


class AppMessage(PebblePacket):
    """
    Represents an AppMessage packet for Pebble communication.

    This class encapsulates the structure of an AppMessage, which is used for
    sending and receiving application-specific messages between the Pebble device
    and a connected host.

    Attributes:
        command (Uint8): The command identifier for the message.
        transaction_id (Uint8): The transaction ID to correlate requests and responses.
        data (Union): The payload of the message, which is determined by the value
            of `command`. Possible types include:
                - AppMessagePush (for command 0x01)
                - AppMessageACK (for command 0xFF)
                - AppMessageNACK (for command 0x7F)

    Meta:
        endpoint (int): The protocol endpoint for AppMessage (0x30).
        endianness (str): The byte order used for serialization ("<" for little-endian).
    """

    class Meta:
        """
        Meta class containing protocol configuration for app messages.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x30).
            endianness (str): Byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0x30
        endianness = "<"

    command = Uint8()
    transaction_id = Uint8()
    data = Union(
        command,
        {
            0x01: AppMessagePush,
            0xFF: AppMessageACK,
            0x7F: AppMessageNACK,
        },
    )


class StockAppSetTitle(PebblePacket):
    """
    Represents a Pebble protocol packet for setting the title of a stock application.

    This packet is used to communicate with the Pebble device to update the title of a specific app,
    such as Sports or Golf, via the protocol endpoint 0x32.

        app (Uint8): The application type to set the title for. Uses the `App` enumeration:
            - App.Sports (0x00): Sports application.
            - App.Golf (0x01): Golf application.
        title (FixedString): The new title to set for the specified application.

    Meta:
        endpoint (int): Protocol endpoint identifier (0x32).
        endianness (str): Byte order for serialization ("<" for little-endian).
        register (bool): Indicates if the protocol should be registered (False).

    Enums:
        App (IntEnum): Enumeration of supported stock apps.
            - Sports: 0x00
            - Golf: 0x01
    """

    class Meta:
        """
        Meta class containing protocol configuration for app messages.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x32).
            endianness (str): Byte order used for serialization ("<" for little-endian).
            register (bool): Indicates whether the protocol should be registered (False).
        """

        endpoint = 0x32
        endianness = "<"
        register = False

    class App(IntEnum):
        """
        An enumeration representing different application types.

        Attributes:
            Sports (int): Represents the Sports application (value: 0x00).
            Golf (int): Represents the Golf application (value: 0x01).
        """

        Sports = 0x00
        Golf = 0x01

    app = Uint8(enum=App)
    title = FixedString(None)


class StockAppSetIcon(PebblePacket):
    """
    Represents a packet for setting an icon in a stock Pebble app.

    Attributes:
        app (StockAppSetIcon.App): The target app to set the icon for (e.g., Sports, Golf).
        row_size (int): The size of a row in the icon image data.
        info_flags (int): Flags providing additional information about the icon (default: 0x1000).
        origin_x (int): The X coordinate of the icon's origin.
        origin_y (int): The Y coordinate of the icon's origin.
        size_x (int): The width of the icon.
        size_y (int): The height of the icon.
        image_data (bytes): The binary image data for the icon.

    Meta:
        endpoint (int): The protocol endpoint for this packet (0x32).
        endianness (str): Byte order for serialization ("<").
        register (bool): Whether this packet should be registered (False).

    Enums:
        App (IntEnum): Enumeration of supported stock apps.
            - Sports: 0x80
            - Golf: 0x81
    """

    class Meta:
        """
        Meta class containing protocol configuration for app messages.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x32).
            endianness (str): Byte order used for serialization ("<" for little-endian).
            register (bool): Indicates whether the protocol should be registered (False).
        """

        endpoint = 0x32
        endianness = "<"
        register = False

    class App(IntEnum):
        """
        Enumeration of application types for Pebble devices.

        Attributes:
            Sports (int): Represents the Sports application (value: 0x80).
            Golf (int): Represents the Golf application (value: 0x81).
        """

        Sports = 0x80
        Golf = 0x81

    app = Uint8(enum=App)
    row_size = Uint16()
    info_flags = Uint16(default=0x1000)
    origin_x = Uint16()
    origin_y = Uint16()
    size_x = Uint16()
    size_y = Uint16()
    image_data = BinaryArray()
