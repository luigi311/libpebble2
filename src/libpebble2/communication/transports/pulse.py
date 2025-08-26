__author__ = "Liam McLoughlin"

import struct
import time

try:
    from pebble import pulse2  # type: ignore[import]
except ImportError:
    pulse2 = None

import contextlib

from libpebble2.exceptions import ConnectionError

from . import BaseTransport, MessageTarget, MessageTargetWatch


class PULSETransport(BaseTransport):
    """
    Represents a direct connection to a physical/virtual Pebble uses the PULSEv2 interface.
    This transport expects to be given a PULSE2 Link object.

    :param connection: A PULSE2 Link object to tunnel Pebble Protocol over.
    :type link: pulse2.link.Link
    """

    must_initialise = True

    PPOPULSE_PORT = 0x3E22

    OPCODE_PROTOCOL_DATA = 0x1
    OPCODE_PROTOCOL_OPEN = 0x2
    OPCODE_PROTOCOL_CLOSE = 0x3

    def __init__(self, link) -> None:
        if pulse2 is None:
            msg = "pebble.pulse2 is required for PULSETransport"
            raise ImportError(msg) from None

        self.link = link
        self.connection = None
        self.buffer = b""

    @staticmethod
    def _chunks(list_items: bytes, chunk_length: int):
        """Yield successive n-sized chunks from list_items."""
        for i in range(0, len(list_items), chunk_length):
            yield list_items[i : i + chunk_length]

    def connect(self) -> None:
        """
        Establishes a reliable socket connection using the PPoPULSE protocol.

        Opens a socket on the specified PPoPULSE port and sends a protocol open opcode.
        Waits for an acknowledgment (ACK) of the protocol open opcode within 10 seconds.

        Raises:
            ConnectionError: If the socket cannot be opened or if the ACK is not received within
                the timeout period.
        """
        self.connection = self.link.open_socket("reliable", self.PPOPULSE_PORT)
        if not self.connection:
            msg = "Failed to open PPoPULSE socket"
            raise ConnectionError(msg)

        self._send_with_opcode(self.OPCODE_PROTOCOL_OPEN)
        start_time = time.time()
        while time.time() < start_time + 10.0:
            opcode, _ = self._recv_with_opcode()
            if opcode == self.OPCODE_PROTOCOL_OPEN:
                break
        else:
            msg = "Timeout waiting for PPoPULSE open ACK"
            raise ConnectionError(msg)

    def disconnect(self) -> None:
        """
        Disconnects the current connection if it is active.

        If connected, attempts to send a protocol close opcode to the remote endpoint,
        suppressing any SocketClosed exceptions that may occur during this process.
        Then closes the connection and sets the connection attribute to None.
        """
        if pulse2 is None:
            return

        if self.connection is not None:
            with contextlib.suppress(pulse2.exceptions.SocketClosed):
                self._send_with_opcode(self.OPCODE_PROTOCOL_CLOSE)
            self.connection.close()
            self.connection = None

    @property
    def connected(self) -> bool:
        """
        Checks if there is an active connection.

        Returns:
            bool: True if a connection exists, False otherwise.
        """
        return self.connection is not None

    def read_packet(self):
        while self.connected:
            if len(self.buffer) >= 2:
                (length,) = struct.unpack("!H", self.buffer[:2])
                length += 4

                if len(self.buffer) >= length:
                    msg_data = self.buffer[:length]
                    self.buffer = self.buffer[length:]

                    return MessageTargetWatch(), msg_data

            opcode, data = self._recv_with_opcode()
            if opcode == self.OPCODE_PROTOCOL_DATA:
                self.buffer += data

        msg = "PULSETransport is not connected"
        raise ConnectionError(msg)

    def send_packet(self, message, target=None) -> None:
        if target is None:
            target = MessageTargetWatch()

        if not isinstance(target, MessageTargetWatch):
            msg = "PULSETransport can only send to MessageTargetWatch targets"
            raise TypeError(msg)

        if not self.connected or self.connection is None:
            msg = "PULSETransport is not connected"
            raise ConnectionError(msg)

        if not isinstance(message, bytes):
            msg = "PULSETransport can only send byte messages"
            raise TypeError(msg)

        for chunk in self._chunks(message, self.connection.mtu - 1):
            self._send_with_opcode(self.OPCODE_PROTOCOL_DATA, chunk)

    def _recv_with_opcode(self):
        if pulse2 is None:
            msg = "PULSE transport not available"
            raise ConnectionError(msg)

        try:
            if self.connection is None:
                msg = "PULSE transport closed"
                raise ConnectionError(msg)
            packet = self.connection.receive(block=True)
        except (AttributeError, pulse2.exceptions.SocketClosed):
            self.connection = None
            msg = "PULSE transport closed"
            raise ConnectionError(msg)

        if not packet:
            self.connection = None
            msg = "PULSE transport closed"
            raise ConnectionError(msg)

        opcode = packet[0] if isinstance(packet[0], int) else ord(packet[0])
        data = packet[1:]
        return opcode, data

    def _send_with_opcode(self, opcode, body=None):
        if not self.connected or self.connection is None:
            msg = "PULSETransport is not connected"
            raise ConnectionError(msg)

        data = bytes([opcode]) + (body or b"")
        self.connection.send(data)
