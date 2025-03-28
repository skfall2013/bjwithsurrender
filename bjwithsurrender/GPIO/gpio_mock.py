# gpio_mock.py
class MockGPIO:
    OUT = 'OUT'
    IN = 'IN'
    HIGH = 1
    LOW = 0

    @classmethod
    def setmode(cls, mode):
        print(f"[MOCK GPIO] Mode set to {mode}")

    @classmethod
    def setup(cls, pin, mode):
        print(f"[MOCK GPIO] Pin {pin} set as {mode}")

    @classmethod
    def output(cls, pin, state):
        state_str = 'HIGH' if state == cls.HIGH else 'LOW'
        print(f"[MOCK GPIO] Pin {pin} set to {state_str}")

    @classmethod
    def input(cls, pin):
        # Mock always returns LOW for simplicity
        return cls.LOW

    @classmethod
    def cleanup(cls):
        print("[MOCK GPIO] Cleanup called. Resetting pins...")

    # Add the trigger_command function mirroring the one in gpio.py
    @classmethod
    def trigger_command(cls, command, duration=0.5):
        """
        Mock trigger a blackjack command by activating the corresponding GPIO pin

        Args:
            command (str): The blackjack command to trigger
            duration (float): How long to keep the signal high in seconds
        """
        # Define command pins mapping (same as in gpio.py)
        command_pins = {
            "hit": 17,
            "stand": 18,
            "rebet": 18,  # Same as STAND pin
            "double": 22,
            "split": 23,
            "deal": 23,  # Same as SPLIT pin
            "surrender": 24
        }

        if command.lower() in command_pins:
            pin = command_pins[command.lower()]
            print(f"[MOCK GPIO] Executing command: {command.upper()}")

            # Simulate turning the pin on
            cls.output(pin, cls.HIGH)
            # Simulate waiting
            print(f"[MOCK GPIO] Waiting for {duration} seconds")
            # Simulate turning the pin off
            cls.output(pin, cls.LOW)

            # Special cases for shared pins
            if command.lower() == "rebet":
                print("[MOCK GPIO] REBET command uses the same pin as STAND")
            elif command.lower() == "deal":
                print("[MOCK GPIO] DEAL command uses the same pin as SPLIT")
        else:
            print(f"[MOCK GPIO] Unknown command: {command}")