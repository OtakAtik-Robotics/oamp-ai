class YOLODetectionThread(threading.Thread):
    """Background thread for YOLO inference to prevent GUI blocking"""
    def __init__(self, model, use_bantal_model):
        super().__init__(daemon=True)
        self.model = model
        self.use_bantal_model = use_bantal_model
        self.frame_queue = Queue(maxsize=1)  # Reduce to 1 for less memory
        self.result_queue = Queue(maxsize=1)
        self.running = True
        self.inference_count = 0
        self.last_inference_time = 0
        print(">>> YOLO thread initialized")
        
    def run(self):
        print(">>> YOLO thread started")
        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get(timeout=0.01)
                    
                    # Measure inference time
                    start_time = time.time()
                    
                    # YOLO inference
                    if self.use_bantal_model:
                        results = self.model(frame, verbose=False)
                        
                        # Convert Ultralytics results to list format
                        if len(results) > 0 and hasattr(results[0], 'boxes'):
                            boxes = results[0].boxes
                            detections = []
                            
                            for box in boxes:
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                conf = box.conf[0].cpu().numpy()
                                cls = int(box.cls[0].cpu().numpy())
                                detections.append([x1, y1, x2, y2, conf, cls, ''])
                            
                            list_tracked_objects = detections
                        else:
                            list_tracked_objects = []
                    else:
                        results = self.model(frame)
                        df_tracked_objects = results.pandas().xyxy[0]
                        list_tracked_objects = df_tracked_objects.values.tolist()
                    
                    self.last_inference_time = (time.time() - start_time) * 1000
                    self.inference_count += 1
                    
                    # Debug output every 30 inferences
                    if self.inference_count % 30 == 0:
                        print(f">>> YOLO: {self.inference_count} inferences, last: {self.last_inference_time:.1f}ms")
                    
                    # Put results in queue (remove old if full)
                    if self.result_queue.full():
                        try:
                            self.result_queue.get_nowait()
                        except:
                            pass
                    self.result_queue.put(list_tracked_objects)
                else:
                    time.sleep(0.001)
            except Exception as e:
                print(f"YOLO thread error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.01)
    
    def stop(self):
        self.running = False
        print(">>> YOLO thread stopped")