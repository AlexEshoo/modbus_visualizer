import time
from queue import Queue, Empty
from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient
from pymodbus.pdu import ExceptionResponse
from pymodbus.exceptions import ConnectionException, ModbusIOException, ModbusException
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from visualizer.constants import MODBUS_EXCEPTION_CODES


def busy_work_reject(func):
    def wrapper(self, *args, **kwargs):
        if self.busy:
            return
        else:
            self.busy = True
            func(self, *args, **kwargs)
            self.busy = False

    return wrapper


class ModbusWorker(QObject):
    data_available = pyqtSignal(list)
    new_connection_available = pyqtSignal()
    console_message_available = pyqtSignal(str)
    polling_started = pyqtSignal()
    polling_finished = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.client = None
        self.busy = False

        self.poll_requests = Queue(maxsize=1)  # queue for incoming poll requests. limit to one poll at a time.
        self.write_requests = Queue()
        self.stop_polling = False  # Flag signal to stop polling.

    def is_busy(self):
        return self.busy

    @pyqtSlot(dict)
    @busy_work_reject
    def configure_client(self, settings):
        if self.client:
            self.client.close()  # Properly close the client when re-configuring. Needed for Serial.

        if settings["network_type"] is "tcp":
            host = settings["host"]
            port = settings["port"]
            self.client = ModbusTcpClient(host, port)
            self.console_message_available.emit(f"Attempting to connect to {host} on port {port}")

        elif settings["network_type"] is "serial":
            port = settings["port"]
            protocol = settings["protocol"]
            baudrate = settings["baudrate"]
            stop_bits = settings["stop_bits"]
            byte_size = settings["byte_size"]
            parity = settings["parity"]
            self.client = ModbusSerialClient(method=protocol,
                                             port=port,
                                             baudrate=baudrate,
                                             stopbits=stop_bits,
                                             bytesize=byte_size,
                                             parity=parity)
            self.console_message_available.emit(f"Attempting to connect to on port {port}")

        else:
            self.console_message_available.emit("Unknown Network Type")

        connected = self.client.connect()

        if connected:
            self.console_message_available.emit("Connection Successful")
        else:
            self.console_message_available.emit("Connection Failed")

    @pyqtSlot()
    def act_on_poll_request(self):
        self.polling_started.emit()

        try:
            req = self.poll_requests.get(timeout=1)  # Get the request out of the queue.
        except Empty:
            print("No request was found. This should never happen.")
            self.polling_finished.emit()
            return

        while self.busy:
            pass  # Wait for client to be configured if necessary

        try:
            function_code = req.get("function_code")
            start_register = req.get("start_register")
            length = req.get("length")
            poll_interval = req.get("interval", 0)
            poll_duration = req.get("duration", 0)
            # poll_sample_count = options.get("sample_count", None)  # TODO: Implement something like this.
        except KeyError:
            self.console_message_available.emit(f"Request badly formatted: {req}")
            self.polling_finished.emit()
            return

        timer = time.time()
        successful = 1
        retries = 0
        # TODO: This needs some review... Could have timing issues if poll_duration == 0 (default case)
        while time.time() - timer <= poll_duration and not self.stop_polling:
            start = time.time()

            data = self.get_modbus_data(function_code, start_register, length)
            self.data_available.emit(data)

            if data:
                retries = 0
                self.console_message_available.emit(f"Poll {successful} complete.")
                successful += 1
            else:
                successful = 0  # Reset successful counter?
                self.console_message_available.emit(f"Poll Failed. Retrying... {retries}")
                retries += 1

            while time.time() - start < poll_interval:  # Elapsed Time < Interval
                while not self.write_requests.empty():
                    wq = self.write_requests.get()
                    self.write_modbus_data(wq["function_code"], wq["start_register"], wq["values"])

                if self.stop_polling:
                    break

                time.sleep(0.01)  # Do we need this much accuracy on poll interval? Does it hurt?

        self.polling_finished.emit()
        self.stop_polling = False
        self.console_message_available.emit("Polling Stopped.")

    def get_modbus_data(self, function_code, start_reg, length):
        modbus_functions = {0x01: self.client.read_coils,
                            0x02: self.client.read_discrete_inputs,
                            0x04: self.client.read_input_registers,
                            0x03: self.client.read_holding_registers}

        try:
            rr = modbus_functions[function_code](start_reg, length)

        except KeyError:
            self.console_message_available.emit(f"Function code not supported: {function_code}")
            return []
        except ConnectionException:
            self.console_message_available.emit("Connection Failed.")
            return []

        # This works for TCP Exceptions
        if isinstance(rr, ExceptionResponse):
            code = rr.exception_code
            msg = MODBUS_EXCEPTION_CODES[code]
            self.console_message_available.emit(f"Modbus Error Code {code}: {msg}")
            return []

        # This works for Serial Exceptions
        elif isinstance(rr, ModbusException):
            self.console_message_available.emit(f"{str(rr)}")
            return []

        else:  # Response is ModbusResponse
            try:
                data = rr.registers  # For Input/Holding Register Responses
            except AttributeError:
                data = rr.bits[:length]  # For Coil/Discrete Input Responses

        return data

    def write_modbus_data(self, function_code, start_reg, values):
        modbus_functions = {0x15: self.client.write_coils,
                            0x16: self.client.write_registers}

        try:
            wr = modbus_functions[function_code](start_reg, values)
            print(wr)

        except ConnectionException:
            self.console_message_available.emit("Connection Failed.")
            return False

        # This works for TCP Exceptions
        if isinstance(wr, ExceptionResponse):
            code = wr.exception_code
            msg = MODBUS_EXCEPTION_CODES[code]
            self.console_message_available.emit(f"Modbus Error Code {code}: {msg}")
            return False

        # This works for Serial Exceptions
        elif isinstance(wr, ModbusException):
            self.console_message_available.emit(f"{str(wr)}")
            return False

        return True


    def shutdown(self):
        if self.client:
            self.client.close()
