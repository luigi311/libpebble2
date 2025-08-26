__author__ = "andrews"

import unittest
import uuid
import struct

from libpebble2.protocol.voice import (
    VoiceControlCommand,
    VoiceControlResult,
    Command,
    Result,
    SessionType,
    Flags,
    SessionSetupCommand,
    SessionSetupResult,
    TranscriptionType,
    Transcription,
    DictationResult,
    Attribute,
    AttributeList,
    AppUuid,
    SpeexEncoderInfo,
    Word,
    Sentence,
    SentenceList,
)


# Helpers for little-endian packing
def u16(n: int) -> bytes:
    return struct.pack("<H", int(n))


def u32(n: int) -> bytes:
    return struct.pack("<I", int(n))


def word_bytes(conf: int, text: str) -> bytes:
    b = text.encode("ascii")
    return bytes([conf]) + u16(len(b)) + b


class TestVoiceProtocol(unittest.TestCase):
    def test_session_setup_command(self):
        # Build the expected wire payload using bytes and struct, not array/ord.
        app_uuid = uuid.uuid4()

        # Compose attributes: [AppUuid(...), SpeexEncoderInfo(...)]
        # Speex encoder attribute payload:
        version_padded = b"1.2rc1".ljust(20, b"\x00")
        sample_rate_le = u32(16000)  # 0x00003E80
        bit_rate_le = u16(12800)  # 0x3200
        bitstream_version_b = bytes([4])
        frame_size_le = u16(320)  # 0x0140
        speex_payload = (
            version_padded
            + sample_rate_le
            + bit_rate_le
            + bitstream_version_b
            + frame_size_le
        )
        speex_attr = (
            bytes([0x01]) + u16(len(speex_payload)) + speex_payload
        )  # attr id 0x01

        # App UUID attribute (id 0x03)
        app_uuid_attr = bytes([0x03]) + u16(16) + app_uuid.bytes

        # Header for SessionSetup command
        header = (
            bytes([0x01])  # Message ID: Session setup
            + u32(Flags.AppInitiated)  # flags (little-endian u32)
            + bytes([SessionType.Dictation])  # session type
            + u16(0x55)  # session id
            + bytes([0x02])  # number of attributes
        )

        expected = header + app_uuid_attr + speex_attr

        # Build the packet via the lib types (actual under-test serialization)
        attributes = [
            Attribute(data=AppUuid(uuid=app_uuid)),
            Attribute(
                data=SpeexEncoderInfo(
                    version="1.2rc1",
                    sample_rate=16000,
                    bit_rate=12800,
                    bitstream_version=4,
                    frame_size=320,
                )
            ),
        ]
        attr_list = AttributeList(dictionary=attributes)
        packet = VoiceControlCommand(
            flags=Flags.AppInitiated,
            data=SessionSetupCommand(
                session_type=SessionType.Dictation,
                session_id=0x55,
                attributes=attr_list,
            ),
        )

        self.assertEqual(expected, packet.serialise())

        # Parse round-trip checks
        cmd = VoiceControlCommand.parse(packet.serialise())[0]
        self.assertEqual(cmd.flags, Flags.AppInitiated)
        self.assertEqual(cmd.command, Command.SessionSetup)
        self.assertIsInstance(cmd.data, SessionSetupCommand)
        setup = cmd.data
        self.assertEqual(setup.session_type, SessionType.Dictation)
        self.assertEqual(setup.session_id, 0x55)
        self.assertEqual(setup.attributes.count, 2)
        attrs = setup.attributes.dictionary
        self.assertIsInstance(attrs[0].data, AppUuid)
        self.assertIsInstance(attrs[1].data, SpeexEncoderInfo)
        self.assertEqual(attrs[0].data.uuid, app_uuid)
        self.assertEqual(attrs[1].data.version, "1.2rc1")
        self.assertEqual(attrs[1].data.sample_rate, 16000)
        self.assertEqual(attrs[1].data.bit_rate, 12800)
        self.assertEqual(attrs[1].data.bitstream_version, 4)
        self.assertEqual(attrs[1].data.frame_size, 320)

    def test_session_setup_result(self):
        expected = (
            bytes([0x01])  # Message ID: Session setup
            + u32(Flags.AppInitiated)  # flags
            + bytes([SessionType.Dictation])
            + bytes([0x00])  # result success
        )

        msg = VoiceControlResult(
            flags=Flags.AppInitiated,
            data=SessionSetupResult(
                session_type=SessionType.Dictation, result=Result.Success
            ),
        )
        self.assertEqual(expected, msg.serialise())

    def test_transcription(self):
        # Build expected transcription bytes
        s1 = word_bytes(85, "Hello") + word_bytes(74, "computer")
        s2 = word_bytes(13, "hell") + word_bytes(3, "oh") + word_bytes(0, "computa")
        transcription_payload = (
            bytes([TranscriptionType.SentenceList])  # 0x01
            + bytes([2])  # sentence count
            + u16(2)
            + s1  # sentence #1 (2 words)
            + u16(3)
            + s2  # sentence #2 (3 words)
        )
        expected = transcription_payload

        t = Transcription(
            transcription=SentenceList(
                sentences=[
                    Sentence(
                        words=[
                            Word(confidence=85, data="Hello"),
                            Word(confidence=74, data="computer"),
                        ]
                    ),
                    Sentence(
                        words=[
                            Word(confidence=13, data="hell"),
                            Word(confidence=3, data="oh"),
                            Word(confidence=0, data="computa"),
                        ]
                    ),
                ]
            )
        )
        self.assertEqual(expected, t.serialise(default_endianness="<"))

    def test_dictation_result(self):
        app_uuid = uuid.uuid4()

        # Reuse the transcription payload from above
        s1 = word_bytes(85, "Hello") + word_bytes(74, "computer")
        s2 = word_bytes(13, "hell") + word_bytes(3, "oh") + word_bytes(0, "computa")
        transcription_payload = (
            bytes([TranscriptionType.SentenceList])  # 0x01
            + bytes([2])
            + u16(2)
            + s1
            + u16(3)
            + s2
        )

        # Attribute: App UUID (id 0x03)
        app_uuid_attr = bytes([0x03]) + u16(16) + app_uuid.bytes

        # Attribute: Transcription (id 0x02) with computed length
        transcription_attr = (
            bytes([0x02]) + u16(len(transcription_payload)) + transcription_payload
        )

        attributes = app_uuid_attr + transcription_attr

        expected = (
            bytes([0x02])  # Message ID: Dictation result
            + u32(Flags.AppInitiated)  # flags
            + u16(0x2211)  # session id (0x11,0x22 on wire LE in original test)
            + bytes([Result.Success])  # result
            + bytes([0x02])  # num attributes
            + attributes
        )

        t = Transcription(
            type=TranscriptionType.SentenceList,
            transcription=SentenceList(
                sentences=[
                    Sentence(
                        words=[
                            Word(confidence=85, data="Hello"),
                            Word(confidence=74, data="computer"),
                        ]
                    ),
                    Sentence(
                        words=[
                            Word(confidence=13, data="hell"),
                            Word(confidence=3, data="oh"),
                            Word(confidence=0, data="computa"),
                        ]
                    ),
                ]
            ),
        )
        attr_list = AttributeList(
            dictionary=[Attribute(data=AppUuid(uuid=app_uuid)), Attribute(data=t)]
        )
        msg = VoiceControlResult(
            flags=1,
            data=DictationResult(
                session_id=0x2211, result=Result.Success, attributes=attr_list
            ),
        )
        self.assertEqual(expected, msg.serialise())


if __name__ == "__main__":
    unittest.main()
