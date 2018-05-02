import struct


def format_data(data, dtype:str, byte_order=">", word_order=">", base=10):
    raw_byte_str = b""
    for d in data:
        byte = struct.pack('H', d)
        raw_byte_str += byte

    size = struct.calcsize(dtype)

    stub = len(raw_byte_str) % size
    print(size, stub)
    if stub > 0:
        byte_str = raw_byte_str[:-stub]  # lop off any segmented data that wont fit in target datatype
    else:
        byte_str = raw_byte_str[:]

    fmt_len = len(byte_str) // size
    result = struct.unpack(byte_order + dtype*fmt_len, byte_str)

    print("raw", raw_byte_str)
    print("new", byte_str)
    print("fmt_len", fmt_len)

    return result

if __name__ == '__main__':
    data = [0b1010111000010100, 0b0100001000101001]  # SHould be ~42.42 in float. (little endian)
    print(data)

    thing = format_data(data, "f", byte_order='<')
    print(thing)

