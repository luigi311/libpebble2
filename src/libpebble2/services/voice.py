__author__ = "andrews"

import logging
import uuid
from enum import IntEnum
from typing import TYPE_CHECKING

from libpebble2.events.mixin import EventSourceMixin
from libpebble2.protocol.audio import AudioStream, DataTransfer, StopTransfer
from libpebble2.protocol.voice import (
    AppUuid,
    Attribute,
    AttributeList,
    AttributeType,
    DictationResult,
    Flags,
    Sentence,
    SentenceList,
    SessionSetupCommand,
    SessionSetupResult,
    SessionType,
    Transcription,
    VoiceControlCommand,
    VoiceControlResult,
    Word,
)

if TYPE_CHECKING:
    from libpebble2.communication import PebbleConnection

__all__ = ["SetupResult", "TranscriptionResult", "VoiceService"]

logger = logging.getLogger("libpebble2.voice")


class SetupResult(IntEnum):
    Success = 0
    FailTimeout = 2
    FailDisabled = 5


class TranscriptionResult(IntEnum):
    Success = 0
    FailNoInternet = 1
    FailRecognizerError = 3
    FailSpeechNotRecognized = 4


class VoiceService(EventSourceMixin):
    """
    Service to expose voice control to external tools.

    :param pebble: The pebble with which to establish a voice session.
    :type pebble: .PebbleConnection
    """

    SESSION_ID_INVALID = 0

    def __init__(self, pebble: PebbleConnection) -> None:
        self._pebble = pebble
        self._session_id = VoiceService.SESSION_ID_INVALID
        self._subscriber = None
        self._session_id = VoiceService.SESSION_ID_INVALID
        self._encoder_info = None
        self._app_uuid = None

        self._pebble.register_endpoint(VoiceControlCommand, self._handle_voice_control)
        self._pebble.register_endpoint(AudioStream, self._handle_audio)

        EventSourceMixin.__init__(self)

    def _handle_voice_control(self, packet: VoiceControlCommand) -> None:
        if not isinstance(packet, VoiceControlCommand):
            msg = "Expected VoiceControlCommand packet"
            raise TypeError(msg)

        if isinstance(packet.data, SessionSetupCommand):
            self._handle_session_setup(packet.flags, packet.data)

    def _handle_session_setup(self, flags: int, message: SessionSetupCommand) -> None:
        if (
            (message.session_type != SessionType.Dictation)
            or (message.session_id == VoiceService.SESSION_ID_INVALID)
            or (message.attributes.is_empty())
            or (message.attributes.get_attribute(AttributeType.SpeexEncoderInfo) is None)
        ):
            return

        if self._session_id != VoiceService.SESSION_ID_INVALID:
            return

        app_initiated = flags & Flags.AppInitiated != 0
        app_uuid = message.attributes.get_attribute(AttributeType.AppUuid)
        app_uuid_present = app_uuid is not None
        if app_initiated != app_uuid_present:
            return

        self._app_uuid = app_uuid.uuid if app_uuid else None
        self._session_id = message.session_id
        self._encoder_info = message.attributes.get_attribute(
            AttributeType.SpeexEncoderInfo,
        )
        if self._encoder_info is None:
            return

        logger.debug(
            "Received session setup message " + f"from app {self._app_uuid}"
            if self._app_uuid
            else "",
        )
        self._broadcast_event("session_setup", self._app_uuid, self._encoder_info)

    def _handle_audio(self, packet: AudioStream) -> None:
        if not isinstance(packet, AudioStream):
            msg = "Expected AudioStream packet"
            raise TypeError(msg)

        if isinstance(packet.data, DataTransfer):
            self._handle_audio_frame(packet.session_id, packet.data)
        elif isinstance(packet.data, StopTransfer):
            self._handle_stop_transfer(packet.session_id)

    def _handle_audio_frame(self, session_id: int, frame_data: DataTransfer) -> None:
        if session_id != self._session_id:
            self.send_stop_audio(session_id)
        else:
            self._broadcast_event("audio_frame", self._session_id, frame_data)

    def _handle_stop_transfer(self, session_id: int) -> None:
        if session_id == self._session_id:
            self._broadcast_event("audio_stop")
            self._session_id = VoiceService.SESSION_ID_INVALID

    def send_stop_audio(self, session_id: int | None = None) -> None:
        """Stop an audio streaming session."""
        sid = session_id if session_id is not None else self._session_id
        if sid == self.SESSION_ID_INVALID:
            logger.debug("send_stop_audio: no active session; ignoring")
            return

        self._pebble.send_packet(AudioStream(session_id=sid, data=StopTransfer()))

    def send_session_setup_result(
        self,
        result: SetupResult,
        app_uuid: uuid.UUID | None = None,
    ) -> None:
        """
        Send the result of setting up a dictation session requested by the watch.

        :param result:  result of setting up the session
        :type result: .SetupResult
        :param app_uuid:uuid.UUID of app that initiated the session
        :type app_uuid:uuid.UUID
        """
        if self._session_id == VoiceService.SESSION_ID_INVALID:
            logger.debug("send_session_setup_result: no active session; ignoring")
            return

        if not isinstance(result, SetupResult):
            msg = "Expected SetupResult for result"
            raise TypeError(msg)

        flags = 0
        if app_uuid is not None:
            if not isinstance(app_uuid, uuid.UUID):
                msg = "Expected uuid.UUID for app_uuid"
                raise TypeError(msg)

            flags |= Flags.AppInitiated

        logger.debug(
            f"Sending session setup result (result={result}, app={app_uuid})"
            if app_uuid is not None
            else ")",
        )

        self._pebble.send_packet(
            VoiceControlResult(
                flags=flags,
                data=SessionSetupResult(session_type=SessionType.Dictation, result=result),
            )
        )

        if result != SetupResult.Success:
            self._session_id = VoiceService.SESSION_ID_INVALID

    def send_dictation_result(
        self,
        result: TranscriptionResult,
        sentences: list[list[str]] | None = None,
        app_uuid: uuid.UUID | None = None,
    ) -> None:
        """
        Send the result of a dictation session.

        :param result: Result of the session
        :type result: DictationResult
        :param sentences: list of sentences, each of which is a list of words and punctuation
        :param app_uuid: uuid.UUID of app that initiated the session
        :type app_uuid: uuid.UUID
        """
        if self._session_id == VoiceService.SESSION_ID_INVALID:
            logger.debug("send_dictation_result: no active session; ignoring")
            return

        if not isinstance(result, TranscriptionResult):
            msg = "Expected TranscriptionResult for result"
            raise TypeError(msg)

        transcription = None
        if result == TranscriptionResult.Success and sentences:
            s_list = []
            for s in sentences:
                words = [Word(confidence=100, data=w) for w in s]
                s_list.append(Sentence(words=words))
            transcription = Transcription(transcription=SentenceList(sentences=s_list))

        flags = 0
        if app_uuid is not None:
            if not isinstance(app_uuid, uuid.UUID):
                msg = "Expected uuid.UUID for app_uuid"
                raise TypeError(msg)

            flags |= Flags.AppInitiated

        attributes = []
        if app_uuid is not None:
            if not isinstance(app_uuid, uuid.UUID):
                msg = "Expected uuid.UUID for app_uuid"
                raise TypeError(msg)

            attributes.append(Attribute(id=AttributeType.AppUuid, data=AppUuid(uuid=app_uuid)))

        if transcription is not None:
            attributes.append(Attribute(id=AttributeType.Transcription, data=transcription))

        logger.debug(
            f"Sending dictation result (result={result}, app={app_uuid})"
            if app_uuid is not None
            else ")",
        )
        self._pebble.send_packet(
            VoiceControlResult(
                flags=flags,
                data=DictationResult(
                    session_id=self._session_id,
                    result=result,
                    attributes=AttributeList(dictionary=attributes),
                ),
            ),
        )
        self._session_id = VoiceService.SESSION_ID_INVALID
