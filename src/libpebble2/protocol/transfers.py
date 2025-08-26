__author__ = "katharine"

from enum import IntEnum

from .base import PebblePacket
from .base.types import (
    BinaryArray,
    NullTerminatedString,
    PascalString,
    Uint8,
    Uint32,
    Union,
)

__all__ = [
    "GetBytes",
    "GetBytesCoredumpRequest",
    "GetBytesDataResponse",
    "GetBytesFileRequest",
    "GetBytesFlashRequest",
    "GetBytesInfoResponse",
    "GetBytesUnreadCoredumpRequest",
    "ObjectType",
    "PutBytes",
    "PutBytesAbort",
    "PutBytesApp",
    "PutBytesAppInit",
    "PutBytesCommit",
    "PutBytesInit",
    "PutBytesInstall",
    "PutBytesPut",
    "PutBytesResponse",
]


class ObjectType(IntEnum):
    """
    Enumeration of object types used in transfer protocols.

    Attributes:
        Firmware (int): Represents a firmware object (0x01).
        Recovery (int): Represents a recovery object (0x02).
        SystemResource (int): Represents a system resource object (0x03).
        AppResource (int): Represents an application resource object (0x04).
        AppExecutable (int): Represents an application executable object (0x05).
        File (int): Represents a generic file object (0x06).
        Worker (int): Represents a worker object (0x07).
    """

    Firmware = 0x01
    Recovery = 0x02
    SystemResource = 0x03
    AppResource = 0x04
    AppExecutable = 0x05
    File = 0x06
    Worker = 0x07


class PutBytesInit(PebblePacket):
    """
    Represents the initialization packet for a 'PutBytes' transfer in the Pebble protocol.

    Attributes:
        object_size (Uint32): The size of the object being transferred, in bytes.
        object_type (Uint8): The type identifier for the object.
        bank (Uint8): The bank identifier where the object will be stored.
        filename (NullTerminatedString): The filename associated with the object.
    """

    object_size = Uint32()
    object_type = Uint8()
    bank = Uint8()
    filename = NullTerminatedString()


class PutBytesAppInit(PebblePacket):
    """
    Represents the initialization packet for a 'PutBytes' transfer related to an app.

    Attributes:
        object_size (Uint32): The size of the object being transferred.
        object_type (Uint8): The type of object (e.g., binary, resource, etc.).
        app_id (Uint32): The identifier of the app associated with the transfer.
    """

    object_size = Uint32()
    object_type = Uint8()
    app_id = Uint32()


class PutBytesPut(PebblePacket):
    """
    Represents a packet for the 'PutBytes' protocol used to transfer binary data.

    Attributes:
        cookie (Uint32): Unique identifier for the transfer session.
        payload_size (Uint32): Size of the payload in bytes.
        payload (BinaryArray): Binary data to be transferred, with length specified by payload_size.
    """

    cookie = Uint32()
    payload_size = Uint32()
    payload = BinaryArray(length=payload_size)


class PutBytesCommit(PebblePacket):
    """
    Represents a packet used to commit a 'PutBytes' transfer in the Pebble protocol.

    Attributes:
        cookie (Uint32): A unique identifier for the transfer session.
        object_crc (Uint32): CRC32 checksum of the transferred object for integrity verification.
    """

    cookie = Uint32()
    object_crc = Uint32()


class PutBytesAbort(PebblePacket):
    """
    Represents a packet to abort an ongoing PutBytes transfer.

    Attributes:
        cookie (Uint32): Unique identifier for the transfer session to be aborted.
    """

    cookie = Uint32()


class PutBytesInstall(PebblePacket):
    """
    Represents a packet for initiating a 'PutBytes' install operation on a Pebble device.

    Attributes:
        cookie (Uint32): A unique identifier used to track the transfer session.
    """

    cookie = Uint32()


