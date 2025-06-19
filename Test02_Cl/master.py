#===============================================
# MASTER RASPBERRY PI CONTROLLER WITH LOGGING
#===============================================

import spidev
import time
import json
import os
import datetime
import logging
import threading
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import sys

# Import your existing modules
from image_packet_handler import decode_packets_to_image

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class SlaveConfig:
    slave_id: int
    spi_bus: int
    spi_device: int
    status: str = "DISCONNECTED"
    last_response: Optional[str] = None
    packet_count: int = 0

class SPILogger:
    """Enhanced logging system for SPI communication and camera operations"""
    
    def __init__(self, log_dir="logs", console_output=True):
        self.log_dir = log_dir
        self.console_output = console_output
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration with multiple handlers"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        # Create timestamp for log files
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Configure main logger
        self.logger = logging.getLogger('MasterController')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler for all logs
        all_log_file = os.path.join(self.log_dir, f"master_controller_{timestamp}.log")
        file_handler = logging.FileHandler(all_log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # File handler for errors only
        error_log_file = os.path.join(self.log_dir, f"errors_{timestamp}.log")
        error_handler = logging.FileHandler(error_log_file)
        error_handler.setLevel(logging.ERROR)
        
        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(funcName)20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set formatters
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        if self.console_output:
            console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        if self.console_output:
            self.logger.addHandler(console_handler)
            
        self.logger.info("=" * 60)
        self.logger.info("Master Controller Logging System Initialized")
        self.logger.info("=" * 60)
    
    def log_spi_transaction(self, slave_id: int, command: str, response: str = None, success: bool = True):
        """Log SPI communication details"""
        status = "SUCCESS" if success else "FAILED"
        message = f"SPI[Slave-{slave_id}] CMD: {command} | STATUS: {status}"
        if response:
            message += f" | RESPONSE: {response[:50]}{'...' if len(response) > 50 else ''}"
        
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
    
    def log_image_operation(self, slave_id: int, operation: str, details: Dict):
        """Log image capture and processing operations"""
        message = f"IMG[Slave-{slave_id}] {operation}: "
        for key, value in details.items():
            message += f"{key}={value} | "
        self.logger.info(message.rstrip(" | "))
    
    def log_system_status(self, slaves_status: Dict):
        """Log overall system status"""
        self.logger.info("=" * 40)
        self.logger.info("SYSTEM STATUS REPORT")
        for slave_id, status in slaves_status.items():
            self.logger.info(f"Slave-{slave_id}: {status}")
        self.logger.info("=" * 40)

class MasterController:
    """
    Master Raspberry Pi controller for managing 5 slave cameras via SPI
    
    SPI Connection Map:
    - Slave 1: SPI Bus 0, Device 0 (GPIO 8  - CE0)
    - Slave 2: SPI Bus 0, Device 1 (GPIO 7  - CE1) 
    - Slave 3: SPI Bus 1, Device 0 (GPIO 18 - CE0)
    - Slave 4: SPI Bus 1, Device 1 (GPIO 17 - CE1)
    - Slave 5: SPI Bus 1, Device 2 (GPIO 16 - CE2 - requires overlay)
    
    Note: For 5 slaves, you need to enable additional SPI interfaces in /boot/config.txt:
    dtparam=spi=on
    dtoverlay=spi1-3cs
    """
    
    def __init__(self, output_dir="captured_images"):
        self.logger = SPILogger()
        self.output_dir = output_dir
        self.spi_connections = {}
        self.slaves_data = {}
        
        # Configure slaves
        self.slave_configs = [
            SlaveConfig(1, 0, 0),  # SPI0 CE0
            SlaveConfig(2, 0, 1),  # SPI0 CE1
            SlaveConfig(3, 1, 0),  # SPI1 CE0
            SlaveConfig(4, 1, 1),  # SPI1 CE1
            SlaveConfig(5, 1, 2),  # SPI1 CE2
        ]
        
        self.setup_directories()
        self.initialize_spi_connections()
    
    def setup_directories(self):
        """Create necessary directories"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.logger.info(f"Created output directory: {self.output_dir}")
    
    def initialize_spi_connections(self):
        """Initialize SPI connections to all slaves"""
        self.logger.logger.info("Initializing SPI connections...")
        
        for slave in self.slave_configs:
            try:
                spi = spidev.SpiDev()
                spi.open(slave.spi_bus, slave.spi_device)
                spi.max_speed_hz = 1000000  # 1MHz
                spi.mode = 0
                
                self.spi_connections[slave.slave_id] = spi
                slave.status = "CONNECTED"
                
                self.logger.logger.info(
                    f"Slave-{slave.slave_id} connected on SPI{slave.spi_bus}.{slave.spi_device}"
                )
                
                # Test connection
                if self.test_slave_connection(slave.slave_id):
                    slave.status = "READY"
                
            except Exception as e:
                slave.status = "ERROR"
                self.logger.logger.error(
                    f"Failed to connect to Slave-{slave.slave_id}: {str(e)}"
                )
    
    def test_slave_connection(self, slave_id: int) -> bool:
        """Test connection to a specific slave"""
        try:
            response = self.send_command(slave_id, "PING")
            success = response and "PONG" in response
            
            self.logger.log_spi_transaction(
                slave_id, "PING", response, success
            )
            return success
            
        except Exception as e:
            self.logger.logger.error(f"Connection test failed for Slave-{slave_id}: {str(e)}")
            return False
    
    def send_command(self, slave_id: int, command: str) -> Optional[str]:
        """Send command to specific slave via SPI"""
        if slave_id not in self.spi_connections:
            self.logger.logger.error(f"No SPI connection for Slave-{slave_id}")
            return None
        
        try:
            spi = self.spi_connections[slave_id]
            
            # Prepare command
            cmd_bytes = command.encode('utf-8')
            cmd_length = len(cmd_bytes)
            
            # Send command length first, then command
            spi.xfer2([cmd_length])
            time.sleep(0.01)  # Small delay
            
            response_bytes = spi.xfer2(cmd_bytes)
            response = bytes(response_bytes).decode('utf-8', errors='ignore')
            
            self.logger.log_spi_transaction(slave_id, command, response, True)
            return response
            
        except Exception as e:
            self.logger.log_spi_transaction(slave_id, command, str(e), False)
            return None
    
    def broadcast_capture_command(self) -> Dict[int, bool]:
        """Broadcast capture command to all slaves"""
        self.logger.logger.info("Broadcasting capture command to all slaves...")
        
        capture_results = {}
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for slave in self.slave_configs:
            if slave.status != "READY":
                self.logger.logger.warning(f"Skipping Slave-{slave.slave_id} - Status: {slave.status}")
                capture_results[slave.slave_id] = False
                continue
            
            try:
                response = self.send_command(slave.slave_id, f"CAPTURE:{timestamp}")
                success = response and "CAPTURE_STARTED" in response
                capture_results[slave.slave_id] = success
                
                if success:
                    self.logger.log_image_operation(
                        slave.slave_id, 
                        "CAPTURE_INITIATED",
                        {"timestamp": timestamp, "status": "SUCCESS"}
                    )
                else:
                    self.logger.logger.error(f"Capture command failed for Slave-{slave.slave_id}")
                    
            except Exception as e:
                capture_results[slave.slave_id] = False
                self.logger.logger.error(f"Error sending capture command to Slave-{slave.slave_id}: {str(e)}")
        
        return capture_results
    
    def wait_for_capture_completion(self, timeout: int = 60) -> Dict[int, bool]:
        """Wait for all slaves to complete image capture"""
        self.logger.logger.info("Waiting for slaves to complete image capture...")
        
        completion_status = {}
        start_time = time.time()
        
        for slave in self.slave_configs:
            if slave.status != "READY":
                completion_status[slave.slave_id] = False
                continue
                
            completed = False
            slave_start_time = time.time()
            
            while not completed and (time.time() - slave_start_time) < timeout:
                try:
                    response = self.send_command(slave.slave_id, "STATUS")
                    if response and "CAPTURE_COMPLETE" in response:
                        completed = True
                        self.logger.log_image_operation(
                            slave.slave_id,
                            "CAPTURE_COMPLETED",
                            {"duration": f"{time.time() - slave_start_time:.2f}s"}
                        )
                    elif response and "ERROR" in response:
                        break
                    else:
                        time.sleep(1)  # Wait before next status check
                        
                except Exception as e:
                    self.logger.logger.error(f"Error checking status for Slave-{slave.slave_id}: {str(e)}")
                    break
            
            completion_status[slave.slave_id] = completed
            
            if not completed:
                self.logger.logger.error(f"Slave-{slave.slave_id} capture timeout or failed")
        
        total_time = time.time() - start_time
        self.logger.logger.info(f"Capture phase completed in {total_time:.2f}s")
        
        return completion_status
    
    def receive_image_packets(self, slave_id: int) -> List[Dict]:
        """Receive image packets from a specific slave"""
        self.logger.logger.info(f"Receiving image packets from Slave-{slave_id}...")
        
        packets = []
        try:
            # Request packet count
            response = self.send_command(slave_id, "GET_PACKET_COUNT")
            if not response:
                raise Exception("Failed to get packet count")
            
            packet_count = int(response.split(':')[1])
            self.logger.log_image_operation(
                slave_id,
                "PACKET_TRANSFER_START",
                {"total_packets": packet_count}
            )
            
            # Receive each packet
            for i in range(packet_count):
                packet_response = self.send_command(slave_id, f"GET_PACKET:{i}")
                if packet_response:
                    try:
                        packet_data = json.loads(packet_response)
                        packets.append(packet_data)
                        
                        if i % 10 == 0:  # Log progress every 10 packets
                            self.logger.logger.debug(f"Received packet {i+1}/{packet_count} from Slave-{slave_id}")
                            
                    except json.JSONDecodeError as e:
                        self.logger.logger.error(f"Invalid packet data from Slave-{slave_id}, packet {i}: {str(e)}")
                else:
                    self.logger.logger.error(f"Failed to receive packet {i} from Slave-{slave_id}")
            
            self.logger.log_image_operation(
                slave_id,
                "PACKET_TRANSFER_COMPLETE",
                {"received_packets": len(packets), "expected_packets": packet_count}
            )
            
        except Exception as e:
            self.logger.logger.error(f"Error receiving packets from Slave-{slave_id}: {str(e)}")
        
        return packets
    
    def save_received_images(self, all_packets: Dict[int, List[Dict]]):
        """Save received image packets as image files"""
        self.logger.logger.info("Saving received images...")
        
        for slave_id, packets in all_packets.items():
            if not packets:
                self.logger.logger.warning(f"No packets received from Slave-{slave_id}")
                continue
            
            try:
                # Save image using your existing decoder
                image_path = decode_packets_to_image(packets, self.output_dir)
                
                # Log successful save
                file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
                self.logger.log_image_operation(
                    slave_id,
                    "IMAGE_SAVED",
                    {
                        "filepath": image_path,
                        "file_size": f"{file_size} bytes",
                        "packets_used": len(packets)
                    }
                )
                
            except Exception as e:
                self.logger.logger.error(f"Failed to save image from Slave-{slave_id}: {str(e)}")
    
    def run_capture_sequence(self):
        """Execute the complete capture sequence"""
        self.logger.logger.info("Starting capture sequence...")
        
        # Step 1: Broadcast capture command
        capture_results = self.broadcast_capture_command()
        successful_captures = sum(capture_results.values())
        
        if successful_captures == 0:
            self.logger.logger.error("No slaves responded to capture command")
            return False
        
        self.logger.logger.info(f"{successful_captures}/5 slaves started capture successfully")
        
        # Step 2: Wait for completion
        completion_status = self.wait_for_capture_completion()
        completed_captures = sum(completion_status.values())
        
        if completed_captures == 0:
            self.logger.logger.error("No slaves completed capture")
            return False
        
        self.logger.logger.info(f"{completed_captures}/{successful_captures} slaves completed capture")
        
        # Step 3: Receive image packets
        all_packets = {}
        for slave_id, completed in completion_status.items():
            if completed:
                packets = self.receive_image_packets(slave_id)
                all_packets[slave_id] = packets
        
        # Step 4: Save images
        self.save_received_images(all_packets)
        
        # Final status report
        slaves_status = {}
        for slave in self.slave_configs:
            if slave.slave_id in all_packets and all_packets[slave.slave_id]:
                slaves_status[slave.slave_id] = "SUCCESS"
            else:
                slaves_status[slave.slave_id] = "FAILED"
        
        self.logger.log_system_status(slaves_status)
        
        return True
    
    def cleanup(self):
        """Clean up SPI connections"""
        self.logger.logger.info("Cleaning up SPI connections...")
        
        for slave_id, spi in self.spi_connections.items():
            try:
                spi.close()
                self.logger.logger.info(f"Closed SPI connection for Slave-{slave_id}")
            except Exception as e:
                self.logger.logger.error(f"Error closing SPI connection for Slave-{slave_id}: {str(e)}")
        
        self.logger.logger.info("Master Controller shutdown complete")

def main():
    """Main function to run the master controller"""
    print("=" * 60)
    print("Multi-Camera Master Controller")
    print("=" * 60)
    
    master = MasterController()
    
    try:
        while True:
            command = input("\nEnter 'start' to begin capture sequence, 'status' for system status, or 'quit' to exit: ").strip().lower()
            
            if command == 'start':
                print("\nStarting capture sequence...")
                success = master.run_capture_sequence()
                if success:
                    print("✓ Capture sequence completed successfully!")
                else:
                    print("✗ Capture sequence failed. Check logs for details.")
                    
            elif command == 'status':
                slaves_status = {}
                for slave in master.slave_configs:
                    slaves_status[slave.slave_id] = slave.status
                master.logger.log_system_status(slaves_status)
                
            elif command == 'quit':
                break
                
            else:
                print("Invalid command. Use 'start', 'status', or 'quit'.")
    
    except KeyboardInterrupt:
        print("\nReceived interrupt signal...")
    
    finally:
        master.cleanup()
        print("Goodbye!")

if __name__ == "__main__":
    main()
