import sys
import time
import threading
from pymodbus.client.sync import ModbusTcpClient
from modbus_visualizer_gui import Ui_MainWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot


class PollingThread(QThread):

    finished = pyqtSignal(list)

    def __init__(self, modbus, start, length, register_type):
        super().__init__()

        self.client = modbus
        self.start_reg = start
        self.length = length
        self.register_type = register_type
        print("Starting polling thread")
        self.start()

    def run(self):
        print("running polling")
        print(f"{self.register_type}, {self.start_reg}, {self.length}, {self.client}")

        if self.register_type == "Coils":
            try:
                print("reading coils")
                rr = self.client.read_coils(self.start_reg, self.length)
                print(rr)
                data = rr.bits[:self.length]
                print(data)
            except Exception as e:
                print(e)


        elif self.register_type == "Discrete Inputs":
            rr = self.client.read_discrete_inputs(self.start_reg, self.length)
            data = rr.bits[:self.length]

        elif self.register_type == "Input Registers":
            rr = self.client.read_input_registers(self.start_reg, self.length)
            data = rr.registers

        elif self.register_type == "Holding Registers":
            rr = self.client.read_holding_registers(self.start_reg, self.length)
            data = rr.registers

        else:
            self.write_console("Unknown Register Type.")
            data = []

        print(f"will emit: {data}")

        self.finished.emit(data)



class VisualizerApp(Ui_MainWindow):
    def __init__(self, main_window):
        self.setupUi(main_window)

        self.connect_slots()
        self.init_poll_table()
        self.update_poll_table_column_headers()

        self.configure_modbus_client()

        self.connected = False
        self.polling = False
        self.poll_thread = None

    def connect_slots(self):
        self.singlePollPushButton.clicked.connect(self.single_poll)
        self.startRegisterSpinBox.valueChanged.connect(self.update_poll_table_column_headers)

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

    #@pyqtSlot(list)  # Works without this. Not sure why this breaks it. Fails to Connect the method for some reason...
    def write_poll_table(self, data):
        print("made it here")
        self.clear_poll_table()
        num_rows = self.pollTable.rowCount()

        cur_col = 0
        for i, datum in enumerate(data):
            self.pollTable.item(i % 10, cur_col).setText(str(datum))
            # self.pollTable.setItem(i % 10, cur_col, QTableWidgetItem(str(datum)))
            if (i + 1) % num_rows == 0:
                cur_col += 1

    def configure_modbus_client(self):
        tcp_mode = self.tcpRadioButton.isChecked()
        rtu_mode = self.rtuRadioButton.isChecked()

        if rtu_mode:
            pass
        elif tcp_mode:
            host = self.tcpHostLineEdit.text()
            port = self.tcpPortLineEdit.text()
            self.client = ModbusTcpClient(host, port)

        self.connected = self.client.connect()

        if not self.connected:
            self.write_console("Could not connect.")

        else:
            self.write_console("Connection Successful.")

    def single_poll(self):
        # data = self.poll_modbus_data()
        self.configure_modbus_client()
        data = []
        if self.connected:
            start = self.startRegisterSpinBox.value()
            length = self.numberOfRegistersSpinBox.value()
            register_type = self.registerTypeComboBox.currentText()
            self.poll_thread = PollingThread(self.client, start, length, register_type)
            try:
                result = self.poll_thread.finished.connect(self.write_poll_table)  # Causing issues.
            except Exception as e:
                print(e)


        if data:
            self.write_console("Poll Successful")

    def poll_modbus_data(self):
        self.configure_modbus_client()

        if not self.connected:
            return []

        start = self.startRegisterSpinBox.value()
        length = self.numberOfRegistersSpinBox.value()
        register_type = self.registerTypeComboBox.currentText()

        if register_type == "Coils":
            rr = self.client.read_coils(start, length)
            data = rr.bits[:length]

        elif register_type == "Discrete Inputs":
            rr = self.client.read_discrete_inputs(start, length)
            data = rr.bits[:length]

        elif register_type == "Input Registers":
            rr = self.client.read_input_registers(start, length)
            data = rr.registers

        elif register_type == "Holding Registers":
            rr = self.client.read_holding_registers(start, length)
            data = rr.registers

        else:
            self.write_console("Unknown Register Type.")
            data = []

        return data

    #@threaded
    def write_console(self, msg, *args, **kwargs):
        self.consoleLineEdit.setText("")
        time.sleep(0.05)
        self.consoleLineEdit.setText(msg)

    def exit(self):
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window_obj = QMainWindow()
    window = VisualizerApp(main_window_obj)
    main_window_obj.show()
    sys.exit(app.exec_())
