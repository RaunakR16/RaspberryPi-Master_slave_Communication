import spidev
import RPi.GPIO as GPIO
import time
from image_packet_handler import decode_packets_to_image

# SPI Chip Select Pins (BCM numbering)
CS_PINS = [5, 6, 13, 19, 26]  # One for each slave

# SPI Setup
SPI_SPEED = 1000000  # 1 MHz
spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, Device 0
spi.max_speed_hz = SPI_SPEED
spi.mode = 0b00

# GPIO Setup
GPIO.setmode(GPIO.BCM)
for pin in CS_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

def send_command(slave_idx, command):
    """Send command to specific slave and get response"""
    GPIO.output(CS_PINS[slave_idx], GPIO.LOW)  # Select slave
    response = spi.xfer2([command])
    GPIO.output(CS_PINS[slave_idx], GPIO.HIGH)  # Deselect slave
    return response[0]

def receive_data(slave_idx, size):
    """Receive data from specific slave"""
    GPIO.output(CS_PINS[slave_idx], GPIO.LOW)
    data = spi.xfer2([0x00] * size)  # Dummy bytes to clock in data
    GPIO.output(CS_PINS[slave_idx], GPIO.HIGH)
    return bytes(data)

def capture_and_save_images():
    """Orchestrate image capture from all slaves"""
    packets = {}
    
    # Step 1: Broadcast capture command
    for slave_idx in range(5):
        status = send_command(slave_idx, 0x01)  # Capture command
        if status != 0x00:
            print(f"Slave {slave_idx} capture failed")
            return False
        print(f"Slave {slave_idx} capture initiated")
    
    # Step 2: Retrieve packets from each slave
    for slave_idx in range(5):
        # Get packet count
        send_command(slave_idx, 0x02)  # Request packet count
        count_data = receive_data(slave_idx, 2)
        total_packets = int.from_bytes(count_data, 'big')
        print(f"Slave {slave_idx} packets: {total_packets}")
        
        # Retrieve all packets
        packets[slave_idx] = []
        for pkt_idx in range(total_packets):
            send_command(slave_idx, 0x03)  # Request packet
            pkt_data = receive_data(slave_idx, 160)  # Max packet size
            packets[slave_idx].append({
                'id': slave_idx,
                'packet_index': pkt_idx,
                'data': pkt_data.decode('utf-8').strip('\x00')
            })
    
    # Step 3: Save images
    for slave_idx in range(5):
        image_path = decode_packets_to_image(packets[slave_idx], "received_images")
        print(f"Slave {slave_idx} image saved to {image_path}")
    
    return True

if __name__ == "__main__":
    print("Master ready. Type 'start' to begin capture:")
    if input().strip().lower() == 'start':
        print("Starting image capture...")
        if capture_and_save_images():
            print("All images saved successfully!")
    else:
        print("Aborted")
    spi.close()
    GPIO.cleanup()
