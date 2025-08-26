from libpebble2.protocol.transfers import GetBytes, GetBytesDataResponse, GetBytesInfoResponse
from libpebble2.services.getbytes import GetBytesService


def wrap(msg):  # convenience to wrap into outer envelope type expected by queue
    return GetBytes(message=msg, transaction_id=1, command=0)


def test_getbytes_happy_path(fake_pebble):
    svc = GetBytesService(fake_pebble)

    # Two chunks totalling 6 bytes
    info = GetBytesInfoResponse(error_code=GetBytesInfoResponse.ErrorCode.Success, num_bytes=6)
    data1 = GetBytesDataResponse(offset=0, data=b"abc")
    data2 = GetBytesDataResponse(offset=3, data=b"def")
    fake_pebble.queue_for(GetBytes, [wrap(info), wrap(data1), wrap(data2)])

    out = svc._get(
        data1
    )  # method under test; accepts any "message", outer wrapper built by GetBytesService
    assert out == b"abcdef"