class PutBytes(PebblePacket):
    """
    Represents a Pebble protocol packet for the PutBytes transfer operation.

    This packet is used to manage the transfer of data to the Pebble device, supporting
    various commands such as initialization, data transfer, commit, abort, and install.

    Attributes:
        command (Uint8): The command identifier for the transfer operation.
        data (Union): The payload associated with the command, which varies depending
            on the command value:
                0x01: PutBytesInit    - Initializes a new transfer.
                0x02: PutBytesPut     - Sends a chunk of data.
                0x03: PutBytesCommit  - Commits the transfer.
                0x04: PutBytesAbort   - Aborts the transfer.
                0x05: PutBytesInstall - Installs the transferred data.

    Meta:
        endpoint (int): The protocol endpoint for PutBytes (0xBEEF).
        register (bool): Indicates whether the packet should be registered (False).
    """

    class Meta:
        """
        Meta class containing protocol configuration for transfers.

        Attributes:
            endpoint (int): The protocol endpoint identifier.
            register (bool): Indicates whether the protocol should be registered.
        """

        endpoint = 0xBEEF
        register = False

    command = Uint8()
    data = Union(
        command,
        {
            0x01: PutBytesInit,
            0x02: PutBytesPut,
            0x03: PutBytesCommit,
            0x04: PutBytesAbort,
            0x05: PutBytesInstall,
        },
    )


# This is something of a hack: there are two different and fundamentally incompatible init packers,
# which can only be distinguished by the 33rd bit. We rely on the user to know what they're doing.
class PutBytesApp(PebblePacket):
    """
    Represents a Pebble packet for the PutBytes application protocol.

    This class encapsulates the structure and behavior for sending and receiving
    PutBytes commands to the Pebble device, supporting various operations such as
    initialization, data transfer, commit, abort, and install.

    Attributes:
        command (Uint8): The command identifier for the PutBytes operation.
        data (Union): The payload associated with the command, which varies depending
            on the command value:
                0x01: PutBytesAppInit
                0x02: PutBytesPut
                0x03: PutBytesCommit
                0x04: PutBytesAbort
                0x05: PutBytesInstall

    Meta:
        endpoint (int): The protocol endpoint for PutBytesApp (0xBEEF).
        register (bool): Indicates whether the endpoint should be registered (False).
    """

    class Meta:
        """
        Meta class containing protocol configuration for transfers.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0xBEEF).
            register (bool): Indicates whether the endpoint should be registered (False).
        """

        endpoint = 0xBEEF
        register = False

    command = Uint8()
    data = Union(
        command,
        {
            0x01: PutBytesAppInit,
            0x02: PutBytesPut,
            0x03: PutBytesCommit,
            0x04: PutBytesAbort,
            0x05: PutBytesInstall,
        },
    )


class PutBytesResponse(PebblePacket):
    """
    Represents the response packet for a 'PutBytes' operation in the Pebble protocol.

    Attributes:
        result (PutBytesResponse.Result): The result of the operation, either ACK (0x01) or
            NACK (0x02).
        cookie (int): A 32-bit identifier used to correlate the response with the original request.

    Meta:
        endpoint (int): The protocol endpoint for this packet (0xBEEF).

    Enums:
        Result (IntEnum): Enumeration for possible response results:
            - ACK (0x01): Operation acknowledged.
            - NACK (0x02): Operation not acknowledged.
    """

    class Meta:
        """
        Meta class representing protocol metadata for transfers.

        Attributes:
            endpoint (int): The protocol endpoint identifier, set to 0xBEEF.
        """

        endpoint = 0xBEEF

    class Result(IntEnum):
        """
        Enumeration representing possible results of a transfer operation.

        Attributes:
            ACK (int): Indicates a successful acknowledgment (value: 0x01).
            NACK (int): Indicates a negative acknowledgment or failure (value: 0x02).
        """

        ACK = 0x01
        NACK = 0x02

    result = Uint8(enum=Result)
    cookie = Uint32()


