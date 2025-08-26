from __future__ import annotations

__author__ = "katharine"

import enum as enum_import
import struct
import typing as t
import uuid
from typing import TYPE_CHECKING, ClassVar

from libpebble2.exceptions import PacketDecodeError, PacketEncodeError

# Avoid circular import: only import for type checking, not at runtime.
if TYPE_CHECKING:
    from libpebble2.protocol.base import PebblePacket

else:
    PebblePacket = t.Any  # runtime-safe, avoids circular import

__all__ = [
    "DEFAULT_ENDIANNESS",
    "UUID",
    "BinaryArray",
    "Boolean",
    "Embed",
    "Field",
    "FixedList",
    "FixedString",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "NullTerminatedString",
    "Optional",
    "Padding",
    "PascalList",
    "PascalString",
    "Uint8",
    "Uint16",
    "Uint32",
    "Uint64",
    "Union",
]

DEFAULT_ENDIANNESS: str = "!"


T = t.TypeVar("T")


class Field[T]:
    """
    Base class for Pebble Protocol fields. Subclasses provide concrete behaviour.

    Args:
        default: Default value of the field (if unspecified).
        endianness: Overrides the packet endianness. Use '<' (LE), '>' (BE) or '!' (network).
        enum: An Enum type representing valid values for this field. If provided, decoded
              values will be wrapped as that Enum (and encode expects either the Enum or
              its underlying value).
    """

    # A format code for use in struct.pack/unpack for numeric/boolean fields.
    struct_format: ClassVar[str]

    # Used internally by PebblePacket to sort fields into declaration order.
    next_id: ClassVar[int] = 0

    def __init__(
        self,
        default: T | None = None,
        endianness: str | None = None,
        enum: type[enum_import.Enum] | None = None,
    ) -> None:
        self.type: str = type(self).__name__
        self._name: str | None = None
        self._parent: PebblePacket | None = None
        self._default: T | None = default
        self._enum: type[enum_import.Enum] | None = enum
        self.field_id: int = Field.next_id
        self.endianness: str | None = endianness
        Field.next_id += 1

    @property
    def name(self) -> str | None:
        """The public name of this field, or None if private."""
        return self._name

    # --- decode/encode -----------------------------------------------------

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[T, int]:
        """
        Convert bytes at ``offset`` in ``buffer`` to a Python value, returning
        (value, bytes_used).
        """
        _ = obj
        try:
            pack_fmt = (self.endianness or default_endianness) + self.struct_format
            value = t.cast("t.Any", struct.unpack_from(pack_fmt, buffer, offset)[0])
            length = struct.calcsize(pack_fmt)
            if self._enum is not None:
                try:
                    return t.cast(T, self._enum(value)), length
                except (ValueError, TypeError) as e:
                    msg = f"{self.type}: {e}"
                    raise PacketDecodeError(msg) from e
            return t.cast(T, value), length
        except struct.error as e:
            msg = f"{self.type}: {e}"
            raise PacketDecodeError(msg) from e

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: T,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """Convert a Python value to bytes for transmission."""
        if self._enum is not None and isinstance(value, self._enum):
            # Pack using the underlying enum value
            value = t.cast("T", t.cast("enum_import.Enum", value).value)
        return struct.pack(
            (self.endianness or default_endianness) + self.struct_format,
            t.cast("t.Any", value),
        )

    # --- hooks for composite fields ---------------------------------------

    def prepare(self, _obj: PebblePacket, _value: T) -> None:
        """Hook: called before serialisation to update dependent fields."""
        return

    def dependent_fields(self) -> list[Field[t.Any]]:
        """Hook: which fields must be serialised before this one (for lengths/counts)."""
        return []


# --------------------------- scalars ---------------------------------------


class Int8(Field[int]):
    """int8_t."""

    struct_format = "b"


class Uint8(Field[int]):
    """uint8_t."""

    struct_format = "B"


class Int16(Field[int]):
    """int16_t."""

    struct_format = "h"


class Uint16(Field[int]):
    """uint16_t."""

    struct_format = "H"


class Int32(Field[int]):
    """int32_t."""

    struct_format = "i"


class Uint32(Field[int]):
    """uint32_t."""

    struct_format = "I"


class Int64(Field[int]):
    """int64_t."""

    struct_format = "q"


class Uint64(Field[int]):
    """uint64_t."""

    struct_format = "Q"


class Boolean(Field[bool]):
    """bool."""

    struct_format = "?"


