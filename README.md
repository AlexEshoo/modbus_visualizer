# modbus_visualizer

## Current Features
* Modbus TCP support
* Single and Continuous Polling of registers
* Data display settings including:
    * Data type
    * Radix
    * Byte and Word Endianness
* Modbus Error Response Handling

## Future Features
* Modbus RTU support (ascii too?)
* Writing Registers
* Logging to File
* Zero mode (1 or 0 index for registers)
* Full register address display (show what the full register number is)
* Read Device information metadata
* Unit ID Support
* Settings save to and load from file.

## Developing

### Install dependencies
1. Clone the repository and checkout the develop branch (default)
1. Install dependencies with `pip install -r requirements.txt` (can be in virtualenv)
1. Install `pyqt5-tools` Global or user python installation (not virtualenv)

### Editing the `.ui` files
To edit the `.ui` files navigate to where `pyqt5-tools` installed and launch `designer.exe`. Open the `.ui` file in 
QtDesigner and edit it. Save it in the `ui_files` directory. Generate the related python file using the `pyuic5` command 
(part of `pyqt5-tools`). Example:
```bash
pyuic5 ./ui_files/modbus_visualizer.ui > ./visualizer/gui_main_window.py
```

### Running
Run the program: `python main.py`

For testing the server without a live modbus server or serial modbus device, run the testserver `python test_server.py`.