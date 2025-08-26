__author__ = "katharine"

from libpebble2.communication import PebbleConnection
from libpebble2.events.mixin import EventSourceMixin
from libpebble2.exceptions import AppInstallError
from libpebble2.protocol.apps import (
    AppFetchRequest,
    AppFetchResponse,
    AppFetchStatus,
    AppMetadata,
    AppRunState,
    AppRunStateStart,
)
from libpebble2.protocol.blobdb import BlobDatabaseID
from libpebble2.protocol.legacy2 import (
    LegacyAppAvailable,
    LegacyAppInstallRequest,
    LegacyAppInstallResponse,
    LegacyAppLaunchMessage,
    LegacyBankEntry,
    LegacyBankInfoRequest,
    LegacyBankInfoResponse,
    LegacyUpgradeAppUUID,
)
from libpebble2.services.appmessage import AppMessageService
from libpebble2.services.appmessage import Uint8 as AMUint8
from libpebble2.util.bundle import PebbleBundle

from .blobdb import BlobDBClient, BlobStatus, SyncWrapper
from .putbytes import PutBytes, PutBytesType

__all__ = ["AppInstaller"]


class AppInstaller(EventSourceMixin):
    """
    Installs an app on the Pebble via Pebble Protocol.

    .. note:
       If you use a :class:`BlobDBClient` in use elsewhere, pass it in here. If none is passed
       it will create one, and they will conflict.

    Args:
        pebble (PebbleConnection): The connection over which to install the app.
        pbw_path (str): The path to the PBW file to be installed on the filesystem.
        blobdb_client (BlobDBClient, optional): An optional BlobDBClient to use,
            if one already exists. If omitted, one will be created.
    """

    def __init__(
        self,
        pebble: PebbleConnection,
        pbw_path: str,
        blobdb_client: BlobDBClient | None = None,
    ) -> None:
        self._pebble = pebble
        self._blobdb = blobdb_client or BlobDBClient(pebble)
        EventSourceMixin.__init__(self)
        #: Total number of bytes sent so far.
        self.total_sent = 0
        #: Total number of bytes to send.
        self.total_size: int = 0
        self._prepare(pbw_path)

    def _prepare(self, pbw_path: str) -> None:
        if self._pebble.watch_info is None or not self._pebble.watch_info.running:
            msg = "Watch info not available; cannot install app."
            raise AppInstallError(msg)

        self._bundle = PebbleBundle(
            pbw_path,
            hardware=self._pebble.watch_info.running.hardware_platform,
        )
        if not self._bundle.is_app_bundle:
            msg = "This is not an app bundle."
            raise AppInstallError(msg)

        app_path = self._bundle.get_app_path()
        if app_path is None:
            msg = "Bundle is missing the app binary path."
            raise AppInstallError(msg)
        self.total_size += self._bundle.zip.getinfo(app_path).file_size

        if self._bundle.has_resources:
            res_path = self._bundle.get_resource_path()
            if res_path is None:
                msg = "Bundle declares resources but none were found."
                raise AppInstallError(msg)
            self.total_size += self._bundle.zip.getinfo(res_path).file_size

        if self._bundle.has_worker:
            worker_path = self._bundle.get_worker_path()
            if worker_path is None:
                msg = "Bundle declares a worker but none was found."
                raise AppInstallError(msg)
            self.total_size += self._bundle.zip.getinfo(worker_path).file_size

    def install(self, force_install: bool = False) -> None:
        """
        Installs an app. Blocks until the installation is complete.

        While this method runs, "progress" events will be emitted regularly with the following
        signature: ::
           (sent_this_interval, sent_total, total_size)

        Args:
            force_install (bool): Install even if installing this pbw on this platform is usually
                forbidden (default is ``False``).

        Raises:
            AppInstallError: If the installation fails for any reason.
        """
        if not (force_install or self._bundle.should_permit_install()):
            msg = "This pbw is not supported on this platform."
            raise AppInstallError(msg)
        if self._pebble.firmware_version.major < 3:
            self._install_legacy2()
        else:
            self._install_modern()

    def _install_modern(self) -> None:
        metadata = self._bundle.get_app_metadata()
        app_uuid = metadata["uuid"]
        blob_packet = AppMetadata(
            uuid=app_uuid,
            flags=metadata["flags"],
            icon=metadata["icon_resource_id"],
            app_version_major=metadata["app_version_major"],
            app_version_minor=metadata["app_version_minor"],
            sdk_version_major=metadata["sdk_version_major"],
            sdk_version_minor=metadata["sdk_version_minor"],
            app_face_bg_color=0,
            app_face_template_id=0,
            app_name=metadata["app_name"],
        )

        result = SyncWrapper(
            self._blobdb.insert, BlobDatabaseID.App, app_uuid, blob_packet.serialise()
        ).wait()
        if result != BlobStatus.Success:
            msg = f"BlobDB error: {result!s}"
            raise AppInstallError(msg)

        # Start the app.
        app_fetch = self._pebble.send_and_read(
            AppRunState(data=AppRunStateStart(uuid=app_uuid)), AppFetchRequest
        )
        if app_fetch.uuid != app_uuid:
            self._pebble.send_packet(AppFetchResponse(response=AppFetchStatus.InvalidUUID))
            msg = f"App requested the wrong UUID! Asked for {app_fetch.uuid}; expected {app_uuid}"
            raise AppInstallError(msg)
        self._broadcast_event("progress", 0, self.total_sent, self.total_size)

        app_path = self._bundle.get_app_path()
        if app_path is None:
            msg = "Bundle is missing the app binary path."
            raise AppInstallError(msg)
        binary = self._bundle.zip.read(app_path)
        self._send_part(PutBytesType.Binary, binary, app_fetch.app_id)

        if self._bundle.has_resources:
            res_path = self._bundle.get_resource_path()
            if res_path is None:
                msg = "Bundle declares resources but none were found."
                raise AppInstallError(msg)
            resources = self._bundle.zip.read(res_path)
            self._send_part(PutBytesType.Resources, resources, app_fetch.app_id)

        if self._bundle.has_worker:
            worker_path = self._bundle.get_worker_path()
            if worker_path is None:
                msg = "Bundle declares a worker but none was found."
                raise AppInstallError(msg)
            worker = self._bundle.zip.read(worker_path)
            self._send_part(PutBytesType.Worker, worker, app_fetch.app_id)

    def _send_part(self, type: PutBytesType, object: bytes, install_id: int) -> None:
        pb = PutBytes(self._pebble, type, object, app_install_id=install_id)
        pb.register_handler("progress", self._handle_progress)
        pb.send()

    def _install_legacy2(self) -> None:
        metadata = self._bundle.get_app_metadata()
        app_uuid = metadata["uuid"]

        # We don't really care if this worked; we're just waiting for it.
        self._pebble.send_and_read(
            LegacyAppInstallRequest(data=LegacyUpgradeAppUUID(uuid=app_uuid)),
            LegacyAppInstallResponse,
        )

        # Find somewhere to install to.
        result = self._pebble.send_and_read(
            LegacyAppInstallRequest(data=LegacyBankInfoRequest()),
            LegacyAppInstallResponse,
        ).data

        if not isinstance(result, LegacyBankInfoResponse):
            msg = "Did not receive bank info response."
            raise AppInstallError(msg)

        first_free = 0
        for app in result.apps:
            if not isinstance(app, LegacyBankEntry):
                continue
            if app.bank_number == first_free:
                first_free += 1
        if first_free == result.bank_count:
            msg = "No app banks free."
            raise AppInstallError(msg)
        self._broadcast_event("progress", 0, self.total_sent, self.total_size)

        app_path = self._bundle.get_app_path()
        if app_path is None:
            msg = "Bundle is missing the app binary path."
            raise AppInstallError(msg)

        binary = self._bundle.zip.read(app_path)
        self._send_part_legacy2(PutBytesType.Binary, binary, first_free)

        if self._bundle.has_resources:
            res_path = self._bundle.get_resource_path()
            if res_path is None:
                msg = "Bundle declares resources but none were found."
                raise AppInstallError(msg)
            resources = self._bundle.zip.read(res_path)
            self._send_part_legacy2(PutBytesType.Resources, resources, first_free)

        if self._bundle.has_worker:
            worker_path = self._bundle.get_worker_path()
            if worker_path is None:
                msg = "Bundle declares a worker but none was found."
                raise AppInstallError(msg)
            worker = self._bundle.zip.read(worker_path)
            self._send_part_legacy2(PutBytesType.Worker, worker, first_free)

        # Mark it as available
        self._pebble.send_and_read(
            LegacyAppInstallRequest(data=LegacyAppAvailable(bank=first_free, vibrate=True)),
            LegacyAppInstallResponse,
        )

        # Launch it (which is painful on 2.x).
        appmessage = AppMessageService(self._pebble, message_type=LegacyAppLaunchMessage)
        appmessage.send_message(
            app_uuid,
            {LegacyAppLaunchMessage.Keys.RunState: AMUint8(LegacyAppLaunchMessage.States.Running)},
        )
        appmessage.shutdown()

    def _send_part_legacy2(self, type: PutBytesType, object: bytes, bank: int) -> None:
        pb = PutBytes(self._pebble, type, object, bank=bank)
        pb.register_handler("progress", self._handle_progress)
        pb.send()

    def _handle_progress(self, sent: int, total_sent: int, total_length: int) -> None:
        self.total_sent += sent
        self._broadcast_event("progress", sent, self.total_sent, self.total_size)