class UUID(Field[uuid.UUID]):
    """16-byte UUID (uint8_t[16]). Endianness is ignored."""

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[uuid.UUID, int]:
        """
        Convert bytes at the given offset in the buffer to a UUID value.

        Args:
            obj (PebblePacket): The packet object for context.
            buffer (bytes): The byte buffer containing the UUID.
            offset (int): The starting index in the buffer.
            default_endianness (str, optional): The default endianness (ignored for UUID).

        Returns:
            tuple[uuid.UUID, int]: The decoded UUID and the number of bytes consumed (16).

        Raises:
            PacketDecodeError: If the UUID cannot be decoded from the buffer.
        """
        try:
            return uuid.UUID(bytes=buffer[offset : offset + 16]), 16
        except (ValueError, IndexError) as e:
            msg = f"{self.type}: failed to decode UUID: {e}"
            raise PacketDecodeError(msg) from e

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: uuid.UUID,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """Return the raw 16-byte representation of the UUID (endianness ignored).

        Raises:
            PacketEncodeError: If the provided value is not a uuid.UUID instance.
        """
        if not isinstance(value, uuid.UUID):
            msg = f"{self.type}: expected uuid.UUID, got {type(value).__name__}"
            raise PacketEncodeError(msg)
        return value.bytes


# ----------------------- composites / containers ---------------------------