class GetBytesCoredumpRequest(PebblePacket):
    """Requests a coredump."""


class GetBytesInfoResponse(PebblePacket):
    """
    Represents a response packet for a request to get information about a byte transfer.

    Attributes:
        error_code (ErrorCode): The status of the request, indicating success or the type of
            error encountered.
        num_bytes (int): The number of bytes associated with the transfer.

    Inner Classes:
        ErrorCode (IntEnum): Enumeration of possible error codes:
            - Success (0x0): The request was successful.
            - MalformedRequest (0x1): The request was malformed.
            - InProgress (0x2): The transfer is still in progress.
            - DoesNotExist (0x3): The requested data does not exist.
            - Corrupted (0x4): The data is corrupted.
    """

    class ErrorCode(IntEnum):
        """
        Enumeration of error codes for transfer protocol operations.

        Attributes:
            Success (int): Operation completed successfully.
            MalformedRequest (int): The request was malformed or invalid.
            InProgress (int): The operation is currently in progress.
            DoesNotExist (int): The requested resource does not exist.
            Corrupted (int): The resource is corrupted or unusable.
        """

        Success = 0x0
        MalformedRequest = 0x1
        InProgress = 0x2
        DoesNotExist = 0x3
        Corrupted = 0x4

    error_code = Uint8(enum=ErrorCode)
    num_bytes = Uint32()


class GetBytesDataResponse(PebblePacket):
    """
    Represents a response packet containing a chunk of binary data from a transfer operation.

    Attributes:
        offset (Uint32): The offset in the data stream where this chunk of data begins.
        data (BinaryArray): The binary data payload received in this response.
    """

    offset = Uint32()
    data = BinaryArray()


class GetBytesFileRequest(PebblePacket):
    """
    Represents a request packet to retrieve the contents of a file as bytes from a Pebble device.
    This only works on non-release firmwares.

    Attributes:
        filename (PascalString): The name of the file to retrieve, encoded as a Pascal string
            with a null terminator (not counted in the length).
    """

    filename = PascalString(null_terminated=True, count_null_terminator=False)


class GetBytesFlashRequest(PebblePacket):
    """
    Represents a request packet to retrieve a region of flash memory from a Pebble device.
    This only works on non-release firmwares.

    Attributes:
        offset (Uint32): The offset in the flash memory where the read operation should begin.
        length (Uint32): The length of the data to read from flash memory.
    """

    offset = Uint32()
    length = Uint32()


class GetBytesUnreadCoredumpRequest(PebblePacket):
    """Requests a coredump, but errors if it has already been read."""


class GetBytes(PebblePacket):
    """
    Represents a Pebble protocol packet for transferring bytes using various commands.

    Attributes:
        command (Uint8): The command identifier for the transfer operation.
        transaction_id (Uint8): The transaction ID for correlating requests and responses.
        message (Union): The message payload, which varies depending on the command value:
            - 0x00: GetBytesCoredumpRequest
            - 0x01: GetBytesInfoResponse
            - 0x02: GetBytesDataResponse
            - 0x03: GetBytesFileRequest
            - 0x04: GetBytesFlashRequest
            - 0x05: GetBytesUnreadCoredumpRequest

    Meta:
        endpoint (int): The protocol endpoint for GetBytes packets (value: 9000).
    """

    class Meta:
        """
        Meta class containing protocol-specific metadata.

        Attributes:
            endpoint (int): The endpoint identifier for the protocol, set to 9000.
        """

        endpoint = 9000

    command = Uint8()
    transaction_id = Uint8()
    message = Union(
        command,
        {
            0x00: GetBytesCoredumpRequest,
            0x01: GetBytesInfoResponse,
            0x02: GetBytesDataResponse,
            0x03: GetBytesFileRequest,
            0x04: GetBytesFlashRequest,
            0x05: GetBytesUnreadCoredumpRequest,
        },
    )
