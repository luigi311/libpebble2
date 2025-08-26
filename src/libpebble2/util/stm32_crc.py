from __future__ import division

import array

CRC_POLY = 0x04C11DB7


def process_word(data, crc=0xFFFFFFFF):
    if len(data) < 4:
        d_array = array.array("B", data)
        for x in range(0, 4 - len(data)):
            d_array.insert(0, 0)
        d_array.reverse()
        data = d_array.tobytes()

    d = array.array("I", data)[0]
    crc = crc ^ d

    for i in range(0, 32):
        if (crc & 0x80000000) != 0:
            crc = (crc << 1) ^ CRC_POLY
        else:
            crc = crc << 1

    result = crc & 0xFFFFFFFF
    return result


def process_buffer(buf, c=0xFFFFFFFF):
    word_count = len(buf) // 4
    if len(buf) % 4 != 0:
        word_count += 1

    crc = c
    for i in range(0, word_count):
        crc = process_word(buf[i * 4 : (i + 1) * 4], crc)
    return crc


def crc32(data):
    return process_buffer(data)
