import os
import requests
import json
from datetime import datetime

BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8080/api/v1")

def send_game_session(user_data, task_times, cognitive_age, visuo_spatial_fit):
    endpoint = f"{BASE_URL}/sessions"
    
    payload = {
        "session": {
            "ParticipantID": 1,
            "Mode": "1_PLAYER",
            "LevelReached": len(task_times),
            "TotalTime": sum(task_times) if task_times else 0,
            "CognitiveAge": cognitive_age,
            "VisuoSpatialFit": visuo_spatial_fit,
            "GripStrength": 0.0,
            "DexterityScore": 0.0
        },
        "expressions": [],
        "datasets": []
    }

    try:
        print(f">>> Sending data to API: {endpoint}")
        response = requests.post(endpoint, json=payload, timeout=5)
        
        if response.status_code in [200, 201]:
            print(">>> Data successfully sent to Server")
            return True
        else:
            print(f">>> Failed to send data. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f">>> API connection error: {e}")
        print("Ensure the Golang server is running")
        return False