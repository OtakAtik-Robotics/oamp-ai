import customtkinter

from PIL import Image, ImageTk
import cv2

customtkinter.set_appearance_mode("System")         # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

# Input Data
nick_name       = "NULL"
gender_code     = "NULL"
age_range_code  = "NULL"

class MyTextboxFrame(customtkinter.CTkFrame):
    def __init__(self, master, title, values):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.title = title

        self.title = customtkinter.CTkLabel(self, text=self.title, fg_color="gray", text_color="white", font=("Helvetica",30), corner_radius=6)
        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        self.textbox = customtkinter.CTkTextbox(master=self, width=100, height=10, corner_radius=0, font=("Helvetica",50))
        self.textbox.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="nsew")

    def get(self):
        str_name = self.textbox.get('0.0', '10.0')
        str_name = str_name.rstrip()
        return str_name


class MyRadiobuttonFrame(customtkinter.CTkFrame):
    def __init__(self, master, title, values):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.title = title
        self.radiobuttons = []
        self.variable = customtkinter.StringVar(value="")

        self.title = customtkinter.CTkLabel(self, text=self.title, fg_color="gray", text_color="white", font=("Helvetica",30), corner_radius=6)
        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        for i, value in enumerate(self.values):
            radiobutton = customtkinter.CTkRadioButton(self, text=value, value=value, variable=self.variable, font=("Helvetica",30))
            radiobutton.grid(row=i + 1, column=0, padx=10, pady=(10, 0), sticky="w")
            self.radiobuttons.append(radiobutton)

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)

class App_Input(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("User Input")
        
        spawn_x = 600       
        spawn_y = 10 
        self.geometry(f"{480}x{320}+{spawn_x}+{spawn_y}")


        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.resizable(0,0)

        self.textbox_frame_0 = MyTextboxFrame(self, "Nick Name", values=" ")
        self.textbox_frame_0.grid(row=0, column=0, padx=10, columnspan=2, pady=(5, 0), sticky="nsew")

        self.textbox_frame_1 = MyTextboxFrame(self, "Age", values=" ")
        self.textbox_frame_1.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="nsew")      
        
        self.radiobutton_frame_0 = MyRadiobuttonFrame(self, "Gender", values=["male", "female"])
        self.radiobutton_frame_0.grid(row=1, column=1, padx=(0, 10), pady=(10, 0), sticky="nsew")

        self.button = customtkinter.CTkButton(self, text="SUBMIT", command=self.button_callback, font=("Helvetica",30))
        self.button.grid(row=2, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

    def report_callback_exception(self, exc, val, tb):
        """Capture tkinter callback exceptions with full traceback."""
        log_exception("Tk callback exception (App_Input)", exc, val, tb)

    def button_callback(self):
        import tkinter.messagebox as messagebox
        try:
            name = self.textbox_frame_0.get().strip()
            age = self.textbox_frame_1.get().strip()
            gender = self.radiobutton_frame_0.get()

            if not name:
                raise ValueError("Nama tidak boleh kosong")
            if not age.isdigit():
                raise ValueError("Usia harus berupa angka")
            if not gender:
                raise ValueError("Silakan pilih jenis kelamin")

            age_int = int(age)
            
            print("Name   :", name)
            print("Age    :", age_int)
            print("Gender :", gender)

            global nick_name, gender_code, age_range_code
            nick_name = name
            age_range_code = age_int
            gender_code = gender

            self.destroy()

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            print(f"Unexpected error: {e}")
            messagebox.showerror("Error", "Terjadi kesalahan saat memproses input")


def show_input_window():
    """Wrapper function to show input window and return user data as dict"""
    global nick_name, gender_code, age_range_code

    nick_name = ""
    gender_code = ""
    age_range_code = 0
    
    try:
        app_input = App_Input()
        app_input.mainloop()
        
        if nick_name != "" and nick_name != "NULL":
            return {
                "name": nick_name,
                "age": age_range_code,
                "gender": gender_code
            }
        return None
    except Exception as e:
        import traceback
        print(">>> Failed while running input window. Full traceback:")
        traceback.print_exc()
        return None