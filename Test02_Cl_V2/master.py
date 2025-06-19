import time
import spidev
import RPi.GPIO as GPIO
import json
from image_packet_handler import decode_packets_to_image

# SPI device map: slave_id -> (spi_bus, spi_cs)
SPI_DEVICES = {
    1: (0, 0),
    2: (0, 1),
    3: (1, 0),
    4: (1, 1),
    5: (1, 2)
}

TRIGGER_GPIO = 22  # GPIO pin used to broadcast trigger to all slaves

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIGGER_GPIO, GPIO.OUT)
GPIO.output(TRIGGER_GPIO, GPIO.LOW)

def trigger_all_slaves():
    print("[Master] Broadcasting capture trigger to all selected slaves...")
    GPIO.output(TRIGGER_GPIO, GPIO.HIGH)
    time.sleep(0.1)  # Shorter pulse
    GPIO.output(TRIGGER_GPIO, GPIO.LOW)
    print("[Master] Trigger pulse sent.")

def receive_image(spi_bus, spi_cs, slave_id):
    print(f"[Master] Opening SPI({spi_bus}, {spi_cs}) for Slave {slave_id}")
    spi = spidev.SpiDev()
    
    try:
        spi.open(spi_bus, spi_cs)
        spi.max_speed_hz = 500000  # Match slave speed
        spi.mode = 0  # Ensure SPI mode matches
        
        # Give slave more time to process and be ready
        print(f"[Master] Waiting for Slave {slave_id} to be ready...")
        time.sleep(2.0)  # Increased wait time
        
        # Try multiple times to get packet count
        total_packets = 0
        for attempt in range(5):
            try:
                response = spi.xfer2([0x00])
                total_packets = response[0]
                print(f"[Master] Attempt {attempt + 1}: Received packet count: {total_packets}")
                if total_packets > 0:
                    break
                time.sleep(0.2)
            except Exception as e:
                print(f"[Master] Attempt {attempt + 1} failed: {e}")
                time.sleep(0.2)
        
        if total_packets == 0:
            print(f"[Master] No packets received from Slave {slave_id} after 5 attempts")
            return
        
        print(f"[Master] Receiving {total_packets} packets from Slave {slave_id}")
        packets = []
        
        for i in range(total_packets):
            try:
                # Read packet size (2 bytes)
                length_bytes = spi.xfer2([0x00, 0x00])
                packet_size = int.from_bytes(length_bytes, byteorder='big')
                print(f"[Master] Packet {i+1}/{total_packets}: size = {packet_size} bytes")
                
                if packet_size == 0 or packet_size > 10000:  # Sanity check
                    print(f"[Master] Invalid packet size: {packet_size}")
                    continue
                
                # Read packet data
                packet_data = bytearray()
                chunk_size = 64  # Read in chunks for efficiency
                
                for offset in range(0, packet_size, chunk_size):
                    remaining = min(chunk_size, packet_size - offset)
                    chunk = spi.xfer2([0x00] * remaining)
                    packet_data.extend(chunk)
                
                # Parse JSON
                packet_json = json.loads(packet_data.decode('utf-8'))
                packets.append(packet_json)
                print(f"[Master] Successfully received packet {i+1}")
                
            except Exception as e:
                print(f"[Master] Error receiving packet {i+1}: {e}")
                continue
        
        if packets:
            filepath = decode_packets_to_image(packets, output_dir="images")
            print(f"[Master] Image from Slave {slave_id} saved at: {filepath}")
        else:
            print(f"[Master] No valid packets received from Slave {slave_id}")
            
    except Exception as e:
        print(f"[Master] Error communicating with Slave {slave_id}: {e}")
    finally:
        spi.close()

def main():
    print("--- MULTI-SLAVE CAMERA SYSTEM ---")
    print("Available Slaves: 1 2 3 4 5")
    selected = input("Enter slave numbers to trigger (space-separated): ")

    try:
        slave_ids = [int(sid) for sid in selected.strip().split() if int(sid) in SPI_DEVICES]
        if not slave_ids:
            print("No valid slaves selected. Exiting.")
            return

        print(f"[Master] Selected slaves: {slave_ids}")
        
        # Send GPIO trigger to all selected slaves
        trigger_all_slaves()
        
        print("[Master] Waiting for slaves to capture images...")
        time.sleep(3.0)  # Give slaves time to capture

        # Sequentially receive images from each selected slave
        for sid in slave_ids:
            bus, cs = SPI_DEVICES[sid]
            print(f"\n[Master] Processing Slave {sid} on SPI({bus}, {cs})")
            receive_image(bus, cs, sid)

        print("\n[Master] All images received and saved.")

    except KeyboardInterrupt:
        print("\n[Master] Interrupted by user")
    except Exception as e:
        print(f"[Master] Error: {e}")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
