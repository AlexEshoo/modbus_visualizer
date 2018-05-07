from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QLineEdit, QWidget, QComboBox, QSpinBox, QDoubleSpinBox

from visualizer.gui_main_window import Ui_MainWindow
from visualizer.modbus_worker import ModbusWorker
from visualizer.constants import REGISTER_TYPE_TO_READ_FUNCTION_CODE, STRUCT_DATA_TYPE, ENDIANNESS, RADIX
from visualizer.utils import format_data, serial_ports


class VisualizerApp(Ui_MainWindow, QObject):

    modbus_settings_changed = pyqtSignal(dict)
    polling_settings_available = pyqtSignal(int, int, str)
    poll_request = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(main_window)

        self.new_network_settings_flag = False
        self.current_table_data = []
        self.console_message_number = 0

        self.worker_thread = QThread()
        self.worker = ModbusWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.connect_slots()
        self.init_poll_table()
        self.update_poll_table_column_headers()
        self.configure_modbus_client()
        self.update_display_settings_options()
        self.init_serial_com_port_combo_box()

    def connect_slots(self):
        # Connect all signals/slots
        # Note: Don't seem to need Qt.QueuedConnection for threaded events, but I put it there for show of good faith.

        self.singlePollPushButton.clicked.connect(self.single_poll)
        self.startPollingPushButton.clicked.connect(self.continuous_poll_begin)
        self.stopPollingPushButton.clicked.connect(self.stop_polling)
        self.startRegisterSpinBox.valueChanged.connect(self.update_poll_table_column_headers)
        self.registerTypeComboBox.currentTextChanged.connect(lambda: self.clear_poll_table(clear_data=True))

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

        # Connect Display Settings Functions
        for cbox in self.displaySettingsGroupBox.findChildren(QComboBox):
            cbox.currentTextChanged.connect(self.update_display_settings_options)

        self.registerTypeComboBox.currentTextChanged.connect(self.update_display_settings_options)

        for widget in self.networkSettingsGroupBox.findChildren(QWidget):
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self.set_new_network_settings_flag)
            if isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self.set_new_network_settings_flag)
            if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                widget.valueChanged.connect(self.set_new_network_settings_flag)

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

    def init_serial_com_port_combo_box(self):
        com_ports = serial_ports()
        self.serialPortComboBox.insertItems(0, com_ports)

    def update_poll_table_column_headers(self):
        self.clear_poll_table()  # Avoids confusion

        start = self.startRegisterSpinBox.value()
        num_cols = self.pollTable.columnCount()
        num_rows = self.pollTable.rowCount()

        for i in range(num_cols):
            self.pollTable.horizontalHeaderItem(i).setText(str(start + i * num_rows))

    def clear_poll_table(self, clear_data=False):
        num_rows = self.pollTable.rowCount()
        num_cols = self.pollTable.columnCount()

        for j in range(num_cols):
            for i in range(num_rows):
                self.pollTable.item(i, j).setText("")
        if clear_data:
            self.current_table_data = []

    @pyqtSlot(list)
    def write_poll_table(self, data):
        self.current_table_data = data
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
            serial_mode = self.serialRadioButton.isChecked()

            settings = {}
            if serial_mode:
                settings["network_type"] = "serial"
                settings["port"] = self.serialPortComboBox.currentText()
                settings["protocol"] = self.serialProtocolComboBox.currentText().lower()
                settings["baudrate"] = self.serialBaudRateSpinBox.value()
                settings["stop_bits"] = int(self.serialStopBitsComboBox.currentText())
                settings["byte_size"] = int(self.serialByteSizeComboBox.currentText())
                settings["parity"] = self.serialParityComboBox.currentText()[0]  # Only uses first capital letter.
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
        MAX_LINES = 500
        current_text_lines = self.consoleTextEdit.toPlainText().split('\n')
        number_of_lines = len(current_text_lines)

        if number_of_lines > MAX_LINES:
            self.consoleTextEdit.setPlainText('\n'.join(current_text_lines[1:]))  # Rewrite all but the first line.

        # Using `insertPlainText` on `self.consoleTextEdit` uses a different cursor which starts at the end of it's
        # known document. After the `setPlainText` method is called, that cursor doesnt move, hence why we need a
        # new cursor to write at the end of the document.
        cursor = self.consoleTextEdit.textCursor()
        cursor.movePosition(cursor.End)
        self.consoleTextEdit.setTextCursor(cursor)
        cursor.insertText("\n" + f"({self.console_message_number}): " + msg)

        self.consoleTextEdit.ensureCursorVisible()  # Auto scroll to bottom
        self.console_message_number += 1

    def update_display_settings_options(self):
        if self.registerTypeComboBox.currentText() in ("Coils", "Discrete Inputs"):
            self.displaySettingsGroupBox.setDisabled(True)
            return
        else:
            self.displaySettingsGroupBox.setEnabled(True)

        dtype = STRUCT_DATA_TYPE[self.dataTypeComboBox.currentText()]
        if dtype == 'f':
            self.numberBaseComboBox.setDisabled(True)  # Disable number base selection when using float.
            self.numberBaseComboBox.blockSignals(True)  # Prevent application from making another call to this function
            i = self.numberBaseComboBox.findText("Decimal")
            self.numberBaseComboBox.setCurrentIndex(i)  # Change selected base to Decimal
            self.numberBaseComboBox.blockSignals(False)  # Re-Allow signals from numberBaseComboBox
        else:
            self.numberBaseComboBox.setEnabled(True)

        if dtype in ('H', 'h'):
            self.wordEndianessComboBox.setDisabled(True)
        else:
            self.wordEndianessComboBox.setEnabled(True)

        self.write_poll_table(self.current_table_data)  # Write the table again with the updated display settings.

    @staticmethod
    def exit():
        QApplication.quit()