class Union(Field[PebblePacket | None]):
    r"""
    Discriminated union determined by another field (``determinant``).

    Example:
        command = Uint8()
        data = Union(command, {0: SomePacket, 1: OtherPacket})
    """

    def __init__(
        self,
        determinant: Field[t.Any],
        contents: dict[int, type[PebblePacket]],
        accept_missing: bool = False,
        length: Field[int] | int | None = None,
    ) -> None:
        self.determinant = determinant
        self.contents: dict[int, type[PebblePacket]] = contents
        self.type_map: dict[type[PebblePacket], int] = {v: k for k, v in contents.items()}
        self.accept_missing = accept_missing
        self.length = length
        super().__init__()

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: PebblePacket | None,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Serializes the union field value to bytes.

        Args:
            obj (PebblePacket): The parent packet object containing the field.
            value (PebblePacket | None): The value to serialize, or None.
            default_endianness (str, optional): The endianness to use for serialization.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The serialized byte representation of the value.

        Raises:
            PacketEncodeError: If value is None and accept_missing is False.
        """
        if value is not None:
            return value.serialise(default_endianness=default_endianness)
        if self.accept_missing:
            return b""
        msg = f"{self.type}: missing union value and accept_missing=False"
        raise PacketEncodeError(msg)

    def prepare(self, obj: PebblePacket, value: PebblePacket | None) -> None:
        """
        Prepares a PebblePacket object by setting determinant and length fields based on the
        provided value.

        Args:
            obj (PebblePacket): The packet object to modify.
            value (PebblePacket | None): The value to encode into the packet, or None.

        Raises:
            PacketEncodeError: If the type of value is not present in the type_map and
                accept_missing is False.

        Side Effects:
            - Sets the determinant field on `obj` if `value` is not None and type is in `type_map`.
            - Sets the length field on `obj` if `length` is a Field and `value` is not None.
        """
        if value is not None:
            try:
                if self.determinant.name is None:
                    msg = f"{self.type}: determinant field has no public 'name' attribute"
                    raise PacketEncodeError(msg)
                setattr(obj, t.cast("str", self.determinant.name), self.type_map[type(value)])
            except KeyError as e:
                if not self.accept_missing:
                    msg = f"{self.type}: value type {type(value).__name__} not in union"
                    raise PacketEncodeError(msg) from e

        if isinstance(self.length, Field) and value is not None and self.length.name is not None:
            setattr(obj, self.length.name, len(value.serialise()))

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[PebblePacket | None, int]:
        """
        Parses a buffer to extract a value based on the union type specified by the
        determinant field.

        Args:
            obj (PebblePacket): The packet object containing field values used for parsing.
            buffer (bytes): The byte buffer to parse.
            offset (int): The starting offset in the buffer.
            default_endianness (str, optional): The default endianness to use for parsing.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[PebblePacket | None, int]: A tuple containing the parsed packet (or None if
                missing is accepted) and the number of bytes consumed.

        Raises:
            PacketDecodeError: If the determinant key is not recognized and missing values are
                not accepted.
        """
        if isinstance(self.length, Field):
            if self.length.name is None:
                msg = f"{self.type}: length field has no public 'name' attribute"
                raise PacketDecodeError(msg)
            max_len = t.cast("int", getattr(obj, self.length.name))
        else:
            max_len = len(buffer) - offset if self.length is None else int(self.length)

        if self.determinant.name is None:
            msg = f"{self.type}: determinant field has no public 'name' attribute"
            raise PacketDecodeError(msg)
        k = getattr(obj, self.determinant.name)
        packet_type = self.contents.get(k)
        if packet_type is None:
            if self.accept_missing:
                # Consume the declared length (if any), return None
                return None, max_len
            msg = f"{self.type}: unrecognised union key {k}"
            raise PacketDecodeError(msg)

        return packet_type.parse(buffer[offset : offset + max_len], default_endianness)

    def dependent_fields(self) -> list[Field[t.Any]]:
        """
        Returns a list containing the determinant field if missing values are not accepted,
        otherwise returns an empty list.

        Returns:
            list[Field[t.Any]]: A list with the determinant field or an empty list.
        """
        return [self.determinant] if not self.accept_missing else []


class Embed(Field[PebblePacket]):
    """
    Embed another PebblePacket. Useful for repetitive structures.

    Args:
        packet: The packet *class* to embed.
        length: Optional max length (Field or int). If provided, serialisation
                is truncated-checked and deserialisation uses it as a bound.
    """

    def __init__(
        self,
        packet: type[PebblePacket],
        length: Field[int] | int | None = None,
    ) -> None:
        self.packet = packet
        self.length = length
        super().__init__()

    def prepare(self, obj: PebblePacket, value: PebblePacket) -> None:
        """
        Prepares the given PebblePacket object by setting the length attribute if required.

        If the 'length' attribute of the current instance is a Field, this method sets the
            corresponding attribute on 'obj' to the length of the serialized 'value'.

        Args:
            obj (PebblePacket): The packet object whose length attribute may be set.
            value (PebblePacket): The packet whose serialized length is used to set the
                length attribute.

        Returns:
            None
        """
        if isinstance(self.length, Field) and self.length.name is not None:
            setattr(obj, self.length.name, len(value.serialise()))

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: PebblePacket,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Serializes the given value to bytes, ensuring it does not exceed the maximum allowed length.

        Args:
            obj (PebblePacket): The parent packet object containing the field.
            value (PebblePacket): The value to serialize.
            default_endianness (str, optional): The endianness to use for serialization.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The serialized byte representation of the value.

        Raises:
            PacketEncodeError: If the serialized value exceeds the maximum allowed length.
        """
        v = value.serialise(default_endianness=default_endianness)
        max_len: int | None
        if isinstance(self.length, Field):
            if not self.length.name:
                msg = f"{self.type}: length field has no name"
                raise PacketEncodeError(msg)
            max_len = t.cast("int", getattr(obj, self.length.name))
        else:
            max_len = t.cast("int | None", self.length)
        if max_len is not None and len(v) > max_len:
            msg = f"Embedded field with max length {max_len} is {len(v)} bytes long."
            raise PacketEncodeError(msg)
        return v

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[PebblePacket, int]:
        """
        Parses a buffer into a PebblePacket object starting from a given offset.

        Args:
            obj (PebblePacket): The packet object used for context, especially for dynamic length
                fields.
            buffer (bytes): The byte buffer to parse.
            offset (int): The starting index in the buffer to begin parsing.
            default_endianness (str, optional): The endianness to use for parsing.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[PebblePacket, int]: A tuple containing the parsed PebblePacket and the number
                of bytes consumed.

        Notes:
            - If `self.length` is None, the entire buffer from the offset is parsed.
            - If `self.length` is a Field, its value is retrieved from `obj` to determine the
                maximum length to parse.
            - Otherwise, `self.length` is treated as an integer specifying the number of bytes
                to parse.
        """
        if self.length is None:
            return self.packet.parse(buffer[offset:], default_endianness)
        if isinstance(self.length, Field):
            if not self.length.name:
                msg = f"{self.type}: length field has no name"
                raise PacketDecodeError(msg)
            max_len = t.cast("int", getattr(obj, self.length.name))
        else:
            max_len = int(self.length)
        return self.packet.parse(buffer[offset : offset + max_len], default_endianness)

    def dependent_fields(self) -> list[Field[t.Any]]:
        """
        Returns a list containing the length field if it is an instance of Field, otherwise
            returns an empty list.

        Returns:
            list[Field[t.Any]]: A list with the length field if applicable, otherwise an empty list.
        """
        return [self.length] if isinstance(self.length, Field) else []


