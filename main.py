import os
import platform
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
        
        app = GameWindow(user_data=user_data, hardware_conn=hardware_conn) 
        
        def maximize_window():
            try:
                if platform.system() == 'Windows':
                    app.state('zoomed')
                else:
                    app.attributes('-zoomed', True)
            except Exception:
                pass

        app.after(0, maximize_window)
        app.mainloop()

if __name__ == "__main__":
    main()