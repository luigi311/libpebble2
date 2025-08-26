__author__ = "katharine"

import struct

import websocket

from libpebble2.communication.transports import BaseTransport, MessageTarget, MessageTargetWatch
from libpebble2.exceptions import ConnectionError, PebbleError
from libpebble2.protocol.base import PebblePacket

from .protocol import (
    WebSocketRelayFromWatch,
    WebSocketRelayToWatch,
    endpoints,
    from_watch,
)


class MessageTargetPhone(MessageTarget):
    """
    Indicates that the message is directed at a connected phone running the Pebble mobile app.
    For this purpose, `pypkjs <https://github.com/pebble/pypkjs>`_ counts as a phone.
    """


class WebsocketTransport(BaseTransport):
    """
    Represents a connection via WebSocket to a phone running the Pebble mobile app,
    which is in turn connected to a Pebble over Bluetooth.

    :param url: The WebSocket URL to connect to, in standard format (e.g. ``ws://localhost:9000/``)
    """

    must_initialise = False

    def __init__(self, url: str) -> None:
        self.url: str = url
        self.ws: websocket.WebSocket | None = None

    def connect(self) -> None:
        """Connect to the WebSocket server."""
        try:
            self.ws = websocket.create_connection(self.url)
        except (OSError, websocket.WebSocketException) as e:
            raise ConnectionError(str(e))

    @property
    def connected(self) -> bool:
        """Whether the transport is currently connected."""
        return self.ws is not None and self.ws.connected

    def send_packet(
        self,
        message: PebblePacket | bytes | bytearray | memoryview,
        target: MessageTarget | None = None,
    ) -> None:
        """Send a message to the watch or to the phone."""
        if not self.connected or self.ws is None:
            msg = "Not connected"
            raise ConnectionError(msg)

        # Default to watch
        if target is None or isinstance(target, MessageTargetWatch):
            # Accept PebblePacket or raw framed bytes
            if isinstance(message, PebblePacket):
                payload = message.serialise_packet()  # length + endpoint + payload
            else:
                payload = bytes(message)
            return self._send_to_watch(payload)

        if isinstance(target, MessageTargetPhone):
            if not isinstance(message, PebblePacket):
                msg = "Phone-target messages must be PebblePacket instances"
                raise PebbleError(msg)
            return self._send_to_phone(message)

        msg = f"Unsupported message target: {type(target).__name__}"
        raise PebbleError(msg)

    def _send_to_watch(self, payload: bytes) -> None:
        # Relay raw framed watch bytes via the phone
        self._send_to_phone(WebSocketRelayToWatch(payload=payload))

    def _send_to_phone(self, message: PebblePacket) -> None:
        try:
            try:
                endpoint = endpoints[type(message)]
            except KeyError as e:
                msg = f"Unknown message type: {type(message).__name__}"
                raise PebbleError(msg) from e

            if self.ws is None:
                msg = "Not connected"
                raise ConnectionError(msg)

            frame = struct.pack("!B", endpoint) + message.serialise()
            self.ws.send_binary(frame)

        except websocket.WebSocketException as e:
            raise ConnectionError(str(e)) from e

    def read_packet(self) -> tuple[MessageTarget, bytes | PebblePacket]:
        """Read a message from the watch or from the phone."""
        if not self.connected or self.ws is None:
            msg = "Not connected"
            raise ConnectionError(msg)
        try:
            opcode, payload = self.ws.recv_data()
        except websocket.WebSocketException as e:
            raise ConnectionError(str(e)) from e

        if opcode == websocket.ABNF.OPCODE_BINARY:
            (endpoint,) = struct.unpack_from("!B", payload, 0)
            cls = from_watch.get(endpoint)
            if cls is None:
                msg = f"Unknown endpoint: {endpoint:#02x}"
                raise PebbleError(msg)
            if cls is WebSocketRelayFromWatch:
                return MessageTargetWatch(), payload[1:]
            packet, _ = cls.parse(payload[1:])
            return MessageTargetPhone(), packet

        if opcode == websocket.ABNF.OPCODE_CLOSE:
            msg = "Connection gracefully closed by peer."
            raise ConnectionError(msg)

        msg = f"Got unexpected WebSocket opcode {opcode}"
        raise PebbleError(msg)

    def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if self.ws is not None:
            try:
                self.ws.close()
            finally:
                self.ws = None