class Padding(Field[None]):
    """
    Unused padding bytes.

    Args:
        length: Number of padding bytes.
    """

    def __init__(self, length: int) -> None:
        self.length = int(length)
        super().__init__()

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[None, int]:
        """
        Converts a buffer to a value for the given PebblePacket object.

        Args:
            obj (PebblePacket): The packet object to populate.
            buffer (bytes): The input buffer containing data.
            offset (int): The starting offset in the buffer.
            default_endianness (str, optional): The default endianness to use.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[None, int]: A tuple containing None as the value and the length
                of the data processed.
        """
        return None, self.length

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: None,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Converts the given value to its byte representation.

        Args:
            obj (PebblePacket): The packet object containing the value.
            value (None): The value to convert. Currently unused.
            default_endianness (str, optional): The endianness to use for conversion.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: A bytes object of length `self.length`, filled with zero bytes.
        """
        return b"\x00" * self.length


class PascalString(Field[str]):
    """
    UTF-8 string prefixed with a length byte.

    Args:
        null_terminated: Append a NUL (and optionally count it).
        count_null_terminator: If True, the appended NUL is *not* counted in length.
    """

    def __init__(
        self,
        null_terminated: bool = False,
        count_null_terminator: bool = True,
        **kwargs: t.Any,
    ) -> None:
        self.null_terminated = bool(null_terminated)
        self.count_null_terminator = bool(count_null_terminator)
        super().__init__(**kwargs)

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[str, int]:
        """
        Decodes a value from a buffer starting at the given offset.

        Args:
            obj (PebblePacket): The packet object being decoded.
            buffer (bytes): The buffer containing the data.
            offset (int): The offset in the buffer to start decoding from.
            default_endianness (str, optional): The default endianness to use for decoding.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[str, int]: A tuple containing the decoded string value and the number of
                bytes consumed.

        Raises:
            PacketDecodeError: If the buffer does not contain enough data or if unpacking fails.
        """
        try:
            (length,) = struct.unpack_from("B", buffer, offset)
        except struct.error as e:
            msg = f"{self.type}: {e}"
            raise PacketDecodeError(msg) from e

        extra = 1 + (1 if (self.null_terminated and not self.count_null_terminator) else 0)
        needed = length + extra
        if len(buffer) < offset + needed:
            msg = f"{self.type}: expected {needed} bytes, only have {len(buffer) - offset}"
            raise PacketDecodeError(msg)
        raw = buffer[offset + 1 : offset + 1 + length]
        return raw.split(b"\x00")[0].decode("utf-8"), needed

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: str,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        r"""
        Converts a string value to a bytes representation suitable for packet transmission.

        The string is encoded in UTF-8 and truncated to a maximum of 255 bytes. If `null_terminated`
        is True, a null terminator (`b"\x00"`) is appended to the string. The behavior of the null
        terminator depends on the `count_null_terminator` flag:
            - If True, the null terminator is included in the length count (max 254 bytes + null).
            - If False, the null terminator is not included in the length count
                (max 255 bytes + null).

        The resulting bytes object consists of a single length byte followed by the encoded
        string data.

        Args:
            obj (PebblePacket): The packet object containing the value.
            value (str): The string value to encode.
            default_endianness (str, optional): The default endianness to use.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The encoded bytes representation of the value, prefixed with its length.
        """
        raw = value.encode("utf-8")[:255]
        if self.null_terminated:
            if self.count_null_terminator:
                raw = raw[:254] + b"\x00"
                length = len(raw)
            else:
                raw = raw[:255] + b"\x00"
                length = len(raw) - 1
        else:
            length = len(raw)
        return struct.pack("B", length) + raw


class NullTerminatedString(Field[str]):
    """C-style NUL-terminated UTF-8 string."""

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[str, int]:
        """
        Decodes a null-terminated UTF-8 string from a buffer starting at the given offset.

        Args:
            obj (PebblePacket): The packet object (unused in this method).
            buffer (bytes): The byte buffer containing the data.
            offset (int): The starting index in the buffer to decode from.
            default_endianness (str, optional): The default endianness (unused in this method).

        Returns:
            tuple[str, int]: A tuple containing the decoded string and the number of bytes
                consumed (including the null terminator).

        Raises:
            PacketDecodeError: If there are no bytes available at the offset or if the buffer does
                not contain a null terminator.
        """
        end = offset
        if end >= len(buffer):
            msg = f"{self.type}: no bytes available."
            raise PacketDecodeError(msg)
        while end < len(buffer) and buffer[end] != 0:
            end += 1
        if end >= len(buffer):
            msg = f"{self.type}: reached end of buffer without terminator."
            raise PacketDecodeError(msg)
        return buffer[offset:end].decode("utf-8"), (end - offset + 1)

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: str,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Converts a string value to bytes using UTF-8 encoding and appends a null terminator.

        Args:
            obj (PebblePacket): The packet object associated with the value.
            value (str): The string value to convert.
            default_endianness (str, optional): The default endianness to use.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The UTF-8 encoded bytes of the string value, followed by a null byte.
        """
        return value.encode("utf-8") + b"\x00"


