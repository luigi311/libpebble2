__author__ = "katharine"

from enum import IntEnum

from .appmessage import AppMessage
from .base import PebblePacket
from .base.types import (
    UUID,
    Boolean,
    FixedList,
    FixedString,
    PascalString,
    Uint8,
    Uint32,
    Union,
)

__all__ = [
    "LegacyAppAvailable",
    "LegacyAppDescribeResponse",
    "LegacyAppInstallRequest",
    "LegacyAppInstallResponse",
    "LegacyAppInstallResult",
    "LegacyAppLaunchMessage",
    "LegacyAppUUIDsResult",
    "LegacyBankEntry",
    "LegacyBankInfoRequest",
    "LegacyBankInfoResponse",
    "LegacyCurrentAppRequest",
    "LegacyCurrentAppResponse",
    "LegacyDescribeInstalledUUID",
    "LegacyListInstalledUUIDs",
    "LegacyNotification",
    "LegacyRemoveAppUUID",
    "LegacyUpgradeAppUUID",
]


class LegacyNotification(PebblePacket):
    """
    Represents a legacy notification packet for Pebble devices.

    Attributes:
        type (Source): The source type of the notification (Email, SMS, Facebook, Twitter).
        sender (PascalString): The sender of the notification.
        body (PascalString): The body content of the notification.
        timestamp (PascalString): The timestamp of the notification.
        subject (PascalString): The subject of the notification.

    Meta:
        endpoint (int): The protocol endpoint for legacy notifications (3000).
        endianness (str): The byte order used for serialization ("<" for little-endian).

    Source (IntEnum):
        Email (int): 0
        SMS (int): 1
        Facebook (int): 2
        Twitter (int): 3
    """

    class Meta:
        """
        Meta class containing protocol configuration constants.

        Attributes:
            endpoint (int): The protocol endpoint identifier.
            endianness (str): The byte order used for serialization ("<" for little-endian).
        """

        endpoint = 3000
        endianness = "<"

    class Source(IntEnum):
        """
        An enumeration representing the source of a message or notification.

        Attributes:
            Email (int): Represents an email source (value: 0).
            SMS (int): Represents an SMS source (value: 1).
            Facebook (int): Represents a Facebook source (value: 2).
            Twitter (int): Represents a Twitter source (value: 3).
        """

        Email = 0
        SMS = 1
        Facebook = 2
        Twitter = 3

    type = Uint8(enum=Source)
    sender = PascalString()
    body = PascalString()
    timestamp = PascalString()
    subject = PascalString()


class LegacyBankInfoRequest(PebblePacket):
    """
    Represents a request packet for legacy bank information in the Pebble protocol.

    This class is used to initiate a request for bank information from a Pebble device
    using the legacy protocol version 2. It does not define any additional fields or methods,
    and serves as a marker for this specific packet type.

    Inheritance:
        PebblePacket: Base class for Pebble protocol packets.
    """


class LegacyRemoveAppUUID(PebblePacket):
    """
    Represents a packet for removing an application by its UUID on legacy Pebble devices.

    Attributes:
        uuid (UUID): The universally unique identifier of the application to be removed.
    """

    uuid = UUID()


class LegacyUpgradeAppUUID(PebblePacket):
    """
    Represents a packet for upgrading an application's UUID in the legacy Pebble protocol.

    Attributes:
        uuid (UUID): The universally unique identifier (UUID) of the application to be upgraded.
    """

    uuid = UUID()


class LegacyAppAvailable(PebblePacket):
    """
    Represents the availability status of a legacy Pebble app.

    Attributes:
        bank (Uint32): Identifier for the app bank.
        vibrate (Boolean): Indicates whether vibration is enabled for the app.
    """

    bank = Uint32()
    vibrate = Boolean()


class LegacyListInstalledUUIDs(PebblePacket):
    """Represents a packet for listing installed application UUIDs on legacy Pebble devices."""


class LegacyDescribeInstalledUUID(PebblePacket):
    """
    Represents a packet for describing an installed application by its UUID on legacy Pebble
    devices.

    Attributes:
        uuid (UUID): The universally unique identifier of the application to be described.
    """

    uuid = UUID()


class LegacyCurrentAppRequest(PebblePacket):
    """Represents a request packet for the currently active application on legacy Pebble devices."""


