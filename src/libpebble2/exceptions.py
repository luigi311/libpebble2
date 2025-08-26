__author__ = "katharine"


class PebbleError(Exception):
    """The base class for all exceptions raised by libpebble2."""


class AppInstallError(PebbleError):
    """An app install failed."""


class PutBytesError(PebbleError):
    """A putbytes session failed."""


class GetBytesError(PebbleError):
    """A getbytes session failed."""

    def __init__(self, code: int) -> None:
        self.code = code
        PebbleError.__init__(self, f"Failed to get bytes: {code!s}")


class ScreenshotError(PebbleError):
    """A screenshot failed."""



class TimeoutError(PebbleError):
    """Something was waiting for an event and timed out."""



class PacketDecodeError(PebbleError):
    """Decoding a packet received from the Pebble failed."""


class PacketEncodeError(PebbleError):
    """Encoding a packet failed."""


class ConnectionError(PebbleError):
    """Connecting to the Pebble failed."""


class IncompleteMessage(PebbleError):
    """The message received from the Pebble was incomplete."""
