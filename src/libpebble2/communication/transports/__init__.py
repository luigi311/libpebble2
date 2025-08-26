__author__ = "katharine"

from abc import ABCMeta, abstractmethod

from libpebble2.protocol.base import PebblePacket


class MessageTarget:
    """A base class representing the target of a message, either to or from the watch."""
    def __repr__(self) -> str:
        return type(self).__name__ + "()"


class MessageTargetWatch(MessageTarget):
    """Indicates that the message is directed at or from the watch itself."""


class BaseTransport(metaclass=ABCMeta):
    """Base class for all transports."""
    # default for transports that don't need the phone-app handshake
    must_initialise = False

    @property
    def connected(self) -> bool:
        """:return: ``True`` if the transport is currently connected; otherwise ``False``."""
        return False

    @abstractmethod
    def connect(self) -> None:
        """
        Synchronously connect to the Pebble. Once this method returns, libpebble2 should be able
        to safely send messages to the connected Pebble.

        Ordinarily, this method should only be called by :class:`.PebbleConnection`.
        """

    @abstractmethod
    def read_packet(self) -> tuple[MessageTarget, bytes | PebblePacket]:
        """
        Synchronously read a message. This message could be from the Pebble(in which case it will
        be a :class:`PebblePacket`), or it could be from the transport, in which case the result
        is transport-defined. The origin of the result is indicated by the
        returned :class:`MessageTarget`.

        :return: (:class:`MessageTarget`, :type bytes or
            :class:`libpebble2.protocol.base.PebblePacket`)
        """

    @abstractmethod
    def send_packet(
        self,
        message: PebblePacket | bytes | bytearray | memoryview,
        target: MessageTarget | None = None,
    ) -> None:
        """
        Send a message. This message could be to the Pebble (in which case it must be a
        :class:`PebblePacket`), or to the transport (in which case the message type is
        transport-defined).

        :param message: Message to send.
        :type message: PebblePacket
        :param target: Target for the message
        :type target: MessageTarget
        """

    def disconnect(self) -> None:
        """Transports may implement graceful shutdown; default is no-op."""
        return
