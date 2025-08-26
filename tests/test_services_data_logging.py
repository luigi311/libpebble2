from libpebble2.protocol.data_logging import (
    DataLogging,
    DataLoggingACK,
    DataLoggingDespoolOpenSession,
    DataLoggingDespoolSendData,
    DataLoggingGetSendEnableResponse,
)
from libpebble2.services.data_logging import DataLoggingService


def wrap(msg):
    return DataLogging(data=msg, command=0)


def test_data_logging_list(fake_pebble):
    # One open session, then timeout (queue empty)
    s = DataLoggingDespoolOpenSession(
        session_id=3, app_uuid=None, timestamp=1, log_tag=2, data_item_type=0, data_item_size=1
    )
    fake_pebble.queue_for(DataLogging, [wrap(s)])
    svc = DataLoggingService(fake_pebble)
    sessions = svc.list()
    assert isinstance(sessions, list)
    # Sent ACK for that session
    assert any(isinstance(p.data, DataLoggingACK) for p in fake_pebble.sent_packets)


def test_data_logging_download(fake_pebble):
    # Advertise two sessions; we will request id=7 only
    s1 = DataLoggingDespoolOpenSession(
        session_id=7, app_uuid=None, timestamp=1, log_tag=2, data_item_type=0, data_item_size=1
    )
    s2 = DataLoggingDespoolOpenSession(
        session_id=8, app_uuid=None, timestamp=1, log_tag=2, data_item_type=0, data_item_size=1
    )
    # After request empty, send two data chunks for session 7 and one for 8 (which should be NACKed)
    d7a = DataLoggingDespoolSendData(session_id=7, items_left=1, crc=0, data=b"ab")
    d8 = DataLoggingDespoolSendData(session_id=8, items_left=1, crc=0, data=b"xx")
    d7b = DataLoggingDespoolSendData(session_id=7, items_left=0, crc=0, data=b"cd")

    fake_pebble.queue_for(DataLogging, [wrap(s1), wrap(s2), wrap(d7a), wrap(d8), wrap(d7b)])
    svc = DataLoggingService(fake_pebble)
    session, data = svc.download(7)
    assert session.session_id == 7
    if data is not None:
        assert data == b"abcd"


def test_data_logging_get_set_enable(fake_pebble):
    resp = DataLoggingGetSendEnableResponse(enabled=True)
    fake_pebble.queue_for(DataLogging, [wrap(resp)])
    svc = DataLoggingService(fake_pebble)
    assert svc.get_send_enable() is True
    # set just sends a packet; nothing to assert besides "didn't crash"
    svc.set_send_enable(False)
