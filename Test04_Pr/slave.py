import json
from camera_module import CameraModule
from image_packet_handler import encode_image_to_packets
import SPIslave  # Custom SPI slave driver

SLAVE_ID = 0  # Unique for each slave (0-4)
device = SPIslave.SPIslave(device='/dev/spislave0')
cam = CameraModule()
packets = []

def capture_image():
    global packets
    img_bytes = cam.capture_image(byte_image=True)
    packets = encode_image_to_packets(img_bytes, SLAVE_ID)

# Main SPI command loop
while True:
    command = device.read(1)[0]
    
    if command == 0x01:  # Capture command
        capture_image()
        device.write([0x01])  # ACK
        
    elif command == 0x02:  # Status request
        status = 0x01 if packets else 0x00  # 1=ready, 0=busy
        device.write([status])
        
    elif command == 0x03:  # Packet request
        if packets:
            packet_str = json.dumps(packets.pop(0))
            device.write(packet_str.encode('utf-8').ljust(200, b'\x00'))
        else:
            device.write(b'\x00' * 200)  # End signal
