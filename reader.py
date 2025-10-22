import serial
import time
import re
from commands import build_power_command, build_antenna_command, re_RF_power

class CF816Reader:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        self.tag_counts = {}

    def extract_eids(self, response):
        response_hex = response.hex()
        return re.findall(r"e280[0-9a-f]{20}", response_hex)

    def send_and_receive_once(self, port_num):
        """Send antenna command and receive response"""
        command = build_antenna_command(port_num)
        self.ser.write(command)
        time.sleep(0.1)
        response = self.ser.read(self.ser.in_waiting or 4096)
        return self.extract_eids(response)

    def set_rf_power(self, power_level):
        try:
            power_cmd = build_power_command(power_level)
            print(f"Setting power to {power_level} dBm: {power_cmd.hex()}")
            
            self.ser.write(power_cmd)
            time.sleep(0.2)
            
            response = self.ser.read(6)
            if response == re_RF_power:
                return True
            print(f"Unexpected response: {response.hex() if response else 'None'}")
            return False
        except Exception as e:
            print(f"Power setting error: {str(e)}")
            return False

    def close(self):
        self.ser.close()