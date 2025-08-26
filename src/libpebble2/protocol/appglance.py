import struct
from copy import deepcopy
from enum import IntEnum

from .base import PebblePacket
from .base.types import FixedList, Uint8, Uint16, Uint32
from .timeline import TimelineAttribute

__author__ = "katharine"

"""
This file is special in that it actually contains definitions of
blobdb blob formats rather than pebble protocol messages.
"""

__all__ = ["AppGlance", "AppGlanceSliceIconAndSubtitle"]


class AppGlanceSliceType(IntEnum):
    IconAndSubtitle = 0


class AppGlanceSlice(PebblePacket):
    def __init__(
        self,
        expiration_time: int,
        slice_type: AppGlanceSliceType,
        extra_attributes: list[TimelineAttribute] | None = None,
    ) -> None:
        attributes = []
        if extra_attributes:
            attributes.extend(deepcopy(extra_attributes))
        attributes.append(
            TimelineAttribute(attribute_id=37, content=struct.pack("<I", expiration_time)),
        )

        # Add 4 bytes to account for total_size (2), type (1), and attribute_count (1)
        total_size = 4 + sum([len(attribute.serialise()) for attribute in attributes])

        super().__init__(
            total_size=total_size,
            type=slice_type,
            attribute_count=len(attributes),
            attributes=attributes,
        )

    class Meta:
        endianness = "<"

    total_size = Uint16()
    type = Uint8(enum=AppGlanceSliceType)
    attribute_count = Uint8()
    attributes = FixedList(TimelineAttribute, count=attribute_count)


class AppGlanceSliceIconAndSubtitle(AppGlanceSlice):
    """
    Represents an AppGlance slice with an icon and subtitle.

    This class extends `AppGlanceSlice` to provide a slice that can display both an icon and a
    subtitle. It constructs the appropriate timeline attributes for the icon and subtitle
    if provided.

    Args:
        expiration_time (int): The expiration time for the slice.
        icon (Optional[int]): The icon identifier to display. If provided, it is packed as a
            timeline attribute.
        subtitle_template_string (Optional[str]): The subtitle text to display. If provided,
            it is encoded as a timeline attribute.

    Attributes:
        attributes (List[TimelineAttribute]): List of timeline attributes for the icon and subtitle.
    """

    def __init__(
        self,
        expiration_time: int,
        icon: int | None = None,
        subtitle_template_string: str | None = None,
    ) -> None:
        attributes = []
        if icon is not None:
            attributes.append(TimelineAttribute(attribute_id=48, content=struct.pack("<I", icon)))
        if subtitle_template_string is not None:
            attributes.append(
                TimelineAttribute(
                    attribute_id=47,
                    content=subtitle_template_string.encode("utf-8"),
                ),
            )
        super().__init__(
            expiration_time,
            AppGlanceSliceType.IconAndSubtitle,
            extra_attributes=attributes,
        )


class AppGlance(PebblePacket):
    """
    Represents an AppGlance packet for Pebble devices.

    Attributes:
        version (Uint8): The version of the AppGlance packet.
        creation_time (Uint32): The timestamp when the packet was created.
        slices (FixedList[AppGlanceSlice]): A fixed list of AppGlanceSlice objects representing
                glanceable information.

    Meta:
        endianness (str): Specifies little-endian byte order ("<").
    """

    class Meta:
        """
        Meta class specifying protocol configuration.

        Attributes:
            endianness (str): Specifies the byte order for data serialization.
                "<" indicates little-endian format.
        """

        endianness = "<"

    version = Uint8()
    creation_time = Uint32()
    slices = FixedList(AppGlanceSlice)
