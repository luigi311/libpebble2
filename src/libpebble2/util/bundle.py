__author__ = "katharine"

import json
import struct
import uuid
import zipfile
from pathlib import Path
from types import TracebackType

from libpebble2.protocol.apps import AppMetadata

from .hardware import PebbleHardware

__all__ = ["PebbleBundle"]


from typing import Any, ClassVar, TypedDict, cast


class ApplicationInfo(TypedDict):
    name: str  # Path to the app binary inside the zip


class ResourcesInfo(TypedDict):
    name: str  # Path to the resources bundle inside the zip


class WorkerInfo(TypedDict):
    name: str  # Path to the worker binary inside the zip


class Manifest(TypedDict, total=False):
    application: ApplicationInfo
    resources: ResourcesInfo
    worker: WorkerInfo
    firmware: dict[str, Any]
    js: Any

class AppMetadataDict(TypedDict):
    sentinel: bytes
    struct_version_major: int
    struct_version_minor: int
    sdk_version_major: int
    sdk_version_minor: int
    app_version_major: int
    app_version_minor: int
    app_size: int
    offset: int
    crc: int
    app_name: str
    company_name: str
    icon_resource_id: int
    symbol_table_addr: int
    flags: int
    num_relocation_entries: int
    uuid: uuid.UUID

