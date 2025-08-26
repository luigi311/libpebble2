from libpebble2.protocol.transfers import PutBytesResponse
from libpebble2.services.putbytes import PutBytes, PutBytesType


def test_putbytes_full_flow(fake_pebble):
    data = b"0123456789"
    # Prepare -> ACK(cookie=123), send chunks -> ACK for each, commit -> ACK, install -> ACK
    fake_pebble.script_send_and_read(
        [
            # _prepare
            (PutBytesResponse, PutBytesResponse(result=PutBytesResponse.Result.ACK, cookie=123)),
            # _send_object - there will be multiple chunks; we accept any number by scripting enough ACKs
            (PutBytesResponse, PutBytesResponse(result=PutBytesResponse.Result.ACK, cookie=123)),
            (PutBytesResponse, PutBytesResponse(result=PutBytesResponse.Result.ACK, cookie=123)),
            # _commit
            (PutBytesResponse, PutBytesResponse(result=PutBytesResponse.Result.ACK, cookie=123)),
            # _install
            (PutBytesResponse, PutBytesResponse(result=PutBytesResponse.Result.ACK, cookie=123)),
        ]
    )

    pb = PutBytes(fake_pebble, PutBytesType.Binary, data)
    progress = []
    pb.register_handler(
        "progress", lambda sent, so_far, total: progress.append((sent, so_far, total))
    )
    pb.send()

    # Sent at least one progress event and final totals match
    assert progress
    assert progress[-1][2] == len(data)
