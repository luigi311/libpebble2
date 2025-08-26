from enum import IntEnum

from .base import PebblePacket
from .base.types import UUID, BinaryArray, FixedList, Uint8, Uint16, Uint32, Union

__author__ = "katharine"

"""
This file is special in that it actually contains definitions of
blobdb blob formats rather than pebble protocol messages.
"""

__all__ = [
    "ActionResponse",
    "InvokeAction",
    "TimelineAction",
    "TimelineActionEndpoint",
    "TimelineAttribute",
    "TimelineItem",
]


class TimelineAttribute(PebblePacket):
    """
    Represents a timeline attribute packet for Pebble communication.

    This class defines the structure of a timeline attribute, including its ID, length,
    and binary content. Serialization is not handled here, as it is managed externally
    via a JSON file.

    Attributes:
        attribute_id (Uint8): The identifier for the attribute.
        length (Uint16): The length of the content in bytes.
        content (BinaryArray): The binary content of the attribute, with size specified by 'length'.
    """

    attribute_id = Uint8()
    length = Uint16()
    content = BinaryArray(length=length)


class TimelineAction(PebblePacket):
    """
    Represents an action within the Pebble timeline protocol.

    Attributes:
        action_id (Uint8): Unique identifier for the action.
        type (Uint8): Type of the action, defined by the `Type` enum.
        attribute_count (Uint8): Number of attributes associated with the action.
        attributes (FixedList[TimelineAttribute]): List of attributes for the action.

    Inner Classes:
        Type (IntEnum): Enumeration of possible action types, including:
            - AncsDismiss: 0x01
            - Generic: 0x02
            - Response: 0x03
            - Dismiss: 0x04
            - HTTP: 0x05
            - Snooze: 0x06
            - OpenWatchapp: 0x07
            - Empty: 0x08
            - Remove: 0x09
            - OpenPin: 0x0A
    """

    class Type(IntEnum):
        """
        Enumeration of timeline item types.

        Attributes:
            AncsDismiss (int): Represents an ANCS (Apple Notification Center Service)
                dismiss action.
            Generic (int): Represents a generic timeline item.
            Response (int): Represents a response to a timeline item.
            Dismiss (int): Represents a dismiss action for a timeline item.
            HTTP (int): Represents an HTTP timeline item.
            Snooze (int): Represents a snooze action for a timeline item.
            OpenWatchapp (int): Represents an action to open a watch application.
            Empty (int): Represents an empty timeline item.
            Remove (int): Represents a remove action for a timeline item.
            OpenPin (int): Represents an action to open a pin on the timeline.
        """

        AncsDismiss = 0x01
        Generic = 0x02
        Response = 0x03
        Dismiss = 0x04
        HTTP = 0x05
        Snooze = 0x06
        OpenWatchapp = 0x07
        Empty = 0x08
        Remove = 0x09
        OpenPin = 0x0A

    action_id = Uint8()
    type = Uint8(enum=Type)
    attribute_count = Uint8()
    attributes = FixedList(TimelineAttribute, count=attribute_count)


class TimelineItem(PebblePacket):
    """
    Represents a Timeline item packet for Pebble protocol.

    Attributes:
        item_id (UUID): Unique identifier for the timeline item.
        parent_id (UUID): Identifier of the parent item, if any.
        timestamp (Uint32): Unix timestamp for the item.
        duration (Uint16): Duration of the item in seconds.
        type (Uint8): Type of the timeline item (Notification, Pin, Reminder).
        flags (Uint16): Flags associated with the item.
        layout (Uint8): Layout type for the item.
        data_length (Uint16): Total length of the data for attributes and actions.
        attribute_count (Uint8): Number of attributes in the item.
        action_count (Uint8): Number of actions in the item.
        attributes (FixedList[TimelineAttribute]): List of timeline attributes.
        actions (FixedList[TimelineAction]): List of timeline actions.

    Meta:
        endianness (str): Byte order for serialization ("<" for little-endian).

    Type (IntEnum):
        Notification: Timeline item is a notification.
        Pin: Timeline item is a pin.
        Reminder: Timeline item is a reminder.
    """

    class Meta:
        """
        Meta class specifying protocol configuration.

        Attributes:
            endianness (str): Byte order for serialization. "<" indicates little-endian.
        """

        endianness = "<"

    class Type(IntEnum):
        """
        An enumeration representing different timeline item types.

        Attributes:
            Notification (int): Represents a notification item (value: 1).
            Pin (int): Represents a pin item (value: 2).
            Reminder (int): Represents a reminder item (value: 3).
        """

        Notification = 1
        Pin = 2
        Reminder = 3

    item_id = UUID()
    parent_id = UUID()
    timestamp = Uint32()
    duration = Uint16()
    type = Uint8(enum=Type)
    flags = Uint16()
    layout = Uint8()
    data_length = Uint16()
    attribute_count = Uint8()
    action_count = Uint8()
    attributes = FixedList(TimelineAttribute, count=attribute_count, length=data_length)
    actions = FixedList(TimelineAction, count=action_count, length=data_length)


class InvokeAction(PebblePacket):
    """
    Represents a packet to invoke an action on a timeline item.

    Attributes:
        item_id (UUID): The unique identifier of the timeline item.
        action_id (Uint8): The identifier of the action to invoke.
        num_attributes (Uint8): The number of attributes associated with the action.
        attributes (FixedList[TimelineAttribute]): A fixed list of attributes for the action,
            with length specified by num_attributes.
    """

    item_id = UUID()
    action_id = Uint8()
    num_attributes = Uint8()
    attributes = FixedList(TimelineAttribute, count=num_attributes)


class ActionResponse(PebblePacket):
    """
    Represents a response packet for an action in the Pebble timeline protocol.

    Attributes:
        item_id (UUID): The unique identifier of the timeline item associated with the action.
        response (Response): The response status, either ACK (acknowledged) or
            NACK (not acknowledged).
        num_attributes (Uint8): The number of attributes included in the response.
        attributes (FixedList[TimelineAttribute]): A fixed list of timeline attributes,
            with length specified by num_attributes.

    Classes:
        Response (IntEnum): Enumeration of possible response statuses:
            ACK (0): Action acknowledged.
            NACK (1): Action not acknowledged.
    """

    class Response(IntEnum):
        """
        An enumeration representing possible response types for timeline protocol operations.

        Attributes:
            ACK (int): Indicates a successful acknowledgment (value: 0).
            NACK (int): Indicates a negative acknowledgment or failure (value: 1).
        """

        ACK = 0
        NACK = 1

    item_id = UUID()
    response = Uint8(enum=Response)
    num_attributes = Uint8()
    attributes = FixedList(TimelineAttribute, count=num_attributes)


class TimelineActionEndpoint(PebblePacket):
    """
    Represents a Pebble timeline action endpoint packet.

    This class is used to encode and decode packets sent to or received from the Pebble timeline
    action endpoint. It supports multiple command types, with the payload structure determined
    by the command value.

    Attributes:
        command (Uint8): The command identifier for the timeline action.
        data (Union): The payload data, which is determined by the value of `command`.
            - If command == 0x02: uses InvokeAction structure.
            - If command == 0x11: uses ActionResponse structure.

    Meta:
        endpoint (int): The endpoint identifier for timeline actions (0x2CB0).
        endianness (str): The byte order used for encoding/decoding ("<" for little-endian).
    """

    class Meta:
        """
        Meta class containing protocol configuration for timeline communication.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x2CB0).
            endianness (str): Byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0x2CB0
        endianness = "<"

    command = Uint8()
    data = Union(command, {0x02: InvokeAction, 0x11: ActionResponse})
