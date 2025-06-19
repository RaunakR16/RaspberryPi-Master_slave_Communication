# Multi-Slave Camera System Wiring Diagram
https://claude.ai/share/a67ef1ac-04fd-4818-a637-ae7449363276
## Master Raspberry Pi Pin Configuration

### SPI Bus 0 Pins (Primary)
- **GPIO 10 (Pin 19)** → MOSI (Master Out, Slave In)
- **GPIO 9 (Pin 21)** → MISO (Master In, Slave Out) 
- **GPIO 11 (Pin 23)** → SCLK (Serial Clock)
- **GPIO 8 (Pin 24)** → CE0 (Chip Enable 0) - Slave 1
- **GPIO 7 (Pin 26)** → CE1 (Chip Enable 1) - Slave 2

### SPI Bus 1 Pins (Secondary) 
- **GPIO 20 (Pin 38)** → MOSI1 (Master Out, Slave In)
- **GPIO 19 (Pin 35)** → MISO1 (Master In, Slave Out)
- **GPIO 21 (Pin 40)** → SCLK1 (Serial Clock)
- **GPIO 18 (Pin 12)** → CE0 (Chip Enable 0) - Slave 3
- **GPIO 17 (Pin 11)** → CE1 (Chip Enable 1) - Slave 4
- **GPIO 16 (Pin 36)** → CE2 (Chip Enable 2) - Slave 5

### Trigger Signal
- **GPIO 22 (Pin 15)** → Broadcast trigger to all slaves

## Slave Raspberry Pi Pin Configuration

### For Slaves 1 & 2 (SPI Bus 0)
- **GPIO 10 (Pin 19)** → MOSI (receives from master)
- **GPIO 9 (Pin 21)** → MISO (sends to master)
- **GPIO 11 (Pin 23)** → SCLK (receives clock from master)
- **GPIO 8 (Pin 24)** → CE0 (Slave 1 only)
- **GPIO 7 (Pin 26)** → CE1 (Slave 2 only)

### For Slaves 3, 4 & 5 (SPI Bus 1)
- **GPIO 20 (Pin 38)** → MOSI1 (receives from master)
- **GPIO 19 (Pin 35)** → MISO1 (sends to master)
- **GPIO 21 (Pin 40)** → SCLK1 (receives clock from master)
- **GPIO 18 (Pin 12)** → CE0 (Slave 3 only)
- **GPIO 17 (Pin 11)** → CE1 (Slave 4 only)
- **GPIO 16 (Pin 36)** → CE2 (Slave 5 only)

### Trigger Input (All Slaves)
- **GPIO 27 (Pin 13)** → Receives trigger from master GPIO 22

## Wiring Connections

```
MASTER Pi                    SLAVE Pi(s)
===========                  ===========

SPI Bus 0 (Slaves 1 & 2):
GPIO 10 (Pin 19) MOSI   →    GPIO 10 (Pin 19) MOSI
GPIO 9  (Pin 21) MISO   ←    GPIO 9  (Pin 21) MISO  
GPIO 11 (Pin 23) SCLK   →    GPIO 11 (Pin 23) SCLK
GPIO 8  (Pin 24) CE0    →    GPIO 8  (Pin 24) CE0  (Slave 1 only)
GPIO 7  (Pin 26) CE1    →    GPIO 7  (Pin 26) CE1  (Slave 2 only)

SPI Bus 1 (Slaves 3, 4 & 5):
GPIO 20 (Pin 38) MOSI1  →    GPIO 20 (Pin 38) MOSI1
GPIO 19 (Pin 35) MISO1  ←    GPIO 19 (Pin 35) MISO1
GPIO 21 (Pin 40) SCLK1  →    GPIO 21 (Pin 40) SCLK1
GPIO 18 (Pin 12) CE0    →    GPIO 18 (Pin 12) CE0  (Slave 3 only)
GPIO 17 (Pin 11) CE1    →    GPIO 17 (Pin 11) CE1  (Slave 4 only)
GPIO 16 (Pin 36) CE2    →    GPIO 16 (Pin 36) CE2  (Slave 5 only)

Trigger Signal (All Slaves):
GPIO 22 (Pin 15) OUT    →    GPIO 27 (Pin 13) IN   (All slaves)

Power & Ground:
3.3V    (Pin 1/17)      →    3.3V    (Pin 1/17)    (All slaves)
GND     (Pin 6/9/14/20/25/30/34/39) → GND (corresponding pins)
```

## Important Notes

### 1. Ground Connections
- **CRITICAL**: All devices must share common ground
- Connect at least one GND pin between master and each slave
- Use multiple ground connections for better signal integrity

### 2. Power Supply
- Each Pi needs independent 5V power supply
- 3.3V pins are for logic level reference only
- Don't power Pi through 3.3V pins

### 3. Cable Management
- Keep SPI signal wires short (< 30cm recommended)
- Use twisted pair or shielded cables for longer distances
- Separate trigger wire from SPI data lines to avoid interference

### 4. Enable SPI Interface
On all Raspberry Pis, enable SPI:
```bash
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
```

Or edit `/boot/config.txt`:
```
dtparam=spi=on
```

### 5. Slave-Specific Configuration

Update each slave's code with correct SPI parameters:

**Slave 1:**
```python
SPI_BUS = 0
SPI_CS = 0
spi.open(0, 0)
```

**Slave 2:**
```python
SPI_BUS = 0  
SPI_CS = 1
spi.open(0, 1)
```

**Slave 3:**
```python
SPI_BUS = 1
SPI_CS = 0  
spi.open(1, 0)
```

**Slave 4:**
```python
SPI_BUS = 1
SPI_CS = 1
spi.open(1, 1)
```

**Slave 5:**
```python
SPI_BUS = 1
SPI_CS = 2
spi.open(1, 2)
```

## Testing Connections

### 1. Test Trigger Signal
```python
# On master:
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.OUT)
GPIO.output(22, GPIO.HIGH)

# On each slave:
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN)
print(GPIO.input(27))  # Should print 1
```

### 2. Test SPI Loopback
Connect MOSI to MISO temporarily and run:
```python
import spidev
spi = spidev.SpiDev()
spi.open(0, 0)  # Test each bus/cs combination
result = spi.xfer2([0x55])
print(f"Sent: 0x55, Received: {hex(result[0])}")  # Should match
spi.close()
```

## Troubleshooting

- **No response from slave**: Check CE (chip enable) connections
- **Corrupted data**: Verify ground connections and cable quality  
- **Intermittent issues**: Check power supply stability
- **Trigger not working**: Verify GPIO 22 → GPIO 27 connection
