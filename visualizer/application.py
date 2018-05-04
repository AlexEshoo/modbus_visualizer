from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QLineEdit, QWidget

from visualizer.gui_main_window import Ui_MainWindow
from visualizer.modbus_worker import ModbusWorker
from visualizer.constants import REGISTER_TYPE_TO_READ_FUNCTION_CODE, STRUCT_DATA_TYPE, ENDIANNESS, RADIX
from visualizer.utils import format_data


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
        dtype = STRUCT_DATA_TYPE[self.dataTypeComboBox.currentText()]
        byte_order = ENDIANNESS[self.byteEndianessComboBox.currentText()]
        word_order = ENDIANNESS[self.wordEndianessComboBox.currentText()]
        base = RADIX[self.numberBaseComboBox.currentText()]

        if self.registerTypeComboBox.currentText() in ("Holding Registers", "Input Registers"):
            formatted = format_data(data, dtype, byte_order=byte_order, word_order=word_order, base=base)
        else:
            formatted = [ str(i) for i in data ]  # make bools into strings.

        for i, datum in enumerate(formatted):
            self.pollTable.item(i % 10, cur_col).setText(datum)
            # self.pollTable.setItem(i % 10, cur_col, QTableWidgetItem(str(datum)))
            if (i + 1) % num_rows == 0:
                cur_col += 1

    @pyqtSlot()
    def configure_modbus_client(self):
        if not self.worker.is_busy():
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

            # only mark the network settings as applied when they are actually
            # updated. We know this is true since this method checks worker.is_busy()
            self.new_network_settings_flag = False

        else:
            self.write_console("Busy...")

    def single_poll(self):
        if self.worker.poll_requests.full():
            self.write_console("Queue is full")
            return

        if self.new_network_settings_flag:
            self.configure_modbus_client()  # Will initiate client update on threaded worker. BLOCKS!

        function_code = REGISTER_TYPE_TO_READ_FUNCTION_CODE[self.registerTypeComboBox.currentText()]

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

        function_code = REGISTER_TYPE_TO_READ_FUNCTION_CODE[self.registerTypeComboBox.currentText()]

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
    def write_console(self, msg):
        # self.consoleLineEdit.setText("")
        # time.sleep(0.05)  # Seems to be doing nothing now...
        self.consoleLineEdit.setText(msg)

    @staticmethod
    def exit():
        QApplication.quit()
