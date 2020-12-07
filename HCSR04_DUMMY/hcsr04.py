

class HCSR04:
    
    def __init__(self, TEST_PATH: str):
        # Reads 1st value in txt file to get mock value from
        with open(TEST_PATH) as f:
            self._mock_value = float(f.readline().split()[0])


    def measure_dist(self) -> float:
        return self._mock_value