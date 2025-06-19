# Multi-Camera Master-Slave System Setup Guide

## 🔧 Hardware Connections

### SPI Pin Mapping for Master Pi

**Master Raspberry Pi GPIO Pins:**
```
SPI0 (Primary):
- SCLK  (GPIO 11) - Clock line for Slaves 1 & 2
- MOSI  (GPIO 10) - Master Out Slave In for Slaves 1 & 2  
- MISO  (GPIO 9)  - Master In Slave Out for Slaves 1 & 2
- CE0   (GPIO 8)  - Chip Enable for Slave 1
- CE1   (GPIO 7)  - Chip Enable for Slave 2

SPI1 (Secondary):
- SCLK  (GPIO 21) - Clock line for Slaves 3, 4 & 5
- MOSI  (GPIO 20) - Master Out Slave In for Slaves 3, 4 & 5
- MISO  (GPIO 19) - Master In Slave Out for Slaves 3, 4 & 5
- CE0   (GPIO 18) - Chip Enable for Slave 3
- CE1   (GPIO 17) - Chip Enable for Slave 4
- CE2   (GPIO 16) - Chip Enable for Slave 5
```

### Connection Diagram
```
Master Pi                    Slave Pi (Example)
┌─────────────┐             ┌─────────────┐
│ GPIO 11     │─────────────│ GPIO 11     │ (SCLK)
│ GPIO 10     │─────────────│ GPIO 10     │ (MOSI)
│ GPIO 9      │─────────────│ GPIO 9      │ (MISO)
│ GPIO 8      │─────────────│ GPIO 8      │ (CE0 - Slave 1)
│ GND         │─────────────│ GND         │
│ 5V          │─────────────│ 5V          │
└─────────────┘             └─────────────┘
```

**Power Requirements:**
- Use common 5V power supply for all Pi Zero Ws
- Ensure adequate current rating (min 2.5A per Pi)
- Use common ground for all devices

## ⚙️ Software Configuration

### 1. Enable SPI on All Raspberry Pis

Add to `/boot/config.txt` on **ALL** Raspberry Pis:
```bash
# Enable SPI
dtparam=spi=on

# For Master Pi only - enable additional SPI interfaces
dtoverlay=spi1-3cs
```

### 2. Install Required Python Packages

On **ALL** Raspberry Pis:
```bash
sudo apt update
sudo apt install python3-pip python3-dev
pip3 install spidev picamera2 opencv-python numpy imageio
```

### 3. System Setup Commands

**Master Pi Setup:**
```bash
# Create project directory
mkdir ~/camera_system
cd ~/camera_system

# Copy your files
cp camera_module_v4_3.py ~/camera_system/
cp image_packet_handler.py ~/camera_system/
cp master_controller.py ~/camera_system/

# Make executable
chmod +x master_controller.py

# Test SPI interfaces
ls /dev/spi*
# Should show: /dev/spidev0.0 /dev/spidev0.1 /dev/spidev1.0 /dev/spidev1.1 /dev/spidev1.2
```

**Each Slave Pi Setup:**
```bash
# Create project directory
mkdir ~/camera_system
cd ~/camera_system

# Copy your files
cp camera_module_v4_3.py ~/camera_system/
cp image_packet_handler.py ~/camera_system/
cp slave_controller.py ~/camera_system/

# Make executable
chmod +x slave_controller.py

# Test camera
python3 -c "from camera_module_v4_3 import CameraModule; cam = CameraModule(); print('Camera OK')"
```

## 🚀 Running the System

### 1. Start Slave Controllers

**On each Slave Pi (run in separate terminals or as services):**

```bash
# Slave 1 (SPI0.0)
python3 slave_controller.py --slave-id 1 --spi-bus 0 --spi-device 0

# Slave 2 (SPI0.1) 
python3 slave_controller.py --slave-id 2 --spi-bus 0 --spi-device 1

# Slave 3 (SPI1.0)
python3 slave_controller.py --slave-id 3 --spi-bus 1 --spi-device 0

# Slave 4 (SPI1.1)
python3 slave_controller.py --slave-id 4 --spi-bus 1 --spi-device 1

# Slave 5 (SPI1.2)
python3 slave_controller.py --slave-id 5 --spi-bus 1 --spi-device 2
```