class FixedString(Field[str]):
    """
    Fixed-length string, where the length is:
      * another Field (read earlier), or
      * a protocol constant (int), or
      * the remainder of the packet (None).
    """

    def __init__(
        self,
        length: Field[int] | int | None = None,
        default: str | None = None,
        endianness: str | None = None,
        enum: type[enum_import.Enum] | None = None,
    ) -> None:
        self.length = length
        super().__init__(default=default, endianness=endianness, enum=enum)

    def prepare(self, obj: PebblePacket, value: str) -> None:
        """
        Prepares the given PebblePacket object by setting the length attribute based on
        the UTF-8 encoded length of the provided string value.

        Args:
            obj (PebblePacket): The packet object to modify.
            value (str): The string whose encoded length will be set.

        Side Effects:
            If `self.length` is a Field, sets the corresponding attribute on `obj` to the length
                of `value` encoded in UTF-8.
        """
        if isinstance(self.length, Field) and self.length.name is not None:
            setattr(obj, self.length.name, len(value.encode("utf-8")))

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[str, int]:
        """
        Converts a buffer segment to a string value for a PebblePacket field.

        Args:
            obj (PebblePacket): The packet object containing field metadata.
            buffer (bytes): The byte buffer to extract the value from.
            offset (int): The starting position in the buffer.
            default_endianness (str, optional): The default endianness to use.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[str, int]: A tuple containing the decoded string (up to the first null byte)
                and the number of bytes read.

        Raises:
            PacketDecodeError: If the buffer does not contain enough bytes to unpack the
                expected length.
        """
        if isinstance(self.length, Field):
            if self.length.name is None:
                msg = f"{self.type}: length field has no public 'name' attribute"
                raise PacketDecodeError(msg)

            length = t.cast("int", getattr(obj, self.length.name))
        elif self.length is not None:
            length = int(self.length)
        else:
            length = len(buffer) - offset
        try:
            raw = struct.unpack_from(f"{length}s", buffer, offset)[0]
            return raw.split(b"\x00")[0].decode("utf-8"), length
        except struct.error as e:
            msg = f"{self.type}: string not long enough (wanted {length} bytes)"
            raise PacketDecodeError(msg) from e

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: str,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Converts a string value to its byte representation for use in a PebblePacket.

        Args:
            obj (PebblePacket): The packet object containing field data.
            value (str): The string value to convert to bytes.
            default_endianness (str, optional): The default endianness to use.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The byte representation of the string value, packed according to
                the specified length.

        Notes:
            - The length of the byte string is determined by the 'length' attribute,
                which can be a Field, an integer, or None.
            - If 'length' is a Field, its value is retrieved from the packet object.
            - If 'length' is None, the length of the encoded string is used.
            - The string is encoded using UTF-8 before packing.
        """
        raw = value.encode("utf-8")
        if isinstance(self.length, Field):
            if self.length.name is None:
                msg = f"{self.type}: length field has no public 'name' attribute"
                raise PacketEncodeError(msg)
            length = t.cast("int", getattr(obj, self.length.name))
        elif self.length is not None:
            length = int(self.length)
        else:
            length = len(raw)
        return struct.pack(f"{length}s", raw)

    def dependent_fields(self) -> list[Field[t.Any]]:
        """
        Returns a list containing the length field if it is an instance of Field, otherwise
        returns an empty list.

        Returns:
            list[Field[t.Any]]: A list with the length field if applicable, otherwise an empty list.
        """
        return [self.length] if isinstance(self.length, Field) else []


class PascalList(Field[list[PebblePacket]]):
    """List of PebblePackets, each prefixed with a one-byte length."""

    def __init__(self, member_type: type[PebblePacket], count: Field[int] | None = None) -> None:
        self.member_type = member_type
        self.count = count
        super().__init__()

    def prepare(self, obj: PebblePacket, value: list[PebblePacket]) -> None:
        """
        Prepares the given PebblePacket object by setting the count field to the length of the
        provided value list.

        Args:
            obj (PebblePacket): The packet object to modify.
            value (list[PebblePacket]): The list of PebblePacket instances whose length will be
                assigned to the count field.

        Returns:
            None
        """
        if isinstance(self.count, Field):
            if self.count.name is None:
                msg = f"{self.type}: count field has no public 'name' attribute"
                raise PacketEncodeError(msg)
            setattr(obj, self.count.name, len(value))

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: list[PebblePacket],
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Serializes a list of PebblePackets, each prefixed with a one-byte length.

        Args:
            obj (PebblePacket): The parent packet object containing the field.
            value (list[PebblePacket]): The list of PebblePackets to serialize.
            default_endianness (str, optional): The endianness to use for serialization.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The serialized byte representation of the list.

        Raises:
            PacketEncodeError: If any element exceeds 255 bytes.
        """
        result = bytearray()
        for item in value:
            serialised = item.serialise(default_endianness=default_endianness)
            if len(serialised) > 255:
                msg = f"{self.type}: element exceeds 255 bytes"
                raise PacketEncodeError(msg)
            result += struct.pack("B", len(serialised)) + serialised
        return bytes(result)

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[list[PebblePacket], int]:
        """
        Parse a buffer into a list of PebblePacket objects, each prefixed with a one-byte length.

        Args:
            obj (PebblePacket): The packet object containing context for parsing.
            buffer (bytes): The byte buffer to parse.
            offset (int): The starting position in the buffer.
            default_endianness (str, optional): The endianness to use for parsing.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[list[PebblePacket], int]: A tuple containing the list of parsed Pebble
                Packets and the total number of bytes consumed.

        Raises:
            PacketDecodeError: If there is an error parsing the buffer.
        """
        results: list[PebblePacket] = []
        length = 0

        # Only require a name if a count Field was provided.
        if isinstance(self.count, Field):
            if self.count.name is None:
                msg = f"{self.type}: count field has no public 'name' attribute"
                raise PacketDecodeError(msg)
            max_count = t.cast("int", getattr(obj, self.count.name))
        else:
            max_count = None  # no count => read until buffer end

        i = 0
        while offset + length < len(buffer) and (max_count is None or i < max_count):
            try:
                (item_len,) = struct.unpack_from("B", buffer, offset + length)
            except struct.error as e:
                msg = f"{self.type}: couldn't parse entry length: {e}"
                raise PacketDecodeError(msg) from e
            length += 1
            packet, _ = self.member_type.parse(
                buffer[offset + length : offset + length + item_len],
                default_endianness=default_endianness,
            )
            results.append(packet)
            length += item_len
            i += 1

        return results, length

    def dependent_fields(self) -> list[Field[t.Any]]:
        """
        Returns a list containing the `count` field if it is an instance of `Field`, otherwise
            returns an empty list.

        Returns:
            list[Field[Any]]: A list with the `count` field if applicable, or an empty list.
        """
        return [self.count] if isinstance(self.count, Field) else []


