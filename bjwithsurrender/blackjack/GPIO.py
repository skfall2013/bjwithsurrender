try:
    import RPi.GPIO as GPIO
except (ImportError, ModuleNotFoundError):
    from mock_gpio import MockGPIO as GPIO

import time

# Set up GPIO using BCM numbering scheme
GPIO.setmode(GPIO.BCM)

# Define GPIO pins for each command
HIT_PIN = 17
STAND_REBET_PIN = 18  # This pin is used for both STAND and REBET
DOUBLE_DOWN_PIN = 22
SPLIT_DEAL_PIN = 23  # This pin is used for both SPLIT and DEAL
SURRENDER_PIN = 24

# Set up all pins as outputs
command_pins = {
    "hit": HIT_PIN,
    "stand": STAND_REBET_PIN,
    "rebet": STAND_REBET_PIN,  # Same as STAND pin
    "double": DOUBLE_DOWN_PIN,
    "split": SPLIT_DEAL_PIN,
    "deal": SPLIT_DEAL_PIN,  # Same as SPLIT pin
    "surrender": SURRENDER_PIN
}

# Initialize all pins as outputs and set them to LOW (off)
for pin in set(command_pins.values()):
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


def trigger_command(command, duration=0.5):
    """
    Trigger a blackjack command by activating the corresponding GPIO pin

    Args:
        command (str): The blackjack command to trigger
        duration (float): How long to keep the signal high in seconds
    """
    if command.lower() in command_pins:
        pin = command_pins[command.lower()]
        print(f"Executing command: {command.upper()}")

        # Turn the pin on
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(duration)  # Keep it on for the specified duration

        # Turn the pin off
        GPIO.output(pin, GPIO.LOW)

        # Special cases for shared pins
        if command.lower() == "rebet":
            print("REBET command uses the same pin as STAND")
        elif command.lower() == "deal":
            print("DEAL command uses the same pin as SPLIT")
    else:
        print(f"Unknown command: {command}")


try:
    print("Blackjack GPIO Control - Enter commands or 'exit' to quit")
    print("Available commands: HIT, STAND, DOUBLE, SPLIT, DEAL, SURRENDER, REBET")

    while True:
        command = input("Enter command: ").lower()

        if command == "exit":
            break
        elif command in command_pins:
            trigger_command(command)
        else:
            print("Invalid command. Available commands: HIT, STAND, DOUBLE, SPLIT, DEAL, SURRENDER, REBET")

finally:
    # Clean up GPIO on exit
    GPIO.cleanup()
    print("GPIO cleanup complete")