class PebbleBundle:
    """
    Represents a Pebble bundle, which can be an application or firmware package for Pebble devices.

    Provides methods to access bundle contents, metadata, and compatibility information for
    different hardware platforms.
    """

    MANIFEST_FILENAME: ClassVar[str] = "manifest.json"
    UNIVERSAL_FILES: ClassVar[frozenset[str]] = frozenset({"appinfo.json", "pebble-js-app.js"})

    STRUCT_DEFINITION: ClassVar[tuple[str, ...]] = (
        "8s",  # header
        "2B",  # struct version
        "2B",  # sdk version
        "2B",  # app version
        "H",  # size
        "I",  # offset
        "I",  # crc
        "32s",  # app name
        "32s",  # company name
        "I",  # icon resource id
        "I",  # symbol table address
        "I",  # flags
        "I",  # num relocation list entries
        "16s",  # uuid
    )

    PLATFORM_PATHS: ClassVar[dict[str, tuple[str, ...]]] = {
        "unknown": ("",),
        "aplite": ("aplite/", ""),  # dual aplite2/3 apps on 2.x will fail; unsupported & OK
        "basalt": ("basalt/", ""),
        "chalk": ("chalk/",),
        "diorite": ("diorite/", "aplite/", ""),
        "emery": ("emery/", "basalt/", ""),
    }

    MAX_COMPATIBILITY_VERSIONS: ClassVar[dict[str, dict[str, int]]] = {
        "basalt": {"": 0x16},
        "diorite": {"aplite/": 0x50, "": 0x16},
        "emery": {"basalt/": 0x54, "": 0x16},
    }

    def __init__(self, bundle_path: str, hardware: int = PebbleHardware.UNKNOWN) -> None:
        self.hardware = hardware
        bundle_abs_path = Path(bundle_path).resolve()
        if not bundle_abs_path.exists():
            msg = f"Bundle does not exist: {bundle_path}"
            raise FileNotFoundError(msg)

        self.zip = zipfile.ZipFile(bundle_abs_path)
        self.path = bundle_abs_path
        self.manifest: Manifest | None = None
        self.header: AppMetadataDict | None = None
        self._zip_contents = set(self.zip.namelist())

        self.app_metadata_struct = struct.Struct("".join(self.STRUCT_DEFINITION))
        self.app_metadata_length_bytes = self.app_metadata_struct.size

        self.print_pbl_logs = False

    def __enter__(self) -> "PebbleBundle":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        self.close()
        return False

    @classmethod
    def prefixes_for_hardware(cls, hardware: int) -> tuple[str, ...]:
        """
        Returns the tuple of path prefixes associated with the specified hardware.

        Args:
            hardware (int): The hardware identifier.

        Returns:
            tuple[str, ...]: A tuple containing the path prefixes for the hardware's platform.

        Raises:
            KeyError: If the hardware platform is not found in PLATFORM_PATHS.
        """
        platform = PebbleHardware.hardware_platform(hardware)
        return cls.PLATFORM_PATHS[platform]

    def get_real_path(self, path: str) -> str | None:
        """
        Resolves the actual path of a file within the bundle, considering
        hardware-specific prefixes.

        Args:
            path (str): The relative path of the file to resolve.

        Returns:
            str | None: The resolved path if found in the bundle, otherwise None.
        """
        if path in self.UNIVERSAL_FILES:
            return path

        for prefix in self.prefixes_for_hardware(self.hardware):
            real_path = prefix + path
            if real_path in self._zip_contents:
                return real_path
        return None

    def _get_real_prefix(self) -> str | None:
        for prefix in self.prefixes_for_hardware(self.hardware):
            if prefix + self.MANIFEST_FILENAME in self._zip_contents:
                return prefix
        return None

    def should_permit_install(self) -> bool:
        """
        Determines whether the installation of an app should be permitted based on hardware platform
        compatibility and SDK version.

        Returns:
            bool: True if installation is permitted, False otherwise.

        Logic:
            - Retrieves the hardware platform and real prefix.
            - If the prefix is None, installation is not permitted.
            - Checks if the platform has a maximum compatibility version defined.
                - If not defined for the prefix, installation is permitted.
                - If defined, compares the app's SDK minor version to the maximum allowed.
            - If the platform is not in the compatibility list, installation is permitted.
        """
        platform = PebbleHardware.hardware_platform(self.hardware)
        prefix = self._get_real_prefix()
        if prefix is None:
            return False
        if platform in self.MAX_COMPATIBILITY_VERSIONS:
            max_version = self.MAX_COMPATIBILITY_VERSIONS[platform].get(prefix)
            if max_version is None:
                return True
            metadata = self.get_app_metadata()
            sdk_minor_obj: Any = metadata.get("sdk_version_minor")
            if isinstance(sdk_minor_obj, bool):
                return False
            try:
                sdk_minor = int(sdk_minor_obj)
            except (TypeError, ValueError):
                return False
            return sdk_minor < max_version
        return True

    def get_manifest(self) -> Manifest:
        """
        Retrieves and returns the manifest dictionary from the PebbleBundle.

        If the manifest has already been loaded, it returns the cached manifest.
        Otherwise, it attempts to locate and read the manifest file from the bundle.
        Raises a ValueError if the manifest file cannot be found.

        Returns:
            Manifest: The manifest dictionary containing bundle information.

        Raises:
            ValueError: If the manifest file is missing from the bundle.
        """
        if self.manifest is not None:
            return self.manifest

        real = self.get_real_path(self.MANIFEST_FILENAME)
        if real is None or real not in self._zip_contents:
            msg = f"Could not find {self.MANIFEST_FILENAME}; are you sure this is a PebbleBundle?"
            raise ValueError(msg)

        raw = json.loads(self.zip.read(real).decode("utf-8"))
        if not isinstance(raw, dict):
            msg = "Manifest root must be a JSON object."
            raise TypeError(msg)
        self.manifest = cast("Manifest", raw)
        return self.manifest

    def get_app_metadata(self) -> AppMetadataDict:
        """
        Extracts and returns metadata for the application binary contained in the bundle.

        If the metadata has already been extracted, returns the cached header dictionary.
        Otherwise, reads the application manifest, locates the binary, unpacks the metadata
        header using the defined struct, and returns a dictionary containing metadata fields.

        Returns:
            dict[str, object]: A dictionary containing application metadata fields.

        Raises:
            ValueError: If the application binary cannot be found in the bundle.
        """
        if self.header is not None:
            return self.header

        manifest = self.get_manifest()
        if "application" not in manifest:
            msg = "Bundle has no application entry in manifest."
            raise ValueError(msg)
        app_manifest: ApplicationInfo = manifest["application"]

        app_path = self.get_real_path(app_manifest["name"])
        if app_path is None:
            msg = f"Could not find application binary '{app_manifest['name']}' in the bundle."
            raise ValueError(msg)

        app_bin = self.zip.open(app_path).read()
        header = app_bin[: self.app_metadata_length_bytes]
        values = self.app_metadata_struct.unpack(header)
        self.header = {
            "sentinel": values[0],
            "struct_version_major": values[1],
            "struct_version_minor": values[2],
            "sdk_version_major": values[3],
            "sdk_version_minor": values[4],
            "app_version_major": values[5],
            "app_version_minor": values[6],
            "app_size": values[7],
            "offset": values[8],
            "crc": values[9],
            "app_name": values[10].rstrip(b"\0").decode("utf-8"),
            "company_name": values[11].rstrip(b"\0").decode("utf-8"),
            "icon_resource_id": values[12],
            "symbol_table_addr": values[13],
            "flags": values[14],
            "num_relocation_entries": values[15],
            "uuid": uuid.UUID(bytes=values[16]),
        }
        return self.header

    def close(self) -> None:
        """
        Closes the underlying ZIP file associated with the bundle.

        This method should be called when you are done working with the bundle to release any
        resources held by the ZIP file.
        """
        self.zip.close()

    @property
    def is_firmware_bundle(self) -> bool:
        """
        Determines if the current bundle is a firmware bundle.

        Returns:
            bool: True if the manifest contains a 'firmware' entry, False otherwise.
        """
        return "firmware" in self.get_manifest()

    @property
    def is_app_bundle(self) -> bool:
        """
        Determines if the bundle is an application bundle.

        Returns:
            bool: True if the manifest contains an "application" entry, False otherwise.
        """
        return "application" in self.get_manifest()

    @property
    def has_resources(self) -> bool:
        """
        Checks if the bundle contains resources.

        Returns:
            bool: True if "resources" is present in the manifest, False otherwise.
        """
        return "resources" in self.get_manifest()

    @property
    def has_worker(self) -> bool:
        """
        Checks if the manifest contains a 'worker' entry.

        Returns:
            bool: True if 'worker' is present in the manifest, False otherwise.
        """
        return "worker" in self.get_manifest()

    @property
    def has_javascript(self) -> bool:
        """
        Checks if the bundle contains JavaScript by verifying the presence of 'js' in the manifest.

        Returns:
            bool: True if 'js' is present in the manifest, False otherwise.
        """
        return "js" in self.get_manifest()

    def get_firmware_info(self) -> dict[str, Any] | None:
        """
        Retrieves firmware information from the bundle manifest if available.

        Returns:
            dict[str, Any] | None: A dictionary containing firmware information if the bundle
            is a firmware bundle, otherwise None.
        """
        manifest = self.get_manifest()
        if "firmware" not in manifest:
            return None
        return manifest["firmware"]

    def get_application_info(self) -> ApplicationInfo | None:
        """
        Retrieves the application information from the bundle manifest.

        Returns:
            ApplicationInfo | None: An ApplicationInfo object containing application information if
            the bundle is an app bundle, otherwise None.
        """
        manifest = self.get_manifest()
        if "application" not in manifest:
            return None
        return manifest["application"]

    def get_resources_info(self) -> ResourcesInfo | None:
        """
        Retrieves information about resources from the manifest if available.

        Returns:
            ResourcesInfo | None: A ResourcesInfo object containing resource information if the
            bundle has resources, otherwise None.
        """
        manifest = self.get_manifest()
        if "resources" not in manifest:
            return None
        return manifest["resources"]

    def get_worker_info(self) -> WorkerInfo | None:
        """
        Retrieves information about the worker from the app bundle manifest.

        Returns:
            WorkerInfo | None: A WorkerInfo object containing worker information if the bundle
            is an app bundle and has a worker, otherwise None.
        """
        manifest = self.get_manifest()
        if "worker" not in manifest:
            return None
        return manifest["worker"]

    def get_app_path(self) -> str | None:
        """
        Retrieves the real filesystem path of the application based on its name.

        Returns:
            str | None: The real path to the application if available, otherwise None.
        """
        app_info = self.get_application_info()
        if app_info is None:
            return None
        return self.get_real_path(app_info["name"])

    def get_resource_path(self) -> str | None:
        """
        Retrieves the real path to a resource if resource information is available.

        Returns:
            str | None: The real path to the resource if found, otherwise None.
        """
        resources_info = self.get_resources_info()
        if resources_info is None:
            return None
        return self.get_real_path(resources_info["name"])

    def get_worker_path(self) -> str | None:
        """
        Retrieves the real path of the worker if worker information is available.

        Returns:
            str | None: The real path to the worker if found, otherwise None.
        """
        worker_info = self.get_worker_info()
        if worker_info is None:
            return None
        return self.get_real_path(worker_info["name"])
