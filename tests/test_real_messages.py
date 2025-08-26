# encoding: utf-8
__author__ = "katharine"

import pytest
from libpebble2.protocol.system import SystemMessage


def test_system_message():
    assert (
        SystemMessage(message_type=SystemMessage.Type.FirmwareUpdateStart).serialise()
        == b"\x00\x01"
    )
