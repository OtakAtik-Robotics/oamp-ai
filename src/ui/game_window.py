import os
import time
import math
import random
import numpy as np
import cv2
import torch
import customtkinter
from PIL import Image, ImageTk

from src.api_client import send_game_session
from src.utils.audio import play_audio, play_feedback_audio
from src.utils.math_eval import estimate_cognitive_age
from src.ui.components import TextFrame, ImageFrame
from src.vision.blocks import YOLODetectionThread
from src.hardware.serial_io import SerialReaderThread

class TimeIn(customtkinter.CTk):
    def __init__(self, user_data, hardware_conn=None):
        super().__init__()
        
        self.nick_name = user_data.get("name", "")
        self.age_range_code = user_data.get("age", 0)
        self.gender_code = user_data.get("gender", "")
        self.serial_thread = hardware_conn

        self.setup_environment()
        self.setup_ui()
        self.setup_game_variables()
        self.setup_ai_models()
        self.preload_level_images()

    def setup_environment(self):
        self.display_half = os.getenv('DISPLAY_HALF', 'true').lower() == 'true'
        self.hide_camera = os.getenv('HIDE_CAMERA', 'false').lower() == 'true'
        self.button_mode = os.getenv('BUTTON_MODE', 'false').lower() == 'true'
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.max_level = int(os.getenv('MAX_LEVEL', '8'))
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    def setup_game_variables(self):
        self.timer_task_all = []
        self.cognitive_age_list = []
        self.task_flags = {i: True for i in range(1, self.max_level + 1)}
        self.current_question = 1
        self.timer_running = False
        self.start_time = 0
        self.start_task = 0
        self.frame_count = 0
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        self.image_visible = False
        self.image_show_time = None
        self.image_display_duration = 5.0
        self.latest_detections = []
        self.cached_level_images = {}
        
        self.level_answers = {
            '1a': [2,1,1,1], '1b': [2,1,1,2], '1c': [1,1,1,2], '1d': [1,2,2,1],
            '2a': [2,1,6,1], '2b': [3,2,1,2], '2c': [2,2,5,6], '2d': [6,2,2,6],
            '3a': [3,5,1,1], '3b': [1,5,1,6], '3c': [2,3,4,1], '3d': [6,5,3,4],
            '4a': [6,2,1,6], '4b': [3,2,2,5], '4c': [1,5,3,1], '4d': [4,2,2,6],
            '5a': [6,3,5,4], '5b': [5,4,6,3], '5c': [3,5,6,4], '5d': [4,4,6,6],
            '6a': [1,4,3,1], '6b': [6,1,5,5], '6c': [5,1,1,4], '6d': [5,4,4,5],
            '7a': [4,5,5,5], '7b': [4,5,5,6], '7c': [2,5,1,5], '7d': [1,2,3,6],
            '8a': [6,5,6,3], '8b': [6,3,4,2], '8c': [5,6,3,5], '8d': [3,6,5,4],
        }

    def setup_ui(self):
        self.title("Block Design Test")
        self.geometry("960x560" if self.display_half else "1200x800")
        
        self.grid_rowconfigure(0, weight=4 if self.display_half else 1)
        if self.display_half:
            self.grid_rowconfigure(1, weight=1)
            
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.top_container = customtkinter.CTkFrame(self)
        self.top_container.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 150) if self.display_half else 10)
        self.top_container.grid_columnconfigure(0, weight=1)
        self.top_container.grid_columnconfigure(1, weight=1)
        self.top_container.grid_rowconfigure(0, weight=1)

        self.content_container = customtkinter.CTkFrame(self.top_container)
        self.content_container.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(1, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.left_side = customtkinter.CTkFrame(self.content_container)
        self.left_side.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_side.grid_rowconfigure(1, weight=1)
        self.left_side.grid_columnconfigure(1, weight=1)

        self.timer_frame = customtkinter.CTkFrame(self.left_side, corner_radius=6, fg_color="gray30", width=120 if self.display_half else 150)
        self.timer_frame.grid(row=0, column=0, rowspan=2, padx=(0, 10), pady=10, sticky="ns")
        self.timer_frame.pack_propagate(False)
        
        self.timer_label = customtkinter.CTkLabel(self.timer_frame, text="00:00.00", font=("Helvetica", 30, "bold"), text_color="white")
        self.timer_label.pack(expand=True, fill="both")

        self.design_frame_0 = TextFrame(self.left_side, "Block Design")
        self.design_frame_0.grid(row=0, column=1, padx=0, pady=(0, 5), sticky="nsew")

        self.design_frame_1 = ImageFrame(self.left_side, "")
        self.design_frame_1.grid(row=1, column=1, padx=0, pady=0, sticky="nsew")
        self.design_frame_1.grid_propagate(False)

        self.frame_width = 400 if self.display_half else 600
        self.frame_height = 400 if self.display_half else 600

        self.image_label = customtkinter.CTkLabel(master=self.design_frame_1, text='')
        self.image_label.pack(expand=True, fill="both")

        if not self.hide_camera:
            self.content_container.grid_columnconfigure(1, weight=3)
            self.video_frame_1 = ImageFrame(self.content_container, "")
            self.video_frame_1.grid(row=0, column=1, padx=10, pady=(40, 10), sticky="nsew")
            self.video_frame_1.grid_propagate(False)
            self.video_frame_1.grid_rowconfigure(0, weight=1)
            self.video_frame_1.grid_columnconfigure(0, weight=1)
            self.camera = customtkinter.CTkLabel(self.video_frame_1, text="", anchor="center")
            self.camera.grid(row=0, column=0, sticky="nsew")
        else:
            self.camera = None

        self.button_0 = customtkinter.CTkButton(self.top_container, text="(START)", font=("Helvetica", 30), command=self.button_0_callback)
        self.button_0.grid(row=1 if self.display_half else 2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        self.bind('<Return>', self.skip_current_level)

    def setup_ai_models(self):
        pass 
        # TODO: Move YOLO initialization here from vision.blocks

    def preload_level_images(self):
        for level in range(1, 9):
            for variant in ['a', 'b', 'c', 'd']:
                key = f"{level}{variant}"
                path = os.path.join(self.base_dir, 'assets', 'images', 'FILES', 'TEST_RANDOM_1500x1500', f'Lvl {key}.png')
                if os.path.exists(path):
                    img = Image.open(path)
                    self.cached_level_images[key] = img.resize((self.frame_width, self.frame_height), Image.Resampling.LANCZOS)

    def get_random_variant(self, level):
        variants = ['a', 'b', 'c', 'd']
        return f"{level}{random.choice(variants)}"

    def button_0_callback(self):
        self.button_0.grid_remove()
        self.show_current_level_button()
        play_audio(os.path.join(self.base_dir, 'assets', 'audio', 'hitung_mundur.wav'))
        self.setup_next_level_state()
        self.streaming()

    def show_current_level_button(self):
        self.current_level_button = customtkinter.CTkButton(self.top_container, text=f"Level {self.current_question}", font=("Helvetica", 30))
        self.current_level_button.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

    def show_retry_button(self):
        self.retry_button = customtkinter.CTkButton(self.top_container, text="Retry Test", font=("Helvetica", 30), command=self.destroy)
        self.retry_button.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

    def update_timer(self):
        if self.timer_running:
            elapsed = time.time() - self.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            milliseconds = int((elapsed % 1) * 100)
            self.timer_label.configure(text=f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}")
            self.after(50, self.update_timer) 

    def start_timer(self):
        if not self.timer_running:
            self.start_time = time.time()
            self.timer_running = True
            self.update_timer()

    def reset_timer(self):
        self.timer_label.configure(text="00:00.00")
        self.timer_running = False

    def load_level_image(self, variant):
        if variant in self.cached_level_images:
            self.image = customtkinter.CTkImage(light_image=self.cached_level_images[variant], size=(self.frame_width, self.frame_height))
            self.image_label.configure(image=self.image)
            
            if self.button_mode:
                self.image_visible = True
                self.image_show_time = time.time()

    def handle_button_mode(self):
        if not self.button_mode:
            return
        
        if self.image_visible and self.image_show_time:
            if time.time() - self.image_show_time >= self.image_display_duration:
                blank_image = Image.new('RGB', (self.frame_width, self.frame_height), color='gray')
                self.image = customtkinter.CTkImage(light_image=blank_image, size=(self.frame_width, self.frame_height))
                self.image_label.configure(image=self.image)
                self.image_visible = False
                self.image_show_time = None
        
        if self.serial_thread:
            message = self.serial_thread.get_message()
            if message == "disable_image" and not self.image_visible:
                self.load_level_image(self.current_variant)

    def setup_next_level_state(self):
        variant = self.get_random_variant(self.current_question)
        self.current_variant = variant
        self.load_level_image(variant)
        if hasattr(self, 'current_level_button'):
            self.current_level_button.configure(text=f"Level {self.current_question}")
        self.start_task = time.time()
        self.reset_timer()
        self.start_timer()

    def process_level_completion(self, current_time):
        if not self.task_flags.get(self.current_question, False):
            return

        time_elapsed = round((current_time - self.start_task), 2)
        self.timer_task_all.append(time_elapsed)
        self.cognitive_age_list.append(estimate_cognitive_age(time_elapsed))
        self.task_flags[self.current_question] = False
        
        play_feedback_audio(time_elapsed)

        if self.current_question == self.max_level:
            self.end_test()
        else:
            audio_path = os.path.join(self.base_dir, 'assets', 'audio', f'lanjut_lvl{self.current_question + 1}.wav')
            if os.path.exists(audio_path):
                play_audio(audio_path)
                
            self.current_question += 1
            self.setup_next_level_state()

    def skip_current_level(self, event=None):
        if not self.timer_running:
            return
        self.process_level_completion(time.time())

    def end_test(self):
        self.reset_timer()
        self.current_level_button.grid_remove()
        
        avg_time = sum(self.timer_task_all) / len(self.timer_task_all) if self.timer_task_all else 0
        age_cog = int(sum(self.cognitive_age_list) / len(self.cognitive_age_list)) if self.cognitive_age_list else self.age_range_code
        visuo_spatial = 100 if age_cog <= self.age_range_code else 100 - (age_cog - self.age_range_code)

        play_audio(os.path.join(self.base_dir, 'assets', 'audio', 'selesai.wav'))
        time.sleep(3)

        send_game_session(
            user_data={"name": self.nick_name, "age": self.age_range_code, "gender": self.gender_code},
            task_times=self.timer_task_all,
            cognitive_age=age_cog,
            visuo_spatial_fit=visuo_spatial
        )

        end_img_path = os.path.join(self.base_dir, 'assets', 'images', 'FILES', 'TEST_1000x1000', '09.jpg')
        if os.path.exists(end_img_path):
            self.image = customtkinter.CTkImage(light_image=Image.open(end_img_path), size=(self.frame_width, self.frame_height))
            self.image_label.configure(image=self.image)
        self.show_retry_button()

    def streaming(self):
        self.button_0.configure(state="disabled")
        
        # TODO: Frame fetching and YOLO evaluation loop goes here
        # When YOLO confirms arrangement matches self.level_answers[self.current_variant]:
        #     self.process_level_completion(time.time())
        
        self.after(10, self.streaming)

    def cleanup(self):
        if self.serial_thread:
            self.serial_thread.stop()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def destroy(self):
        self.cleanup()
        super().destroy()