"""
Mock serial port
Reads from TEST_PATH from mock weight value
"""

class Serial:
    def __init__(self, TEST_PATH):
        # Reads 1st value from TEST_PATH to use as mock weight value
        with open(TEST_PATH) as f:
            self._mock_value = f.readline().split()[0]

    def readline(self)-> bytes:
        return bytes(self._mock_value, 'utf-8')