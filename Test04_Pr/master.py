import spidev
import time
from image_packet_handler import decode_packets_to_image

# SPI initialization
spi_buses = {
    0: {  # SPI0
        'bus': 0,
        'devices': {
            0: {'ce': 0},  # Slave 0
            1: {'ce': 1}   # Slave 1
        }
    },
    1: {  # SPI1
        'bus': 1,
        'devices': {
            0: {'ce': 0},  # Slave 2
            1: {'ce': 1},  # Slave 3
            2: {'ce': 2}   # Slave 4
        }
    }
}

# Initialize SPI connections
spi_connections = {}
for bus_num, bus in spi_buses.items():
    for device_num, device in bus['devices'].items():
        spi = spidev.SpiDev()
        spi.open(bus_num, device['ce'])
        spi.max_speed_hz = 1000000  # 1 MHz
        spi_connections[f"bus{bus_num}_ce{device['ce']}"] = spi

def send_command(spi, command):
    """Send command to slave and get response"""
    response = spi.xfer2([command])
    return response[0]

def capture_images():
    """Broadcast capture command to all slaves"""
    for spi in spi_connections.values():
        send_command(spi, 0x01)  # Capture command

def check_slave_ready(spi):
    """Poll slave until ready"""
    while True:
        status = send_command(spi, 0x02)  # Status command
        if status == 0x01:  # Ready status
            return True
        time.sleep(0.1)

def receive_image_packets(spi, slave_id):
    """Receive all packets from a slave"""
    packets = []
    packet_index = 0
    
    while True:
        # Request packet
        send_command(spi, 0x03)  # Request command
        # Receive packet (dummy transfer to read data)
        data = spi.xfer2([0x00] * 200)
        packet_str = bytes(data).decode('utf-8').rstrip('\x00')
        
        if not packet_str:  # End of packets
            break
            
        packets.append(json.loads(packet_str))
        packet_index += 1
    
    # Reconstruct image
    image_path = decode_packets_to_image(packets)
    print(f"Image from Slave {slave_id} saved to {image_path}")

# Main workflow
if __name__ == "__main__":
    print("Enter 'start' to begin image capture:")
    if input().strip().lower() == 'start':
        # Broadcast capture command
        capture_images()
        
        # Wait for all slaves to be ready
        for slave_id, spi in enumerate(spi_connections.values()):
            check_slave_ready(spi)
        
        # Receive images sequentially
        for slave_id, spi in enumerate(spi_connections.values()):
            receive_image_packets(spi, slave_id)
        
        print("All images received successfully")
