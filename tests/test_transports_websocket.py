import struct


def test_websocket_transport_send_and_read_watch(patch_websocket):
    from libpebble2.communication.transports.websocket import MessageTargetWatch, WebsocketTransport
    from libpebble2.communication.transports.websocket.protocol import (
        WebSocketRelayFromWatch,
        from_watch,
        to_watch,
    )

    ws = WebsocketTransport("ws://x")
    ws.connect()
    assert ws.connected

    # Reading: fabricate an inbound "from watch" frame (endpoint byte, then payload)
    endpoint = {v: k for k, v in from_watch.items()}[WebSocketRelayFromWatch]
    patch_websocket.instance._in.append(
        (patch_websocket.ABNF.OPCODE_BINARY, struct.pack("B", endpoint) + b"\x01\x02")
    )
    origin, payload = ws.read_packet()
    assert isinstance(origin, MessageTargetWatch)
    assert payload == b"\x01\x02"

    # Sending to watch wraps in phone envelope internally
    ws._send_to_watch(b"\xaa")
    # First, WebsocketTransport will send to phone: endpoint byte + serialised(to_watch[RelayToWatch])
    assert patch_websocket.instance.sent  # one message sent

    ws.disconnect()
    assert not ws.connected
