import time, json
import spidev
import RPi.GPIO as GPIO
from camera_module_v4_3 import CameraModule       # or your image_Capture.py
from image_packet_handler import encode_image_to_packets

# ======== Configuration ========
SLAVE_ID = 1  # set per device 1…5
CS_PIN   = 8  # must match wiring above
CMD_CAPTURE   = 0x01
CMD_PKT_REQ   = 0x02
CMD_ACK_READY = 0x03
PACKET_SIZE   = 150

# ======== Setup ========
GPIO.setmode(GPIO.BCM)
GPIO.setup(CS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # we’ll detect CS falling

spi = spidev.SpiDev()
spi.open(0, 0)   # we only care about MISO, MOSI, SCLK
spi.max_speed_hz = 1_000_000
spi.mode = 0

# State
packets = []
ready = False

def wait_for_commands():
    global packets, ready
    while True:
        # busy‐wait for CS low
        if GPIO.input(CS_PIN) == 0:
            cmd, arg = spi.readbytes(2)
            if cmd == CMD_CAPTURE:
                # capture + packetize
                cam = CameraModule()
                img_bytes = cam.capture_image(byte_image=True)
                cam.close()
                packets = encode_image_to_packets(img_bytes, SLAVE_ID)
                ready = True

                # ack immediately so master’s next poll sees ready
                spi.xfer2([CMD_ACK_READY, 1])

            elif cmd == CMD_ACK_READY:
                # master is just polling — reply 1 if ready else 0
                spi.xfer2([CMD_ACK_READY, 1 if ready else 0])

            elif cmd == CMD_PKT_REQ:
                if arg == 0xFF:
                    # query total count
                    spi.xfer2([CMD_PKT_REQ, len(packets)])
                else:
                    idx = arg
                    pkt = packets[idx]
                    raw = json.dumps(pkt).encode('utf-8')
                    # pad/truncate to 256 bytes
                    buf = raw.ljust(256, b'\x00')[:256]
                    spi.xfer2(list(buf))
        time.sleep(0.001)

if __name__ == "__main__":
    wait_for_commands()
