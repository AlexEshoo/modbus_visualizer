MODBUS_EXCEPTION_CODES = {1: "Illegal Function",
                          2: "Illegal Data Access",
                          3: "Illegal Data Value",
                          4: "Slave Device Failure",
                          5: "Acknowledge",
                          6: "Slave Device Busy",
                          7: "Negative Acknowledge",
                          8: "Memory Parity Error",
                          # There is no 9 apparently.
                          10: "Gateway Path Unavailable",
                          11: "Gateway Target Device Failed to Respond"}

REGISTER_TYPE_TO_READ_FUNCTION_CODE = {"Coils": 0x01,
                                       "Discrete Inputs": 0x02,
                                       "Input Registers": 0x04,
                                       "Holding Registers": 0x03}