import array

CRC_POLY: int = 0x04C11DB7


def process_word(data: bytes, crc: int = 0xFFFFFFFF) -> int:
    """
    Processes a 4-byte word and computes the CRC32 value.

    Args:
        data (bytes): A byte array of length 4.
        crc (int): The initial CRC value. Default is 0xFFFFFFFF.

    Returns:
        int: The updated CRC32 value.
    """
    if len(data) < 4:
        d_array = array.array("B", data)
        for _x in range(4 - len(data)):
            d_array.insert(0, 0)
        d_array.reverse()
        data = d_array.tobytes()

    d = array.array("I", data)[0]
    crc = crc ^ d

    for _i in range(32):
        crc = crc << 1 ^ CRC_POLY if crc & 2147483648 != 0 else crc << 1

    return crc & 0xFFFFFFFF


def process_buffer(buf: bytes, c: int = 0xFFFFFFFF) -> int:
    """
    Processes a buffer of bytes and computes the CRC32 value.

    Args:
        buf (bytes): The input byte buffer.
        c (int): The initial CRC value. Default is 0xFFFFFFFF.

    Returns:
        int: The computed CRC32 value.
    """
    word_count = len(buf) // 4
    if len(buf) % 4 != 0:
        word_count += 1

    crc = c
    for i in range(word_count):
        crc = process_word(buf[i * 4 : (i + 1) * 4], crc)
    return crc


def crc32(data: bytes) -> int:
    """
    Computes the CRC32 checksum for the given data.

    Args:
        data (bytes): The input byte data.

    Returns:
        int: The computed CRC32 checksum.
    """
    return process_buffer(data)