class LegacyAppInstallRequest(PebblePacket):
    """
    Represents a legacy app install request packet for Pebble devices.

    This packet is used to communicate various app-related commands to the device,
    such as requesting bank information, removing or upgrading app UUIDs, checking app availability,
    listing installed UUIDs, describing installed UUIDs, and requesting the current app.

    Attributes:
        command (Uint8): The command identifier specifying the type of request.
        data (Union): The payload associated with the command, which varies depending on the
            command value:
            - 0x01: LegacyBankInfoRequest
            - 0x02: LegacyRemoveAppUUID
            - 0x03: LegacyAppAvailable
            - 0x05: LegacyListInstalledUUIDs
            - 0x06: LegacyDescribeInstalledUUID
            - 0x07: LegacyCurrentAppRequest
            - 0x08: LegacyUpgradeAppUUID

    Meta:
        endpoint (int): The protocol endpoint for legacy app install requests (6000).
        register (bool): Indicates whether the packet should be registered (False).
    """

    class Meta:
        """
        Meta class containing protocol configuration for legacy Pebble 2 devices.

        Attributes:
            endpoint (int): The protocol endpoint identifier.
            register (bool): Indicates whether the protocol should be registered.
        """

        endpoint = 6000
        register = False

    command = Uint8()
    data = Union(
        command,
        {
            0x01: LegacyBankInfoRequest,
            0x02: LegacyRemoveAppUUID,
            0x08: LegacyUpgradeAppUUID,
            0x03: LegacyAppAvailable,
            0x05: LegacyListInstalledUUIDs,
            0x06: LegacyDescribeInstalledUUID,
            0x07: LegacyCurrentAppRequest,
        },
    )


class LegacyBankEntry(PebblePacket):
    """
    Represents an entry in the legacy Pebble app bank.

    Attributes:
        install_id (Uint32): Unique identifier for the installed app.
        bank_number (Uint32): The bank slot number where the app is stored.
        app_name (FixedString): Name of the application (max 32 characters).
        company_name (FixedString): Name of the company (max 32 characters).
        flags (Uint32): Flags associated with the app entry.
        version_minor (Uint8): Minor version number of the app.
        version_major (Uint8): Major version number of the app.
    """

    install_id = Uint32()
    bank_number = Uint32()
    app_name = FixedString(32)
    company_name = FixedString(32)
    flags = Uint32()
    version_minor = Uint8()
    version_major = Uint8()


class LegacyBankInfoResponse(PebblePacket):
    """
    Represents a response packet containing information about legacy app banks on a Pebble device.

    Attributes:
        bank_count (Uint32): The total number of available banks.
        occupied_banks (Uint32): The number of banks currently occupied by apps.
        apps (FixedList[LegacyBankEntry]): A list of LegacyBankEntry objects representing the apps
            in occupied banks.
    """

    bank_count = Uint32()
    occupied_banks = Uint32()
    apps = FixedList(LegacyBankEntry, count=occupied_banks)


class LegacyAppInstallResult(PebblePacket):
    """
    Represents the result of an app installation operation on a Pebble device.

    Attributes:
        status (Status): The status of the installation or removal operation, represented
            as an enum.

    Enums:
        Status (IntEnum):
            Success (1): The operation was successful.
            BankInUse (2): The app bank is currently in use (install).
            InstallInvalidCommand (3): The install command is invalid.
            InstallGeneralFailure (4): A general failure occurred during installation.
            IncompatibleSDK (5): The app is incompatible with the SDK version.
            InvalidUUID (6): The provided UUID is invalid.
            UUIDConflict (7): There is a conflict with the UUID.
            MissingWorker (8): A required worker is missing.
            NoAppInBank (2): No app found in the bank (remove).
            InstallIDMismatch (3): The install ID does not match (remove).
            RemoveInvalidCommand (4): The remove command is invalid.
            RemoveGeneralFailure (5): A general failure occurred during removal.

    Note:
        Some enum values are reused for both install and remove operations.
    """

    class Status(IntEnum):
        """
        Status codes for legacy Pebble protocol operations.

        Members:
            Success (1): Operation completed successfully.
            BankInUse (2): The application bank is currently in use.
            InstallInvalidCommand (3): Invalid command received during installation.
            InstallGeneralFailure (4): General failure occurred during installation.
            IncompatibleSDK (5): The SDK version is incompatible.
            InvalidUUID (6): Provided UUID is invalid.
            UUIDConflict (7): UUID conflict detected.
            MissingWorker (8): Required worker is missing.
            NoAppInBank (2): No application found in the bank (removal operation).
            InstallIDMismatch (3): Mismatch in install ID during removal.
            RemoveInvalidCommand (4): Invalid command received during removal.
            RemoveGeneralFailure (5): General failure occurred during removal.

        Note:
            Some status codes share the same integer value for different contexts (e.g., BankInUse
            and NoAppInBank both use 2).
        """

        Success = 1
        InvalidUUID = 6
        # Install
        BankInUse = 2
        InstallInvalidCommand = 3
        InstallGeneralFailure = 4
        IncompatibleSDK = 5
        UUIDConflict = 7
        MissingWorker = 8
        # Remove
        NoAppInBank = 2
        InstallIDMismatch = 3
        RemoveInvalidCommand = 4
        RemoveGeneralFailure = 5

    status = Uint32(enum=Status)


