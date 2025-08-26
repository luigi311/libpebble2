__author__ = "katharine"

import collections
import logging
import struct
from binascii import hexlify
from typing import Self

from libpebble2.exceptions import IncompleteMessage

from .types import DEFAULT_ENDIANNESS, Field

__all__ = ["PebblePacket"]

logger = logging.getLogger("libpebble2.protocol")

_PacketRegistry: dict[int, type["PebblePacket"]] = {}


def make_output(thing: str) -> object:
    """
    Creates and returns an instance of a dynamically defined class whose __repr__ method returns
    the provided string.

    Args:
        thing (str): The string to be returned by the __repr__ method of the generated class
        instance.

    Returns:
        object: An instance of a class with a custom __repr__ method.
    """

    class C:
        def __repr__(self) -> str:
            return thing

    return C()


class PacketType(type):
    """
    Metaclass for :class:`PebblePacket` that transforms properties that are subclasses of
    :class:`Field` into a Pebble Protocol parser.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple,
        dct: dict,
    ) -> type:
        mapping = []
        # If we have a _Meta property, delete it.
        dct.pop("_Meta", None)
        # If we have a Meta property, move it to _Meta. This effectively prevents it being inherited.
        if "Meta" in dct:
            dct["_Meta"] = dct["Meta"].__dict__
            del dct["Meta"]

        # For each Field, add it to our mapping, then set the exposed value to its default value.
        # We go through the classes we inherited from to add anything in there.
        # This means that inheritance works, with inherited classes appending their fields to the end.
        dct["_type_mapping"] = collections.OrderedDict()
        for base in bases:
            if hasattr(base, "_type_mapping"):
                dct["_type_mapping"].update(base._type_mapping)
        for k, v in dct.items():
            if not isinstance(v, Field):
                continue
            v._name = k
            mapping.append((k, v))
            dct[k] = v._default
        # Put the results into an ordered dict. We sort on field_id to ensure that our dict ends up
        # in the correct order.
        dct["_type_mapping"].update(
            collections.OrderedDict(sorted(mapping, key=lambda x: x[1].field_id))
        )
        return super().__new__(mcs, name, bases, dct)

    def __init__(cls, name: str, bases: tuple, dct: dict) -> None:
        # At this point we actually have a references to the class, so we can register it
        # in our packet type registry for later decoding.
        if hasattr(cls, "_Meta") and "endpoint" in cls._Meta and cls._Meta.get("register", True):
            _PacketRegistry[cls._Meta["endpoint"]] = cls
        # Fill in all of the fields with a reference to this class.
        # TODO: This isn't used any more; remove it?
        for v in cls._type_mapping.values():
            v._parent = cls
        super().__init__(name, bases, dct)

    def __repr__(cls) -> str:
        return cls.__name__


class PebblePacket(metaclass=PacketType):
    r"""
    Represents some sort of Pebble Protocol message.

    A PebblePacket can have an inner class named ``Meta`` containing some information about the
    property:

    ==================  ============================================================================
    **endpoint**        The Pebble Protocol endpoint that is represented by this message.
    **endianness**      The endianness of the packet. The default endianness is big-endian, but it
                        can be overridden by packets and fields, with the priority:
    **register**        If set to ``False``, the packet will not be registered and thus will be
                        ignored by :meth:`parse_message`. This is useful when messages are
                        ambiguous, and distinguished only by whether they are sent to or from
                        the Pebble.
    ==================  ============================================================================

    A sample packet might look like this: ::

       class AppFetchResponse(PebblePacket):
           class Meta:
               endpoint = 0x1771
               endianness = '<'
               register = False

           command = Uint8(default=0x01)
           response = Uint8(enum=AppFetchStatus)

    Args:
        **kwargs (object): Initial values for any properties on the object.
    """

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            if k.startswith("_"):
                msg = "You cannot set internal properties during construction."
                raise AttributeError(msg)
            getattr(self, k)  # Throws an exception if the property doesn't exist.
            setattr(self, k, v)

    def serialise(self, default_endianness: str | None = None) -> bytes:
        """
        Serialise a message, without including any framing.

        Args:
            default_endianness (str | None): The default endianness, unless overridden by the
                fields or class metadata. Should usually be left at ``None``. Otherwise,
                use ``'<'`` for little endian and ``'>'`` for big endian.

        Returns:
            bytes: The serialised message.

        """
        # Figure out an endianness.
        endianness = default_endianness or DEFAULT_ENDIANNESS
        if hasattr(self, "_Meta"):
            endianness = self._Meta.get("endianness", endianness)

        inferred_fields = set()
        for v in self._type_mapping.values():
            inferred_fields |= {x._name for x in v.dependent_fields()}
        for field in inferred_fields:
            setattr(self, field, None)

        # Some fields want to manipulate other fields that appear before them (e.g. Unions)
        for k, v in self._type_mapping.items():
            v.prepare(self, getattr(self, k))

        message = b""
        for k, v in self._type_mapping.items():
            message += v.value_to_bytes(self, getattr(self, k), default_endianness=endianness)
        return message

    def serialise_packet(self) -> bytes:
        """
        Serialise a message, including framing information inferred from the ``Meta`` inner class
        of the packet. ``self.Meta.endpoint`` must be defined to call this method.

        Returns:
            bytes: A serialised message, ready to be sent to the Pebble.
        """
        if not hasattr(self, "_Meta"):
            msg = "Can't serialise a packet that doesn't have an endpoint ID."
            raise ReferenceError(msg)
        serialised = self.serialise()
        return struct.pack("!HH", len(serialised), self._Meta["endpoint"]) + serialised

    @classmethod
    def parse_message(cls, message: bytes) -> tuple["PebblePacket | None", int]:
        """
        Parses a message received from the Pebble. Uses Pebble Protocol framing to figure out what
        sort of packet it is. If the packet is registered (has been defined and imported),
        returns the deserialised packet, which will not necessarily be the same class as this.
        Otherwise returns ``None``.

        Also returns the length of the message consumed during deserialisation.

        Args:
            message (bytes): A serialised message received from the Pebble.

        Returns:
            tuple(object | None, int): ``(decoded_message, decoded length)``

        Raises:
            IncompleteMessage: If the message is too short to contain a complete packet.
        """
        length = struct.unpack_from("!H", message, 0)[0] + 4
        if len(message) < length:
            raise IncompleteMessage()
        (command,) = struct.unpack_from("!H", message, 2)
        if command in _PacketRegistry:
            return _PacketRegistry[command].parse(message[4:length])[0], length

        return None, length

    @classmethod
    def parse(
        cls,
        message: bytes,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[Self, int]:
        """
        Parses a message without any framing, returning the decoded result and length of message
        consumed. The result will always be of the same class as :meth:`parse` was called on.

        Args:
            message (bytes): A serialised message received from the Pebble.
            default_endianness (str): The default endianness, unless overridden by the fields
                or class metadata. Should usually be left at ``None``. Otherwise, use ``'<'``
                for little endian and ``'>'`` for big endian.

        Returns:
            tuple(PebblePacket, int): ``(decoded_message, decoded length)``

        Raises:
            IncompleteMessage: If the message is too short to contain a complete packet.
            ValueError: If the message is not a valid Pebble packet.
        """
        obj = cls()
        offset = 0
        if hasattr(cls, "_Meta"):
            default_endianness = cls._Meta.get("endianness", default_endianness)
        for k, v in cls._type_mapping.items():
            try:
                value, length = v.buffer_to_value(
                    obj, message, offset, default_endianness=default_endianness
                )
            except Exception:
                logger.warning("Exception decoding %s.%s", cls.__name__, k)
                raise
            offset += length
            setattr(obj, k, value)
        return obj, offset

    def __repr__(self) -> str:
        return "{}({})".format(
            type(self).__name__,
            ", ".join(f"{k}={self._format_repr(getattr(self, k))}" for k in self._type_mapping),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PebblePacket):
            return False

        if type(self) is not type(other):
            return False

        return all(getattr(self, k) == getattr(other, k) for k in self._type_mapping)

    # Make value-equal packets unhashable to avoid broken hashing on mutable/list fields.
    __hash__ = None

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def _format_repr(self, value: object) -> object:
        if isinstance(value, bytes):
            if len(value) < 20:
                return hexlify(value).decode()

            return hexlify(value[:17]).decode() + "..."

        return value
