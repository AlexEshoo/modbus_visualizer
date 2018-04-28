import sys
import time
from queue import Queue, Empty
from pymodbus.client.sync import ModbusTcpClient
from modbus_visualizer_gui import Ui_MainWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QLineEdit, QPushButton, QWidget
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt

_REGISTER_TYPE_TO_READ_FUNCTION_CODE = {"Coils": 0x01,
                                        "Discrete Inputs": 0x02,
                                        "Input Registers": 0x04,
                                        "Holding Registers": 0x03}


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

        self.poll_requests = Queue(maxsize=1)  # Make a queue for incoming poll requests. Should be limited to one
                                               # request at a time.
        self.stop_polling = False

    def isBusy(self):
        return self.busy

    @pyqtSlot(dict)
    @busy_work_reject
    def configure_client(self, settings):
        if settings["network_type"] is "tcp":
            host = settings["host"]
            port = settings["port"]
            self.client = ModbusTcpClient(host, port)

        elif settings["network_type"] is "rtu":
            ...
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
        iter = 1
        # TODO: This needs some review... Could have timing issues.
        # TODO: If the stop_polling attribute is set and the interval is long, the program will hang until next iter.
        # TODO: An interrupt of some kind should be used instead of this.
        while time.time() - timer <= poll_duration and not self.stop_polling:
            start = time.time()

            data = self.get_modbus_data(function_code, start_register, length)
            self.data_available.emit(data)

            elapsed = time.time() - start
            try:
                time.sleep(poll_interval - elapsed)
            except ValueError:
                time.sleep(poll_interval)

            self.console_message_available.emit(f"Poll {iter} complete.")
            iter += 1

        self.polling_finished.emit()
        self.stop_polling = False
        self.console_message_available.emit("Polling Stopped.")

    def get_modbus_data(self, function_code, start_reg, length):
        # TODO: Handle Modbus error codes properly.
        modbus_functions = {0x01: self.client.read_coils,
                            0x02: self.client.read_discrete_inputs,
                            0x04: self.client.read_input_registers,
                            0x03: self.client.read_holding_registers}

        try:
            rr = modbus_functions[function_code](start_reg, length)

        except KeyError:
            self.console_message_available.emit(f"Function code not supported: {function_code}")
            return []
        except Exception as e:  # Todo: Make this a real exception
            print(e)
            return []

        try:
            data = rr.registers
        except AttributeError:
            data = rr.bits[:length]

        return data


