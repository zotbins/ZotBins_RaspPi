"""
Ultrasonic HC-SR04 Sensor Driver
Reads from TEST_PATH for mock value
"""

class HCSR04:
    
    def __init__(self, TEST_PATH: str):
        # Reads 2nd value in txt file to get mock value from
        with open(TEST_PATH) as f:
            self._mock_value = float(f.readline().split()[1])


    def measure_dist(self) -> float:
        return self._mock_value