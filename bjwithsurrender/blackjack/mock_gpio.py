# mock_gpio.py
class MockGPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    IN = 'IN'
    HIGH = 1
    LOW = 0

    def __init__(self):
        self.mode = None
        self.pins = {}

    def setmode(self, mode):
        self.mode = mode
        print(f"[MOCK GPIO] Mode set to {mode}")

    def setup(self, pin, mode):
        self.pins[pin] = {'mode': mode, 'state': self.LOW}
        print(f"[MOCK GPIO] Pin {pin} set as {mode}")

    def output(self, pin, state):
        if pin in self.pins:
            self.pins[pin]['state'] = state
            state_str = 'HIGH' if state == self.HIGH else 'LOW'
            print(f"[MOCK GPIO] Pin {pin} set to {state_str}")
        else:
            print(f"[MOCK GPIO] Warning: Pin {pin} not initialized")

    def input(self, pin):
        return self.pins.get(pin, {}).get('state', self.LOW)

    def cleanup(self):
        print("[MOCK GPIO] Cleanup called. Resetting pins...")
        self.pins.clear()
