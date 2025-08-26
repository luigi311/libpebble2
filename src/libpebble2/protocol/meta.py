__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import Uint8, Uint16

__all__ = ["MetaProtocolMessage"]


class MetaProtocolMessage(PebblePacket):
    """
    Represents a meta protocol message for Pebble communication.

    This message is used for meta-level communication, such as indicating disallowed or unhandled
    endpoints.

    Attributes:
        type (MetaProtocolMessage.Type): The type of meta protocol message, indicating the reason
            (e.g., Disallowed, Unhandled).
        endpoint_id (int): The identifier of the endpoint related to the meta message.

    Inner Classes:
        Meta: Contains protocol-specific metadata, such as the endpoint value.
        Type (IntEnum): Enumerates possible meta message types:
            - Disallowed (0xDD): Indicates the endpoint is disallowed.
            - Unhandled (0xDC): Indicates the endpoint is unhandled.
    """

    class Meta:
        """
        Represents the metadata protocol endpoint.

        Attributes:
            endpoint (int): The protocol endpoint identifier for metadata.
        """

        endpoint = 0x00

    class Type(IntEnum):
        """
        An enumeration representing meta types for protocol handling.

        Attributes:
            Disallowed (int): Indicates a disallowed type (value: 0xDD).
            Unhandled (int): Indicates an unhandled type (value: 0xDC).
        """

        Disallowed = 0xDD
        Unhandled = 0xDC

    type = Uint8(enum=Type)
    endpoint_id = Uint16()
