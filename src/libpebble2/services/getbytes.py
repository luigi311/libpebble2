__author__ = "katharine"

from array import array

from libpebble2.communication import PebbleConnection
from libpebble2.events.mixin import EventSourceMixin
from libpebble2.exceptions import GetBytesError
from libpebble2.protocol.transfers import (
    GetBytes,
    GetBytesCoredumpRequest,
    GetBytesDataResponse,
    GetBytesFileRequest,
    GetBytesFlashRequest,
    GetBytesInfoResponse,
    GetBytesUnreadCoredumpRequest,
)

__all__ = ["GetBytesService"]


class GetBytesService(EventSourceMixin):
    """
    Synchronously retrieves data from the watch over GetBytes.

    Args:
        pebble (PebbleConnection): The connection on which to operate.
    """

    def __init__(self, pebble: PebbleConnection) -> None:
        self._pebble = pebble
        self._txid = 0
        super().__init__()

    def get_coredump(self, require_fresh: bool = False) -> bytes:
        """
        Retrieves a coredump, if one exists.

        Args:
            require_fresh (bool): If ``True``, only retrieves a coredump if one has been generated
                since the last time this method was called. If ``False``, retrieves the most recent
                coredump, even if it has already been retrieved. Defaults to ``False``.

        Returns:
            bytes: The retrieved coredump data.

        Raises:
            GetBytesError: If the request fails or no coredump is available.
        """
        return self._get(
            GetBytesUnreadCoredumpRequest() if require_fresh else GetBytesCoredumpRequest(),
        )

    def get_file(self, filename: str) -> bytes:
        """
        Retrieves a PFS file from the watch. This only works on watches running non-release
        firmware.

        Args:
            filename (str): The path of the file to retrieve.

        Returns:
            bytes: The retrieved file

        Raises:
            GetBytesError: If the request fails.
        """
        return self._get(GetBytesFileRequest(filename=filename))

    def get_flash_region(self, offset: int, length: int) -> bytes:
        """
        Retrieves the contents of a region of flash from the watch. This only works on watches
        running non-release firmware.

        Returns:
            bytes: The retrieved flash region data

        Raises:
            GetBytesError: If the request fails.
        """
        return self._get(GetBytesFlashRequest(offset=offset, length=length))

    def _get(self, message: object) -> bytes:
        self._txid = txid = self._txid + 1

        queue = self._pebble.get_endpoint_queue(GetBytes)
        try:
            self._pebble.send_packet(GetBytes(transaction_id=txid, message=message))
            info = queue.get().message
            if not isinstance(info, GetBytesInfoResponse):
                raise GetBytesError(GetBytesInfoResponse.ErrorCode.MalformedRequest)

            if info.error_code != GetBytesInfoResponse.ErrorCode.Success:
                raise GetBytesError(info.error_code)

            # Allocate a mutable array large enough to contain the data
            data = array("B", (0 for _ in range(info.num_bytes)))

            bytes_received = 0
            while bytes_received < info.num_bytes:
                part = queue.get().message
                if not isinstance(part, GetBytesDataResponse):
                    raise GetBytesError(GetBytesInfoResponse.ErrorCode.MalformedRequest)
                bytes_received += len(part.data)

                # Insert the received chunk into our array.
                data[part.offset : part.offset + len(part.data)] = array("B", part.data)

            # Return the data as a more standard bytearray.
            return data.tobytes()
        finally:
            queue.close()
