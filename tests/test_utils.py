import struct
from visualizer.utils import format_data

def _test_single_float():
    # Verification for -3.001957

    print("All should print: -3.0019569396972656")
    d = struct.pack('B' * 4, *[0xC0, 0x40, 0x20, 0x10])  # Big Endian, Big Word Order
    print("DATA", d)

    # BE, BW
    BEBW = [(d[0] << 8) + d[1], (d[2] << 8) + d[3]]
    result = format_data(BEBW, 'f', byte_order=">", word_order='>')
    print("BEBW Result:", result)

    # LE, BW
    LEBW = [(d[1] << 8) + d[0], (d[3] << 8) + d[2]]
    result = format_data(LEBW, 'f', byte_order='<', word_order='>')
    print("LEBW Result:", result)

    # BE, LW
    BELW = [(d[2] << 8) + d[3], (d[0] << 8) + d[1]]
    result = format_data(BELW, 'f', byte_order='>', word_order='<')
    print("BELW Result:", result)

    # LE, LW
    LELW = [(d[3] << 8) + d[2], (d[1] << 8) + d[0]]
    result = format_data(LELW, 'f', byte_order='<', word_order='<')
    print("LELW Result:", result)

def _test_multiple_floats():
    print("All should print: -3.0019569396972656, 2.251983642578125")
    d = struct.pack('B' * 8, *[0xC0, 0x40, 0x20, 0x10, 0x40, 0x10, 0x20, 0x80])  # Big Endian, Big Word Order
    print("DATA", d)

    # BE, BW
    BEBW = [(d[0] << 8) + d[1], (d[2] << 8) + d[3], (d[4] << 8) + d[5], (d[6] << 8) + d[7]]
    result = format_data(BEBW, 'f', byte_order=">", word_order='>')
    print("BEBW Result:", result)

    # LE, BW
    LEBW = [(d[1] << 8) + d[0], (d[3] << 8) + d[2], (d[5] << 8) + d[4], (d[7] << 8) + d[6]]
    result = format_data(LEBW, 'f', byte_order='<', word_order='>')
    print("LEBW Result:", result)

    # BE, LW
    BELW = [(d[2] << 8) + d[3], (d[0] << 8) + d[1], (d[6] << 8) + d[7], (d[4] << 8) + d[5]]
    result = format_data(BELW, 'f', byte_order='>', word_order='<')
    print("BELW Result:", result)

    # LE, LW
    LELW = [(d[3] << 8) + d[2], (d[1] << 8) + d[0], (d[7] << 8) + d[6], (d[5] << 8) + d[4]]
    result = format_data(LELW, 'f', byte_order='<', word_order='<')
    print("LELW Result:", result)

def _test_segmented_data_float():
    print("All should print: -3.0019569396972656")
    d = struct.pack('B' * 6, *[0xC0, 0x40, 0x20, 0x10, 0x01, 0x02])  # Big Endian, Big Word Order
    print("DATA", d)

    # BE, BW
    BEBW = [(d[0] << 8) + d[1], (d[2] << 8) + d[3], (d[4] << 8) + d[5]]
    result = format_data(BEBW, 'f', byte_order=">", word_order='>')
    print("BEBW Result:", result)

    # LE, BW
    LEBW = [(d[1] << 8) + d[0], (d[3] << 8) + d[2], (d[5] << 8) + d[4]]
    result = format_data(LEBW, 'f', byte_order='<', word_order='>')
    print("LEBW Result:", result)

    # BE, LW
    BELW = [(d[2] << 8) + d[3], (d[0] << 8) + d[1], (d[4] << 8) + d[5]]
    result = format_data(BELW, 'f', byte_order='>', word_order='<')
    print("BELW Result:", result)

    # LE, LW
    LELW = [(d[3] << 8) + d[2], (d[1] << 8) + d[0], (d[5] << 8) + d[4]]
    result = format_data(LELW, 'f', byte_order='<', word_order='<')
    print("LELW Result:", result)

def _test_multiple_uint16():
    print("All should print: [49216, 8208]")
    d = struct.pack('B' * 4, *[0xC0, 0x40, 0x20, 0x10])  # Big Endian, Big Word Order
    print("DATA", d)

    # BE
    BE = [(d[0] << 8) + d[1], (d[2] << 8) + d[3]]
    result = format_data(BE, 'H', byte_order=">")
    print("BE Result:", result)

    # LE
    LE = [(d[1] << 8) + d[0], (d[3] << 8) + d[2]]
    result = format_data(LE, 'H', byte_order='<')
    print("LE Result:", result)

def _test_multiple_int16():
    print("All should print: [513, -2]")
    d = struct.pack('B' * 4, *[0x02, 0x01, 0xFF, 0xFE])  # Big Endian, Big Word Order
    print("DATA", d)

    # BE
    BE = [(d[0] << 8) + d[1], (d[2] << 8) + d[3]]
    result = format_data(BE, 'h', byte_order=">")
    print("BE Result:", result)

    # LE
    LE = [(d[1] << 8) + d[0], (d[3] << 8) + d[2]]
    result = format_data(LE, 'h', byte_order='<')
    print("LE Result:", result)

def _test_single_uint32():
    print("All should print: 33685502")
    d = struct.pack('B' * 4, *[0x02, 0x01, 0xFF, 0xFE])  # Big Endian, Big Word Order
    print("DATA", d)

    # BE, BW
    BEBW = [(d[0] << 8) + d[1], (d[2] << 8) + d[3]]
    result = format_data(BEBW, 'L', byte_order=">", word_order='>')
    print("BEBW Result:", result)

    # LE, BW
    LEBW = [(d[1] << 8) + d[0], (d[3] << 8) + d[2]]
    result = format_data(LEBW, 'L', byte_order='<', word_order='>')
    print("LEBW Result:", result)

    # BE, LW
    BELW = [(d[2] << 8) + d[3], (d[0] << 8) + d[1]]
    result = format_data(BELW, 'L', byte_order='>', word_order='<')
    print("BELW Result:", result)

    # LE, LW
    LELW = [(d[3] << 8) + d[2], (d[1] << 8) + d[0]]
    result = format_data(LELW, 'L', byte_order='<', word_order='<')
    print("LELW Result:", result)

if __name__ == '__main__':

    _test_single_float()
    print("\n")
    _test_multiple_floats()
    print("\n")
    _test_segmented_data_float()
    print("\n")
    _test_multiple_uint16()
    print('\n')
    _test_multiple_int16()
    print('\n')
    _test_single_uint32()