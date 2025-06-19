#===============================================
# SLAVE RASPBERRY PI SPI LISTENER WITH CAMERA
#===============================================

import spidev
import time
import json
import os
import datetime
import logging
import threading
from typing import List, Dict, Optional
import sys

# Import your existing modules
from camera_module_v4_3 import CameraModule
from image_packet_handler import encode_image_to_packets

class SlaveController:
    """
    Slave Raspberry Pi controller that:
    1. Listens for SPI commands from master
    2. Captures images using your CameraModule
    3. Encodes images into packets
    4. Sends packets back to master via SPI
    """
    
    def __init__(self, slave_id: int, spi_bus: int = 0, spi_device: int = 0):
        self.slave_id = slave_id
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        
        # State variables
        self.current_packets = []
        self.capture_status = "IDLE"  # IDLE, CAPTURING, COMPLETE, ERROR
        self.last_capture_timestamp = None
        self.camera = None
        
        # Setup logging
        self.setup_logging()
        
        # Initialize camera
        self.initialize_camera()
        
        # Initialize SPI as slave (listening mode)
        self.initialize_spi()
        
        self.logger.info(f"Slave-{self.slave_id} initialized and ready")
    
    def setup_logging(self):
        """Setup logging for the slave"""
        log_dir = f"slave_{self.slave_id}_logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"slave_{self.slave_id}_{timestamp}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | %(funcName)20s | %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(f'Slave-{self.slave_id}')
        self.logger.info("=" * 50)
        self.logger.info(f"Slave-{self.slave_id} Logging Initialized")
        self.logger.info("=" * 50)
    
    def initialize_camera(self):
        """Initialize the camera module"""
        try:
            self.camera = CameraModule()
            self.logger.info("Camera module initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {str(e)}")
            raise
    
    def initialize_spi(self):
        """Initialize SPI connection for slave mode"""
        try:
            # Note: In slave mode, we actually set up to listen for SPI communications
            # This is a simplified version - actual implementation may vary based on your SPI setup
            self.logger.info(f"SPI slave mode initialized on bus {self.spi_bus}, device {self.spi_device}")
        except Exception as e:
            self.logger.error(f"Failed to initialize SPI: {str(e)}")
            raise
    
    def capture_image_async(self, timestamp: str):
        """Capture image asynchronously"""
        def capture_worker():
            try:
                self.capture_status = "CAPTURING"
                self.last_capture_timestamp = timestamp
                
                self.logger.info(f"Starting image capture with timestamp: {timestamp}")
                
                # Use your existing camera module
                filename = f"slave_{self.slave_id}_{timestamp}.jpg"
                image_bytes = self.camera.capture_image(
                    apply_color_correction=True,
                    byte_image=True,
                    filename=filename
                )
                
                if image_bytes:
                    # Encode image into packets
                    self.current_packets = encode_image_to_packets(image_bytes, self.slave_id)
                    self.capture_status = "COMPLETE"
                    
                    self.logger.info(f"Image captured and encoded into {len(self.current_packets)} packets")
                    self.logger.info(f"Image size: {len(image_bytes)} bytes, saved as: {filename}")
                else:
                    self.capture_status = "ERROR"
                    self.logger.error("Failed to capture image - no data returned")
                    
            except Exception as e:
                self.capture_status = "ERROR"
                self.logger.error(f"Error during image capture: {str(e)}")
        
        # Start capture in separate thread
        capture_thread = threading.Thread(target=capture_worker)
        capture_thread.daemon = True
        capture_thread.start()
    
    def handle_command(self, command: str) -> str:
        """Handle incoming commands from master"""
        self.logger.info(f"Received command: {command}")
        
        try:
            if command == "PING":
                return "PONG"
                
            elif command.startswith("CAPTURE:"):
                timestamp = command.split(":", 1)[1]
                if self.capture_status in ["IDLE", "COMPLETE", "ERROR"]:
                    self.capture_image_async(timestamp)
                    return "CAPTURE_STARTED"
                else:
                    return "CAPTURE_BUSY"
                    
            elif command == "STATUS":
                if self.capture_status == "COMPLETE":
                    return "CAPTURE_COMPLETE"
                elif self.capture_status == "CAPTURING":
                    return "CAPTURE_IN_PROGRESS"
                elif self.capture_status == "ERROR":
                    return "CAPTURE_ERROR"
                else:
                    return "IDLE"
                    
            elif command == "GET_PACKET_COUNT":
                if self.capture_status == "COMPLETE":
                    return f"PACKET_COUNT:{len(self.current_packets)}"
                else:
                    return "ERROR:NO_CAPTURE_DATA"
                    
            elif command.startswith("GET_PACKET:"):
                packet_index = int(command.split(":", 1)[1])
                if (self.capture_status == "COMPLETE" and 
                    0 <= packet_index < len(self.current_packets)):
                    return json.dumps(self.current_packets[packet_index])
                else:
                    return "ERROR:INVALID_PACKET_INDEX"
                    
            else:
                return "ERROR:UNKNOWN_COMMAND"
                
        except Exception as e:
            self.logger.error(f"Error handling command '{command}': {str(e)}")
            return f"ERROR:{str(e)}"
    
    def listen_for_commands(self):
        """Main loop to listen for SPI commands"""
        self.logger.info("Starting command listener...")
        
        while True:
            try:
                # This is a simplified SPI listening implementation
                # In a real implementation, you would:
                # 1. Wait for SPI chip select
                # 2. Read incoming command length
                # 3. Read command data
                # 4. Process command
                # 5. Send response
                
                # For demonstration, we'll simulate with a simple input loop
                # Replace this with actual SPI slave implementation
                time.sleep(0.1)  # Prevent busy waiting
                
                # Simulate receiving command (replace with actual SPI read)
                # In real implementation, this would be reading from SPI buffer
                
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Error in command listener: {str(e)}")
                time.sleep(1)  # Wait before retrying
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.camera:
                self.camera.close()
                self.logger.info("Camera module closed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
        
        self.logger.info(f"Slave-{self.slave_id} shutdown complete")

def main():
    """Main function for slave controller"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Slave Pi Camera Controller")
    parser.add_argument("--slave-id", type=int, required=True, help="Slave ID (1-5)")
    parser.add_argument("--spi-bus", type=int, default=0, help="SPI bus number")
    parser.add_argument("--spi-device", type=int, default=0, help="SPI device number")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")
    
    args = parser.parse_args()
    
    print(f"Starting Slave-{args.slave_id} Controller...")
    print(f"SPI Configuration: Bus {args.spi_bus}, Device {args.spi_device}")
    
    slave = SlaveController(args.slave_id, args.spi_bus, args.spi_device)
    
    try:
        if args.test_mode:
            # Test mode for debugging
            print("Running in test mode...")
            while True:
                command = input("Enter command (or 'quit' to exit): ").strip()
                if command.lower() == 'quit':
                    break
                response = slave.handle_command(command)
                print(f"Response: {response}")
        else:
            # Normal operation mode
            slave.listen_for_commands()
            
    except KeyboardInterrupt:
        print("\nReceived interrupt signal...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        slave.cleanup()
        print("Slave controller shutdown complete.")

if __name__ == "__main__":
    main()
