__author__ = "katharine"

import time
import uuid

from libpebble2.communication import PebbleConnection
from libpebble2.protocol.appglance import AppGlance, AppGlanceSlice
from libpebble2.protocol.blobdb import BlobDatabaseID

from .blobdb import BlobDBClient, SyncWrapper


class AppGlances:
    """
    Reloads app glances.

    .. note:
       If a :class:`BlobDBClient` already exists for the given :class:`PebbleConnection`, you should
       pass that in here to avoid conflicts.

    Args:
        pebble (PebbleConnection): The Pebble to send an app glance reload message to.
        blobdb (BlobDBClient, optional): An existing :class:`BlobDBClient`, if any. If necessary,
            one will be created.
    """

    def __init__(self, pebble: PebbleConnection, blobdb: BlobDBClient | None = None) -> None:
        self._pebble = pebble
        self._blobdb = blobdb or BlobDBClient(pebble)

    def reload_glance(
        self,
        target_app: uuid.UUID,
        slices: list[AppGlanceSlice] | None = None,
    ) -> None:
        """
        Reloads an app's glance. Blocks as long as necessary.

        Args:
            target_app (uuid.UUID): The app whose glance should be reloaded.
            slices (list[AppGlanceSlice], optional): The slices to include in the glance
                (defaults to no slices).
        """
        glance = AppGlance(version=1, creation_time=int(time.time()), slices=(slices or []))
        SyncWrapper(
            self._blobdb.insert,
            BlobDatabaseID.AppGlance,
            target_app,
            glance.serialise(),
        ).wait()
