__author__ = "katharine"

import errno
import struct

import serial

from libpebble2.exceptions import ConnectionError, PacketDecodeError
from libpebble2.protocol.base import PebblePacket

from . import BaseTransport, MessageTarget, MessageTargetWatch


class SerialTransport(BaseTransport):
    """
    Represents a direct connection to a physical Pebble paired to the computer via Bluetooth serial.
    This transport expects to be given a device file over which it can communicate with the watch
    via Bluetooth.

    .. warning::
        Using this transport may cause occasional kernel panics on some versions of OS X.

    :param device: The path to the device file (on OS X, often of the form
                   ``/dev/cu.PebbleTimeXXXX-SerialPo`` or
                   ``/dev/cu.PebbleXXXX-SerialPortSe``).
    :type device: str
    """

    must_initialise = True

    def __init__(self, device: str) -> None:
        self.device = device
        self.connection: serial.Serial | None = None

    def connect(self) -> None:
        """Connect to the Pebble via the given device file."""
        try:
            self.connection = serial.Serial(self.device, 115200)
        except (serial.SerialException, OSError) as e:
            if getattr(e, "errno", None) == errno.EBUSY:
                msg = "Could not connect to Pebble."
                raise ConnectionError(msg)
            raise

    @property
    def connected(self) -> bool:
        """Whether the transport is currently connected."""
        return bool(self.connection and self.connection.is_open)

    def _ensure_connected(self) -> serial.Serial:
        if not self.connected or self.connection is None:
            msg = "Not connected."
            raise ConnectionError(msg)
        return self.connection

    def read_packet(self) -> tuple[MessageTarget, bytes | PebblePacket]:
        """Read a framed message from the watch."""
        self.connection = self._ensure_connected()

        try:
            header = self.connection.read(2)
        except (serial.SerialException, OSError):
            if self.connection:
                self.connection.close()
            self.connection = None
            msg = "Disconnected from watch."
            raise ConnectionError(msg)
        if len(header) < 2:
            msg = "Got malformed packet."
            raise PacketDecodeError(msg)

        (length,) = struct.unpack("!H", header)
        try:
            rest = self.connection.read(length + 2)  # endpoint(2) + payload(length)
        except (serial.SerialException, OSError):
            self.connection.close()
            self.connection = None
            msg = "Disconnected from watch."
            raise ConnectionError(msg)
        if len(rest) < length + 2:
            msg = "Got incomplete packet."
            raise ConnectionError(msg)
        return MessageTargetWatch(), header + rest

    def send_packet(
        self,
        message: PebblePacket | bytes | bytearray | memoryview,
        target: MessageTarget | MessageTargetWatch | None = None,
    ) -> None:
        """Send a framed message to the watch."""
        ser = self._ensure_connected()

        if target is not None and not isinstance(target, MessageTargetWatch):
            msg = f"Unsupported message target: {type(target).__name__}"
            raise TypeError(msg)

        # Accept both framed bytes and PebblePacket
        if isinstance(message, PebblePacket):
            payload = message.serialise_packet()  # Frame for serial transport
        else:
            payload = bytes(message)

        try:
            ser.write(payload)
        except (serial.SerialException, OSError):
            try:
                ser.close()
            finally:
                self.connection = None
            msg = "Disconnected from watch."
            raise ConnectionError(msg)

    def disconnect(self) -> None:
        """Disconnect from the watch."""
        if self.connection is not None:
            try:
                self.connection.close()
            finally:
                self.connection = None
