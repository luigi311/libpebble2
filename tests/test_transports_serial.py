def test_serial_transport_connect_and_io(monkeypatch, patch_serial):
    from libpebble2.communication.transports.serial import SerialTransport, MessageTargetWatch

    st = SerialTransport("/dev/ttyFAKE")
    st.connect()
    assert st.connected

    # Push a framed message into the fake serial buffer: length(=2) + endpoint(=1) + payload(2 bytes)
    payload = b"\x00\x02\x00\x01" + b"\xaa\xbb"
    st.connection._buf.extend(payload)
    origin, data = st.read_packet()
    assert isinstance(origin, MessageTargetWatch)
    # Should return the whole frame starting at length
    assert data == payload[0 : 2 + 2 + 2]

    st.send_packet(b"\x12\x34")
    assert st.connection._written == b"\x12\x34"

    st.disconnect()
    assert not st.connected
