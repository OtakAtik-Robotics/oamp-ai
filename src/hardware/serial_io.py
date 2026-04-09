import threading
from queue import Queue
import serial
import serial.tools.list_ports
import os

class SerialReaderThread(threading.Thread):
    """Background thread for reading serial data from ESP32"""
    def __init__(self, port=None, baudrate=115200):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = True
        self.message_queue = Queue(maxsize=10)
        
        # Auto-detect ESP32 port if not specified
        if not self.port:
            self.port = self.find_esp32_port()
        
        if self.port:
            try:
                self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=0.1)
                print(f">>> Serial connected to {self.port} at {self.baudrate} baud")
            except Exception as e:
                print(f">>> Failed to open serial port {self.port}: {e}")
                self.serial_conn = None
        else:
            print(">>> No ESP32 device found")
    
    def find_esp32_port(self):
        """Auto-detect ESP32 COM port (Windows/Linux)"""
        ports = serial.tools.list_ports.comports()
        
        # Check for Linux Bluetooth RFCOMM first
        import platform
        if platform.system() == 'Linux':
            # Check for /dev/rfcomm0 (Bluetooth)
            if os.path.exists('/dev/rfcomm0'):
                print(f">>> Found Bluetooth RFCOMM at /dev/rfcomm0")
                return '/dev/rfcomm0'
        
        # Check standard serial ports
        for port in ports:
            # ESP32 identifiers (USB or Bluetooth)
            identifiers = ['USB', 'CH340', 'CP210', 'UART', 'Serial', 'Bluetooth']
            if any(id in port.description for id in identifiers):
                print(f">>> Found potential ESP32 at {port.device}: {port.description}")
                return port.device
        
        return None
    
    def run(self):
        if not self.serial_conn:
            print(">>> Serial reader thread: No connection available")
            return
            
        print(">>> Serial reader thread started")
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        # Put message in queue
                        if not self.message_queue.full():
                            self.message_queue.put(line)
                        if line == "disable_image":
                            print(f">>> Serial received: {line}")
                time.sleep(0.01)
            except Exception as e:
                print(f">>> Serial read error: {e}")
                time.sleep(0.1)
    
    def get_message(self):
        """Get message from queue (non-blocking)"""
        try:
            return self.message_queue.get_nowait()
        except:
            return None
    
    def stop(self):
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()
        print(">>> Serial reader thread stopped")