import time
import spidev
import RPi.GPIO as GPIO
from datetime import datetime
from image_packet_handler import decode_packets_to_image

# ===================== Configuration =====================
CS_PINS = {
    1: 8,    # GPIO8 → Slave 1
    2: 7,    # GPIO7 → Slave 2
    3: 5,
    4: 6,
    5: 13,
}
CMD_CAPTURE   = 0x01
CMD_PKT_REQ   = 0x02
CMD_ACK_READY = 0x03

# ===================== SPI Setup =====================
GPIO.setmode(GPIO.BCM)
for pin in CS_PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)  # Deselect all

spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, Device 0 (we ignore CS0 because we manually toggle)
spi.max_speed_hz = 500000
spi.mode = 0

def select_slave(slave_id):
    for sid, pin in CS_PINS.items():
        GPIO.output(pin, GPIO.LOW if sid == slave_id else GPIO.HIGH)
    time.sleep(0.001)

def deselect_all():
    for pin in CS_PINS.values():
        GPIO.output(pin, GPIO.HIGH)

def broadcast_capture():
    for sid in CS_PINS:
        select_slave(sid)
        spi.xfer2([CMD_CAPTURE])
        deselect_all()
        time.sleep(0.01)

def wait_for_slave_ready(slave_id, timeout=15):
    select_slave(slave_id)
    print(f"Polling slave {slave_id} for readiness...")
    start = time.time()
    while time.time() - start < timeout:
        resp = spi.xfer2([CMD_ACK_READY, 0x00])
        if resp[1] == 1:
            deselect_all()
            print(f"✔ Slave {slave_id} ready.")
            return True
        time.sleep(0.25)
    deselect_all()
    print(f"✖ Timeout waiting for slave {slave_id}")
    return False

def retrieve_packets(slave_id):
    select_slave(slave_id)
    resp = spi.xfer2([CMD_PKT_REQ, 0xFF])
    total_pkts = resp[1]
    deselect_all()
    print(f"Retrieving {total_pkts} packets from slave {slave_id}...")

    packets = []
    for i in range(total_pkts):
        select_slave(slave_id)
        spi.xfer2([CMD_PKT_REQ, i])
        raw = spi.readbytes(256)
        deselect_all()

        try:
            pkt = bytes(raw).decode('utf-8').rstrip('\x00')
            packets.append(eval(pkt))  # You may use json.loads(pkt) if JSON
        except Exception as e:
            print(f"Packet decode error: {e}")
    return packets

def main():
    input("Press ENTER to begin capture...")

    print("\n📤 Broadcasting CAPTURE command...")
    broadcast_capture()

    for sid in CS_PINS:
        if wait_for_slave_ready(sid):
            packets = retrieve_packets(sid)
            filename = decode_packets_to_image(packets, output_dir="images")
            print(f"✅ Image from Slave {sid} saved → {filename}")
        else:
            print(f"⚠ Skipping Slave {sid} (not ready)")

    spi.close()
    GPIO.cleanup()

if __name__ == "__main__":
    main()
