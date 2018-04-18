import sys
from pymodbus.client.sync import ModbusTcpClient
from modbus_visualizer_gui import Ui_MainWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem


class VisualizerApp(Ui_MainWindow):
    def __init__(self, main_window):
        self.setupUi(main_window)

        self.connect_slots()
        self.init_poll_table()
        self.update_poll_table_column_headers()

        self.client = ModbusTcpClient("127.0.0.1", 5020)

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
        start = self.startRegisterSpinBox.value()
        num_cols = self.pollTable.columnCount()
        num_rows = self.pollTable.rowCount()

        for i in range(num_cols):
            self.pollTable.horizontalHeaderItem(i).setText(str(start + i*num_rows))


    def clear_poll_table(self):
        num_rows = self.pollTable.rowCount()
        num_cols = self.pollTable.columnCount()

        for j in range(num_cols):
            for i in range(num_rows):
                self.pollTable.item(i, j).setText("")

    def write_poll_table(self, data):
        self.clear_poll_table()
        num_rows = self.pollTable.rowCount()

        cur_col = 0
        for i, datum in enumerate(data):
            self.pollTable.item(i % 10, cur_col).setText(str(datum))
            #self.pollTable.setItem(i % 10, cur_col, QTableWidgetItem(str(datum)))
            if (i + 1) % num_rows == 0:
                cur_col += 1

    def single_poll(self):
        data = self.poll_modbus_data()
        self.write_poll_table(data)

    def poll_modbus_data(self):
        start = self.startRegisterSpinBox.value()
        length = self.numberOfRegistersSpinBox.value()

        rr = self.client.read_holding_registers(start, length)

        return rr.registers

    def exit(self):
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window_obj = QMainWindow()
    window = VisualizerApp(main_window_obj)
    main_window_obj.show()
    sys.exit(app.exec_())