__author__ = "katharine"

from enum import IntEnum

from libpebble2.protocol.base import PebblePacket
from libpebble2.protocol.base.types import (
    BinaryArray,
    Boolean,
    FixedList,
    Int8,
    Int16,
    Optional,
    Uint8,
    Uint16,
    Uint32,
    Union,
)

HEADER_SIGNATURE = 0xFEED
FOOTER_SIGNATURE = 0xBEEF


class QemuSPP(PebblePacket):
    """
    Represents a QEMU Serial Port Protocol (SPP) packet for Pebble communication.

    This class extends PebblePacket and defines a payload field as a BinaryArray,
    which holds the raw binary data transmitted over the QEMU SPP transport.

    Attributes:
        payload (BinaryArray): The binary payload of the SPP packet.
    """

    payload = BinaryArray()


class QemuTap(PebblePacket):
    """
    Represents a QEMU tap event packet for Pebble emulator communication.

    Attributes:
        axis (Uint8): The axis on which the tap occurred. Uses the Axis enum (X=0, Y=1, Z=2).
        direction (Int8): The direction of the tap event.

    Classes:
        Axis (IntEnum): Enum representing the possible axes for the tap event.
            X (int): X-axis (0)
            Y (int): Y-axis (1)
            Z (int): Z-axis (2)
    """

    class Axis(IntEnum):
        """
        Enumeration representing the three spatial axes.

        Attributes:
            X (int): The X axis, typically representing horizontal direction.
            Y (int): The Y axis, typically representing vertical direction.
            Z (int): The Z axis, typically representing depth or perpendicular direction.
        """

        X = 0
        Y = 1
        Z = 2

    axis = Uint8()
    direction = Int8()


class QemuBluetoothConnection(PebblePacket):
    """
    Represents a Bluetooth connection status packet for QEMU transport.

    Attributes:
        connected (Boolean): Indicates whether the Bluetooth connection is established.
    """

    connected = Boolean()


class QemuCompass(PebblePacket):
    """
    Represents a compass packet for QEMU transport in Pebble communication.

    Attributes:
        heading (Uint32): The compass heading value in degrees.
        calibrated (Uint8): Calibration status as an integer corresponding to Calibration enum.

    Classes:
        Calibration (IntEnum): Enum representing the calibration state of the compass.
            Uncalibrated (0): The compass is not calibrated.
            Refining (1): The compass is in the process of calibration.
            Complete (2): The compass calibration is complete.
    """

    class Calibration(IntEnum):
        """
        Enumeration representing the calibration status.

        Attributes:
            Uncalibrated (int): The device is not calibrated.
            Refining (int): Calibration is in progress.
            Complete (int): Calibration is finished.
        """

        Uncalibrated = 0
        Refining = 1
        Complete = 2

    heading = Uint32()
    calibrated = Uint8()


class QemuBattery(PebblePacket):
    """
    Represents a battery status packet for QEMU transport.

    Attributes:
        percent (Uint8): The battery percentage (0-100).
        charging (Boolean): Indicates whether the device is currently charging.
    """

    percent = Uint8()
    charging = Boolean()


class QemuAccelSample(PebblePacket):
    """
    Represents an accelerometer sample packet for QEMU transport.

    Attributes:
        x (Int16): The X-axis acceleration value.
        y (Int16): The Y-axis acceleration value.
        z (Int16): The Z-axis acceleration value.
    """

    x = Int16()
    y = Int16()
    z = Int16()


class QemuAccel(PebblePacket):
    """
    Represents an accelerometer data packet for QEMU transport.

    Attributes:
        count (Uint8): The number of accelerometer samples included in the packet.
        samples (FixedList[QemuAccelSample]): A fixed list of QemuAccelSample objects, with
            length specified by `count`.
    """

    count = Uint8()
    samples = FixedList(QemuAccelSample, count=count)


class QemuAccelResponse(PebblePacket):
    """
    Represents a response packet for QEMU acceleration commands.

    Attributes:
        remaining_space (Uint16): The remaining space available, represented as a 16-bit
            unsigned integer.
    """

    remaining_space = Uint16()


class QemuVibration(PebblePacket):
    """
    Represents a vibration command packet for QEMU transport.

    Attributes:
        state (Optional[bool]): Indicates the vibration state. If True, vibration is enabled;
            if False, vibration is disabled.
    """

    state = Optional(Boolean())


class QemuButton(PebblePacket):
    """
    Represents a button event packet for QEMU transport in Pebble emulation.

    Attributes:
        state (Uint8): The state of the button (pressed/released).

    Inner Classes:
        Button (IntEnum): Enumeration of possible buttons:
            - Back: 1
            - Up: 2
            - Select: 4
            - Down: 8
    """

    class Button(IntEnum):
        """
        An enumeration representing the buttons available on the device.

        Attributes:
            Back (int): Represents the 'Back' button (value: 1).
            Up (int): Represents the 'Up' button (value: 2).
            Select (int): Represents the 'Select' button (value: 4).
            Down (int): Represents the 'Down' button (value: 8).
        """

        Back = 1
        Up = 2
        Select = 4
        Down = 8

    state = Uint8()


