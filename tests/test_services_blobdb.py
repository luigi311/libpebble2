import time

from libpebble2.protocol.blobdb import (
    BlobCommand,
    BlobDatabaseID,
    BlobResponse,
    BlobStatus,
    InsertCommand,
)
from libpebble2.services.blobdb import BlobDBClient


def test_blobdb_insert_success_roundtrip(fake_pebble, any_uuid):
    cb_results = []

    def cb(result):
        cb_results.append(result)

    client = BlobDBClient(fake_pebble, timeout=0.1)
    client.insert(BlobDatabaseID.App, any_uuid, b"payload", callback=cb)

    # The send thread will have queued one BlobCommand; grab token from it
    deadline = time.time() + 1.0
    cmd = None
    while time.time() < deadline:
        for pkt in fake_pebble.sent_packets:
            if isinstance(pkt, BlobCommand):
                cmd = pkt
        if cmd:
            break
        time.sleep(0.01)
    assert isinstance(cmd.content, InsertCommand)
    token = cmd.token

    # Simulate success response
    fake_pebble.fire(BlobResponse(token=token, response=BlobStatus.Success))
    # Let callback thread run
    deadline = time.time() + 1.0
    while time.time() < deadline and not cb_results:
        time.sleep(0.01)
    assert cb_results == [BlobStatus.Success]
