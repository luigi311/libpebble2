__author__ = "katharine"

import socket

from libpebble2.communication.transports import BaseTransport, MessageTarget, MessageTargetWatch
from libpebble2.exceptions import ConnectionError, PacketDecodeError
from libpebble2.protocol.base import PebblePacket

from .protocol import (
    FOOTER_SIGNATURE,
    HEADER_SIGNATURE,
    QemuInboundPacket,
    QemuPacket,
    QemuRawPacket,
    QemuSPP,
)


class MessageTargetQemu(MessageTarget):
    """
    MessageTargetQemu is a subclass of MessageTarget used for communication with QEMU-based targets.

    Args:
        protocol (int | None, optional): The protocol identifier to use for communication.
            Defaults to None.
        raw (bool, optional): If True, enables raw message mode. Defaults to False.

    Attributes:
        protocol (int | None): Stores the protocol identifier.
        raw (bool): Indicates whether raw message mode is enabled.
    """
    def __init__(self, protocol: int | None = None, *, raw: bool = False) -> None:
        self.protocol = protocol
        self.raw = raw


class QemuTransport(BaseTransport):
    """
    QemuTransport provides a transport layer for communicating with a QEMU instance over TCP
    sockets.

    This class implements the BaseTransport interface, enabling packet-based communication with
    QEMU or a Pebble watch emulator. It manages socket connections, packet assembly/disassembly,
    and message routing between the host and QEMU.

    Attributes:
        BUFFER_SIZE (int): Number of bytes read from the socket at a time.
        must_initialise (bool): Indicates if the transport must be initialised before use.

    Args:
        host (str): The hostname or IP address of the QEMU instance. Defaults to "127.0.0.1".
        port (int): The TCP port of the QEMU instance. Defaults to 12344.

    Methods:
        connect():
            Establishes a TCP connection to the QEMU instance.

        connected (property):
            Returns True if the transport is currently connected.

        read_packet():
            Reads and parses a packet from the QEMU instance or watch, returning the message
            target and payload.

        send_packet(message, target=None):
            Sends a packet to the QEMU instance, routing to either the watch or QEMU protocol
            as appropriate.

        disconnect():
            Closes the socket and disconnects from the QEMU instance.

    Raises:
        ConnectionError: If a socket operation fails or the transport is not connected.
        PacketDecodeError: If a received packet cannot be decoded or has invalid signatures.
        TypeError: If an unsupported message type or target is provided.
        ValueError: If required protocol information is missing for raw QEMU messages.
    """

    #: Number of bytes read from the socket at a time.
    BUFFER_SIZE = 2048
    must_initialise = True

    def __init__(self, host: str = "127.0.0.1", port: int = 12344) -> None:
        self.host = host
        self.port = port
        self.socket = None
        self.assembled_data = b""
        self._connected = False

    def connect(self) -> None:
        """Connect to the QEMU instance."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((self.host, self.port))
            self.socket = s
            self._connected = True
        except OSError as e:
            raise ConnectionError(str(e))

    @property
    def connected(self) -> bool:
        """Whether the transport is currently connected."""
        return self.socket is not None and self._connected

    def _ensure_connected(self) -> socket.socket:
        if not self.connected or self.socket is None:
            msg = "Not connected."
            raise ConnectionError(msg)
        return self.socket

    def read_packet(self) -> tuple[MessageTarget, bytes | PebblePacket]:
        """Read a message from the watch or QEMU."""
        sock = self._ensure_connected()
        while True:
            if self.assembled_data:
                try:
                    packet, length = QemuInboundPacket.parse(self.assembled_data)
                except PacketDecodeError:
                    # Need more bytes; fall through to recv
                    pass
                else:
                    self.assembled_data = self.assembled_data[length:]
                    if packet.signature == HEADER_SIGNATURE and packet.footer == FOOTER_SIGNATURE:
                        if isinstance(packet.data, QemuSPP):
                            return MessageTargetWatch(), packet.data.payload
                        return MessageTargetQemu(packet.protocol), packet.data
                    msg = (
                        f"QemuTransport: signature mismatch "
                        f"(header {packet.signature:#x} != {HEADER_SIGNATURE:#x}, "
                        f"footer {packet.footer:#x} != {FOOTER_SIGNATURE:#x})"
                    )
                    raise PacketDecodeError(
                        msg,
                    )
            try:
                received = sock.recv(self.BUFFER_SIZE)
                if not received:
                    self._connected = False
                    msg = "Disconnected."
                    raise ConnectionError(msg)
                self.assembled_data += received
            except OSError as e:
                self._connected = False
                raise ConnectionError(str(e))

    def _send_all(self, sock: socket.socket, data: bytes) -> None:
        # Use sendall when available (real sockets). For test stubs with only `send`,
        # do a single best-effort send to avoid tight loops that can spin the CPU.
        sendall = getattr(sock, "sendall", None)
        if callable(sendall):
            sendall(data)
            return

        # Test stub path
        try:
            sent = sock.send(data)
        except OSError as e:
            self._connected = False
            raise ConnectionError(str(e)) from e

        # If a stub returns 0 bytes, treat as disconnect to avoid busy-spin.
        if sent == 0:
            self._connected = False
            msg = "Disconnected."
            raise ConnectionError(msg)

    def send_packet(
        self,
        message: bytes | bytearray | memoryview | PebblePacket,
        target: MessageTarget | None = None,
    ) -> None:
        """Send a packet to the QEMU instance."""
        sock = self._ensure_connected()
        try:
            if target is None:
                target = MessageTargetWatch()

            if isinstance(target, MessageTargetWatch):
                # Accept bytes-like and chunk as SPP frames
                if not isinstance(message, (bytes, bytearray, memoryview)):
                    msg = "SPP payload must be bytes-like for QEMU watch target."
                    raise TypeError(msg)
                payload = bytes(message)
                start_idx = 0
                bytes_left = len(payload)
                while bytes_left:
                    bytes_to_send = min(bytes_left, self.BUFFER_SIZE)
                    chunk = payload[start_idx : start_idx + bytes_to_send]
                    self._send_all(sock, QemuPacket(data=QemuSPP(payload=chunk)).serialise())
                    bytes_left -= bytes_to_send
                    start_idx += bytes_to_send

            elif isinstance(target, MessageTargetQemu):
                if target.raw:
                    if target.protocol is None:
                        msg = "MessageTargetQemu.raw=True requires a non-None protocol."
                        raise ValueError(msg)

                   # Ensure the payload is bytes for the raw wrapper.
                    if isinstance(message, PebblePacket):
                        payload_bytes = message.serialise()
                    else:
                        payload_bytes = bytes(message)

                    self._send_all(
                        sock,
                        QemuRawPacket(protocol=target.protocol, data=payload_bytes).serialise(),
                    )
                else:
                    self._send_all(sock, QemuPacket(data=message).serialise())

            else:
                msg = f"Unsupported message target: {type(target).__name__}"
                raise TypeError(msg)

        except OSError as e:
            self._connected = False
            raise ConnectionError(str(e))

    def disconnect(self) -> None:
        """Disconnect from the QEMU instance."""
        if self.socket is not None:
            try:
                self.socket.close()
            finally:
                self.socket = None
                self._connected = False
