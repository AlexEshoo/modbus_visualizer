import sys
import time
from pymodbus.client.sync import ModbusTcpClient
from modbus_visualizer_gui import Ui_MainWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class ModbusWorker(QObject):
    """
    Possibe for use with movetoThread.
    """

    data_available = pyqtSignal(list)
    new_connection_available = pyqtSignal()
    console_message_available = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.client = None
        self.busy = False  # todo: maybe a decorator for this would be nice?

    def isBusy(self):
        return self.busy

    @pyqtSlot(dict)
    def configure_client(self, settings):
        self.busy = True
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
            self.new_connection_available.emit()
            self.console_message_available.emit("Connection Successful")
        else:
            self.console_message_available.emit("Connection Failed")

        self.busy = False

    @pyqtSlot(int, int, str)
    def poll(self, start_reg, length, register_type):
        data = self.get_modbus_data(start_reg, length, register_type)
        self.data_available.emit(data)

    def get_modbus_data(self, start_reg, length, register_type):
        if register_type == "Coils":
            rr = self.client.read_coils(start_reg, length)
            data = rr.bits[:length]

        elif register_type == "Discrete Inputs":
            rr = self.client.read_discrete_inputs(start_reg, length)
            data = rr.bits[:length]

        elif register_type == "Input Registers":
            rr = self.client.read_input_registers(start_reg, length)
            data = rr.registers

        elif register_type == "Holding Registers":
            rr = self.client.read_holding_registers(start_reg, length)
            data = rr.registers

        else:
            self.console_message_available.emit("Register Type Unknown")
            data = []

        return data


class VisualizerApp(Ui_MainWindow, QObject):

    modbus_settings_changed = pyqtSignal(dict)
    polling_settings_available = pyqtSignal(int, int, str)

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

    def connect_slots(self):
        self.singlePollPushButton.clicked.connect(self.single_poll)
        self.startRegisterSpinBox.valueChanged.connect(self.update_poll_table_column_headers)

        self.modbus_settings_changed.connect(self.worker.configure_client)
        self.worker.console_message_available.connect(self.write_console)
        self.worker.new_connection_available.connect(self.poll_modbus_data)
        self.polling_settings_available.connect(self.worker.poll)
        self.worker.data_available.connect(self.write_poll_table)

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

    @pyqtSlot(list)  # Works without this. Not sure why this breaks it. Fails to Connect the method for some reason...
    def write_poll_table(self, data):
        self.clear_poll_table()
        num_rows = self.pollTable.rowCount()

        cur_col = 0
        for i, datum in enumerate(data):
            self.pollTable.item(i % 10, cur_col).setText(str(datum))
            # self.pollTable.setItem(i % 10, cur_col, QTableWidgetItem(str(datum)))
            if (i + 1) % num_rows == 0:
                cur_col += 1

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
        else:
            self.write_console("Busy...")

    def single_poll(self):
        self.configure_modbus_client()
        # Not an ideal control sequence.
        # This starts a sequence of events that are emitted to call subsequent functions.
        # This can be structured better. Or at least named better.

    @pyqtSlot()
    def poll_modbus_data(self):

        start = self.startRegisterSpinBox.value()
        length = self.numberOfRegistersSpinBox.value()
        register_type = self.registerTypeComboBox.currentText()

        self.polling_settings_available.emit(start, length, register_type)

    @pyqtSlot(str)
    def write_console(self, msg, *args, **kwargs):
        self.consoleLineEdit.setText("")
        time.sleep(0.05)  # Seems to be doing nothing now...
        self.consoleLineEdit.setText(msg)

    def exit(self):
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window_obj = QMainWindow()
    window = VisualizerApp(main_window_obj)
    main_window_obj.show()
    sys.exit(app.exec_())
