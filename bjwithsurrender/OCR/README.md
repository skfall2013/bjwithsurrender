```bash
sudo apt-get update
sudo apt install python3-dev -y
sudo apt-get install python3-rpi.gpio

#Test it after install:
python3 -c "import RPi.GPIO as sGPIO; print(GPIO.VERSION)"