class QemuTimeFormat(PebblePacket):
    """
    Represents a packet for configuring the time format in QEMU transport.

    Attributes:
        is_24_hour (Boolean): Indicates whether the time format is 24-hour (True)
            or 12-hour (False).
    """

    is_24_hour = Boolean()


class QemuTimelinePeek(PebblePacket):
    """
    Represents a packet used to peek the timeline state in the QEMU transport protocol.

    Attributes:
        enabled (Boolean): Indicates whether the timeline peek functionality is enabled.
    """

    enabled = Boolean()


class QemuContentSize(PebblePacket):
    """
    Represents a packet for specifying content size in QEMU communication.

    Attributes:
        size (Uint8): The size value corresponding to the content size.

    Classes:
        ContentSize (IntEnum): Enumeration of possible content sizes.
            Small (0): Small content size.
            Medium (1): Medium content size.
            Large (2): Large content size.
            ExtraLarge (3): Extra large content size.
    """

    class ContentSize(IntEnum):
        """
        An enumeration representing the possible sizes of content.

        Attributes:
            Small (int): Represents a small content size.
            Medium (int): Represents a medium content size.
            Large (int): Represents a large content size.
            ExtraLarge (int): Represents an extra large content size.
        """

        Small = 0
        Medium = 1
        Large = 2
        ExtraLarge = 3

    size = Uint8()


class QemuPacket(PebblePacket):
    """
    Represents a QEMU protocol packet for Pebble communication.

    Attributes:
        signature (Uint16): Packet header signature, defaults to HEADER_SIGNATURE.
        protocol (Uint16): Protocol identifier specifying the type of packet.
        length (Uint16): Length of the packet data.
        data (Union): Packet data, dynamically selected based on the protocol value.
            Supported protocol values and corresponding data types:
                1: QemuSPP
                2: QemuTap
                3: QemuBluetoothConnection
                4: QemuCompass
                5: QemuBattery
                6: QemuAccel
                8: QemuButton
                9: QemuTimeFormat
                10: QemuTimelinePeek
                11: QemuContentSize
            The length of the data is determined by the 'length' attribute.
        footer (Uint16): Packet footer signature, defaults to FOOTER_SIGNATURE.
    """

    signature = Uint16(default=HEADER_SIGNATURE)
    protocol = Uint16()
    length = Uint16()
    data = Union(
        protocol,
        {
            1: QemuSPP,
            2: QemuTap,
            3: QemuBluetoothConnection,
            4: QemuCompass,
            5: QemuBattery,
            6: QemuAccel,
            8: QemuButton,
            9: QemuTimeFormat,
            10: QemuTimelinePeek,
            11: QemuContentSize,
        },
        length=length,
    )
    footer = Uint16(default=FOOTER_SIGNATURE)


class QemuInboundPacket(PebblePacket):
    """
    Represents an inbound packet received from the QEMU transport layer.

    Attributes:
        signature (Uint16): Packet header signature, defaults to HEADER_SIGNATURE.
        protocol (Uint16): Protocol identifier for the packet type.
        length (Uint16): Length of the packet data.
        data (Union): Packet data, dynamically selected based on the protocol value.
            - 1: QemuSPP
            - 6: QemuAccelResponse
            - 7: QemuVibration
        footer (Uint16): Packet footer signature, defaults to FOOTER_SIGNATURE.
    """

    signature = Uint16(default=HEADER_SIGNATURE)
    protocol = Uint16()
    length = Uint16()
    data = Union(
        protocol,
        {
            1: QemuSPP,
            6: QemuAccelResponse,
            7: QemuVibration,
        },
        length=length,
    )
    footer = Uint16(default=FOOTER_SIGNATURE)


class QemuRawPacket(PebblePacket):
    """
    Represents a raw packet used in QEMU-based Pebble communication.

    Attributes:
        signature (Uint16): Packet header signature, defaults to HEADER_SIGNATURE.
        protocol (Uint16): Protocol identifier for the packet.
        length (Uint16): Length of the data payload.
        data (BinaryArray): Binary payload of the packet, sized according to 'length'.
        footer (Uint16): Packet footer signature, defaults to FOOTER_SIGNATURE.
    """

    signature = Uint16(default=HEADER_SIGNATURE)
    protocol = Uint16()
    length = Uint16()
    data = BinaryArray(length=length)
    footer = Uint16(default=FOOTER_SIGNATURE)
