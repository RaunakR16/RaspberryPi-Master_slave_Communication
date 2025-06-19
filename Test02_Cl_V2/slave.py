# ==============================
# FIXED SLAVE CONTROLLER CODE
# ==============================
import time
import spidev
import RPi.GPIO as GPIO
import json
from camera_module_v4_3 import CameraModule
from image_packet_handler import encode_image_to_packets

# === SET THIS PER SLAVE ===
SLAVE_ID = 1  # Change this per device (1 to 5)
TRIGGER_GPIO = 27  # Shared input pin from master's trigger (GPIO 22)

# SPI Setup - IMPORTANT: Each slave needs different CS pins!
# Slave 1: (0,0), Slave 2: (0,1), Slave 3: (1,0), etc.
SPI_BUS = 0  # Adjust based on slave ID
SPI_CS = 0   # Adjust based on slave ID

spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_CS)
spi.max_speed_hz = 500000  # Match master speed
spi.mode = 0

# Camera setup
camera = CameraModule()

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIGGER_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Global variable to store captured image
captured_image = None
packets_ready = False

def wait_for_trigger():
    global captured_image, packets_ready
    
    print(f"[Slave {SLAVE_ID}] Waiting for capture trigger from master...")
    GPIO.wait_for_edge(TRIGGER_GPIO, GPIO.RISING, timeout=30000)  # 30 second timeout
    print(f"[Slave {SLAVE_ID}] Trigger received! Capturing image...")
    
    # Capture image
    try:
        captured_image = camera.capture_image(apply_color_correction=True, byte_image=True)
        if captured_image:
            print(f"[Slave {SLAVE_ID}] Image captured successfully ({len(captured_image)} bytes)")
            packets_ready = True
        else:
            print(f"[Slave {SLAVE_ID}] Image capture failed.")
            packets_ready = False
            
    except Exception as e:
        print(f"[Slave {SLAVE_ID}] Error capturing image: {e}")
        packets_ready = False

def handle_spi_communication():
    global captured_image, packets_ready
    
    if not packets_ready or captured_image is None:
        print(f"[Slave {SLAVE_ID}] No image ready to send")
        # Send 0 packets
        try:
            response = spi.xfer2([0])
            print(f"[Slave {SLAVE_ID}] Sent 0 packet count")
        except Exception as e:
            print(f"[Slave {SLAVE_ID}] Error sending packet count: {e}")
        return
    
    try:
        # Encode image to packets
        packets = encode_image_to_packets(captured_image, SLAVE_ID)
        total_packets = len(packets)
        
        print(f"[Slave {SLAVE_ID}] Prepared {total_packets} packets")
        
        # Wait for master to request packet count
        print(f"[Slave {SLAVE_ID}] Waiting for master request...")
        
        # This is a simplified approach - in reality you'd need proper SPI slave protocol
        # Send packet count when master requests it
        response = spi.xfer2([total_packets])
        print(f"[Slave {SLAVE_ID}] Sent packet count: {total_packets}")
        
        # Send each packet
        for i, packet in enumerate(packets):
            payload = json.dumps(packet).encode('utf-8')
            size_bytes = len(payload).to_bytes(2, byteorder='big')
            
            # Send packet size
            spi.xfer2(list(size_bytes))
            
            # Send packet data in chunks
            chunk_size = 64
            for offset in range(0, len(payload), chunk_size):
                chunk = payload[offset:offset + chunk_size]
                spi.xfer2(list(chunk))
            
            print(f"[Slave {SLAVE_ID}] Sent packet {i+1}/{total_packets}")
            
        print(f"[Slave {SLAVE_ID}] All packets sent successfully")
        
    except Exception as e:
        print(f"[Slave {SLAVE_ID}] Error in SPI communication: {e}")

def main():
    global captured_image, packets_ready
    
    print(f"[Slave {SLAVE_ID}] Starting slave controller...")
    
    try:
        # Wait for trigger and capture image
        wait_for_trigger()
        
        if packets_ready:
            print(f"[Slave {SLAVE_ID}] Ready to send image data")
            
            # Keep trying to send data (master might retry)
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    handle_spi_communication()
                    break  # Success, exit loop
                except Exception as e:
                    print(f"[Slave {SLAVE_ID}] Communication attempt failed: {e}")
                    time.sleep(0.5)
            
            if time.time() - start_time >= timeout:
                print(f"[Slave {SLAVE_ID}] Timeout waiting for master communication")
        else:
            print(f"[Slave {SLAVE_ID}] No image to send")

    except KeyboardInterrupt:
        print(f"\n[Slave {SLAVE_ID}] Interrupted by user")
    except Exception as e:
        print(f"[Slave {SLAVE_ID}] Error: {e}")
    finally:
        camera.close()
        spi.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
