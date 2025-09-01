__author__ = "katharine"

import errno
import socket
import struct
import sys
import time

import serial

from libpebble2.exceptions import ConnectionError, PacketDecodeError
from libpebble2.protocol.base import PebblePacket

from . import BaseTransport, MessageTarget, MessageTargetWatch


def connect_rfcomm(
    mac: str,
    channel: int | None = None,
    timeout: float = 3.0,
    probe: range = range(1, 31),
    pause: float = 0.05,
):
    """Return (sock, channel). Raises the last OSError if all attempts fail."""

    def attempt(ch) -> socket.socket:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(timeout)
        try:
            s.connect((mac, ch))
            return s
        except OSError:
            s.close()  # critical: free resources on failure
            raise

    if channel is not None:
        return attempt(channel), channel

    last = None
    for ch in probe:
        try:
            return attempt(ch), ch
        except OSError as e:
            last = e
            time.sleep(pause)  # give the stack a breather
    raise last or OSError("No RFCOMM channel accepted")


class RFCOMMSerialAdapter:
    """
    Minimal pyserial-like wrapper around a Bluetooth RFCOMM socket.

    Implements: is_open, read(n), write(b), close()
    """

    def __init__(self, sock: socket.socket, timeout: float = 1.0) -> None:
        self._sock = sock
        self._timeout = timeout
        self._sock.settimeout(timeout)
        self._open = True

    @property
    def is_open(self) -> bool:
        """
        Check if the serial transport connection is currently open.

        Returns:
            bool: True if the connection is open, False otherwise.
        """
        return self._open

    def close(self) -> None:
        """
        Closes the serial transport connection if it is currently open.

        This method attempts to close the underlying socket and updates the internal
        state to reflect that the connection is no longer open.

        Exceptions during socket closure are suppressed to ensure the open state is
        always updated.
        """
        if self._open:
            try:
                self._sock.close()
            finally:
                self._open = False

    def write(self, data: bytes | bytearray | memoryview) -> int:
        """
        Writes the given data to the socket.

        Attempts to send the entire buffer using `sendall`, similar to serial write behavior.
        Raises an OSError if the socket is closed.

        Args:
            data (bytes | bytearray | memoryview): The data to be written to the socket.

        Returns:
            int: The number of bytes written.

        Raises:
            OSError: If the socket is closed.
        """
        if not self._open:
            msg = "Socket closed"
            raise OSError(msg)
        # sendall to behave like serial.write (attempts full buffer)
        buf = bytes(data)
        self._sock.sendall(buf)
        return len(buf)

    def read(self, n: int = 1) -> bytes:
        """
        Reads up to `n` bytes from the socket.

        Attempts to read up to `n` bytes from the underlying RFCOMM socket, respecting the timeout.
        Returns the bytes read, which may be fewer than requested if the connection is closed or times out.

        Args:
            n (int): The maximum number of bytes to read. Defaults to 1.

        Returns:
            bytes: The bytes read from the socket.

        Raises:
            OSError: If the socket is closed.
        """
        if not self._open:
            msg = "Socket closed"
            raise OSError(msg)

        out = bytearray()
        while len(out) < n:
            try:
                chunk = self._sock.recv(n - len(out))
                if not chunk:
                    # remote closed gracefully
                    break
                out += chunk
                # If timeout is zero (nonblocking), return whatever we got
                if self._timeout == 0:
                    break
            except socket.timeout:
                # If we already have some data, return it; else it's a timeout
                break
        return bytes(out)


class SerialTransport(BaseTransport):
    """
    Transport class for communicating with a Pebble device over a serial connection.

    Supports both OS-exposed serial devices (e.g., TTY/COM ports) and RFCOMM Bluetooth connections.
    Handles connection management, packet framing, and error handling for serial communication.

    Args:
        device (str | None): Path to the serial device (e.g., '/dev/ttyUSB0' or 'COM3').
        mac (str | None): Bluetooth MAC address for RFCOMM connections.
        channel (int): RFCOMM channel to use (default: 1).
        timeout (float): Timeout for connection operations in seconds (default: 1.0).

    Attributes:
        must_initialise (bool): Indicates if initialisation is required.
        device (str | None): Serial device path.
        mac (str | None): Bluetooth MAC address.
        channel (int | None): RFCOMM channel.
        timeout (float): Connection timeout.
        connection (serial.Serial | RFCOMMSerialAdapter | None): Active connection object.

    Methods:
        connect():
            Establishes a connection to the Pebble device via serial or RFCOMM.

        connected (property):
            Returns True if the transport is currently connected.

        read_packet():
            Reads a framed message packet from the Pebble device.

        send_packet(message, target=None):
            Sends a framed message packet to the Pebble device.

        disconnect():
            Closes the connection to the Pebble device.
    """

    must_initialise = True

    def __init__(
        self,
        device: str | None = None,
        *,
        mac: str | None = None,
        channel: int | None = None,
        timeout: float = 3.0,
    ) -> None:
        if not device and not mac:
            msg = "Provide either 'device' (TTY/COM) or 'mac' (RFCOMM)."
            raise ValueError(msg)
        self.device = device
        self.mac = mac
        self.channel = channel
        self.timeout = timeout

        # connection can be a pyserial Serial or our RFCOMMSerialAdapter
        self.connection: serial.Serial | RFCOMMSerialAdapter | None = None

    def connect(self) -> None:
        """Connect to the Pebble via the given device file."""
        try:
            if self.mac and sys.platform == "darwin":
                msg = (
                    "RFCOMM sockets are not available on macOS. Use 'device=' (/dev/cu.*) "
                    "with pyserial instead."
                )
                raise ConnectionError(msg)


            if self.device:
                # Original behavior: OS-exposed serial device
                self.connection = serial.Serial(self.device, 115200)
            elif self.mac:
                # Pure-Python RFCOMM socket path
                sock, ch = connect_rfcomm(self.mac, channel=self.channel, timeout=self.timeout)
                self.channel = ch  # remember discovered channel
                self.connection = RFCOMMSerialAdapter(sock, timeout=self.timeout)
            else:
                msg = "No device or MAC address specified."
                raise RuntimeError(msg)
        except (serial.SerialException, OSError) as e:
            # Keep existing error shape
            if getattr(e, "errno", None) == errno.EBUSY:
                msg = "Could not connect to Pebble."
                raise ConnectionError(msg)
            raise

    @property
    def connected(self) -> bool:
        """Whether the transport is currently connected."""
        return bool(self.connection and self.connection.is_open)

    def _ensure_connected(self) -> serial.Serial | RFCOMMSerialAdapter:
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
