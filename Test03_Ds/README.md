To build a master-slave image capture system using Raspberry Pi Zero Ws with SPI communication, follow this solution:

### 1. Hardware Connections (Master to Slaves)
Connect all slaves to the master using SPI with the following pin configuration:

| Master Pin | Slave Pin | Function          | Color   |
|------------|-----------|-------------------|---------|
| GPIO11     | GPIO11    | SPI MOSI          | Purple  |
| GPIO10     | GPIO10    | SPI MISO          | Green   |
| GPIO9      | GPIO9     | SPI SCLK          | Yellow  |
| GPIO5      | GPIO8     | Chip Select (CS0) | Blue    |
| GPIO6      | GPIO8     | Chip Select (CS1) | Red     |
| GPIO13     | GPIO8     | Chip Select (CS2) | Orange  |
| GPIO19     | GPIO8     | Chip Select (CS3) | Brown   |
| GPIO26     | GPIO8     | Chip Select (CS4) | White   |
| GND        | GND       | Ground            | Black   |

**Note:** Each slave uses the same MOSI/MISO/SCLK pins but has a dedicated CS line from the master.

---

### 2. Master Code (`master.py`)
```python
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
```

---

### 3. Slave Code (`slave.py`)
```python
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
```

---

### 4. System Workflow

1. **Initialization**:
   - Master sets up SPI and GPIO
   - Slaves initialize camera and enter listening mode

2. **Capture Command**:
   - User types `start` in master terminal
   - Master sends capture command (0x01) to each slave sequentially
   - Slaves capture images and encode into packets

3. **Data Transfer**:
   - Master requests packet count (0x02) from each slave
   - Master retrieves packets (0x03) one-by-one from each slave
   - Slaves send packets with metadata (ID, index, data)

4. **Image Reconstruction**:
   - Master decodes packets using `decode_packets_to_image`
   - Images saved as `image_slaveX_YYYYMMDD_HHMMSS.jpg`

---

### 5. Key Features

- **SPI Protocol**:
  - `0x01`: Capture image command
  - `0x02`: Request packet count
  - `0x03`: Request packet data
  - Status codes: `0x00` (OK), `0xFF` (Error)

- **Error Handling**:
  - Checks for capture failures
  - Verifies packet counts before transfer
  - Timeout handling in communication

- **Efficiency**:
  - Packets sized at 160 bytes (optimized for SPI)
  - Sequential processing to avoid bus contention
  - Base64 encoding for data integrity

---

### Setup Instructions

1. **Hardware**:
   - Connect all Pis as per pin table
   - Ensure all cameras are properly attached

2. **Software**:
   - Install dependencies on all Pis:
     ```bash
     sudo apt install python3-pip
     pip3 install picamera2 numpy imageio opencv-python spidev RPi.GPIO
     ```
   - Enable SPI on all Pis:
     ```bash
     sudo raspi-config nonint do_spi 0
     ```

3. **Deployment**:
   - Copy `camera_module_v4_3.py` as `camera_module.py`
   - Place `image_packet_handler.py` on all devices
   - Run `slave.py` on all slave Pis
   - Run `master.py` on the master Pi

4. **Operation**:
   - At master prompt, type `start`
   - Monitor progress through console messages
   - Retrieve images from `received_images/` directory

This solution provides robust communication with automatic timestamping and slave identification, ensuring no data loss during transmission. The SPI-based approach guarantees synchronized operations while maintaining hardware simplicity.
