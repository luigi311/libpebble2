from uuid import UUID
from unittest.mock import Mock

from libpebble2.services.appmessage import AppMessageService
from libpebble2.protocol.appmessage import (
    AppMessage,
    AppMessagePush,
    AppMessageACK,
    AppMessageTuple,
)


def test_receive_appmessage_string():
    pebble = Mock()

    calls = 0

    def handle_result(txid, app_uuid, result):
        nonlocal calls
        assert app_uuid == UUID(int=128)
        assert txid == 42
        assert result == {
            14: "hello!",
            15: "éclair",  # null-terminated -> trailing 'foo' is ignored
            16: "hello\ufffdworld",  # invalid UTF-8 -> U+FFFD replacement char
        }
        calls += 1

    service = AppMessageService(pebble)
    service.register_handler("appmessage", handle_result)

    # Verify the service registered an endpoint and grab its callback
    pebble.register_endpoint.assert_called()
    callback = pebble.register_endpoint.call_args.args[1]

    # Simulate an incoming AppMessage
    callback(
        AppMessage(
            transaction_id=42,
            data=AppMessagePush(
                uuid=UUID(int=128),
                dictionary=[
                    AppMessageTuple(
                        key=14, type=AppMessageTuple.Type.CString, data=b"hello!\x00"
                    ),
                    AppMessageTuple(
                        key=15,
                        type=AppMessageTuple.Type.CString,
                        data="éclair".encode("utf-8") + b"\x00foo",
                    ),
                    AppMessageTuple(
                        key=16,
                        type=AppMessageTuple.Type.CString,
                        data=b"hello\xffworld",
                    ),
                ],
            ),
        )
    )

    pebble.send_packet.assert_called_once_with(
        AppMessage(transaction_id=42, data=AppMessageACK())
    )
    assert calls == 1