### 2. Start Master Controller

**On Master Pi:**
```bash
python3 master_controller.py
```

Then in the interactive prompt:
- Type `status` to check all slave connections
- Type `start` to begin capture sequence
- Type `quit` to exit

## 📁 File Structure

```
~/camera_system/
├── camera_module_v4_3.py      # Your camera module
├── image_packet_handler.py    # Your packet handler
├── master_controller.py       # Master controller (new)
├── slave_controller.py        # Slave controller (new)
├── logs/                      # Master logs directory
│   ├── master_controller_*.log
│   └── errors_*.log
├── slave_*_logs/              # Slave logs directories
│   └── slave_*_*.log
└── captured_images/           # Output images directory
    └── image_slave*_*.jpg
```

## 🔍 Troubleshooting

### Common Issues and Solutions

**1. SPI Device Not Found**
```bash
# Check if SPI is enabled
lsmod | grep spi
# Should show spi_bcm2835

# Check config.txt
cat /boot/config.txt | grep spi
```

**2. Permission Denied on SPI**
```bash
# Add user to spi group
sudo usermod -a -G spi $USER
# Logout and login again
```

**3. Camera Not Working**
```bash
# Test camera directly
python3 -c "from picamera2 import Picamera2; cam = Picamera2(); cam.start(); cam.stop(); print('Camera OK')"

# Check camera is connected
vcgencmd get_camera
```

**4. No Response from Slaves**
- Check physical connections
- Verify slave processes are running
- Check slave logs for errors
- Test with single slave first

## 📊 Logging System Features

### Master Controller Logs
- **master_controller_*.log**: Complete system activity
- **errors_*.log**: Error-only log for debugging
- **Console output**: Real-time status updates

### Log Information Includes:
- SPI communication details
- Image capture progress
- Packet transfer status
- Error diagnostics
- Performance metrics
- System status reports

### Sample Log Output:
```
2024-06-19 10:30:15 |     INFO |         broadcast_capture_command | Broadcasting capture command to all slaves...
2024-06-19 10:30:15 |     INFO |         log_spi_transaction | SPI[Slave-1] CMD: CAPTURE:20240619_103015 | STATUS: SUCCESS | RESPONSE: CAPTURE_STARTED
2024-06-19 10:30:18 |     INFO |         log_image_operation | IMG[Slave-1] CAPTURE_COMPLETED: duration=2.34s
2024-06-19 10:30:25 |     INFO |         log_image_operation | IMG[Slave-1] IMAGE_SAVED: filepath=./captured_images/image_slave1_20240619_103015.jpg | file_size=245760 bytes | packets_used=1639
```

## 🛠️ Advanced Configuration

### Performance Tuning

**SPI Speed Adjustment:**
```python
# In master_controller.py, modify:
spi.max_speed_hz = 2000000  # Increase to 2MHz for faster transfer
```

**Packet Size Optimization:**
```python
# In image_packet_handler.py, modify:
PACKET_SIZE = 200  # Increase packet size for fewer transfers
```

### Service Setup (Optional)

Create systemd services for automatic startup:

**Master Service (`/etc/systemd/system/camera-master.service`):**
```ini
[Unit]
Description=Camera System Master Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/camera_system
ExecStart=/usr/bin/python3 master_controller.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Slave Service Template (`/etc/systemd/system/camera-slave@.service`):**
```ini
[Unit]
Description=Camera System Slave Controller %i
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/camera_system
ExecStart=/usr/bin/python3 slave_controller.py --slave-id %i --spi-bus 0 --spi-device 0
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable services:
```bash
sudo systemctl enable camera-master.service
sudo systemctl enable camera-slave@1.service
sudo systemctl start camera-master.service
```

## 📈 Monitoring and Maintenance

### System Health Checks
- Monitor log files for errors
- Check disk space for image storage
- Verify SPI communication integrity
- Monitor camera performance metrics

### Regular Maintenance
- Rotate log files to prevent disk full
- Clean up old captured images
- Update camera calibration settings
- Check physical connections

This comprehensive logging system will help you track every aspect of your multi-camera setup, from SPI communication to image capture and storage!
