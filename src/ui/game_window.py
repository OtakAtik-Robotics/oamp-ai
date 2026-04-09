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
from src.vision.hands import HandTracker
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
        self.cap = cv2.VideoCapture(1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.hand_tracker = HandTracker()
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        use_bantal = os.getenv('MODEL_BANTAL', 'false').lower() == 'true'
        model_yolo = None
        
        if use_bantal:
            path_model = os.path.join(self.base_dir, 'models', 'weights', 'bantal.pt')
            try:
                from ultralytics import YOLO
                model_yolo = YOLO(path_model)
                model_yolo.to(device)
            except Exception:
                use_bantal = False
                
        if not use_bantal:
            path_model = os.path.join(self.base_dir, 'models', 'weights', 'best.pt')
            try:
                model_yolo = torch.hub.load(
                    os.path.join(self.base_dir, 'models', 'yolov5'),
                    'custom',
                    path=path_model,
                    force_reload=True,
                    source='local'
                )
                model_yolo.to(device)
            except Exception:
                pass

        if model_yolo is not None:
            self.yolo_thread = YOLODetectionThread(model_yolo, use_bantal)
            self.yolo_thread.start()
        else:
            self.yolo_thread = None
            
        self.yolo_skip_frames = int(os.getenv('YOLO_SKIP_FRAMES', '2'))
        self.mediapipe_skip_frames = int(os.getenv('MEDIAPIPE_SKIP_FRAMES', '2'))

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
        
        if hasattr(self, 'cap') and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            if ret and not self.hide_camera and self.camera is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                if self.frame_count % (self.mediapipe_skip_frames + 1) == 0:
                    frame_rgb, landmarks = self.hand_tracker.process_and_draw(frame_rgb)
                
                imgBlur = cv2.GaussianBlur(frame_rgb, (7,7), 1)
                imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_RGB2GRAY)
                _, imgThres = cv2.threshold(imgGray, 175, 255, cv2.THRESH_BINARY)

                if self.yolo_thread is not None:
                    if self.frame_count % (self.yolo_skip_frames + 1) == 0:
                        if self.yolo_thread.frame_queue.empty():
                            try:
                                self.yolo_thread.frame_queue.put_nowait(np.array(frame, copy=True))
                            except:
                                pass
                                
                    if not self.yolo_thread.result_queue.empty():
                        try:
                            self.latest_detections = self.yolo_thread.result_queue.get_nowait()
                        except:
                            pass

                    box_design = []
                    box_distance = []
                    pos_x = []
                    pos_y = []

                    for x1, y1, x2, y2, conf_pred, cls_id, cls in self.latest_detections:
                        if conf_pred > 0.7:
                            center_x = int((x1+x2)/2)
                            center_y = int((y1+y2)/2)
                            x1, x2, y1, y2 = int(x1), int(x2), int(y1), int(y2)
                            
                            box_distance.append(int(math.sqrt(pow(center_x, 2) + pow(center_y, 2))))
                            pos_x.append(center_x)
                            pos_y.append(center_y)
                            
                            if y1 >= 0 and y2 <= imgThres.shape[0] and x1 >= 0 and x2 <= imgThres.shape[1] and (y2-y1) > 0 and (x2-x1) > 0:
                                dim = (100, 100)
                                imgBox = cv2.resize(imgThres[y1:y2, x1:x2], dim, interpolation=cv2.INTER_AREA)
                                box_class = [imgBox[50,25], imgBox[75,50], imgBox[50,75], imgBox[25,50]]
                                
                                box_face = 0
                                if box_class == [0,0,0,0]: box_face = 1
                                elif box_class == [255,255,255,255]: box_face = 2
                                elif box_class == [255,255,0,0]: box_face = 3
                                elif box_class == [255,0,0,255]: box_face = 4
                                elif box_class == [0,0,255,255]: box_face = 5
                                elif box_class == [0,255,255,0]: box_face = 6
                                
                                if box_face > 0:
                                    box_design.append(box_face)
                                    cv2.rectangle(frame_rgb, (x1,y1), (x2, y2), (0, 255, 0), 2)

                    if len(box_design) == 4 and len(box_distance) == 4:
                        pts = np.array([[pos_x[i], pos_y[i]] for i in range(4)], np.int32)
                        for i in range(4):
                            for j in range(i+1, 4):
                                cv2.line(frame_rgb, tuple(pts[i]), tuple(pts[j]), (0, 0, 0), 2)
                                
                        len_rect = sorted([
                            int(math.sqrt((pos_x[0]-pos_x[1])**2 + (pos_y[0]-pos_y[1])**2)),
                            int(math.sqrt((pos_x[1]-pos_x[2])**2 + (pos_y[1]-pos_y[2])**2)),
                            int(math.sqrt((pos_x[2]-pos_x[3])**2 + (pos_y[2]-pos_y[3])**2)),
                            int(math.sqrt((pos_x[3]-pos_x[0])**2 + (pos_y[3]-pos_y[0])**2)),
                            int(math.sqrt((pos_x[0]-pos_x[2])**2 + (pos_y[0]-pos_y[2])**2)),
                            int(math.sqrt((pos_x[1]-pos_x[3])**2 + (pos_y[1]-pos_y[3])**2))
                        ])
                        
                        if all(abs(len_rect[0] - len_rect[i]) < 100 for i in range(1, 4)) and \
                           all(abs(len_rect[1] - len_rect[i]) < 100 for i in range(2, 4)) and \
                           abs(len_rect[2] - len_rect[3]) < 100:
                           
                            indexed_positions = [(pos_x[i], pos_y[i], i) for i in range(4)]
                            sorted_by_x = sorted(pos_x)
                            mid_point = (sorted_by_x[1] + sorted_by_x[2]) / 2 
                            indexed_positions.sort(key=lambda p: (p[0] >= mid_point, p[1]))
                            sort_index = [idx for (x, y, idx) in indexed_positions]
                            box_design_sort = [box_design[i] for i in sort_index]
                            
                            current_answer = self.level_answers.get(self.current_variant, [])
                            if box_design_sort == current_answer:
                                self.process_level_completion(time.time())

                img = Image.fromarray(frame_rgb)
                container_width = self.video_frame_1.winfo_width()
                container_height = self.video_frame_1.winfo_height()
                
                if container_width > 10 and container_height > 10:
                    frame_height, frame_width = frame.shape[:2]
                    width_ratio = container_width / frame_width
                    height_ratio = container_height / frame_height
                    scale = min(width_ratio, height_ratio)
                    
                    if scale < 1:
                        new_width = int(frame_width * scale)
                        new_height = int(frame_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                ImgTks = ImageTk.PhotoImage(image=img)
                self.camera.imgtk = ImgTks
                self.camera.configure(image=ImgTks)

        self.frame_count += 1
        self.after(10, self.streaming)

    def cleanup(self):
        if self.serial_thread:
            self.serial_thread.stop()
        if hasattr(self, 'hand_tracker'):
            self.hand_tracker.close()
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'yolo_thread') and self.yolo_thread:
            self.yolo_thread.stop()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def destroy(self):
        self.cleanup()
        super().destroy()