__author__ = "katharine"
import logging

from .exceptions import (
    AppInstallError,
    ConnectionError,
    GetBytesError,
    IncompleteMessage,
    PacketDecodeError,
    PacketEncodeError,
    PebbleError,
    PutBytesError,
    ScreenshotError,
    TimeoutError,
)
from .version import __version__, __version_info__

logging.getLogger("libpebble2").addHandler(logging.NullHandler())
