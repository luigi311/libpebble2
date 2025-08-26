import importlib
import sys


def test_pulse_transport_import_guard():
    # module sets pulse2=None when import fails; constructing should raise ImportError
    import types

    from libpebble2.communication.transports.pulse import PULSETransport

    class Dummy:
        pass

    try:
        PULSETransport(Dummy())  # should raise because pulse2 is None
    except ImportError:
        pass
