class TimeIn(customtkinter.CTk):

    def report_callback_exception(self, exc, val, tb):
        """Capture tkinter callback exceptions with full traceback."""
        log_exception("Tk callback exception (TimeIn)", exc, val, tb)

    def __init__(self):

        super().__init__()
        self.title("Block Design Test")

        # Set window size based on display mode
        if DISPLAY_HALF:
            self.geometry("960x560")
        else:
            self.geometry("1200x800")  # Larger window for full display mode
        
        # Configure main grid with different weights based on display mode
        if DISPLAY_HALF:
            # Half display mode (4:1 ratio for top:bottom)
            self.grid_rowconfigure(0, weight=4)  # Top part (larger portion)
            self.grid_rowconfigure(1, weight=1)  # Bottom part (smaller portion)
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=1)
            
            # Create a container for the top half
            self.top_container = customtkinter.CTkFrame(self)
            self.top_container.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 150))
            self.top_container.grid_columnconfigure(0, weight=1)
            self.top_container.grid_columnconfigure(1, weight=1)
            self.top_container.grid_rowconfigure(0, weight=1)
            self.top_container.grid_rowconfigure(1, weight=0)  # For the button row
            
            # Content container for half display
            self.content_container = customtkinter.CTkFrame(self.top_container)
            self.content_container.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.content_container.grid_columnconfigure(0, weight=1)
            self.content_container.grid_columnconfigure(1, weight=1)
            self.content_container.grid_rowconfigure(0, weight=1)
        else:
            # Full display mode (use full window)
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=1)
            
            # Main container for full display
            self.top_container = customtkinter.CTkFrame(self)
            self.top_container.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
            self.top_container.grid_columnconfigure(0, weight=1)
            self.top_container.grid_columnconfigure(1, weight=1)
            self.top_container.grid_rowconfigure(0, weight=1)
            
            # Content container for full display
            self.content_container = customtkinter.CTkFrame(self.top_container)
            self.content_container.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.content_container.grid_columnconfigure(0, weight=1)
            self.content_container.grid_columnconfigure(1, weight=1)
            self.content_container.grid_rowconfigure(0, weight=1)

        # --------------------------------------------------- Design Section

        # Left side container for timer and design
        self.left_side = customtkinter.CTkFrame(self.content_container)
        
        # If camera is hidden, center the left_side by using columnspan
        if HIDE_CAMERA:
            # Center the design section by spanning both columns
            if DISPLAY_HALF:
                self.left_side.grid(row=0, column=0, columnspan=2, sticky="", padx=10, pady=10)
            else:
                self.left_side.grid(row=0, column=0, columnspan=2, sticky="", padx=20, pady=20)
        else:
            # Normal layout with camera on the right
            if DISPLAY_HALF:
                self.left_side.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            else:
                self.left_side.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            
        self.left_side.grid_rowconfigure(1, weight=1)
        self.left_side.grid_columnconfigure(1, weight=1)

        # Timer frame on the left side
        timer_width = 120 if DISPLAY_HALF else 150
        timer_font_size = 30 if DISPLAY_HALF else 36
        
        self.timer_frame = customtkinter.CTkFrame(self.left_side, corner_radius=6, fg_color="gray30", width=timer_width)
        self.timer_frame.grid(row=0, column=0, rowspan=2, padx=(0, 10), pady=10, sticky="ns")
        self.timer_frame.pack_propagate(False)
        
        # Timer label with larger font
        self.timer_label = customtkinter.CTkLabel(
            self.timer_frame, 
            text="00:00.00", 
            font=("Helvetica", timer_font_size, "bold"),
            text_color="white"
        )
        self.timer_label.pack(expand=True, fill="both")
        self.timer_running = False
        self.start_time = 0

        # Configure column weights for left_side (block design) and content_container (camera)
        self.left_side.grid_columnconfigure(1, weight=1)  # Block design column
        
        if not HIDE_CAMERA:
            self.content_container.grid_columnconfigure(1, weight=3)  # Camera column (3x wider than block design)
        else:
            # When camera is hidden, make both columns equal weight for centering
            self.content_container.grid_columnconfigure(0, weight=1)
            self.content_container.grid_columnconfigure(1, weight=1)

        # Design frames next to the timer
        self.design_frame_0 = TextFrame(self.left_side, "Block Design")
        self.design_frame_0.grid(row=0, column=1, padx=0, pady=(0, 5), sticky="nsew")

        self.design_frame_1 = ImageFrame(self.left_side, "")
        self.design_frame_1.grid(row=1, column=1, padx=0, pady=0, sticky="nsew")
        self.design_frame_1.grid_propagate(False)

        # --------------------------------------------------- Camera Section

        # Only create camera section if HIDE_CAMERA is False
        if not HIDE_CAMERA:
            camera_padx = 10 if DISPLAY_HALF else 20
            camera_pady = (40, 10) if DISPLAY_HALF else (50, 20)
            
            self.video_frame_0 = TextFrame(self.content_container, "Upper Table Camera")
            self.video_frame_0.grid(row=0, column=1, padx=camera_padx, pady=0, sticky="nsew")
            
            self.video_frame_1 = ImageFrame(self.content_container, "")
            self.video_frame_1.grid(row=0, column=1, padx=camera_padx, pady=camera_pady, sticky="nsew")
            self.video_frame_1.grid_propagate(False)
        else:
            # Camera hidden - set to None
            self.video_frame_0 = None
            self.video_frame_1 = None
            print(">>> HIDE_CAMERA enabled - Camera section hidden")
        
        # Adjust image sizes to fit the frames
        if DISPLAY_HALF:
            self.frame_width = 400
            self.frame_height = 400
        else:
            self.frame_width = 600
            self.frame_height = 600
        
        # Load and resize the initial image
        IMAGE_PATH = os.path.join(BASE_DIR, 'FILES', 'TEST_1000x1000', '0Bx.jpg')
        self.image = customtkinter.CTkImage(
            light_image=Image.open(IMAGE_PATH).resize((self.frame_width, self.frame_height), Image.Resampling.LANCZOS),
            size=(self.frame_width, self.frame_height)
        )
        # Create the label once and store it as an instance variable
        self.image_label = customtkinter.CTkLabel(master=self.design_frame_1, text='')
        self.image_label.pack(expand=True, fill="both")
        self.image_label.configure(image=self.image)

        # Camera label - Configure grid for video_frame_1 (only if camera not hidden)
        if not HIDE_CAMERA:
            self.video_frame_1.grid_rowconfigure(0, weight=1)
            self.video_frame_1.grid_columnconfigure(0, weight=1)
            
            # Create camera label with grid
            self.camera = customtkinter.CTkLabel(self.video_frame_1, text="", anchor="center")
            self.camera.grid(row=0, column=0, sticky="nsew")
        else:
            # Camera hidden - set to None
            self.camera = None

        # Add the start button
        button_font_size = 30 if DISPLAY_HALF else 36
        button_pady = 10 if DISPLAY_HALF else 20
        
        self.button_0 = customtkinter.CTkButton(
            self.top_container, 
            text="(START)", 
            font=("Helvetica", button_font_size), 
            command=self.button_0_callback
        )
        if DISPLAY_HALF:
            self.button_0.grid(row=1, column=0, columnspan=2, padx=20, pady=button_pady, sticky="ew")
        else:
            # In full mode, place the button at the bottom of the left panel
            self.button_0.grid(row=2, column=0, columnspan=2, padx=20, pady=button_pady, sticky="ew")

        # Bottom container (only used in half display mode)
        if DISPLAY_HALF:
            self.bottom_container = customtkinter.CTkFrame(self)
            self.bottom_container.grid(row=1, column=0, columnspan=2, sticky="nsew")

        #self.start_zero = time.time()
        #self.start_thumb = time.time()

        self.timer_task_all = []

        self.timer_task_01 = 0
        self.timer_task_02 = 0
        self.timer_task_03 = 0
        self.timer_task_04 = 0
        self.timer_task_05 = 0
        self.timer_task_06 = 0
        self.timer_task_07 = 0
        self.timer_task_08 = 0

        self.task_flag_01 = True
        self.task_flag_02 = True
        self.task_flag_03 = True
        self.task_flag_04 = True
        self.task_flag_05 = True
        self.task_flag_06 = True
        self.task_flag_07 = True
        self.task_flag_08 = True

        self.current_question = 1

        self.cognitive_age_list = []

        global nick_name
        global gender_code
        global age_range_code

        self.nick_name = nick_name
        self.gender_code = gender_code
        self.age_range_code = age_range_code

        self.retry_button = None

        #self.task_state = 1

        # Set the maximum level from environment variable
        self.max_level = MAX_LEVEL
        
        # Bind Enter key to skip level
        self.bind('<Return>', self.skip_current_level)
        
        # Initialize YOLO detection thread
        self.yolo_thread = YOLODetectionThread(model_yolo, USE_BANTAL_MODEL)
        self.yolo_thread.start()
        self.latest_detections = []
        self.frame_count = 0
        self.yolo_skip_frames = int(os.getenv('YOLO_SKIP_FRAMES', '2'))  # Process every 3rd frame
        
        # Initialize MediaPipe Hands once (not every frame)
        self.mp_hands_detector = None
        if mp_hands is not None:
            try:
                self.mp_hands_detector = mp_hands.Hands(
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                    max_num_hands=2
                )
            except Exception as e:
                print(f">>> Failed to initialize MediaPipe Hands: {e}. Hand landmark detection disabled.")
        
        # FPS monitoring
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        # Skip MediaPipe on same frames as YOLO for better performance
        self.mediapipe_skip_frames = int(os.getenv('MEDIAPIPE_SKIP_FRAMES', '2'))
        
        # Debug mode
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        # Button mode for image display control
        self.button_mode = BUTTON_MODE
        self.image_visible = False
        self.image_show_time = None
        self.image_display_duration = 5.0  # 5 seconds
        
        # Serial communication thread for button mode
        self.serial_thread = None
        if self.button_mode:
            print(">>> BUTTON_MODE enabled - Image will show for 5 seconds then hide")
            self.serial_thread = SerialReaderThread()
            self.serial_thread.start()
        
        # Cache for level images
        self.cached_level_images = {}
        self.preload_level_images()
        
        #SpeakTextG("赤と白の 4 つのブロックから表示されたデザインを作成してください。")
        #SpeakTextG("左手または利き手と反対の手で操作してください。")
        #SpeakTextG("準備ができたらスタートボタンを押してください。")
    
    def preload_level_images(self):
        """Preload and cache all level images to avoid I/O lag during gameplay"""
        print(">>> Preloading level images...")
        for variant, path in LEVEL_PATHS.items():
            try:
                img = Image.open(path)
                # Cache resized version for display
                self.cached_level_images[variant] = img.resize(
                    (self.frame_width, self.frame_height), 
                    Image.Resampling.LANCZOS
                )
            except Exception as e:
                print(f"Error loading {variant}: {e}")
        print(f">>> Cached {len(self.cached_level_images)} level images")
    
    def get_cached_level_image(self, variant):
        """Get cached level image or load if not cached"""
        if variant in self.cached_level_images:
            return self.cached_level_images[variant]
        else:
            # Fallback: load on demand
            try:
                img = Image.open(LEVEL_PATHS[variant])
                return img.resize((self.frame_width, self.frame_height), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"Error loading {variant}: {e}")
                return None

    def end_test(self):
        self.current_question = 9
        self.reset_timer()
        self.stop_timer()
        self.current_level_button.grid_remove()
        self.timer_task_avg = format(float(sum(self.timer_task_all) / len(self.timer_task_all)), ".3f")
        cognitive_age_avg = int(sum(self.cognitive_age_list) / len(self.cognitive_age_list))
        age_real = int(self.age_range_code)
        age_cog = cognitive_age_avg

        visuo_spatial = 100

        if age_cog <= age_real:
            visuo_spatial = 100 
        else:
            visuo_spatial = 100 - (age_cog - age_real)

        print("Your name is " + self.nick_name)
        print("Your gender is " + self.gender_code)
        print("Your Average Completed Time is " + str(self.timer_task_avg) + " second")
        print("Your Current Age is " + str(age_real) + " years")
        print("Your Cognitive Age is " + str(age_cog) + " years")
        print("Your Cognitive Fitness is " + str(visuo_spatial) + " %")

        play_audio("AUDIO/selesai.wav")
        time.sleep(3)

        # Generate SQL file for cronjob to execute
        try:
            import datetime
            
            # Create SQL directory if it doesn't exist
            sql_dir = Path('./cron/sql')
            sql_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename with timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            sql_filename = sql_dir / f'participant_{timestamp}.sql'
            
            # Prepare values
            name = self.nick_name.replace("'", "''")  # Escape single quotes
            real_age = int(self.age_range_code)
            gender = self.gender_code
            estimated_age = int(age_cog)
            cognitive_fitness = f"{visuo_spatial}%"
            avg_time_all = float(self.timer_task_avg)
            avg_time_1 = float(self.timer_task_all[0]) if len(self.timer_task_all) > 0 else 'NULL'
            avg_time_2 = float(self.timer_task_all[1]) if len(self.timer_task_all) > 1 else 'NULL'
            avg_time_3 = float(self.timer_task_all[2]) if len(self.timer_task_all) > 2 else 'NULL'
            avg_time_4 = float(self.timer_task_all[3]) if len(self.timer_task_all) > 3 else 'NULL'
            avg_time_5 = float(self.timer_task_all[4]) if len(self.timer_task_all) > 4 else 'NULL'
            avg_time_6 = float(self.timer_task_all[5]) if len(self.timer_task_all) > 5 else 'NULL'
            avg_time_7 = float(self.timer_task_all[6]) if len(self.timer_task_all) > 6 else 'NULL'
            avg_time_8 = float(self.timer_task_all[7]) if len(self.timer_task_all) > 7 else 'NULL'
            
            # Build SQL content
            sql_content = f"""-- Auto-generated SQL for participant data
-- Generated at: {datetime.datetime.now().isoformat()}

DO $$
DECLARE
    v_participant_id INTEGER;
    v_timestamp TIMESTAMP;
BEGIN
    -- Check if participant exists
    SELECT id INTO v_participant_id
    FROM bdt.participant_data
    WHERE LOWER(name) = LOWER('{name}')
    AND real_age = {real_age}
    AND gender = '{gender}'
    LIMIT 1;

    IF v_participant_id IS NOT NULL THEN
        -- Update existing participant
        UPDATE bdt.participant_data
        SET 
            estimated_cognitive_age = {estimated_age},
            cognitive_fitness = '{cognitive_fitness}',
            avg_time_all = {avg_time_all},
            avg_time_1 = {avg_time_1},
            avg_time_2 = {avg_time_2},
            avg_time_3 = {avg_time_3},
            avg_time_4 = {avg_time_4},
            avg_time_5 = {avg_time_5},
            avg_time_6 = {avg_time_6},
            avg_time_7 = {avg_time_7},
            avg_time_8 = {avg_time_8},
            updated_at = CURRENT_TIMESTAMP
        WHERE id = v_participant_id
        RETURNING updated_at INTO v_timestamp;

        -- Insert history record
        INSERT INTO bdt.participant_data_history (
            name, real_age, gender, estimated_cognitive_age,
            cognitive_fitness, avg_time_all, avg_time_1,
            avg_time_2, avg_time_3, avg_time_4, avg_time_5,
            avg_time_6, avg_time_7, avg_time_8, created_at
        ) VALUES (
            '{name}', {real_age}, '{gender}', {estimated_age},
            '{cognitive_fitness}', {avg_time_all}, {avg_time_1},
            {avg_time_2}, {avg_time_3}, {avg_time_4}, {avg_time_5},
            {avg_time_6}, {avg_time_7}, {avg_time_8}, v_timestamp
        );

        RAISE NOTICE 'Updated existing participant: %', '{name}';
    ELSE
        -- Insert new participant
        INSERT INTO bdt.participant_data (
            name, real_age, gender, estimated_cognitive_age,
            cognitive_fitness, avg_time_all, avg_time_1,
            avg_time_2, avg_time_3, avg_time_4, avg_time_5,
            avg_time_6, avg_time_7, avg_time_8, created_at
        ) VALUES (
            '{name}', {real_age}, '{gender}', {estimated_age},
            '{cognitive_fitness}', {avg_time_all}, {avg_time_1},
            {avg_time_2}, {avg_time_3}, {avg_time_4}, {avg_time_5},
            {avg_time_6}, {avg_time_7}, {avg_time_8}, CURRENT_TIMESTAMP
        )
        RETURNING created_at INTO v_timestamp;

        -- Insert initial history record
        INSERT INTO bdt.participant_data_history (
            name, real_age, gender, estimated_cognitive_age,
            cognitive_fitness, avg_time_all, avg_time_1,
            avg_time_2, avg_time_3, avg_time_4, avg_time_5,
            avg_time_6, avg_time_7, avg_time_8, created_at
        ) VALUES (
            '{name}', {real_age}, '{gender}', {estimated_age},
            '{cognitive_fitness}', {avg_time_all}, {avg_time_1},
            {avg_time_2}, {avg_time_3}, {avg_time_4}, {avg_time_5},
            {avg_time_6}, {avg_time_7}, {avg_time_8}, v_timestamp
        );

        RAISE NOTICE 'Inserted new participant: %', '{name}';
    END IF;
END $$;
"""
            
            # Write SQL file
            with open(sql_filename, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            
            print(f">>> SQL file generated: {sql_filename}")
            print(">>> Cronjob will execute this file automatically")
            
        except Exception as e:
            print(">>> Error generating SQL file:")
            print(f"Error: {e}")

        IMAGE_PATH = os.path.join(BASE_DIR, 'FILES', 'TEST_1000x1000', '09.jpg')
        self.image = customtkinter.CTkImage(light_image=Image.open(IMAGE_PATH), size=(self.frame_width, self.frame_height))
        self.image_label.configure(image=self.image)
        self.show_retry_button()
    
    def skip_current_level(self, event=None):
        """Skip the current level when Enter key is pressed"""
        if not hasattr(self, 'current_question') or not hasattr(self, 'timer_running') or not self.timer_running:
            return
            
        current_time = time.time()
        time_elapsed = round((current_time - self.start_task), 2)
        
        print(f"Skipping level {self.current_question} after {time_elapsed} seconds")
        
        # Record the actual time taken for the level
        if self.current_question == 1 and self.task_flag_01:
            self.timer_task_01 = time_elapsed
            self.timer_task_all.append(self.timer_task_01)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_01))
            self.task_flag_01 = False
            print(f"TASK 1 SKIPPED after {self.timer_task_01} seconds")
            if int(self.timer_task_01) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_01) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_01) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_01) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_01) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            # tts_indo("Jangan menyerah.")
            if self.max_level != 1:
                play_audio("AUDIO/lanjut_lvl2.wav")
            self.current_question = 2
            
        elif self.current_question == 2 and self.task_flag_02:
            self.timer_task_02 = time_elapsed
            self.timer_task_all.append(self.timer_task_02)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_02))
            self.task_flag_02 = False
            print(f"TASK 2 SKIPPED after {self.timer_task_02} seconds")
            if int(self.timer_task_02) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_02) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_02) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_02) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_02) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            # tts_indo("Jangan menyerah.")
            if self.max_level != 2:
                play_audio("AUDIO/lanjut_lvl3.wav")
            self.current_question = 3
            
        # Add more levels as needed (up to 8)
        elif self.current_question == 3 and self.task_flag_03:
            self.timer_task_03 = time_elapsed
            self.timer_task_all.append(self.timer_task_03)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_03))
            self.task_flag_03 = False
            print(f"TASK 3 SKIPPED after {self.timer_task_03} seconds")
            if int(self.timer_task_03) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_03) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_03) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_03) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_03) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            # tts_indo("Jangan menyerah.")
            if self.max_level != 3:
                play_audio("AUDIO/lanjut_lvl4.wav")
            self.current_question = 4
            
        elif self.current_question == 4 and self.task_flag_04:
            self.timer_task_04 = time_elapsed
            self.timer_task_all.append(self.timer_task_04)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_04))
            self.task_flag_04 = False
            print(f"TASK 4 SKIPPED after {self.timer_task_04} seconds")
            if int(self.timer_task_04) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_04) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_04) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_04) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_04) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            # tts_indo("Jangan menyerah.")
            if self.max_level != 4:
                play_audio("AUDIO/lanjut_lvl5.wav")
            self.current_question = 5
            
        elif self.current_question == 5 and self.task_flag_05:
            self.timer_task_05 = time_elapsed
            self.timer_task_all.append(self.timer_task_05)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_05))
            self.task_flag_05 = False
            print(f"TASK 5 SKIPPED after {self.timer_task_05} seconds")
            if int(self.timer_task_05) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_05) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_05) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_05) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_05) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            # tts_indo("Jangan menyerah.")
            if self.max_level != 5:
                play_audio("AUDIO/lanjut_lvl6.wav")
            self.current_question = 6
            
        elif self.current_question == 6 and self.task_flag_06:
            self.timer_task_06 = time_elapsed
            self.timer_task_all.append(self.timer_task_06)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_06))
            self.task_flag_06 = False
            print(f"TASK 6 SKIPPED after {self.timer_task_06} seconds")
            if int(self.timer_task_06) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_06) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_06) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_06) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_06) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            # tts_indo("Jangan menyerah.")
            if self.max_level != 6:
                play_audio("AUDIO/lanjut_lvl7.wav")
            self.current_question = 7
            
        elif self.current_question == 7 and self.task_flag_07:
            self.timer_task_07 = time_elapsed
            self.timer_task_all.append(self.timer_task_07)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_07))
            self.task_flag_07 = False
            print(f"TASK 7 SKIPPED after {self.timer_task_07} seconds")
            if int(self.timer_task_07) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_07) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_07) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_07) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_07) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            # tts_indo("Jangan menyerah.")
            if self.max_level != 7:
                play_audio("AUDIO/lanjut_lvl8.wav")
            self.current_question = 8
            
        elif self.current_question == 8 and self.task_flag_08:
            self.timer_task_08 = time_elapsed
            self.timer_task_all.append(self.timer_task_08)
            self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_08))
            self.task_flag_08 = False
            print(f"TASK 8 SKIPPED after {self.timer_task_08} seconds")
            if int(self.timer_task_08) < 10:
                play_audio("AUDIO/menakjubkan.wav")
            # tts_indo("Menakjubkan.")
            elif int(self.timer_task_08) < 15:
                play_audio("AUDIO/hebat_sekali.wav")
            # tts_indo("Hebat sekali.")
            elif int(self.timer_task_08) < 20:
                play_audio("AUDIO/mantap.wav")
            # tts_indo("Mantap.")
            elif int(self.timer_task_08) < 25:
                play_audio("AUDIO/kerja_bagus.wav")
            # tts_indo("Kerja bagus.")
            elif int(self.timer_task_08) < 30:
                play_audio("AUDIO/ayo_semangat.wav")
            # tts_indo("Ayo semangat.")
            else:
                play_audio("AUDIO/jangan_menyerah.wav")
            self.current_question = 9
            # tts_indo("Jangan menyerah.")
            # No need to change current_question as this is the last level
        
        # Update the display for the next level if not the last level
        if 1 <= self.current_question <= self.max_level:
            variant = self.get_random_variant(self.current_question)
            self.current_variant = variant
            
            # Load image with button mode support
            self.load_level_image(variant)
            self.current_level_button.grid_remove()
            self.show_current_level_button(self.current_question)
            # Reset the start time for the next level
            self.start_task = time.time()
            self.reset_timer()
            self.start_timer()
        elif self.current_question > self.max_level:
            self.end_test()
    
    def get_random_variant(self, level):
        """Get a variant for the specified level, using custom levels if available."""
        # If we have a custom level defined, use it
        if level in CUSTOM_LEVELS:
            return CUSTOM_LEVELS[level]
            
        # Otherwise, choose a random variant (a-d)
        variants = ['a', 'b', 'c', 'd']
        return f"{level}{random.choice(variants)}"

    def button_0_callback(self):

        # Hide the start button
        self.button_0.grid_remove()
        # Show the current level button in the same position
        self.show_current_level_button(self.current_question)
        
        play_audio("AUDIO/hitung_mundur.wav")
        # tts_indo("Permainan akan dimulai dalam. tiga, dua, satu, mulai.")
        print("START")
        #self.start_task = time.time()
        
        # Load and resize the initial image
        variant = self.get_random_variant(self.current_question)
        self.current_variant = variant
        
        # Use helper method to load image with button mode support
        self.load_level_image(variant)
        
        self.start_task = time.time()
        self.streaming()

        # Reset and start the timer
        self.reset_timer()
        self.start_timer()

    #def button_1_callback(self):

        #os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)
        #sys.exit() 



    def estimate_cognitive_age(self, time_finish_one_task):
        
        from sklearn.preprocessing import PolynomialFeatures
        from sklearn.linear_model import LinearRegression

        # Transform the input features to higher-degree polynomials, Create a polynomial regression model
        # Fit the model to the transformed data, Predict y values for new x values

        degree = 2
        poly_features = PolynomialFeatures(degree=degree)

        #x_time      = np.array([13, 14, 15, 16, 17, 18, 22, 25, 30, 33, 37, 40, 45, 50]).reshape(-1, 1)
        
        x_time      = np.array([ 9, 10, 11, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50]).reshape(-1, 1)
        y_age       = np.array([20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85])

        time_avg = time_finish_one_task # * 1.5  # second

        x_time_poly = poly_features.fit_transform(x_time)
        model_time = LinearRegression()
        model_time.fit(x_time_poly, y_age)

        new_x_time = np.array([time_avg]).reshape(-1, 1)
        new_x_time_poly = poly_features.transform(new_x_time)
        cognitive_age = model_time.predict(new_x_time_poly)

        #print(cognitive_age)

        if (cognitive_age < 20):
            cognitive_age = 20
        elif (cognitive_age > 85):
            cognitive_age = 90
        
        cognitive_age = int(cognitive_age)

        return cognitive_age #.tolist()[0]

        #print("Estimated Cognitive Age : " + str(round(cognitive_age[0], 1)) + " years")

    def show_current_level_button(self, level):
        self.current_level_button = customtkinter.CTkButton(
            self.top_container,
            text="Level " + str(level),
            font=("Helvetica", 30)
        )
        
        self.current_level_button.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
    
    def show_retry_button(self):
        self.retry_button = customtkinter.CTkButton(
            self.top_container,
            text="Retry Test",
            font=("Helvetica", 30),
            command=self.retry_test
        )
        
        # Position the retry button in the same place as the start button was
        self.retry_button.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

    def retry_test(self):
        # Reset the application state
        self.destroy()  # Close the current window
        # Restart the application
        app_input = App_Input()
        app_input.mainloop()

        if nick_name:  # Only proceed if user provided input
            app = TimeIn()
            app.after(0, lambda:app.state('zoomed'))
            app.mainloop()

    def update_timer(self):
        if self.timer_running:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            milliseconds = int((elapsed % 1) * 100)
            self.timer_label.configure(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")
            self.after(50, self.update_timer)  # Reduced from 10ms to 50ms

    def start_timer(self):
        if not self.timer_running:
            self.start_time = time.time()
            self.timer_running = True
            self.update_timer()

    def stop_timer(self):
        self.timer_running = False

    def reset_timer(self):
        self.timer_label.configure(text="00:00.00")
        self.timer_running = False

    def load_level_image(self, variant):
        """Load level image with button mode support"""
        # Load cached image
        cached_img = self.get_cached_level_image(variant)
        if cached_img:
            self.image = customtkinter.CTkImage(
                light_image=cached_img,
                size=(self.frame_width, self.frame_height)
            )
        
        # Button mode: Show image for 5 seconds then hide
        if self.button_mode:
            self.image_label.configure(image=self.image)
            self.image_visible = True
            self.image_show_time = time.time()
            print(">>> Image displayed (will hide after 5 seconds)")
        else:
            # Normal mode: Always show image
            self.image_label.configure(image=self.image)
    
    def handle_button_mode(self):
        """Handle button mode image visibility logic"""
        if not self.button_mode:
            return
        
        # Check if image should be hidden after 5 seconds
        if self.image_visible and self.image_show_time:
            elapsed = time.time() - self.image_show_time
            if elapsed >= self.image_display_duration:
                # Hide image by showing blank
                blank_image = Image.new('RGB', (self.frame_width, self.frame_height), color='gray')
                self.image = customtkinter.CTkImage(
                    light_image=blank_image,
                    size=(self.frame_width, self.frame_height)
                )
                self.image_label.configure(image=self.image)
                self.image_visible = False
                self.image_show_time = None
                print(">>> Image hidden (press button to show again)")
        
        # Check for button press from ESP32
        if self.serial_thread:
            message = self.serial_thread.get_message()
            if message == "disable_image" and not self.image_visible:
                # Show image again for 5 seconds
                variant = self.current_variant
                cached_img = self.get_cached_level_image(variant)
                if cached_img:
                    self.image = customtkinter.CTkImage(
                        light_image=cached_img,
                        size=(self.frame_width, self.frame_height)
                    )
                self.image_label.configure(image=self.image)
                self.image_visible = True
                self.image_show_time = time.time()
                print(">>> Button pressed - Image displayed (will hide after 5 seconds)")
    
    # code for video streaming
    def streaming(self):

        self.button_0._state = "disabled"

        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame from camera")
            self.after(100, self.streaming)
            return
            
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Handle button mode image visibility
        self.handle_button_mode()
        # Don't resize to 1000x800, use original resolution for better performance
        # frame = cv2.resize(frame, (1000, 800))

        # --------------------------------------------------------------------------- Start Process

        # Frame threshold 
        imgBlur = cv2.GaussianBlur(frame, (7,7), 1)
        imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_RGB2GRAY)
        ret, imgThres = cv2.threshold(imgGray, 175, 255, cv2.THRESH_BINARY) #175   195
        
        # Make detections using background thread (non-blocking)
        self.frame_count += 1
        
        # Only submit frame to YOLO every N frames to reduce load
        if self.frame_count % (self.yolo_skip_frames + 1) == 0:
            if self.yolo_thread.frame_queue.empty():  # Only if queue is empty
                try:
                    # MUST copy frame to avoid race condition with drawing operations
                    # Use numpy copy which is faster than frame.copy()
                    frame_for_yolo = np.array(frame, copy=True)
                    self.yolo_thread.frame_queue.put_nowait(frame_for_yolo)
                except:
                    pass  # Queue full, skip this frame
        
        # Get latest detection results if available (non-blocking)
        if not self.yolo_thread.result_queue.empty():
            try:
                self.latest_detections = self.yolo_thread.result_queue.get_nowait()
            except:
                pass
        
        # Use latest detections (may be from previous frame, but that's OK)
        list_tracked_objects = self.latest_detections

        #if len(list_tracked_objects) == 4: #>0
        
        box_num = 0
        box_face = 0
        box_list = []
        box_design = []
        box_distance = []
        box_design_sort = []

        box_near_hand = []
        #avg_confidence = []

        pos_x = []
        pos_y = []

        for x1, y1, x2, y2, conf_pred, cls_id, cls in list_tracked_objects:

            if conf_pred > 0.7:

                #avg_confidence.append( round(conf_pred,2) )

                center_x = int ((x1+x2)/2)
                center_y = int ((y1+y2)/2)
                x1 = int(x1)
                x2 = int(x2)
                y1 = int(y1)
                y2 = int(y2)
                w = int (x2-x1)
                h = int (y2-y1)

                box_distance.append( int (math.sqrt( pow(center_x, 2) + pow(center_y, 2) )) )
                #print(center_x, center_y)

                pos_x.append( int (center_x) )
                pos_y.append( int (center_y) )
                
                # Optimize: check bounds before resize to avoid errors
                if y1 >= 0 and y2 <= imgThres.shape[0] and x1 >= 0 and x2 <= imgThres.shape[1] and (y2-y1) > 0 and (x2-x1) > 0:
                    dim = (100, 100)
                    imgBox = cv2.resize(imgThres[y1:y2, x1:x2], dim, interpolation = cv2.INTER_AREA)
                else:
                    # Skip invalid box
                    continue
                #cv2.imshow("Box_"+str(box_num), imgBox)
                
                box_class = [ imgBox[50,25], imgBox[75,50], imgBox[50,75], imgBox[25,50] ]

                if box_class == [0,0,0,0] :
                    box_face = 1
                    box_design.append(1)
                elif box_class == [255,255,255,255]:
                    box_face = 2
                    box_design.append(2)
                #... dipisah
                elif box_class == [255,255,0,0]:
                    box_face = 3
                    box_design.append(3)  
                elif box_class == [255,0,0,255]:
                    box_face = 4
                    box_design.append(4)  
                elif box_class == [0,0,255,255]:
                    box_face = 5
                    box_design.append(5)  
                elif box_class == [0,255,255,0]:
                    box_face = 6
                    box_design.append(6)               
                
                cv2.rectangle(frame, (x1,y1), (x1+w, y1+h), (0, 255, 0), 2)

                box_num = box_num + 1
                roi_label = frame[y1:y1+50, x1:x1+50]

                if(box_face == 1):
                    try:                            
                        roi_label [np.where(mask_face_01)] = 0
                        roi_label += face_01
                    except IndexError:
                        pass
                elif(box_face == 2):
                    try:                            
                        roi_label [np.where(mask_face_02)] = 0
                        roi_label += face_02
                    except IndexError:
                        pass
                elif(box_face == 3):
                    try:                            
                        roi_label [np.where(mask_face_03)] = 0
                        roi_label += face_03
                    except IndexError:
                        pass
                elif(box_face == 4):
                    try:                            
                        roi_label [np.where(mask_face_04)] = 0
                        roi_label += face_04
                    except IndexError:
                        pass
                elif(box_face == 5):
                    try:                            
                        roi_label [np.where(mask_face_05)] = 0
                        roi_label += face_05
                    except IndexError:
                        pass
                elif(box_face == 6):
                    try:                            
                        roi_label [np.where(mask_face_06)] = 0
                        roi_label += face_06
                    except IndexError:
                        pass

        
        # >>>>>>>>>>>>

        if len(box_design) == 4 and len(box_distance) == 4:

            box_0 = (pos_x[0], pos_y[0])
            box_1 = (pos_x[1], pos_y[1])
            box_2 = (pos_x[2], pos_y[2])
            box_3 = (pos_x[3], pos_y[3])

            # Draw lines connecting boxes (optimized with polylines)
            pts = np.array([
                [pos_x[0], pos_y[0]],
                [pos_x[1], pos_y[1]],
                [pos_x[2], pos_y[2]],
                [pos_x[3], pos_y[3]]
            ], np.int32)
            # Draw all connecting lines at once
            for i in range(4):
                for j in range(i+1, 4):
                    cv2.line(frame, tuple(pts[i]), tuple(pts[j]), (0, 0, 0), 2)

            #pos_x_order = [ pos_x[0], pos_x[1], pos_x[2], pos_x[3] ]
            #pos_y_order = [ pos_y[0], pos_y[1], pos_y[2], pos_y[3] ]

            len_0 = int (math.sqrt( (pos_x[0]-pos_x[1])**2 + (pos_y[0]-pos_y[1])**2 ) )
            len_1 = int (math.sqrt( (pos_x[1]-pos_x[2])**2 + (pos_y[1]-pos_y[2])**2 ) )
            len_2 = int (math.sqrt( (pos_x[2]-pos_x[3])**2 + (pos_y[2]-pos_y[3])**2 ) )
            len_3 = int (math.sqrt( (pos_x[3]-pos_x[0])**2 + (pos_y[3]-pos_y[0])**2 ) )
            len_4 = int (math.sqrt( (pos_x[0]-pos_x[2])**2 + (pos_y[0]-pos_y[2])**2 ) )
            len_5 = int (math.sqrt( (pos_x[1]-pos_x[3])**2 + (pos_y[1]-pos_y[3])**2 ) )

            # Order Len
            len_order = [ len_0, len_1, len_2, len_3, len_4, len_5 ]
            len_rect = sorted(len_order)

            #print(len_rect)

            if  ( abs(len_rect[0] - len_rect[1]) < 100) and \
                ( abs(len_rect[0] - len_rect[2]) < 100) and \
                ( abs(len_rect[0] - len_rect[3]) < 100) and \
                ( abs(len_rect[1] - len_rect[2]) < 100) and \
                ( abs(len_rect[1] - len_rect[3]) < 100) and \
                ( abs(len_rect[2] - len_rect[3]) < 100):

                # 1. Gabungkan posisi x, y, dan index asli
                indexed_positions = [(pos_x[i], pos_y[i], i) for i in range(len(pos_x))]

                # 2. Urutkan berdasarkan x untuk memisahkan kelompok kiri dan kanan
                sorted_by_x = sorted(pos_x)
                mid_point = (sorted_by_x[1] + sorted_by_x[2]) / 2  # Titik tengah antara x terbesar kedua dan terkecil kedua

                # 3. Urutkan: kelompok kiri (x < mid_point) dulu, lalu kelompok kanan, dalam setiap kelompok urutkan berdasarkan y
                indexed_positions.sort(key=lambda p: (p[0] >= mid_point, p[1]))

                # 4. Ambil index asli yang sudah terurut
                sort_index = [idx for (x, y, idx) in indexed_positions]

                # 5. Urutkan box_design berdasarkan index yang sudah diurutkan
                box_design_sort = [box_design[i] for i in sort_index]

                current_answer = LEVEL_ANSWERS.get(self.current_variant, [])    
                if self.current_question == 1 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_01)] = 0
                    test_label += img_01
                    
                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_01):
                        end_task = time.time()
                        self.timer_task_01 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_01)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_01))

                        print ("TASK 1 COMPLETED in " + str(self.timer_task_01) +" seconds")
                        # tts_indo("Level satu selesai dalam " + number_to_words_id(int(self.timer_task_01)) +" detik.")

                        if int(self.timer_task_01) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_01) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_01) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_01) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_01) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        if self.max_level == 1:
                            self.end_test()
                        else:
                            play_audio("AUDIO/lanjut_lvl2.wav")
                            # tts_indo("Lanjut ke level dua.")

                            #IMAGE_WIDTH = 650
                            #IMAGE_HEIGHT = 650
                            self.current_question = 2
                            variant = self.get_random_variant(self.current_question)
                            self.current_variant = variant
                            current_answer = LEVEL_ANSWERS.get(self.current_variant, [])
            
                            # Load image with button mode support
                            self.load_level_image(variant)
                            self.current_level_button.grid_remove()
                            self.show_current_level_button(self.current_question)
                            self.task_flag_01 = False
                            self.start_task = time.time()
                            # Reset and start the timer
                            self.reset_timer()
                            self.start_timer()

                    # Detect Thumb
                    """
                    if (thumb_state == 1 and thumb_flag_01 == True):
                        end_thumb = time.time()
                        timer_thumb = end_thumb - start_thumb
                        t_thumb_04 = round((timer_thumb - self.timer_task_04), 2)
                        t_thumb_all.append(t_thumb_04)

                        start_thumb = time.time()
                        thumb_flag_04 = False

                        timer_speak = self.timer_task_04
                        if timer_speak < 10:
                            SpeakTextG("Amazing.")
                        if timer_speak < 15:
                            SpeakTextG("Awesome.")
                        elif timer_speak < 20:
                            SpeakTextG("Great.")
                        elif timer_speak < 25:
                            SpeakTextG("Good job.")
                        elif timer_speak < 30:
                            SpeakTextG("Well done.")
                        else:
                            SpeakTextG("Give your best.")
                    """

                elif self.current_question == 2 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_02)] = 0
                    test_label += img_02
                    
                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_02):
                        end_task = time.time()
                        self.timer_task_02 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_02)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_02))

                        print ("TASK 2 COMPLETED in " + str(self.timer_task_02) +" seconds")
                        # tts_indo("Level dua selesai dalam " + number_to_words_id(int(self.timer_task_02)) +" detik.")

                        if int(self.timer_task_02) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_02) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_02) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_02) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_02) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        if self.max_level == 2:
                            self.end_test()
                        else:
                            play_audio("AUDIO/lanjut_lvl3.wav")
                            # tts_indo("Lanjut ke level tiga")

                            #IMAGE_WIDTH = 650
                            #IMAGE_HEIGHT = 650
                            self.current_question = 3
                            variant = self.get_random_variant(self.current_question)
                            self.current_variant = variant
                            current_answer = LEVEL_ANSWERS.get(self.current_variant, [])
            
                            # Load image with button mode support
                            self.load_level_image(variant)
                            self.current_level_button.grid_remove()
                            self.show_current_level_button(self.current_question)
                            self.task_flag_02 = False
                            self.start_task = time.time()
                            # Reset and start the timer
                            self.reset_timer()
                            self.start_timer()

                    # Detect Thumb
                    """
                    if (thumb_state == 1 and thumb_flag_04 == True):
                        end_thumb = time.time()
                        timer_thumb = end_thumb - start_thumb
                        t_thumb_04 = round((timer_thumb - self.timer_task_04), 2)
                        t_thumb_all.append(t_thumb_04)

                        start_thumb = time.time()
                        thumb_flag_04 = False

                        timer_speak = self.timer_task_04
                        if timer_speak < 10:
                            SpeakTextG("Amazing.")
                        if timer_speak < 15:
                            SpeakTextG("Awesome.")
                        elif timer_speak < 20:
                            SpeakTextG("Great.")
                        elif timer_speak < 25:
                            SpeakTextG("Good job.")
                        elif timer_speak < 30:
                            SpeakTextG("Well done.")
                        else:
                            SpeakTextG("Give your best.")
                    """
                
                elif self.current_question == 3 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_03)] = 0
                    test_label += img_03
                    
                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_03):
                        end_task = time.time()
                        self.timer_task_03 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_03)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_03))

                        print ("TASK 3 COMPLETED in " + str(self.timer_task_03) +" seconds")
                        # tts_indo("Level tiga selesai dalam " + number_to_words_id(int(self.timer_task_03)) +" detik.")

                        if int(self.timer_task_03) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_03) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_03) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_03) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_03) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        if self.max_level == 3:
                            self.end_test()
                        else:
                            play_audio("AUDIO/lanjut_lvl4.wav")
                            # tts_indo("Lanjut ke level empat.")

                            #IMAGE_WIDTH = 650
                            #IMAGE_HEIGHT = 650
                            self.current_question = 4
                            variant = self.get_random_variant(self.current_question)
                            self.current_variant = variant
                            current_answer = LEVEL_ANSWERS.get(self.current_variant, [])
            
                            # Load image with button mode support
                            self.load_level_image(variant)
                            self.current_level_button.grid_remove()
                            self.show_current_level_button(self.current_question)
                            self.task_flag_03 = False
                            self.start_task = time.time()
                            # Reset and start the timer
                            self.reset_timer()
                            self.start_timer()

                    # Detect Thumb
                    """
                    if (thumb_state == 1 and thumb_flag_04 == True):
                        end_thumb = time.time()
                        timer_thumb = end_thumb - start_thumb
                        t_thumb_04 = round((timer_thumb - self.timer_task_04), 2)
                        t_thumb_all.append(t_thumb_04)

                        start_thumb = time.time()
                        thumb_flag_04 = False

                        timer_speak = self.timer_task_04
                        if timer_speak < 10:
                            SpeakTextG("Amazing.")
                        if timer_speak < 15:
                            SpeakTextG("Awesome.")
                        elif timer_speak < 20:
                            SpeakTextG("Great.")
                        elif timer_speak < 25:
                            SpeakTextG("Good job.")
                        elif timer_speak < 30:
                            SpeakTextG("Well done.")
                        else:
                            SpeakTextG("Give your best.")
                    """    

                elif self.current_question == 4 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_04)] = 0
                    test_label += img_04
                    
                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_04):
                        end_task = time.time()
                        self.timer_task_04 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_04)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_04))

                        print ("TASK 4 COMPLETED in " + str(self.timer_task_04) +" seconds")
                        # tts_indo("Level empat selesai dalam " + number_to_words_id(int(self.timer_task_04)) +" detik.")

                        if int(self.timer_task_04) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_04) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_04) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_04) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_04) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        if self.max_level == 4:
                            self.end_test()
                        else:
                            play_audio("AUDIO/lanjut_lvl5.wav")
                            # tts_indo("Lanjut ke level lima")

                            #IMAGE_WIDTH = 650
                            #IMAGE_HEIGHT = 650
                            self.current_question = 5
                            variant = self.get_random_variant(self.current_question)
                            self.current_variant = variant
                            current_answer = LEVEL_ANSWERS.get(self.current_variant, [])
            
                            # Load image with button mode support
                            self.load_level_image(variant)
                            self.current_level_button.grid_remove()
                            self.show_current_level_button(self.current_question)
                            self.task_flag_04 = False
                            self.start_task = time.time()
                            # Reset and start the timer
                            self.reset_timer()
                            self.start_timer()

                    # Detect Thumb
                    """
                    if (thumb_state == 1 and thumb_flag_04 == True):
                        end_thumb = time.time()
                        timer_thumb = end_thumb - start_thumb
                        t_thumb_04 = round((timer_thumb - self.timer_task_04), 2)
                        t_thumb_all.append(t_thumb_04)

                        start_thumb = time.time()
                        thumb_flag_04 = False

                        timer_speak = self.timer_task_04
                        if timer_speak < 10:
                            SpeakTextG("Amazing.")
                        if timer_speak < 15:
                            SpeakTextG("Awesome.")
                        elif timer_speak < 20:
                            SpeakTextG("Great.")
                        elif timer_speak < 25:
                            SpeakTextG("Good job.")
                        elif timer_speak < 30:
                            SpeakTextG("Well done.")
                        else:
                            SpeakTextG("Give your best.")
                    """


                elif self.current_question == 5 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_05)] = 0
                    test_label += img_05

                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_05):
                        end_task = time.time()
                        self.timer_task_05 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_05)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_05))

                        print ("TASK 5 COMPLETED in " + str(self.timer_task_05) +" seconds")
                        # tts_indo("Level lima selesai dalam " + number_to_words_id(int(self.timer_task_05)) +" detik.")

                        if int(self.timer_task_05) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_05) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_05) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_05) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_05) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        if self.max_level == 5:
                            self.end_test()
                        else:
                            play_audio("AUDIO/lanjut_lvl6.wav")
                            # tts_indo("Lanjut ke level enam.")

                            #IMAGE_WIDTH = 650
                            #IMAGE_HEIGHT = 650
                            self.current_question = 6
                            variant = self.get_random_variant(self.current_question)
                            self.current_variant = variant
                            current_answer = LEVEL_ANSWERS.get(self.current_variant, [])
            
                            # Load image with button mode support
                            self.load_level_image(variant)
                            self.current_level_button.grid_remove()
                            self.show_current_level_button(self.current_question)
                            self.task_flag_05 = False
                            self.start_task = time.time()
                            # Reset and start the timer
                            self.reset_timer()
                            self.start_timer()
                    
                    # Detect Thumb
                    """
                    if (thumb_state == 1 and thumb_flag_05 == True):
                        end_thumb = time.time()
                        timer_thumb = end_thumb - start_thumb
                        t_thumb_05 = round((timer_thumb - self.timer_task_05), 2)
                        t_thumb_all.append(t_thumb_05)

                        start_thumb = time.time()
                        thumb_flag_05 = False

                        timer_speak = self.timer_task_05
                        if timer_speak < 10:
                            SpeakTextG("Amazing.")
                        if timer_speak < 15:
                            SpeakTextG("Awesome.")
                        elif timer_speak < 20:
                            SpeakTextG("Great.")
                        elif timer_speak < 25:
                            SpeakTextG("Good job.")
                        elif timer_speak < 30:
                            SpeakTextG("Well done.")
                        else:
                            SpeakTextG("Give your best.")
                    """


                elif self.current_question == 6 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_06)] = 0
                    test_label += img_06

                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_06):
                        end_task = time.time()
                        self.timer_task_06 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_06)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_06))

                        print ("TASK 6 COMPLETED in " + str(self.timer_task_06) +" seconds")
                        # tts_indo("Level enam selesai dalam " + number_to_words_id(int(self.timer_task_06)) +" detik.")

                        if int(self.timer_task_06) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_06) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_06) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_06) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_06) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        if self.max_level == 6:
                            self.end_test()
                        else:
                            play_audio("AUDIO/lanjut_lvl7.wav")
                            # tts_indo("Lanjut ke level tujuh.")

                            #IMAGE_WIDTH = 650
                            #IMAGE_HEIGHT = 650
                            self.current_question = 7
                            variant = self.get_random_variant(self.current_question)
                            self.current_variant = variant
                            current_answer = LEVEL_ANSWERS.get(self.current_variant, [])
            
                            # Load image with button mode support
                            self.load_level_image(variant)
                            self.current_level_button.grid_remove()
                            self.show_current_level_button(self.current_question)
                            self.task_flag_06 = False
                            self.start_task = time.time()
                            # Reset and start the timer
                            self.reset_timer()
                            self.start_timer()

                    # Detect Thumb
                    """
                    if (thumb_state == 1 and thumb_flag_06 == True):
                        end_thumb = time.time()
                        timer_thumb = end_thumb - start_thumb
                        t_thumb_06 = round((timer_thumb - self.timer_task_06), 2)
                        t_thumb_all.append(t_thumb_06)

                        start_thumb = time.time()
                        thumb_flag_06 = False
                    
                        timer_speak = self.timer_task_06
                        if timer_speak < 10:
                            SpeakTextG("Amazing.")
                        if timer_speak < 15:
                            SpeakTextG("Awesome.")
                        elif timer_speak < 20:
                            SpeakTextG("Great.")
                        elif timer_speak < 25:
                            SpeakTextG("Good job.")
                        elif timer_speak < 30:
                            SpeakTextG("Well done.")
                        else:
                            SpeakTextG("Give your best.")
                    """

                elif self.current_question == 7 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_07)] = 0
                    test_label += img_07
                    
                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_07):
                        end_task = time.time()
                        self.timer_task_07 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_07)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_07))

                        print ("TASK 7 COMPLETED in " + str(self.timer_task_07) +" seconds")
                        # tts_indo("Level tujuh selesai dalam " + number_to_words_id(int(self.timer_task_07)) +" detik.")

                        if int(self.timer_task_07) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_07) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_07) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_07) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_07) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        if self.max_level == 7:
                            self.end_test()
                        else:
                            play_audio("AUDIO/lanjut_lvl8.wav")
                            # tts_indo("Lanjut ke level delapan.")

                            #IMAGE_WIDTH = 650
                            #IMAGE_HEIGHT = 650
                            self.current_question = 8
                            variant = self.get_random_variant(self.current_question)
                            self.current_variant = variant
                            current_answer = LEVEL_ANSWERS.get(self.current_variant, [])
            
                            # Load image with button mode support
                            self.load_level_image(variant)
                            self.current_level_button.grid_remove()
                            self.show_current_level_button(self.current_question)
                            self.task_flag_07 = False
                            self.start_task = time.time()
                            # Reset and start the timer
                            self.reset_timer()
                            self.start_timer()

                    # Detect Thumb
                    """
                    if (thumb_state == 1 and thumb_flag_04 == True):
                        end_thumb = time.time()
                        timer_thumb = end_thumb - start_thumb
                        t_thumb_04 = round((timer_thumb - self.timer_task_04), 2)
                        t_thumb_all.append(t_thumb_04)

                        start_thumb = time.time()
                        thumb_flag_04 = False

                        timer_speak = self.timer_task_04
                        if timer_speak < 10:
                            SpeakTextG("Amazing.")
                        if timer_speak < 15:
                            SpeakTextG("Awesome.")
                        elif timer_speak < 20:
                            SpeakTextG("Great.")
                        elif timer_speak < 25:
                            SpeakTextG("Good job.")
                        elif timer_speak < 30:
                            SpeakTextG("Well done.")
                        else:
                            SpeakTextG("Give your best.")
                    """

                elif self.current_question == 8 and box_design_sort == current_answer:
                    test_label = frame[20:120, 20:120]
                    test_label [np.where(mask_img_08)] = 0
                    test_label += img_08

                    #self.task_state = self.task_state + 1
                    
                    if(self.task_flag_08):
                        end_task = time.time()
                        self.timer_task_08 = round((end_task - self.start_task - timer_return), 2)
                        self.timer_task_all.append(self.timer_task_08)

                        self.cognitive_age_list.append(self.estimate_cognitive_age(self.timer_task_08))

                        print ("TASK 8 COMPLETED in " + str(self.timer_task_08) +" seconds")
                        # tts_indo("Level delapan selesai dalam " + number_to_words_id(int(self.timer_task_08)) +" detik.")

                        if int(self.timer_task_08) < 10:
                            play_audio("AUDIO/menakjubkan.wav")
                            # tts_indo("Menakjubkan.")
                        elif int(self.timer_task_08) < 15:
                            play_audio("AUDIO/hebat_sekali.wav")
                            # tts_indo("Hebat sekali.")
                        elif int(self.timer_task_08) < 20:
                            play_audio("AUDIO/mantap.wav")
                            # tts_indo("Mantap.")
                        elif int(self.timer_task_08) < 25:
                            play_audio("AUDIO/kerja_bagus.wav")
                            # tts_indo("Kerja bagus.")
                        elif int(self.timer_task_08) < 30:
                            play_audio("AUDIO/ayo_semangat.wav")
                            # tts_indo("Ayo semangat.")
                        else:
                            play_audio("AUDIO/jangan_menyerah.wav")
                            # tts_indo("Jangan menyerah.")

                        self.task_flag_08 = False
                        self.end_test()
                else:
                    #print ("NOT COMPLETE")
                    pass

                box_design = []
                box_distance = []
                box_design_sort = []
    


        # --------------------------------------------------------------------------- End Process

        # Use persistent MediaPipe Hands instance (not recreated every frame)
        # Skip MediaPipe on same frames as YOLO to reduce load
        if self.mp_hands_detector is not None and self.frame_count % (self.mediapipe_skip_frames + 1) == 0:
            # frame_rgb already in RGB format, no need to convert
            hand_result = self.mp_hands_detector.process(frame)

            if hand_result and hand_result.multi_hand_landmarks:
                for hand_landmarks in hand_result.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS, landmark_style, connection_style)

        # Update camera display only if camera is not hidden
        if not HIDE_CAMERA and self.camera is not None:
            # Convert frame to ImageTk format
            # img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img = Image.fromarray(frame)
            
            # Calculate aspect ratio
            frame_height, frame_width = frame.shape[:2]
            container_width = self.video_frame_1.winfo_width()
            container_height = self.video_frame_1.winfo_height()
            
            # Calculate scaling factor while maintaining aspect ratio
            width_ratio = container_width / frame_width
            height_ratio = container_height / frame_height
            scale = min(width_ratio, height_ratio)
            
            # Resize image if needed
            if scale < 1:
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            ImgTks = ImageTk.PhotoImage(image=img)
            self.camera.imgtk = ImgTks
            self.camera.configure(image=ImgTks)
        
        # FPS monitoring
        self.fps_counter += 1
        if time.time() - self.fps_start_time >= 1.0:
            self.current_fps = self.fps_counter
            
            # Enhanced FPS output with debug info
            if self.debug_mode:
                queue_size = self.yolo_thread.frame_queue.qsize()
                result_size = self.yolo_thread.result_queue.qsize()
                last_inference = self.yolo_thread.last_inference_time
                print(f"FPS: {self.current_fps} | YOLO: {last_inference:.1f}ms | Queue: {queue_size}/{result_size}")
            else:
                print(f"FPS: {self.current_fps}")
            
            self.fps_counter = 0
            self.fps_start_time = time.time()

        # Reduce delay for better responsiveness
        self.after(10, self.streaming)
    
    def cleanup(self):
        """Cleanup resources before closing"""
        print(">>> Cleaning up resources...")
        if hasattr(self, 'yolo_thread'):
            self.yolo_thread.stop()
        if hasattr(self, 'serial_thread') and self.serial_thread:
            self.serial_thread.stop()
        if hasattr(self, 'mp_hands_detector') and self.mp_hands_detector is not None:
            self.mp_hands_detector.close()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def destroy(self):
        """Override destroy to cleanup resources"""
        self.cleanup()
        super().destroy()