__author__ = "katharine"

from .base import PebblePacket
from .base.types import PascalList, PascalString, Uint8, Uint32, Union

__all__ = [
    "AnswerCall",
    "CallEnd",
    "CallStart",
    "CallStateItem",
    "HangUpCall",
    "IncomingCall",
    "MissedCall",
    "OutgoingCall",
    "PhoneNotification",
    "PhoneStateRequest",
    "PhoneStateResponse",
    "Ring",
]


class AnswerCall(PebblePacket):
    """Represents a packet to answer an incoming call on the Pebble device."""


class HangUpCall(PebblePacket):
    """Represents a packet to hang up an ongoing call on the Pebble device."""


class PhoneStateRequest(PebblePacket):
    """Represents a request for the current phone state from the Pebble device."""


class IncomingCall(PebblePacket):
    """
    Represents an incoming call packet.

    Attributes:
        number (PascalString): The phone number of the incoming call.
        name (PascalString): The name associated with the incoming call.
    """

    number = PascalString()
    name = PascalString()


class OutgoingCall(PebblePacket):
    """
    Represents an outgoing call packet.

    Attributes:
        number (PascalString): The phone number of the outgoing call.
        name (PascalString): The name associated with the outgoing call.
    """

    number = PascalString()
    name = PascalString()


class MissedCall(PebblePacket):
    """Represents a packet indicating that a call was missed."""


class Ring(PebblePacket):
    """Represents a packet indicating that the phone is ringing."""


class CallStart(PebblePacket):
    """Represents a packet indicating that a call has started."""


class CallEnd(PebblePacket):
    """Represents a packet indicating that a call has ended."""


class CallStateItem(PebblePacket):
    """
    Represents a call state item packet for Pebble protocol communication.

    Attributes:
        command_id (Uint8): Identifier for the command type.
        cookie (Uint32): Unique identifier for the call session.
        item (Union): Union field determined by `command_id`:
            - 0x04: IncomingCall
            - 0x05: OutgoingCall
            - 0x08: CallStart

    The `item` field dynamically selects the appropriate call state class
    based on the value of `command_id`.
    """

    command_id = Uint8()
    cookie = Uint32()
    item = Union(
        command_id,
        {
            0x04: IncomingCall,
            0x05: OutgoingCall,
            0x08: CallStart,
        },
    )


class PhoneStateResponse(PebblePacket):
    """
    Represents a response packet containing the current phone state.

    Attributes:
        items (PascalList[CallStateItem]): A list of call state items, each representing
            the state of an individual call on the phone.
    """

    items = PascalList(CallStateItem)


class PhoneNotification(PebblePacket):
    """
    Represents a phone notification packet exchanged between the Pebble device and the phone.

    This packet contains a command identifier, a cookie for tracking, and a message payload
    whose type is determined by the command_id. The message can represent various phone-related
    actions or states, such as answering a call, hanging up, requesting phone state, or reporting
    call events.

    Attributes:
        command_id (Uint8): Identifier for the type of phone notification command.
        cookie (Uint32): A unique value used to correlate requests and responses.
        message (Union): The payload of the notification, whose type depends on command_id.
            Supported command_id values and their corresponding message types:
                0x01: AnswerCall
                0x02: HangUpCall
                0x03: PhoneStateRequest
                0x83: PhoneStateResponse
                0x04: IncomingCall
                0x05: OutgoingCall
                0x06: MissedCall
                0x07: Ring
                0x08: CallStart
                0x09: CallEnd

    Meta:
        endpoint (int): Protocol endpoint for phone notifications (0x21).
    """

    class Meta:
        """
        Meta class for protocol configuration.

        Attributes:
            endpoint (int): The endpoint identifier for the protocol, set to 0x21.
        """

        endpoint = 0x21

    command_id = Uint8()
    cookie = Uint32()
    message = Union(
        command_id,
        {
            0x01: AnswerCall,
            0x02: HangUpCall,
            0x03: PhoneStateRequest,
            0x83: PhoneStateResponse,
            0x04: IncomingCall,
            0x05: OutgoingCall,
            0x06: MissedCall,
            0x07: Ring,
            0x08: CallStart,
            0x09: CallEnd,
        },
    )
