PRESET_VALUE = 0xFFFF
POLYNOMIAL = 0x8408

def calculate_crc(data: bytes) -> bytes:
    """Calculate CRC16 (Kermit) and return LSB, MSB bytes"""
    crc = PRESET_VALUE
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ POLYNOMIAL
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

def build_power_command(power_dbm: int) -> bytes:
    """Build power command (05 00 2F PP) where PP is power level"""
    if not 10 <= power_dbm <= 33:
        raise ValueError("Power level must be between 10 and 33 dBm")
    frame = bytes([0x05, 0x00, 0x2F, power_dbm])
    return frame + calculate_crc(frame)

def build_antenna_command(port: int) -> bytes:
    """Build antenna command (09 00 01 00 00 00 8P 0A) where P is port-1"""
    if not 1 <= port <= 8:
        raise ValueError("Port must be between 1 and 8")
    frame = bytes([0x09, 0x00, 0x01, 0x00, 0x00, 0x00, 0x80 + port - 1, 0x0A])
    return frame + calculate_crc(frame)

# Pre-built response
re_RF_power = bytes([0x05, 0x00, 0x2F, 0x00]) + calculate_crc(bytes([0x05, 0x00, 0x2F, 0x00]))