class VisualizerApp(Ui_MainWindow, QObject):

    modbus_settings_changed = pyqtSignal(dict)
    polling_settings_available = pyqtSignal(int, int, str)
    poll_request = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(main_window)

        self.worker_thread = QThread()
        self.worker = ModbusWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.connect_slots()
        self.init_poll_table()
        self.update_poll_table_column_headers()

        self.configure_modbus_client()

        self.new_network_settings_flag = False

    def connect_slots(self):
        # Connect all signals/slots
        # Note: Don't seem to need Qt.QueuedConnection for threaded events, but I put it there for show of good faith.

        self.singlePollPushButton.clicked.connect(self.single_poll)
        self.startPollingPushButton.clicked.connect(self.continuous_poll_begin)
        self.stopPollingPushButton.clicked.connect(self.stop_polling)
        self.startRegisterSpinBox.valueChanged.connect(self.update_poll_table_column_headers)

        self.modbus_settings_changed.connect(self.worker.configure_client, Qt.QueuedConnection)
        self.worker.console_message_available.connect(self.write_console, Qt.QueuedConnection)
        self.worker.data_available.connect(self.write_poll_table)
        self.poll_request.connect(self.worker.act_on_poll_request, Qt.QueuedConnection)

        # Disable buttons while polling, re-enable when polling complete
        for widget in self.pollingSettingsGroupBox.findChildren(QWidget):
            if widget.objectName() == "stopPollingPushButton":
                self.worker.polling_started.connect(lambda w=widget: w.setEnabled(True), Qt.QueuedConnection)
                self.worker.polling_finished.connect(lambda w=widget: w.setDisabled(True), Qt.QueuedConnection)
            else:
                self.worker.polling_finished.connect(lambda w=widget: w.setEnabled(True), Qt.QueuedConnection)
                self.worker.polling_started.connect(lambda w=widget: w.setDisabled(True), Qt.QueuedConnection)

        for line_edit in self.networkSettingsGroupBox.findChildren(QLineEdit):
            line_edit.textChanged.connect(self.set_new_network_settings_flag)

    @pyqtSlot()
    def set_new_network_settings_flag(self):
        self.new_network_settings_flag = True

    def init_poll_table(self):
        """
        Initialize the table with QTableWidgetItem objects that are empty strings.
        """
        num_rows = self.pollTable.rowCount()
        num_cols = self.pollTable.columnCount()

        for j in range(num_cols):
            for i in range(num_rows):
                self.pollTable.setItem(i, j, QTableWidgetItem(""))

    def update_poll_table_column_headers(self):
        self.clear_poll_table()  # Avoids confusion

        start = self.startRegisterSpinBox.value()
        num_cols = self.pollTable.columnCount()
        num_rows = self.pollTable.rowCount()

        for i in range(num_cols):
            self.pollTable.horizontalHeaderItem(i).setText(str(start + i * num_rows))

    def clear_poll_table(self):
        num_rows = self.pollTable.rowCount()
        num_cols = self.pollTable.columnCount()

        for j in range(num_cols):
            for i in range(num_rows):
                self.pollTable.item(i, j).setText("")

    @pyqtSlot(list)
    def write_poll_table(self, data):
        self.clear_poll_table()
        num_rows = self.pollTable.rowCount()

        cur_col = 0
        for i, datum in enumerate(data):
            self.pollTable.item(i % 10, cur_col).setText(str(datum))
            # self.pollTable.setItem(i % 10, cur_col, QTableWidgetItem(str(datum)))
            if (i + 1) % num_rows == 0:
                cur_col += 1

    @pyqtSlot()
    def configure_modbus_client(self):
        if not self.worker.isBusy():
            tcp_mode = self.tcpRadioButton.isChecked()
            rtu_mode = self.rtuRadioButton.isChecked()

            settings = {}
            if rtu_mode:
                pass
            elif tcp_mode:
                settings["network_type"] = "tcp"
                settings["host"] = self.tcpHostLineEdit.text()
                settings["port"] = self.tcpPortLineEdit.text()

            self.modbus_settings_changed.emit(settings)
            self.new_network_settings_flag = False  # only mark the network settings as applied when they are actually
                                                    # updated. We know this is true since this method checks
                                                    # worker.isBusy()
        else:
            self.write_console("Busy...")

    def single_poll(self):
        if self.worker.poll_requests.full():
            self.write_console("Queue is full")
            return

        if self.new_network_settings_flag:
            self.configure_modbus_client()  # Will initiate client update on threaded worker. BLOCKS!

        function_code = _REGISTER_TYPE_TO_READ_FUNCTION_CODE[self.registerTypeComboBox.currentText()]

        request = {
            "function_code": function_code,
            "start_register": self.startRegisterSpinBox.value(),
            "length": self.numberOfRegistersSpinBox.value()
        }

        self.worker.poll_requests.put(request)
        self.poll_request.emit()

    def continuous_poll_begin(self):
        if self.worker.poll_requests.full():
            self.write_console("Queue is full")
            return

        if self.new_network_settings_flag:
            self.configure_modbus_client()  # Will initiate client update on threaded worker. BLOCKS!

        function_code = _REGISTER_TYPE_TO_READ_FUNCTION_CODE[self.registerTypeComboBox.currentText()]

        request = {
            "function_code": function_code,
            "start_register": self.startRegisterSpinBox.value(),
            "length": self.numberOfRegistersSpinBox.value(),
            "duration": 9999999999999,  # TODO: Make this a real parameter.
            "interval": self.updateTimeSpinBox.value()
        }

        self.worker.poll_requests.put(request)
        self.poll_request.emit()

    def stop_polling(self):
        self.worker.stop_polling = True
        self.write_console("Stopping...")



    @pyqtSlot(str)
    def write_console(self, msg, *args, **kwargs):
        # self.consoleLineEdit.setText("")
        # time.sleep(0.05)  # Seems to be doing nothing now...
        self.consoleLineEdit.setText(msg)

    def exit(self):
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window_obj = QMainWindow()
    window = VisualizerApp(main_window_obj)
    main_window_obj.show()
    sys.exit(app.exec_())
