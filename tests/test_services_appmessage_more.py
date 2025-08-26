from libpebble2.protocol.appmessage import (
    AppMessage,
    AppMessageACK,
    AppMessageNACK,
    AppMessagePush,
)
from libpebble2.services.appmessage import AppMessageService, ByteArray, CString, Int16, Uint8


def test_send_appmessage_builds_tuples_and_tracks_txid(fake_pebble, any_uuid):
    svc = AppMessageService(fake_pebble)
    tid = svc.send_message(
        any_uuid,
        {
            1: Uint8(7),
            2: Int16(-2),
            3: ByteArray(b"\x01\x02"),
            4: CString("hi"),
        },
    )
    assert tid in (1, 2, 3, 4, 5, 6, 7, 8)  # monotonic but we only sent 1
    # The last sent is the AppMessage envelope
    sent = fake_pebble.sent_packets[-1]
    assert isinstance(sent, AppMessage)
    assert isinstance(sent.data, AppMessagePush)
    keys = {t.key for t in sent.data.dictionary}
    assert keys == {1, 2, 3, 4}


def test_ack_and_nack_events_are_broadcast(fake_pebble, any_uuid):
    calls = {"ack": [], "nack": []}
    svc = AppMessageService(fake_pebble)

    # Simulate an outbound message stored as pending
    txid = svc.send_message(any_uuid, {1: Uint8(1)})

    def on_ack(t, u):
        calls["ack"].append((t, u))

    def on_nack(t, u):
        calls["nack"].append((t, u))

    svc.register_handler("ack", on_ack)
    svc.register_handler("nack", on_nack)

    # Craft ACK then NACK frames back into the endpoint handler
    fake_pebble.fire(AppMessage(transaction_id=txid, data=AppMessageACK()))
    fake_pebble.fire(AppMessage(transaction_id=txid + 1, data=AppMessageNACK()))
    assert calls["ack"] == [(txid, any_uuid)]
    # txid+1 wasn't pending -> uuid in callback is None
    assert calls["nack"] == [(txid + 1, None)]