class FixedList(Field[list[t.Any]]):
    """
    List of either PebblePackets or fixed-size Fields with either:
      * a fixed element count,
      * a fixed byte length,
      * both, or
      * neither (read to end of buffer).
    """

    def __init__(
        self,
        member_type: Field[t.Any] | type[PebblePacket],
        count: Field[int] | None = None,
        length: Field[int] | None = None,
    ) -> None:
        self.member_type = member_type
        self.count = count
        self.length = length
        super().__init__()

    def prepare(self, obj: PebblePacket, value: list[t.Any]) -> None:
        """
        Prepares the packet object by updating count and length fields based on the provided
            list of values.

        Args:
            obj (PebblePacket): The packet object to update.
            value (list[Any]): The list of values to process.

        Side Effects:
            - Sets the count field of `obj` to the length of `value` if `self.count` is a Field.
            - Updates the length field of `obj` by adding the total serialized size of all items
                in `value` if `self.length` is a Field.
        """
        if isinstance(self.count, Field):
            if self.count.name is None:
                msg = f"{self.type}: count field has no public 'name' attribute"
                raise PacketEncodeError(msg)
            setattr(obj, self.count.name, len(value))
        if isinstance(self.length, Field):
            if self.length.name is None:
                msg = f"{self.type}: length field has no public 'name' attribute"
                raise PacketEncodeError(msg)

            current = t.cast("int | None", getattr(obj, self.length.name)) or 0
            if isinstance(self.member_type, Field):
                total = sum(len(self.member_type.value_to_bytes(obj, x)) for x in value)
            else:
                total = sum(len(x.serialise()) for x in value)
            setattr(obj, self.length.name, current + total)

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: list[t.Any],
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Serializes a list of values (either PebblePackets or fixed-size Fields) into bytes.

        Args:
            obj (PebblePacket): The parent packet object containing the field.
            value (list[Any]): The list of values to serialize.
            default_endianness (str, optional): The endianness to use for serialization.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The serialized byte representation of the list.
        """
        out = bytearray()
        for v in value:
            if isinstance(self.member_type, Field):
                out += self.member_type.value_to_bytes(
                    obj,
                    v,
                    default_endianness=default_endianness,
                )
            else:
                out += v.serialise(default_endianness=default_endianness)
        return bytes(out)

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[list[t.Any], int]:
        """
        Parses a sequence of values from a buffer starting at the given offset.

        This method iterates over the buffer and extracts values of the specified member type,
        respecting optional count and length constraints. It supports both Field-based and
        non-Field member types for parsing.

        Args:
            obj (PebblePacket): The packet object containing context for parsing.
            buffer (bytes): The byte buffer to parse values from.
            offset (int): The starting position in the buffer.
            default_endianness (str, optional): The endianness to use for parsing.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[list[Any], int]: A tuple containing the list of parsed values and the total
                number of bytes consumed.
        """
        results: list[t.Any] = []
        length = 0

        max_count = (
            t.cast("int | None", getattr(obj, self.count.name))
            if isinstance(self.count, Field) and self.count.name is not None
            else None
        )
        max_len = (
            t.cast("int | None", getattr(obj, self.length.name))
            if isinstance(self.length, Field) and self.length.name is not None
            else None
        )

        i = 0
        while (
            offset + length < len(buffer)
            and (max_count is None or i < max_count)
            and (max_len is None or length < max_len)
        ):
            if isinstance(self.member_type, Field):
                value, item_len = self.member_type.buffer_to_value(
                    obj,
                    buffer,
                    offset + length,
                    default_endianness=default_endianness,
                )
            else:
                end = len(buffer) if max_len is None else min(len(buffer), offset + max_len)
                value, item_len = self.member_type.parse(
                    buffer[offset + length : end],
                    default_endianness=default_endianness,
                )
            results.append(value)
            length += item_len
            i += 1
        return results, length

    def dependent_fields(self) -> list[Field[t.Any]]:
        """
        Returns a list of fields that this field depends on, specifically the 'count'
            and 'length' attributes if they are instances of Field.

        Returns:
            list[Field[t.Any]]: A list containing the dependent Field instances for
                'count' and 'length'.
        """
        deps: list[Field[t.Any]] = []
        if isinstance(self.count, Field):
            deps.append(self.count)
        if isinstance(self.length, Field):
            deps.append(self.length)
        return deps


class BinaryArray(Field[bytes]):
    """Arbitrary bytes. Length can be another Field, a fixed int, or the remainder."""

    def __init__(
        self,
        length: Field[int] | int | None = None,
        default: bytes | None = None,
        endianness: str | None = None,
        enum: type[enum_import.Enum] | None = None,
    ) -> None:
        self.length = length
        super().__init__(default=default, endianness=endianness, enum=enum)

    def prepare(self, obj: PebblePacket, value: bytes) -> None:
        """
        Prepares the packet object by setting the length field if applicable.

        Args:
            obj (PebblePacket): The packet object to modify.
            value (bytes): The byte array whose length is used to set the length field.

        Returns:
            None
        """
        if isinstance(self.length, Field):
            if not self.length.name:
                msg = f"{self.type}: length field is None or has no public 'name' attribute"
                raise PacketEncodeError(msg)
            setattr(obj, self.length.name, len(value))

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: bytes,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Convert a Python bytes value to a padded byte array for transmission.

        Args:
            obj (PebblePacket): The parent packet object containing the field.
            value (bytes): The bytes value to serialize.
            default_endianness (str, optional): The endianness to use for serialization.

        Returns:
            bytes: The serialized and padded byte representation.

        Raises:
            TypeError: If value is not bytes or bytearray.
        """
        if not isinstance(value, (bytes, bytearray)):
            msg = f"BinaryArray expects 'bytes'; got {type(value).__name__}"
            raise TypeError(msg)
        data = bytes(value)
        if isinstance(self.length, Field):
            if not self.length.name:
                msg = f"{self.type}: length field is None or has no public 'name' attribute"
                raise PacketEncodeError(msg)
            length = t.cast("int", getattr(obj, self.length.name))
        elif self.length is not None:
            length = int(self.length)
        else:
            return data
        data = data[:length]
        return data + b"\x00" * (length - len(data))

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[bytes, int]:
        """
        Extracts a value from a buffer starting at a given offset, using the specified length.

        Args:
            obj (PebblePacket): The packet object containing field information.
            buffer (bytes): The input buffer from which to extract the value.
            offset (int): The starting position in the buffer.
            default_endianness (str, optional): The default byte order to use.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[bytes, int]: A tuple containing the extracted bytes and the length used.

        Raises:
            PacketDecodeError: If the buffer does not contain enough bytes to extract the value.
        """
        if isinstance(self.length, Field):
            if not self.length.name:
                msg = f"{self.type}: length field is None or has no public 'name' attribute"
                raise PacketDecodeError(msg)
            length = t.cast("int", getattr(obj, self.length.name))
        elif self.length is None:
            length = len(buffer) - offset
        else:
            length = int(self.length)
        if len(buffer) - offset < length:
            msg = f"{self.type}: expected {length} bytes, got {len(buffer) - offset}"
            raise PacketDecodeError(msg)
        return buffer[offset : offset + length], length

    def dependent_fields(self) -> list[Field[t.Any]]:
        """
        Returns a list containing the length field if it is an instance of Field, otherwise
            returns an empty list.

        Returns:
            list[Field[Any]]: A list with the length field if applicable, otherwise an empty list.
        """
        return [self.length] if isinstance(self.length, Field) else []