class LegacyAppUUIDsResult(PebblePacket):
    """
    Represents the result packet containing a list of legacy application UUIDs.

    Attributes:
        count (Uint8): The number of UUIDs included in the packet.
        uuids (FixedList[UUID]): A fixed-length list of UUIDs, with length specified by `count`.
    """

    count = Uint8()
    uuids = FixedList(UUID(), count=count)


class LegacyAppDescribeResponse(PebblePacket):
    """
    Represents the response packet for describing a legacy Pebble application.

    Attributes:
        version_minor (Uint8): The minor version number of the application.
        version_major (Uint8): The major version number of the application.
        app_name (FixedString): The name of the application (up to 32 characters).
        company_name (FixedString): The name of the company that developed the application
            (up to 32 characters).
    """

    version_minor = Uint8()
    version_major = Uint8()
    app_name = FixedString(32)
    company_name = FixedString(32)


class LegacyCurrentAppResponse(PebblePacket):
    """
    Represents a response packet containing the UUID of the currently running app
    on a Pebble device.

    Attributes:
        uuid (UUID): The universally unique identifier of the current app.
    """

    uuid = UUID()


class LegacyAppInstallResponse(PebblePacket):
    """
    Represents a response packet for legacy app installation operations.

    Attributes:
        command (Uint8): The command identifier for the response.
        data (Union): The response data, which is determined by the value of `command`.
            Possible mappings:
                0x01: LegacyBankInfoResponse
                0x02: LegacyAppInstallResult
                0x05: LegacyAppUUIDsResult
                0x06: LegacyAppDescribeResponse
                0x07: LegacyCurrentAppResponse

    Meta:
        endpoint (int): The protocol endpoint for legacy app install responses (6000).
    """

    class Meta:
        """
        Meta class containing protocol configuration for legacy Pebble 2 devices.

        Attributes:
            endpoint (int): The protocol endpoint identifier, set to 6000.
        """

        endpoint = 6000

    command = Uint8()
    data = Union(
        command,
        {
            0x01: LegacyBankInfoResponse,
            0x02: LegacyAppInstallResult,
            0x05: LegacyAppUUIDsResult,
            0x06: LegacyAppDescribeResponse,
            0x07: LegacyCurrentAppResponse,
        },
    )


class LegacyAppLaunchMessage(AppMessage):
    """
    Represents a legacy app launch message for Pebble devices.

    This message is used to communicate the launch state of an application,
    including whether it is running or not, and to fetch the current state.

    Attributes:
        Meta (class): Contains protocol metadata such as endpoint and endianness.
        Keys (IntEnum): Enumerates message keys for run state and state fetch.
            - RunState (0x01): Key for indicating the run state of the app.
            - StateFetch (0x02): Key for requesting the current state.
        States (IntEnum): Enumerates possible app states.
            - NotRunning (0x00): Indicates the app is not running.
            - Running (0x01): Indicates the app is running.
    """

    class Meta:
        """
        Meta class containing protocol configuration for legacy Pebble communication.

        Attributes:
            endpoint (int): The protocol endpoint identifier (0x31).
            endianness (str): The byte order used for serialization ("<" for little-endian).
        """

        endpoint = 0x31
        endianness = "<"

    class Keys(IntEnum):
        """
        An enumeration representing legacy protocol keys.

        Attributes:
            RunState (int): Key for the run state (value: 0x01).
            StateFetch (int): Key for fetching the state (value: 0x02).
        """

        RunState = 0x01
        StateFetch = 0x02

    class States(IntEnum):
        """
        Enumeration representing the possible states of the legacy protocol.

        Attributes:
            NotRunning (int): Indicates that the protocol is not running (value: 0x00).
            Running (int): Indicates that the protocol is running (value: 0x01).
        """

        NotRunning = 0x00
        Running = 0x01
