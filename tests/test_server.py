import argparse
import time
import threading
import sys
from pymodbus.server.sync import StartTcpServer, StartSerialServer, \
    ModbusAsciiFramer, ModbusRtuFramer, ModbusBinaryFramer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
import logging

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server-type", default="tcp", choices=["tcp", "serial"], type=str.lower)
parser.add_argument("-i", "--ip", default="127.0.0.1", type=str)
parser.add_argument("-p", "--tcp-port", default=5020, type=int)
parser.add_argument("-f", "--framer", default="rtu", choices=["rtu", "ascii", "binary"], type=str.lower)
parser.add_argument("-c", "--com-port", default=None, type=str)
parser.add_argument("--stop-bits", default=1, choices=[1,2], type=int)
parser.add_argument("--byte-size", default=8, choices=[5,6,7,8], type=int)
parser.add_argument("-b", "--baud-rate", default=19200, type=int)
parser.add_argument("-u", "--unit-id", default=None, type=int, choices=range(256))
args = parser.parse_args()

FRAMER = {"rtu": ModbusRtuFramer,
          "ascii": ModbusAsciiFramer,
          "binary": ModbusBinaryFramer}

def register_updater(ctxt):
    increment = 0

    while True:
        ctxt[slave_id].setValues(0x03, 0x00, [increment])

        if increment == 65535:
            increment = 0
        else:
            increment += 1

        time.sleep(1)


slave_id = args.unit_id

store = ModbusSlaveContext(
    di=ModbusSequentialDataBlock(0, [17] * 1000),
    co=ModbusSequentialDataBlock(0, [False] * 1000),
    hr=ModbusSequentialDataBlock(0, [0]*1000),
    ir=ModbusSequentialDataBlock(0, [0]*1000))
if args.unit_id:
    slaves_dict = {args.unit_id: store}
    context = ModbusServerContext(slaves=slaves_dict, single=False)
else:
    context = ModbusServerContext(slaves=store, single=True)

identity = ModbusDeviceIdentification()
identity.VendorName = 'Pymodbus'
identity.ProductCode = 'PM'
identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
identity.ProductName = 'Pymodbus Server'
identity.ModelName = 'Pymodbus Server'
identity.MajorMinorRevision = '1.0'

# The following all represent the same value in different byte and word orders.
# In float it should be 42.125
# In Unsigned Long it should be 0x42288000 (1109950464)
# In Signed Long it should be the same, but the BELW representation is a negative number.
# By changing the byte and word order settings in the application, should be able to verify that data conversion
# is working properly.
# TODO: 0x8000 is displayed as -32768 in signed short format. This may not follow the spec for the datatype.
BEBW = [0x4228, 0x8000]
BELW = [0x8000, 0x4228]
LEBW = [0x2842, 0x0080]
LELW = [0x0080, 0x2842]

registers = BEBW + BELW + LEBW + LELW
context[slave_id].setValues(0x04, 0x00, registers)  # Sets holding registers (fx=3), start address 0x00 with registers.
context[slave_id].setValues(0x03, 0x01, [0xFFFF, 0xABCD])


update_thread = threading.Thread(target=register_updater ,args=(context,))
update_thread.start()

if args.server_type.lower() == "tcp":
    StartTcpServer(context, identity=identity, address=(args.ip, args.tcp_port))
elif args.server_type.lower() == "serial":
    if not args.com_port:
        print("Please provide the COM port with --com-port.")
        sys.exit(0)

    StartSerialServer(context, identity=identity,
                      framer=FRAMER[args.framer],
                      port=args.com_port,
                      stopbits=args.stop_bits,
                      bytesize=args.byte_size,
                      baudrate=args.baud_rate,
                      timeout = 0.1)
else:
    print("Something went wrong.")
