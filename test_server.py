import time
import threading
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from pymodbus.client.sync import ModbusTcpClient

from pymodbus.payload import BinaryPayloadBuilder

import logging

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def run_server():



    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [17] * 1000),
        co=ModbusSequentialDataBlock(0, [False] * 1000),
        hr=ModbusSequentialDataBlock(0, [0]*1000),
        ir=ModbusSequentialDataBlock(0, [0]*1000))
    context = ModbusServerContext(slaves=store, single=True)

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
    identity.ProductName = 'Pymodbus Server'
    identity.ModelName = 'Pymodbus Server'
    identity.MajorMinorRevision = '1.0'

    StartTcpServer(context, identity=identity, address=("localhost", 5020))


if __name__ == "__main__":
    th = threading.Thread(target=run_server)
    th.start()

    client = ModbusTcpClient("127.0.0.1", 5020)

    # The following all represent the same value in different byte and word orders.
    # In float it should be 6.000121593475342
    # In Unsigned Long it should be 1086324991
    # In Signed Long it should be 1086324991
    # By changing the byte and word order settings in the application, should be able to verify that data conversion
    # is working properly.
    BEBW = [0x40C0, 0x00FF]
    BELW = [0x00FF, 0x40C0]
    LEBW = [0xC040, 0xFF00]
    LELW = [0xFF00, 0xC040]

    registers = BEBW + BELW + LEBW + LELW
    print(registers)

    client.write_registers(0,registers)

    # Makes registers 8-108 constantly cycle from 1 to 100
    while True:
        for i in range(100):
            client.write_registers(8,[i]*100)
            time.sleep(1)