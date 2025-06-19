import spidev
import RPi.GPIO as GPIO
import time
from camera_module import CameraModule
from image_packet_handler import encode_image_to_packets

# SPI Setup
SPI_CS = 8  # Chip Select Pin (BCM)
spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, Device 0
spi.max_speed_hz = 1000000
spi.mode = 0b00

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(SPI_CS, GPIO.OUT)
GPIO.output(SPI_CS, GPIO.HIGH)

# Camera Setup
camera = CameraModule()
packets = []
total_packets = 0

def process_command(command):
    """Handle commands from master"""
    global packets, total_packets
    
    if command == 0x01:  # Capture image
        img_bytes = camera.capture_image()
        packets = encode_image_to_packets(img_bytes, slave_id=0)
        total_packets = len(packets)
        return 0x00  # Success
    
    elif command == 0x02:  # Send packet count
        return total_packets.to_bytes(2, 'big')
    
    elif command == 0x03:  # Send packet
        if not packets:
            return b'\x00' * 160
        pkt = packets.pop(0)
        return pkt['data'].encode('utf-8').ljust(160, b'\x00')
    
    return 0xFF  # Unknown command

def slave_loop():
    """Main slave listening loop"""
    while True:
        if GPIO.input(SPI_CS) == GPIO.LOW:
            command = spi.xfer2([0x00])[0]  # Read command byte
            response = process_command(command)
            
            if isinstance(response, int):
                spi.xfer2([response])
            else:
                spi.xfer2(list(response))
        
        time.sleep(0.01)

if __name__ == "__main__":
    try:
        slave_loop()
    except KeyboardInterrupt:
        camera.close()
        spi.close()
        GPIO.cleanup()
