import os
from dotenv import load_dotenv
from src.ui.input_window import show_input_window
from src.ui.game_window import GameWindow
from src.hardware.serial_io import SerialReaderThread

def main():
    load_dotenv()
    
    user_data = show_input_window()
    
    if user_data:
        hardware_conn = SerialReaderThread()
        hardware_conn.start()
        
        app = GameWindow(user_data, hardware_conn)
        app.mainloop()

if __name__ == "__main__":
    main()