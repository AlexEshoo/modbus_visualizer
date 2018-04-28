import time
import threading
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from pymodbus.client.sync import ModbusTcpClient

import logging

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def run_server():
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [17] * 1000),
        co=ModbusSequentialDataBlock(0, [False] * 1000),
        hr=ModbusSequentialDataBlock(0, [17] * 1000),
        ir=ModbusSequentialDataBlock(0, [17] * 1000))
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

    while True:
        for i in range(100):
            client.write_registers(0,[i]*100)
            time.sleep(1)