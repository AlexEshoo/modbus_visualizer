import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from visualizer.application import VisualizerApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window_obj = QMainWindow()
    window = VisualizerApp(main_window_obj)
    main_window_obj.show()
    sys.exit(app.exec_())
