class App_Input(customtkinter.CTk): #CTkToplevel
    def __init__(self):
        super().__init__()

        self.title("User Input")
        
        spawn_x = 600           # int((self.winfo_screenwidth()-480)/2) 
        spawn_y = 10            # int((self.winfo_screenheight()-320)/2)
        self.geometry(f"{480}x{320}+{spawn_x}+{spawn_y}")
        #self.geometry("480x320")
        
        # from AppOpener import open
        # open("on-screen keyboard")

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

        #play_audio("AUDIO/selamat_datang.wav")
        # tts_indo("Selamat datang di permainan Blok Desain Tes.") #名前、年齢、性別を入力してください。
        #SpeakTextG("... ")


    def report_callback_exception(self, exc, val, tb):
        """Capture tkinter callback exceptions with full traceback."""
        log_exception("Tk callback exception (App_Input)", exc, val, tb)

    def button_callback(self):
        import tkinter.messagebox as messagebox
        try:
            # Get values from UI
            name = self.textbox_frame_0.get().strip()
            age = self.textbox_frame_1.get().strip()
            gender = self.radiobutton_frame_0.get()

            # Input validation
            if not name:
                raise ValueError("Nama tidak boleh kosong")
            if not age.isdigit():
                raise ValueError("Usia harus berupa angka")
            if not gender:
                raise ValueError("Silakan pilih jenis kelamin")

            # Convert age to integer
            age_int = int(age)
            
            # Debug print
            print("Name   :", name)
            print("Age    :", age_int)
            print("Gender :", gender)

            # Set global variables
            global nick_name, gender_code, age_range_code
            nick_name = name
            age_range_code = age_int #str(age_int)  # Store as string if needed for display
            gender_code = gender

            # Close the window
            self.destroy()

        except ValueError as e:
            # Show error message to user
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            print(f"Unexpected error: {e}")
            messagebox.showerror("Error", "Terjadi kesalahan saat memproses input")
        

try:
    app_input = App_Input()
    app_input.mainloop()
except Exception:
    print(">>> Failed while running input window. Full traceback:")
    traceback.print_exc()
    raise SystemExit(1)