#!/usr/bin/env python3
"""Generate a 100% synthetic .fit fixture for fit_ingest smoke tests.

No athlete data — no GPS, no real timestamps, synthetic power ramp. Encodes
a minimal FIT file: a file_id message + 60 record messages. Re-run after any
change: py -3 tests/fixtures/make_sample_fit.py
"""
import os
import struct

# Standard FIT CRC-16 nibble table.
_CRC_TABLE = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
              0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]


def _crc16(data):
    crc = 0
    for byte in data:
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[byte & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc & 0xFFFF


def build_fit():
    body = bytearray()
    # file_id definition (local type 0, global msg 0), 1 field: type (enum).
    body += bytes([0x40, 0x00, 0x00])
    body += struct.pack("<H", 0)
    body += bytes([1])
    body += bytes([0, 1, 0x00])
    # file_id data: type = 4 (activity).
    body += bytes([0x00, 4])
    # record definition (local type 1, global msg 20), 4 fields.
    body += bytes([0x41, 0x00, 0x00])
    body += struct.pack("<H", 20)
    body += bytes([4])
    body += bytes([253, 4, 0x86])  # timestamp  uint32
    body += bytes([7,   2, 0x84])  # power      uint16
    body += bytes([3,   1, 0x02])  # heart_rate uint8
    body += bytes([4,   1, 0x02])  # cadence    uint8
    # 60 synthetic record data messages.
    base_ts = 1000000000  # arbitrary synthetic FIT timestamp (not a real date)
    for i in range(60):
        body += bytes([0x01])
        body += struct.pack("<I", base_ts + i)
        body += struct.pack("<H", 180 + i)  # synthetic 180-239W ramp
        body += bytes([140, 90])            # fixed HR 140, cadence 90
    # 14-byte header: size, protocol 2.0, profile version, data size, ".FIT", CRC.
    header = bytearray([14, 0x20])
    header += struct.pack("<H", 2100)
    header += struct.pack("<I", len(body))
    header += b".FIT"
    header += struct.pack("<H", _crc16(bytes(header)))
    full = bytes(header) + bytes(body)
    return full + struct.pack("<H", _crc16(full))


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_ride.fit")
    with open(out, "wb") as f:
        f.write(build_fit())
    print(f"Wrote {out} ({os.path.getsize(out)} bytes)")
