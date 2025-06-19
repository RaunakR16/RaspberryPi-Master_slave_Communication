import time
import spidev
import RPi.GPIO as GPIO
import json
from datetime import datetime

# ======== Configuration ========
CS_PINS = {
    1: 8,   # CE0
    2: 7,   # CE1
    3: 5,   # software CS
    4: 6,
    5: 13,
}
CMD_CAPTURE   = 0x01
CMD_PKT_REQ   = 0x02
CMD_ACK_READY = 0x03

# ======== Setup ========
GPIO.setmode(GPIO.BCM)
for cs in CS_PINS.values():
    GPIO.setup(cs, GPIO.OUT, initial=GPIO.HIGH)

spi = spidev.SpiDev()
spi.open(0, 0)    # bus 0, CE0 (we’ll manually toggle CS for others)
spi.max_speed_hz = 1_000_000
spi.mode = 0

def select(slave_id):
    """Assert only this slave’s CS low."""
    for sid, pin in CS_PINS.items():
        GPIO.output(pin, GPIO.LOW if sid == slave_id else GPIO.HIGH)

def deselect_all():
    for pin in CS_PINS.values():
        GPIO.output(pin, GPIO.HIGH)

def broadcast_capture():
    print("Broadcasting capture command...")
    # Briefly assert and deassert each CS with CMD_CAPTURE
    for sid in CS_PINS:
        select(sid)
        spi.xfer2([CMD_CAPTURE])
        time.sleep(0.01)
    deselect_all()

def wait_until_ready(slave_id, timeout=10):
    select(slave_id)
    start = time.time()
    while time.time() - start < timeout:
        resp = spi.xfer2([CMD_ACK_READY, 0x00])
        # If slave pulls MISO low or returns non-zero ack → ready
        if resp[1] == 1:
            break
        time.sleep(0.1)
    deselect_all()

def retrieve_packets(slave_id):
    # ask slave how many packets it has
    select(slave_id)
    resp = spi.xfer2([CMD_PKT_REQ, 0xFF])  # 0xFF as “query total”
    total_pkts = resp[1]
    deselect_all()

    packets = []
    for idx in range(total_pkts):
        select(slave_id)
        # send [CMD_PKT_REQ, packet_index]
        resp = spi.xfer2([CMD_PKT_REQ, idx])  
        # data comes back as a JSON string split over multiple bytes…
        # Here we read a fixed len block then decode
        raw = spi.readbytes(256)
        deselect_all()
        try:
            pkt = json.loads(bytes(raw).decode('utf-8').rstrip('\x00'))
            packets.append(pkt)
        except Exception as e:
            print(f"Decoding error from slave {slave_id} pkt#{idx}: {e}")
    return packets

def main():
    input("Press Enter to START capture → ")
    broadcast_capture()

    for sid in CS_PINS:
        print(f"-- Waiting for Slave {sid} ready…")
        wait_until_ready(sid)
        print(f"-- Retrieving packets from Slave {sid}…")
        pkts = retrieve_packets(sid)
        from image_packet_handler import decode_packets_to_image
        out = decode_packets_to_image(pkts, output_dir="./images")
        print(f"Saved image from Slave {sid} → {out}")

    spi.close()
    GPIO.cleanup()

if __name__ == "__main__":
    main()
