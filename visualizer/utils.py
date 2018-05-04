import struct
from pymodbus.payload import BinaryPayloadDecoder, Endian

def format_data(data, dtype:str, byte_order=">", word_order=">", base=10):
    raw_byte_str = struct.pack(byte_order + 'H'*len(data), *data)
    print("raw", raw_byte_str)

    size = struct.calcsize(dtype)
    stub = len(raw_byte_str) % size

    if stub > 0:
        byte_str = raw_byte_str[:-stub]  # lop off any segmented data that wont fit in target datatype
    else:
        byte_str = raw_byte_str[:]

    print("original byte_str", byte_str)

    if word_order == "<":
        byte_str = b"".join([ byte_str[i:i+2][::-1] for i in range(0,len(byte_str),2) ])

    fmt_len = len(byte_str) // size
    result = struct.unpack(word_order + dtype*fmt_len, byte_str)

    print("final byte_Str", byte_str)

    return result

if __name__ == '__main__':

    # Verification for -3.001957
    d = struct.pack('B'*4, *[0xC0, 0x40, 0x20, 0x10])  # Big Endian, Big Word Order
    print("DATA", d)
    print('\n')

    # BE, BW
    BEBW = [ (d[0] << 8) + d[1], (d[2] << 8) + d[3] ]
    result = format_data(BEBW, 'f', byte_order=">", word_order='>')
    print("BEBW Result:", result)
    print('\n')

    # LE, BW
    LEBW = [ (d[1] << 8) + d[0], (d[3] << 8) + d[2] ]
    result = format_data(LEBW, 'f', byte_order='<', word_order='>')
    print("LEBW Result:", result)
    print('\n')

    # BE, LW
    BELW = [(d[2] << 8) + d[3], (d[0] << 8) + d[1]]
    result = format_data(BELW, 'f', byte_order='>', word_order='<')
    print("BELW Result:", result)
    print('\n')

    # LE, LW
    LELW = [(d[3] << 8) + d[2], (d[1] << 8) + d[0]]
    result = format_data(LELW, 'f', byte_order='<', word_order='<')
    print("LELW Result:", result)