class Optional(Field[t.Any]):
    """
    Optional field wrapper. If omitted during deserialisation,
    leaves default and consumes 0 bytes.
    """

    def __init__(
        self,
        actual_field: Field[t.Any],
        default: object = None,
        endianness: str | None = None,
        enum: type[enum_import.Enum] | None = None,
    ) -> None:
        self.field = actual_field
        super().__init__(default=default, endianness=endianness, enum=enum)

    def prepare(self, obj: PebblePacket, value: object) -> None:
        """
        Prepares the field of a PebblePacket object with the given value.

        Args:
            obj (PebblePacket): The packet object whose field is to be prepared.
            value (object): The value to prepare the field with.

        Returns:
            None
        """
        self.field.prepare(obj, value)

    def value_to_bytes(
        self,
        obj: PebblePacket,
        value: object,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> bytes:
        """
        Converts a given value to its byte representation using the underlying field's
        conversion method.

        Args:
            obj (PebblePacket): The packet object containing context for the conversion.
            value (object): The value to be converted to bytes.
            default_endianness (str, optional): The endianness to use for conversion.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            bytes: The byte representation of the value. Returns an empty bytes object
                if value is None.
        """
        if value is None:
            return b""
        return self.field.value_to_bytes(obj, value, default_endianness=default_endianness)

    def buffer_to_value(
        self,
        obj: PebblePacket,
        buffer: bytes,
        offset: int,
        default_endianness: str = DEFAULT_ENDIANNESS,
    ) -> tuple[object, int]:
        """
        Decode the optional field from the buffer starting at the given offset.

        If the buffer is too short, returns (None, 0). Otherwise, delegates decoding to
            the wrapped field.

        Args:
            obj (PebblePacket): The packet object containing context for decoding.
            buffer (bytes): The byte buffer to decode from.
            offset (int): The starting position in the buffer.
            default_endianness (str, optional): The default byte order to use.
                Defaults to DEFAULT_ENDIANNESS.

        Returns:
            tuple[object, int]: A tuple containing the decoded value (or None if not present)
                and the number of bytes consumed (0 if not present).
        """
        if len(buffer) <= offset:
            return None, 0
        return self.field.buffer_to_value(
            obj,
            buffer,
            offset,
            default_endianness=default_endianness,
        )

    def dependent_fields(self) -> list[Field[object]]:
        """
        Returns the dependent fields for the wrapped field.

        Returns:
            list[Field[object]]: The dependent fields of the actual field.
        """
        return self.field.dependent_fields()
