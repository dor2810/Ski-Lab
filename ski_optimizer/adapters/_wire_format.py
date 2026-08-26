"""
Minimal hand-rolled protobuf wire-format primitives -- shared by every
adapter that has to build an opaque Google URL param with no public
.proto schema to generate from (google_hotels_adapter.py's `ts`,
google_flights_adapter.py's booking-page `tfs`/`tfu`). Generic
varint/tag/length-delimited encoding only, nothing endpoint-specific --
each adapter assembles its own message shape by calling these.
"""


def varint(n: int) -> bytes:
    # Protobuf varints are unsigned. A negative n never reaches 0 via
    # `n >>= 7` (Python ints are infinite-precision two's complement --
    # right-shifting a negative value stays negative forever), so this
    # would hang instead of encoding garbage. Caught in code review:
    # reachable from _build_ts's night-count field if a caller ever
    # passes checkout_date <= checkin_date.
    if n < 0:
        raise ValueError(f"varint() requires a non-negative value, got {n}")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def tag(field_num: int, wire_type: int) -> bytes:
    return varint((field_num << 3) | wire_type)


def field_varint(field_num: int, value: int) -> bytes:
    return tag(field_num, 0) + varint(value)


def field_bytes(field_num: int, data: bytes) -> bytes:
    return tag(field_num, 2) + varint(len(data)) + data


def field_str(field_num: int, s: str) -> bytes:
    return field_bytes(field_num, s.encode("utf-8"))
